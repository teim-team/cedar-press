#!/usr/bin/env python3
"""
92_build_gaming_capacity_official.py -- Cedar Press.

WHY THIS EXISTS
---------------
`data/clean/gaming_property_capacity_history.csv` holds 64,181 dated
observations across 10 metrics for 409 properties. Every single one carries

    source      = "Casino City Press gaming-property panel (tribal_casino_panel.dta)"
    value_basis = "reported"

One vendor. Zero independent observations. Two separate problems follow:

  1. EVIDENTIARY. The vendor does not disclose its method, so a subscriber
     cannot audit a single number in the file.
  2. COMMERCIAL. It is a third party's property. Per Elijah, 2026-08-06, it is
     an INTERNAL FACT-CHECKING LAYER and never publishes -- the same rule the
     project already applies to DUNS. `code/87_build_dataset_notes.py` enforces
     it: both vendor files sit in LICENSED_SOURCE_FILES and get no notes
     contract, so they cannot ship by accident.

This script builds the layer that DOES ship: `gaming_capacity_official.csv`,
same metric grammar as the vendor file so the two compare row for row, but
sourced from regulators and primary documents.

WHAT "OFFICIAL" MEANS HERE, AND WHAT IT DOES NOT
------------------------------------------------
Three measurement statuses, never pooled:

  reported_measurement   A regulator or the operator states a COUNT of things
                         that exist. AZ Dept of Gaming's per-casino device
                         table; CT DCP's weighted average machine count.
  reported_revenue       A regulator publishes actual revenue. Not an estimate,
                         so the project's no-estimation rule does not block it.
  authorization          A compact or regulator states a CEILING. This is what
                         a tribe MAY operate, never what it DOES. Metric names
                         carry `_authorized_max` so the distinction survives any
                         downstream filter, join or chart.
  proposed               An environmental review describes a facility that was
                         evaluated. A project evaluated is not a project built.

Conflating any two of these produces a file that looks richer and is wrong.

NAME RESOLUTION
---------------
Tribe names go through `resolve_entity` imported from
`code/33_apply_party_rulings.py`. No second matcher is written here -- that is
a standing project rule and AGENTS.md documents five separate money-losing
failures from home-grown containment matching on 2026-08-06 alone.

`resolve_entity` maps names to the ENTITY spine. It has no facility layer, so
facility resolution is done by EXACT normalised name within state, plus
`facility_alias_rulings.csv` if present. Anything that does not resolve exactly
is STAGED to review/, never guessed. AGENTS.md's containment defect is the
reason: `Chickasaw Nation` -> `Chickasaw Children's Village` carried $2.8B onto
a school. A gaming file has the same trap in abundance -- one tribe routinely
runs `Choctaw Casino Durant`, `Choctaw Casino Pocola`, `Choctaw Travel Plaza -
Atoka` and a dozen more, and a fuzzy match between any two of them is a false
attribution of a specific number to a specific building.

READS
-----
  data/interim/compact_authorizations.csv                    (script 91)
  data/raw/external/gaming_official/ct_dcp_slot_*.csv        (CT DCP, Socrata)
  data/raw/external/gaming_official/agent_*_2026-*.csv       (agent evidence)
  data/clean/gaming_properties.csv                           (facility spine)
  data/clean/compacts.csv, compact_versions.csv
  data/spine/cedar_entity_spine.csv

WRITES
------
  data/clean/gaming_capacity_official.csv
  review/gaming_capacity_official_unresolved_<date>.csv
  review/gaming_capacity_vendor_vs_official_<date>.csv

TOUCHES NOTHING ELSE. gaming_facilities.csv, nigc_*, admin_region*, resource_*,
gaming_source_claims.csv and series_breaks.csv belong to other agents and are
not opened for writing anywhere in this file.
"""
import csv, os, re, sys, collections, importlib.util
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
INT = CEDAR / "data" / "interim"
RAW = CEDAR / "data" / "raw" / "external" / "gaming_official"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = "2026-08-07"

# ------------------------------------------------------------------ resolver
# Import the ONE resolver. AGENTS.md: "code/33_apply_party_rulings.py holds the
# ONE resolver. Import resolve_entity; never write another name matcher."
_spec = importlib.util.spec_from_file_location(
    "party_rulings", str(CEDAR / "code" / "33_apply_party_rulings.py"))
_pr = importlib.util.module_from_spec(_spec)
sys.modules["party_rulings"] = _pr
_spec.loader.exec_module(_pr)
resolve_entity = _pr.resolve_entity
norm = _pr.norm

# The domain vocabulary is imported, never restated. `may_promote` is the guard
# that makes measurement_status load-bearing rather than decorative: an
# AUTHORIZED_MAXIMUM or a PROJECTED figure can never become an
# ACTIVE_FLOOR_COUNT by relabelling. Asserted at import, so a future edit to
# cedar_domain that weakened the guard would fail this build loudly instead of
# quietly letting a compact device cap publish as a device count.
_dspec = importlib.util.spec_from_file_location(
    "cedar_domain", str(CEDAR / "code" / "cedar_domain.py"))
_cd = importlib.util.module_from_spec(_dspec)
sys.modules["cedar_domain"] = _cd
_dspec.loader.exec_module(_cd)
MeasurementType, may_promote, NAME_TRAPS = (
    _cd.MeasurementType, _cd.may_promote, _cd.NAME_TRAPS)
for _bad in (MeasurementType.AUTHORIZED_MAXIMUM, MeasurementType.PROJECTED,
             MeasurementType.ENVIRONMENTAL_REVIEW_COUNT):
    assert not may_promote(_bad, MeasurementType.ACTIVE_FLOOR_COUNT), _bad

# measurement_status (this file's vocabulary, kept for continuity) -> the typed
# cedar_domain MeasurementType that governs what may be done with the row.
MEASUREMENT_TYPE = {
    "reported_measurement": MeasurementType.REGULATORY_REPORTED_COUNT,
    "reported_revenue": MeasurementType.REGULATORY_REPORTED_COUNT,
    "reported_payment": MeasurementType.REGULATORY_REPORTED_COUNT,
    "exact_derived_revenue": MeasurementType.COMPACT_REPORTED_COUNT,
    "authorization": MeasurementType.AUTHORIZED_MAXIMUM,
    "proposed": MeasurementType.PROJECTED,
    "audited_filing_measurement": MeasurementType.PROPERTY_REPORTED_COUNT,
}


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


# ------------------------------------------------------------------ schema
COLS = [
    "observation_id",
    "facility_id", "facility_name", "tribe_id", "tribe_canonical_name",
    "facility_name_as_published", "tribe_name_as_published", "state",
    "metric", "metric_class", "measurement_status", "measurement_type",
    "value", "unit",
    "qualifier", "applies_to", "proposed_vs_actual",
    "as_of_date", "as_of_date_precision", "period_start", "period_end",
    "source_authority", "source_document_type", "source_url", "source_page",
    "source_quote",
    "facility_match_method", "tribe_match_method", "corroborating_sources",
    "exclusion_flag", "exclusion_reason",
    "fetched_date", "built_date",
]

# Which metric names belong to which class. A metric that is not in this table
# is refused rather than published under a guessed class.
METRIC_CLASS = {
    # counts of things that exist
    "gaming_machines": "capacity_measurement",
    "class_ii_gaming_machines": "capacity_measurement",
    "class_iii_gaming_machines": "capacity_measurement",
    "table_games": "capacity_measurement",
    "poker_tables": "capacity_measurement",
    "bingo_seats": "capacity_measurement",
    "hotel_rooms": "capacity_measurement",
    "gaming_square_feet": "capacity_measurement",
    "total_square_feet": "capacity_measurement",
    "parking_spaces": "capacity_measurement",
    "employees": "capacity_measurement",
    "restaurant_seats": "capacity_measurement",
    "meeting_square_feet": "capacity_measurement",
    "acres": "capacity_measurement",
    "construction_cost": "capacity_measurement",
    "water_demand": "capacity_measurement",
    "wastewater_demand": "capacity_measurement",
    "hotel_occupancy_rate": "capacity_measurement",
    # Added after the vocabulary refused them on the first NEPA run. Both are
    # genuine environmental-review capacity facts and both are things a casino
    # directory does not carry: `gaming_positions` (seats at devices and tables,
    # the measure NEPA traffic and water analyses actually use) and `cabins`.
    "gaming_positions": "capacity_measurement",
    "cabins": "capacity_measurement",
    "blackjack_tables": "capacity_measurement",
    "house_banked_poker_tables": "capacity_measurement",
    "keno_games": "capacity_measurement",
    "event_wagering_kiosks": "capacity_measurement",
    "event_wagering_otc": "capacity_measurement",
    "dcetg": "capacity_measurement",
    "baccarat_tables": "capacity_measurement",
    "craps_tables": "capacity_measurement",
    "roulette_tables": "capacity_measurement",
    "baccarat_craps_roulette_tables": "capacity_measurement",
    # ceilings
    "gaming_machines_authorized_max": "authorization",
    "table_games_authorized_max": "authorization",
    "gaming_facilities_authorized_max": "authorization",
    "wager_limit_max": "authorization",
    "minimum_gambling_age": "operating_rule",
    # money
    "net_win": "revenue",
    "gross_gaming_revenue": "revenue",
    "handle": "revenue",
    "payment_to_state": "payment",
    # Michigan remits to TWO different payees under the same compacts, both per
    # tribe per year. One metric name for both would silently stack two
    # unrelated obligations into a single series, so they stay separate.
    "payment_to_local_government": "payment",
    "revenue_share_distribution": "payment",
}

STATUS_BY_CLASS = {
    "capacity_measurement": "reported_measurement",
    "authorization": "authorization",
    "operating_rule": "authorization",
    "revenue": "reported_revenue",
    "payment": "reported_payment",
}

STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Florida": "FL", "Idaho": "ID",
    "Iowa": "IA", "Kansas": "KS", "Louisiana": "LA", "Michigan": "MI",
    "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Mexico": "NM", "New York": "NY",
    "North Carolina": "NC", "North Dakota": "ND", "Oklahoma": "OK",
    "Oregon": "OR", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Texas": "TX", "Washington": "WA",
    "Wisconsin": "WI", "Wyoming": "WY",
}


def st(s):
    s = (s or "").strip()
    if len(s) == 2:
        return s.upper()
    return STATE_ABBR.get(s, s[:2].upper() if s else "")


# ---------------------------------------------------- facility name matching
FACILITY_NOISE = re.compile(
    r"\b(casino|resort|hotel|and|the|of|at|inc|llc|spa|lodge|club|center|centre)\b")


def fkey(name):
    """EXACT normalised key. Deliberately weak: it folds case, punctuation and
    whitespace and NOTHING else. It does not drop tokens, because dropping
    `casino` is what made `Choctaw Casino Atoka` score identical to
    `Choctaw Travel Plaza - Atoka` in the duplicate queue (see
    docs/GAMING_TEMPORAL_BUILD_LOG.md 7.5). A weak key that abstains is the
    correct instrument here; the strong key belongs in a review queue with a
    human on the other end."""
    return norm(name)


def build_facility_index(props):
    """(state, exact-normalised-name) -> [facility rows]. Collisions are kept as
    lists so an ambiguous name can be REFUSED rather than silently taking the
    first."""
    idx = collections.defaultdict(list)
    for p in props:
        k = (st(p.get("state", "")), fkey(p.get("facility_name", "")))
        if k[1]:
            idx[k].append(p)
    return idx


def main():
    print("=" * 78)
    print("92: gaming_capacity_official -- the layer that ships")
    print("=" * 78)

    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    props = read_csv(CLEAN / "gaming_properties.csv")
    compacts = {r["compact_id"]: r for r in read_csv(CLEAN / "compacts.csv")}
    versions = {r["version_id"]: r for r in read_csv(CLEAN / "compact_versions.csv")}
    print(f"  spine {len(spine):,} entities | properties {len(props):,} | "
          f"compacts {len(compacts):,} | compact versions {len(versions):,}")

    fidx = build_facility_index(props)
    props_by_tribe = collections.defaultdict(list)
    for p in props:
        if p.get("tribe_id"):
            props_by_tribe[p["tribe_id"]].append(p)

    _tribe_cache = {}
    _class_by_id = {r["tribe_id"]: r.get("entity_class", "") for r in spine}
    _name_by_id = {r["tribe_id"]: r.get("canonical_name", "") for r in spine}

    # A gaming regulator's device count, casino payment or compact ceiling is
    # NEVER about a college, a school, a clinic or a lender. These classes exist
    # in the spine and `resolve_entity`'s containment tier reaches them.
    #
    # MEASURED, this build: the Michigan Gaming Control Board's per-tribe
    # payment table names "Keweenaw Bay Indian Community". `resolve_entity`
    # returned `TCU-KWNWB1-00 Keweenaw Bay Ojibwa Community College` by
    # containment, and TEN payment observations were attributed to a tribal
    # college. The spine holds the correct entity two rows away
    # (`TRBF-KWNWBY-00 Keweenaw`, Federally recognized tribe, MI).
    #
    # This is AGENTS.md's `Chickasaw Nation -> Chickasaw Children's Village`
    # defect, which moved $2.8B onto a school, reproduced exactly.
    #
    # No second matcher is written -- that is a standing project rule and this
    # build imports the one resolver. What is added is a REFUSAL: a class the
    # source cannot be talking about is rejected and queued for a ruling. A
    # guard that refuses is not a matcher that guesses.
    REFUSED_CLASSES = {
        "Tribal College or University", "BIE School", "Urban Indian Organization",
        "Native Community Development Financial Institution",
        "Native Financial Institution",
    }
    class_refusals = collections.Counter()

    def tribe(name):
        if not name:
            return None, None, "no_name_given"
        if name not in _tribe_cache:
            tid, tname, meth = resolve_entity(name, spine)
            cls = _class_by_id.get(tid or "", "")
            if tid and cls in REFUSED_CLASSES:
                class_refusals[(name, tname, cls)] += 1
                tid, tname, meth = None, None, (
                    f"refused_entity_class:{cls.replace(' ', '_')}"
                    f"->{(tname or '')[:40]}")
            _tribe_cache[name] = (tid, tname, meth)
        return _tribe_cache[name]

    rows = []
    unresolved = []
    implausible = []
    seq = collections.Counter()

    # Plausibility gates on COUNT metrics. These do not delete and do not
    # correct -- the source value is the evidence and it stays. They set
    # `exclusion_flag` so a single number that is almost certainly a typo in the
    # underlying federal document cannot quietly become the largest value in a
    # chart.
    #
    # The live case: the Oneida Indian Nation Record of Decision genuinely
    # prints "1000 table games" for Turning Stone (verified against the rendered
    # page, not just the text layer). That is almost certainly a federal typo
    # for 100. It is retained, quoted, and flagged -- which is the same
    # treatment `open_date_postdates_observation` gives a contradictory vendor
    # date in GAMING_TEMPORAL_BUILD_LOG.md 2.
    PLAUSIBLE = {
        "table_games": (0, 400),
        "poker_tables": (0, 200),
        "gaming_machines": (0, 10000),
        "class_iii_gaming_machines": (0, 10000),
        "hotel_rooms": (0, 2500),
        "bingo_seats": (0, 5000),
    }

    def emit(**k):
        metric = k.get("metric", "")
        cls = METRIC_CLASS.get(metric)
        if cls is None:
            unresolved.append(dict(
                reason="metric_not_in_vocabulary", metric=metric,
                facility_name_as_published=k.get("facility_name_as_published", ""),
                tribe_name_as_published=k.get("tribe_name_as_published", ""),
                state=k.get("state", ""), value=k.get("value", ""),
                source_url=k.get("source_url", ""),
                source_quote=(k.get("source_quote", "") or "")[:400],
                YOUR_RULING=""))
            return
        src = k.get("source_layer", "X")
        seq[src] += 1
        k["observation_id"] = f"GCO-{src}-{seq[src]:05d}"
        k["metric_class"] = cls
        k.setdefault("measurement_status", STATUS_BY_CLASS[cls])
        mt = MEASUREMENT_TYPE.get(k["measurement_status"])
        if mt is None:
            unresolved.append(dict(
                reason="measurement_status_not_in_cedar_domain",
                metric=metric, value=k.get("value", ""),
                state=k.get("state", ""),
                source_url=k.get("source_url", ""),
                source_quote=(k.get("source_quote", "") or "")[:400],
                YOUR_RULING=""))
            return
        k["measurement_type"] = mt.value
        if metric in PLAUSIBLE:
            try:
                fv = float(k.get("value", ""))
                lo, hi = PLAUSIBLE[metric]
                if not (lo <= fv <= hi):
                    implausible.append((metric, fv, k.get("source_url", "")))
                    k["exclusion_flag"] = "1"
                    k["exclusion_reason"] = (
                        (k.get("exclusion_reason", "") + " | " if k.get("exclusion_reason") else "")
                        + f"value {fv:g} is outside the plausible range [{lo}, {hi}] for "
                          f"{metric}; retained and quoted as the source states it, but "
                          f"flagged as a probable error IN THE SOURCE DOCUMENT. Do not "
                          f"publish without a second source.")
            except (TypeError, ValueError):
                pass
        k["built_date"] = TODAY
        rows.append({c: k.get(c, "") for c in COLS})

    def stage(reason, **k):
        k["reason"] = reason
        k["YOUR_RULING"] = ""
        unresolved.append(k)

    def candidates_for(tribe_id, state, limit=12):
        """The tribe's properties in that state, as CANDIDATES for a human.

        This is the `23g_gaming_duplicate_candidates.py` pattern and it exists
        for the same reason: the matching rules forbid the automated leap that
        is tempting here, but a queue row that merely says "unresolved" wastes
        the evidence. Arizona is the live case -- ADG publishes
        `Gila River - Lone Butte` and `Desert Diamond - Sahuarita` while the
        Cedar spine holds those properties under different names, so 54 rows of
        genuine regulator device counts cannot land automatically. Listing the
        tribe's four Gila River properties beside the regulator's four names
        makes the ruling a two-minute job instead of a research task.

        It RULES NOTHING and MERGES NOTHING."""
        c = [p for p in props_by_tribe.get(tribe_id or "", [])
             if st(p.get("state", "")) == st(state)]
        return " | ".join(f"{p['facility_id']}={p['facility_name']}" for p in c[:limit])

    def resolve_facility(pubname, state, tribe_id, layer, ctx):
        """Return (facility_id, facility_name, method) or (None, None, reason).

        Order: exact name within state -> the tribe's SOLE property in that
        state -> refuse. There is no third tier, on purpose."""
        s = st(state)
        if pubname:
            hits = fidx.get((s, fkey(pubname)), [])
            if len(hits) == 1:
                return hits[0]["facility_id"], hits[0]["facility_name"], "exact_name_in_state"
            if len(hits) > 1:
                return None, None, f"ambiguous_exact_name:{len(hits)}_properties"
        if tribe_id:
            cands = [p for p in props_by_tribe.get(tribe_id, []) if st(p.get("state", "")) == s]
            if len(cands) == 1:
                return (cands[0]["facility_id"], cands[0]["facility_name"],
                        "sole_property_of_tribe_in_state")
            if len(cands) > 1:
                return None, None, f"tribe_has_{len(cands)}_properties_in_state"
        return None, None, "no_facility_match"

    # =====================================================================
    # LAYER 1 -- Connecticut DCP, monthly slot data for Foxwoods and Mohegan Sun
    # =====================================================================
    # This is the deepest single official series available anywhere in the
    # country: monthly, per property, back to January 1993. It carries a machine
    # COUNT as well as revenue, which is the part that matters most -- it is a
    # direct independent measurement of the vendor's core metric.
    #
    # `Weighted Average # of Machines` is the regulator's own column name. It is
    # an average over the month, NOT a point-in-time count, so period_start /
    # period_end carry the month and the precision column says `month`. Reading
    # it as an end-of-month count would be a small lie repeated 748 times.
    ct_files = sorted(RAW.glob("ct_dcp_slot_*.csv"))
    ct_rows = read_csv(ct_files[-1]) if ct_files else []
    CT_FACILITY = {
        # The DCP publishes the two properties under their trading names. Both
        # resolve exactly against the property spine, so no ruling is needed --
        # but the mapping is stated here rather than inferred at run time so a
        # reader can see exactly what was assumed.
        "Foxwoods": ("Foxwoods Resort Casino", "Mashantucket Pequot Tribe"),
        "Mohegan Sun": ("Mohegan Sun", "Mohegan Tribe"),
    }
    CT_METRICS = [
        ("Win (9)", "net_win", "usd", ""),
        # Published as `gaming_machines` so it compares row-for-row with the
        # vendor's metric of the same name -- but it is the regulator's
        # WEIGHTED MONTHLY AVERAGE, not an end-of-month count, and the qualifier
        # says so on every row. Silently treating an average as a point count
        # would be a small lie repeated 748 times.
        ("Weighted Average # of Machines", "gaming_machines", "machines",
         "monthly weighted average of machines in service, not a point-in-time count "
         "(regulator's own column name: 'Weighted Average # of Machines')"),
        ("Slot Machine Contributions to the State of Connecticut (1) (6)",
         "payment_to_state", "usd", ""),
        ("Handle", "handle", "usd", ""),
    ]
    ct_n = 0
    for r in ct_rows:
        cas = (r.get("Casino") or "").strip()
        if cas not in CT_FACILITY:
            stage("ct_unknown_casino_label", state="CT", tribe_name_as_published=cas,
                  source_url="https://data.ct.gov/d/i6ts-ib7c")
            continue
        pubname, tribename = CT_FACILITY[cas]
        d = (r.get("Date") or "").split(" ")[0]
        try:
            mm, dd, yy = d.split("/")
            month_end = f"{yy}-{mm}-{dd}"
            month_start = f"{yy}-{mm}-01"
        except ValueError:
            stage("ct_unparseable_date", state="CT", value=d,
                  source_url="https://data.ct.gov/d/i6ts-ib7c")
            continue
        tid, tname, tmeth = tribe(tribename)
        fid, fname, fmeth = resolve_facility(pubname, "CT", tid, "CT", cas)
        for col, metric, unit, qual in CT_METRICS:
            raw = (r.get(col) or "").strip()
            if not raw:
                continue
            try:
                val = float(raw.replace(",", "").replace("$", ""))
            except ValueError:
                continue
            if fid is None:
                stage("ct_facility_unresolved:" + fmeth, state="CT",
                      facility_name_as_published=pubname, metric=metric, value=val,
                      as_of_date=month_end, source_url="https://data.ct.gov/d/i6ts-ib7c")
                continue
            emit(source_layer="CT",
                 facility_id=fid, facility_name=fname,
                 tribe_id=tid or "", tribe_canonical_name=tname or "",
                 facility_name_as_published=cas, tribe_name_as_published=tribename,
                 state="CT", metric=metric, value=val, unit=unit, qualifier=qual,
                 as_of_date=month_end, as_of_date_precision="month",
                 period_start=month_start, period_end=month_end,
                 source_authority="Connecticut Department of Consumer Protection",
                 source_document_type="state_regulator_open_data",
                 source_url="https://data.ct.gov/d/i6ts-ib7c",
                 source_quote=(
                     f'Casino "{cas}", Date "{d}", Fiscal Year "{r.get("Fiscal Year","")}", '
                     f'"{col}" = {raw}'),
                 facility_match_method=fmeth, tribe_match_method=tmeth,
                 corroborating_sources="Connecticut Department of Consumer Protection",
                 fetched_date=TODAY)
            ct_n += 1
    print(f"  [CT] {ct_n:,} observations from {len(ct_rows):,} regulator months")

    # =====================================================================
    # LAYER 2 -- compact authorizations (script 91)
    # =====================================================================
    # A compact binds a TRIBE, not a building. Where the tribe has exactly one
    # property in that state the authorisation is attached to it; where it has
    # several the row is published at TRIBE level with facility_id blank, which
    # is the honest shape. A device ceiling silently split across four casinos
    # would be four fabricated numbers.
    auth = read_csv(INT / "compact_authorizations.csv")
    auth_n, auth_tribe_level = 0, 0
    for a in auth:
        if a.get("applies_to") == "statewide_pool_or_tier":
            # Genuine compact content, but it describes the STATE's licence pool
            # (California 1999), not this tribe's ceiling. Recorded in the
            # review queue so the fact is not lost, never published as the
            # tribe's own authorisation.
            stage("compact_statewide_pool_not_tribe_specific",
                  tribe_name_as_published=a.get("tribe", ""), state=a.get("state", ""),
                  metric=a.get("metric", ""), value=a.get("value", ""),
                  source_url=a.get("source_url", ""),
                  source_quote=(a.get("quote", "") or "")[:400])
            continue
        cid = a.get("compact_id", "")
        cm = compacts.get(cid, {})
        ver = versions.get(a.get("version_id", ""), {})
        tid = a.get("tribe_id") or cm.get("tribe_id") or ""
        tname = a.get("tribe_canonical_name") or cm.get("tribe_canonical_name") or ""
        tmeth = "inherited_from_compact_id"
        if not tid:
            tid, tname, tmeth = tribe(a.get("tribe", ""))
        state = a.get("state", "")
        if not tid and not state:
            # A compact authorisation with NEITHER a tribe NOR a state is
            # attached to nothing. Four such rows shipped in the 2026-08-06
            # build reading `Tribal-State Gaming Compact,  (approved by the
            # Secretary of the Interior)` with an empty state and an empty
            # tribe -- a device cap and two wager limits belonging to no one.
            # A well-formed row about nobody is worse than a queue item,
            # because it looks publishable.
            stage("compact_authorization_no_tribe_and_no_state",
                  metric=a.get("metric", ""), value=a.get("value", ""),
                  source_url=a.get("source_url", ""),
                  source_file=a.get("source_pdf", ""),
                  source_quote=(a.get("quote", "") or "")[:400])
            continue
        fid, fname, fmeth = resolve_facility("", state, tid, "CP", cid)
        if fid is None:
            fmeth = "tribe_level_authorization:" + fmeth
            auth_tribe_level += 1
        # The compact's own approval date is the as-of date. An authorisation
        # has no observation date of its own -- it takes effect when approved.
        aod = (ver.get("approval_date") or cm.get("original_effective_date") or "").strip()
        emit(source_layer="CP",
             facility_id=fid or "", facility_name=fname or "",
             tribe_id=tid, tribe_canonical_name=tname,
             facility_name_as_published="", tribe_name_as_published=a.get("tribe", ""),
             state=st(state), metric=a.get("metric", ""), value=a.get("value", ""),
             unit=a.get("unit", ""), qualifier=a.get("qualifier", ""),
             applies_to=a.get("applies_to", ""),
             as_of_date=aod, as_of_date_precision="day" if len(aod) == 10 else "year",
             period_start=aod, period_end=cm.get("term_end", ""),
             source_authority=(f"Tribal-State Gaming Compact, {state} "
                               f"(approved by the Secretary of the Interior)"),
             source_document_type="tribal_state_compact",
             source_url=a.get("source_url") or cm.get("source_url", ""),
             source_page=a.get("source_pdf", ""),
             source_quote=a.get("quote", ""),
             facility_match_method=fmeth, tribe_match_method=tmeth,
             corroborating_sources="Bureau of Indian Affairs compact index",
             exclusion_flag="1" if a.get("n_distinct_values_in_document", "1") not in ("", "1") else "",
             exclusion_reason=("document states more than one value for this metric: "
                               + a.get("other_values_in_document", ""))
                              if a.get("n_distinct_values_in_document", "1") not in ("", "1") else "",
             fetched_date=TODAY)
        auth_n += 1
    print(f"  [CP] {auth_n:,} compact authorizations "
          f"({auth_tribe_level:,} tribe-level, no single property)")

    # =====================================================================
    # LAYER 3 -- agent-collected regulator evidence
    # =====================================================================
    # Each agent wrote one evidence CSV in a fixed schema. They are ingested
    # generically so a later sweep drops in without touching this code.
    # ---- unit-driven de-conflation ------------------------------------------
    # MEASURED DEFECT, caught by the vendor comparison rather than by reading
    # the file: the Arizona evidence CSV maps FOUR distinct regulator columns
    # onto TWO metric names.
    #
    #   Class III devices        -> gaming_machines   (unit class_iii_gaming_devices)
    #   Class II devices         -> gaming_machines   (unit class_ii_gaming_devices)
    #   blackjack tables         -> table_games       (unit blackjack_tables)
    #   house-banked poker       -> table_games       (unit house_banked_poker_tables)
    #
    # The result is two rows for `Casino Del Sol / gaming_machines / 2026-07-01`
    # reading 1,035 and 9. Those are not disagreeing observations -- they are
    # different things wearing one name, and published that way they would read
    # as a contradiction to any user and double-count in any sum.
    #
    # The unit column already carries the truth, so the metric is derived FROM
    # the unit rather than trusted. Nothing is dropped and no value changes.
    UNIT_METRIC = {
        "class_iii_gaming_devices": "class_iii_gaming_machines",
        "class_ii_gaming_devices": "class_ii_gaming_machines",
        "blackjack_tables": "blackjack_tables",
        "house_banked_poker_tables": "house_banked_poker_tables",
    }

    # ---- supersession -------------------------------------------------------
    # `code/93_extract_az_gaming_status.py` re-extracts the Arizona Gaming Status
    # Report positionally and validates every column against the report's own
    # printed TOTALS row (all nine foot exactly). A survey agent had read the
    # same PDF linearly and dropped 20 of 26 Class II values, because the table's
    # text layer is ragged -- some rows omit the DCETG cell, so counting tokens
    # puts different columns in the same slot on different rows.
    #
    # Both files are kept on disk as evidence. Only the VERIFIED one is
    # ingested, keyed on the source URL so the rule is about the document rather
    # than about which agent happened to write which filename.
    SUPERSEDED_SOURCE_URLS = {
        "https://gaming.az.gov/sites/default/files/Gaming%20Status%20Report%2007012026_0.pdf",
    }

    agent_files = (sorted(RAW.glob("agent_*_2026-*.csv"))
                   + sorted(RAW.glob("az_adg_status_report_extracted_*.csv"))
                   + sorted(RAW.glob("mi_mgcb_revshare_extracted_*.csv"))
                   + sorted(RAW.glob("az_status_archive_extracted_*.csv")))
    ag_n = 0
    superseded_n = 0
    per_file = collections.Counter()
    deconflated = collections.Counter()
    # (facility_id, as_of_date) -> {component metric: value}, for the derived totals
    device_parts = collections.defaultdict(dict)
    table_parts = collections.defaultdict(dict)
    part_ctx = {}
    already_total = set()
    for af in agent_files:
        # Rosters and logs are not observations. `nepa` and `bond_sec` have
        # their own layers below and MUST be excluded here -- they match this
        # glob too, and ingesting them twice silently doubled every NEPA metric
        # on the first run.
        if any(x in af.name for x in ("roster", "document_log", "nepa", "bond_sec")):
            continue
        for r in read_csv(af):
            metric = (r.get("metric") or "").strip()
            valraw = (r.get("value") or "").strip()
            if not metric or not valraw:
                continue
            try:
                val = float(valraw.replace(",", "").replace("$", "").replace("%", ""))
            except ValueError:
                stage("agent_unparseable_value", source_file=af.name, metric=metric,
                      value=valraw, source_url=r.get("source_url", ""),
                      facility_name_as_published=r.get("facility_name_as_published", ""),
                      tribe_name_as_published=r.get("tribe_name_as_published", ""))
                continue
            if (af.name.startswith("agent_")
                    and (r.get("source_url") or "").strip() in SUPERSEDED_SOURCE_URLS):
                superseded_n += 1
                continue
            unit_in = (r.get("unit") or "").strip()
            if unit_in in UNIT_METRIC and UNIT_METRIC[unit_in] != metric:
                deconflated[(metric, unit_in, UNIT_METRIC[unit_in])] += 1
                metric = UNIT_METRIC[unit_in]
            if not (r.get("source_url") or "").strip() or not (r.get("source_quote") or "").strip():
                # The prime directive, enforced mechanically rather than trusted.
                stage("agent_row_missing_url_or_quote", source_file=af.name,
                      metric=metric, value=valraw,
                      facility_name_as_published=r.get("facility_name_as_published", ""),
                      tribe_name_as_published=r.get("tribe_name_as_published", ""))
                continue
            state = r.get("state", "")
            tid, tname, tmeth = tribe(r.get("tribe_name_as_published", ""))
            if tid is None and tmeth in ("no_spine_match",) or (
                    tmeth or "").startswith("refused_entity_class:"):
                stage("agent_tribe_unresolved:" + (tmeth or ""),
                      source_file=af.name, state=state, metric=metric,
                      value=valraw,
                      tribe_name_as_published=r.get("tribe_name_as_published", ""),
                      source_url=r.get("source_url", ""),
                      source_quote=(r.get("source_quote", "") or "")[:400])
            pub = (r.get("facility_name_as_published") or "").strip()
            if pub:
                fid, fname, fmeth = resolve_facility(pub, state, tid, "AG", af.name)
            else:
                # A blank published facility name is MEANINGFUL: the agents were
                # told to leave it blank where the figure is tribe-level. Never
                # promote such a row to a property.
                fid, fname, fmeth = None, None, "published_at_tribe_level"
            if fid is None and pub:
                stage("agent_facility_unresolved:" + fmeth, source_file=af.name,
                      facility_name_as_published=pub, state=state, metric=metric,
                      value=valraw, tribe_name_as_published=r.get("tribe_name_as_published", ""),
                      candidate_properties=candidates_for(tid, state),
                      source_url=r.get("source_url", ""),
                      source_quote=(r.get("source_quote", "") or "")[:400])
            emit(source_layer="AG",
                 facility_id=fid or "", facility_name=fname or "",
                 tribe_id=tid or "", tribe_canonical_name=tname or "",
                 facility_name_as_published=pub,
                 tribe_name_as_published=r.get("tribe_name_as_published", ""),
                 state=st(state), metric=metric, value=val,
                 unit=r.get("unit", ""),
                 as_of_date=r.get("as_of_date", ""),
                 as_of_date_precision=r.get("as_of_date_precision", ""),
                 period_start=r.get("period_start", ""), period_end=r.get("period_end", ""),
                 source_authority=r.get("source_authority", ""),
                 source_document_type=r.get("source_document_type", ""),
                 source_url=r.get("source_url", ""),
                 source_quote=r.get("source_quote", ""),
                 facility_match_method=fmeth, tribe_match_method=tmeth,
                 corroborating_sources=r.get("source_authority", ""),
                 # Typed columns an extractor MAY set. Optional, so an older
                 # evidence file carrying none of them behaves exactly as
                 # before, while a newer one -- script 94's exact-derived
                 # Michigan Class III net win -- declares its own status
                 # instead of leaving this loop to guess it from the metric.
                 **{c: r[c] for c in ("measurement_status", "qualifier",
                                      "applies_to", "exclusion_flag",
                                      "exclusion_reason", "source_page")
                    if (r.get(c) or "").strip()},
                 fetched_date=r.get("fetched_date", TODAY))
            ag_n += 1
            per_file[af.name] += 1
            # Collect the split components so a comparable TOTAL can be derived
            # below. Keyed on the resolved facility where there is one, else on
            # the published name, so a tribe-level row never merges into a
            # property total.
            pkey = (fid or f"PUB::{st(state)}::{pub}", r.get("as_of_date", ""))
            if metric in ("gaming_machines", "table_games"):
                # The source states the total itself, so nothing is derived for
                # this key. Without this, script 93's Arizona totals and the
                # derivation below would both fire and double-count.
                already_total.add((pkey, metric))
            if metric in ("class_ii_gaming_machines", "class_iii_gaming_machines"):
                device_parts[pkey][metric] = val
                part_ctx[pkey] = (fid, fname, tid, tname, pub,
                                  r.get("tribe_name_as_published", ""), state,
                                  r.get("as_of_date", ""), r.get("as_of_date_precision", ""),
                                  r.get("source_authority", ""), r.get("source_document_type", ""),
                                  r.get("source_url", ""), fmeth, tmeth,
                                  r.get("fetched_date", TODAY))
            if metric in ("blackjack_tables", "house_banked_poker_tables"):
                table_parts[pkey][metric] = val
                part_ctx[pkey] = (fid, fname, tid, tname, pub,
                                  r.get("tribe_name_as_published", ""), state,
                                  r.get("as_of_date", ""), r.get("as_of_date_precision", ""),
                                  r.get("source_authority", ""), r.get("source_document_type", ""),
                                  r.get("source_url", ""), fmeth, tmeth,
                                  r.get("fetched_date", TODAY))
    for k, v in per_file.most_common():
        print(f"  [AG] {v:6,}  {k}")
    if superseded_n:
        print(f"  [AG] superseded {superseded_n:4,}  agent rows replaced by the "
              f"totals-verified re-extraction (script 93)")
    for (was, unit_in, now), n in deconflated.most_common():
        print(f"  [AG] de-conflated {n:4,}  {was} (unit={unit_in}) -> {now}")

    # ---- derived totals -----------------------------------------------------
    # The components above are the reported values. A subscriber comparing
    # against any directory wants ONE machine count, so the total is derived by
    # ADDING two published columns of the same regulator table.
    #
    # This is arithmetic on reported values, not an estimate, and it is labelled
    # as derived on every row so it can be excluded in one filter. The total is
    # emitted ONLY where BOTH components are present -- deriving a total from
    # one component would silently publish a Class III count as if it were the
    # whole floor.
    for parts, total_metric, unit, label in (
            (device_parts, "gaming_machines", "machines",
             "class III + class II gaming devices"),
            (table_parts, "table_games", "tables",
             "blackjack + house-banked poker tables")):
        need = (["class_iii_gaming_machines", "class_ii_gaming_machines"]
                if total_metric == "gaming_machines"
                else ["blackjack_tables", "house_banked_poker_tables"])
        made = 0
        for pkey, comps in parts.items():
            if not all(c in comps for c in need):
                continue
            if (pkey, total_metric) in already_total:
                continue
            (fid, fname, tid, tname, pub, tpub, state, aod, aodp,
             auth, dtype, url, fmeth, tmeth, fetched) = part_ctx[pkey]
            emit(source_layer="AG",
                 facility_id=fid or "", facility_name=fname or "",
                 tribe_id=tid or "", tribe_canonical_name=tname or "",
                 facility_name_as_published=pub, tribe_name_as_published=tpub,
                 state=st(state), metric=total_metric,
                 value=sum(comps[c] for c in need), unit=unit,
                 qualifier=(f"DERIVED total = {label}; the components are published "
                            f"separately by the regulator and are also carried as "
                            f"their own metrics in this file"),
                 as_of_date=aod, as_of_date_precision=aodp,
                 source_authority=auth, source_document_type=dtype, source_url=url,
                 source_quote="; ".join(f"{c} = {comps[c]:g}" for c in need),
                 facility_match_method=fmeth, tribe_match_method=tmeth,
                 corroborating_sources=auth,
                 exclusion_flag="1",
                 exclusion_reason=("derived by addition from two reported columns; "
                                   "exclude to avoid double-counting against the "
                                   "component metrics"),
                 fetched_date=fetched)
            made += 1
        if made:
            print(f"  [AG] derived {made:4,}  {total_metric} ({label})")

    # =====================================================================
    # LAYER 4 -- BIA environmental review (proposed, never operating)
    # =====================================================================
    nepa_files = sorted(RAW.glob("agent_nepa_facilities_*.csv"))
    np_n = 0
    for nf in nepa_files:
        for r in read_csv(nf):
            metric = (r.get("metric") or "").strip()
            valraw = (r.get("value") or "").strip()
            if not metric or not valraw:
                continue
            try:
                val = float(valraw.replace(",", "").replace("$", ""))
            except ValueError:
                stage("nepa_unparseable_value", source_file=nf.name, metric=metric,
                      value=valraw, source_url=r.get("source_url", ""))
                continue
            state = r.get("state", "")
            tid, tname, tmeth = tribe(r.get("tribe_name_as_published", ""))
            fid, fname, fmeth = None, None, "environmental_review_not_keyed_to_property"
            emit(source_layer="NEPA",
                 facility_id="", facility_name="",
                 tribe_id=tid or "", tribe_canonical_name=tname or "",
                 facility_name_as_published=r.get("project_name", ""),
                 tribe_name_as_published=r.get("tribe_name_as_published", ""),
                 state=st(state), metric=metric, value=val, unit=r.get("unit", ""),
                 qualifier=r.get("alternative", ""),
                 applies_to=r.get("alternative_role", ""),
                 measurement_status="proposed",
                 proposed_vs_actual=r.get("proposed_vs_actual", "proposed"),
                 as_of_date=r.get("as_of_date", ""),
                 as_of_date_precision=r.get("as_of_date_precision", ""),
                 source_authority=r.get("source_authority", "Bureau of Indian Affairs"),
                 source_document_type=r.get("source_document_type", "environmental_review"),
                 source_url=r.get("source_url", ""), source_page=r.get("source_page", ""),
                 source_quote=r.get("source_quote", ""),
                 facility_match_method=fmeth, tribe_match_method=tmeth,
                 corroborating_sources="Bureau of Indian Affairs",
                 exclusion_flag="1",
                 exclusion_reason=("proposed in an environmental review; a project "
                                   "evaluated is not a project built"),
                 fetched_date=r.get("fetched_date", TODAY))
            np_n += 1
    if nepa_files:
        print(f"  [NEPA] {np_n:,} proposed-facility specifications")

    # =====================================================================
    # LAYER 5 -- bond official statements / SEC filings
    # =====================================================================
    bond_files = [f for f in sorted(RAW.glob("agent_bond_sec_2026-*.csv"))
                  if "rejected" not in f.name]
    bd_n = 0
    for bf in bond_files:
        if "document_log" in bf.name:
            continue
        for r in read_csv(bf):
            metric = (r.get("metric") or "").strip()
            valraw = (r.get("value") or "").strip()
            if not metric or not valraw:
                continue
            try:
                val = float(valraw.replace(",", "").replace("$", "").replace("%", ""))
            except ValueError:
                continue
            state = r.get("state", "")
            tid, tname, tmeth = tribe(r.get("tribe_name_as_published", ""))
            pub = (r.get("facility_name_as_published") or "").strip()
            fid, fname, fmeth = (resolve_facility(pub, state, tid, "BD", bf.name)
                                 if pub else (None, None, "published_at_issuer_level"))
            if fid is None and pub:
                stage("bond_facility_unresolved:" + fmeth, source_file=bf.name,
                      facility_name_as_published=pub, state=state, metric=metric,
                      value=valraw, source_url=r.get("source_url", ""),
                      source_quote=(r.get("source_quote", "") or "")[:400])
            # A filing's per-AREA figure and the total derived by adding the
            # areas are both true and both quoted, but they measure different
            # things and must never be summed together. Both are flagged so one
            # filter separates them from the figures the filing states directly
            # for the whole property.
            app = (r.get("applies_to") or "").strip()
            xflag, xreason = "", ""
            if app.startswith("area_of_property:"):
                xflag, xreason = "1", (
                    "figure for a NAMED AREA of the property ("
                    + app.split(":", 1)[1] + "), not the whole property; exclude "
                    "to avoid summing an area with its own property total")
            elif app.startswith("whole_property_derived"):
                xflag, xreason = "1", (
                    "derived by adding the filing's separately stated areas of "
                    "the property; exclude to avoid double-counting against the "
                    "area rows")
            emit(source_layer="BD",
                 facility_id=fid or "", facility_name=fname or "",
                 tribe_id=tid or "", tribe_canonical_name=tname or "",
                 facility_name_as_published=pub,
                 tribe_name_as_published=r.get("tribe_name_as_published", ""),
                 state=st(state), metric=metric, value=val, unit=r.get("unit", ""),
                 measurement_status="audited_filing_measurement",
                 applies_to=app, exclusion_flag=xflag, exclusion_reason=xreason,
                 as_of_date=r.get("as_of_date", ""),
                 as_of_date_precision=r.get("as_of_date_precision", ""),
                 period_start=r.get("period_start", ""), period_end=r.get("period_end", ""),
                 source_authority=r.get("source_authority", ""),
                 source_document_type=r.get("source_document_type", ""),
                 source_url=r.get("source_url", ""), source_page=r.get("source_page", ""),
                 source_quote=r.get("source_quote", ""),
                 facility_match_method=fmeth, tribe_match_method=tmeth,
                 corroborating_sources=r.get("source_authority", ""),
                 fetched_date=r.get("fetched_date", TODAY))
            bd_n += 1
    if bond_files:
        print(f"  [BD] {bd_n:,} audited filing observations")

    # =====================================================================
    # WRITE
    # =====================================================================
    print()
    write_csv(CLEAN / "gaming_capacity_official.csv", rows, COLS)

    ucols = sorted({k for u in unresolved for k in u.keys()})
    for pref in ("YOUR_RULING", "reason"):
        if pref in ucols:
            ucols.remove(pref)
            ucols.insert(0, pref)
    write_csv(REVIEW / f"gaming_capacity_official_unresolved_{TODAY}.csv", unresolved, ucols)

    # =====================================================================
    # THE COMPARISON -- QA in ONE direction only
    # =====================================================================
    # Per Elijah 2026-08-06 the vendor panel is an internal fact-checking layer,
    # not a thing we publish and not a thing we grade. So this file is not
    # "does the vendor survive". It is:
    #
    #   agree   -> confidence in OUR official row rises
    #   differ  -> a lead to re-check OUR official row
    #
    # The vendor never breaks a tie on its own and is never the published value.
    vendor = read_csv(CLEAN / "gaming_property_capacity_history.csv")
    vend = collections.defaultdict(list)
    for v in vendor:
        d = (v.get("as_of_date") or "")[:4]
        if d and v.get("facility_id") and v.get("metric"):
            try:
                vend[(v["facility_id"], v["metric"], d)].append(float(v["value"]))
            except (ValueError, TypeError):
                pass

    # Index of which years the vendor covers for each (facility, metric), so a
    # NEAR miss can be reported instead of silently dropped. A same-year match
    # is the real QA comparison; a 3-year gap is reported with the gap on the
    # row so nobody reads it as one.
    vend_years = collections.defaultdict(list)
    for (fid_, met_, yr_) in vend:
        vend_years[(fid_, met_)].append(yr_)

    def _bucket(ov, vv):
        """Fixed buckets so the distribution is a column, not an anecdote.

        The brief asks for the distribution of differences and not just
        examples, so the band is a COLUMN on every comparison row and not only
        a line in a printed summary nobody downstream can read.

        The bands are EXCLUSIVE, and they are named that way on purpose. An
        earlier version labelled them `within_1pct`, `within_5pct` and so on,
        which reads as cumulative; a reader summing those would double-count
        and a reader quoting one would understate agreement."""
        if not vv:
            return "vendor_value_zero_no_ratio"
        d = abs(100.0 * (ov - vv) / vv)
        for lo, lab in ((0.0001, "pct_diff_exact_0"),
                        (1, "pct_diff_band_0_to_1"),
                        (5, "pct_diff_band_1_to_5"),
                        (10, "pct_diff_band_5_to_10"),
                        (25, "pct_diff_band_10_to_25"),
                        (50, "pct_diff_band_25_to_50")):
            if d < lo:
                return lab
        return "pct_diff_band_over_50"

    comp = []
    for r in rows:
        if r["metric_class"] != "capacity_measurement":
            continue          # never compare a ceiling or a proposal to a count
        if not r["facility_id"] or not r["as_of_date"]:
            continue
        yr = r["as_of_date"][:4]
        key = (r["facility_id"], r["metric"], yr)
        gap = 0
        if key not in vend:
            avail = vend_years.get((r["facility_id"], r["metric"]), [])
            if not avail:
                continue      # vendor has nothing for this property-metric at all
            near = min(avail, key=lambda y: abs(int(y) - int(yr)))
            gap = int(near) - int(yr)
            key = (r["facility_id"], r["metric"], near)
        try:
            ov = float(r["value"])
        except (ValueError, TypeError):
            continue
        vs = vend[key]
        vv = sum(vs) / len(vs)
        comp.append(dict(
            facility_id=r["facility_id"], facility_name=r["facility_name"],
            state=r["state"], metric=r["metric"], year=yr,
            vendor_year=key[2], year_gap=gap,
            comparison_kind=("same_year" if gap == 0 else "nearest_year_not_same_year"),
            official_value=ov, official_as_of=r["as_of_date"],
            official_source_authority=r["source_authority"],
            official_source_url=r["source_url"],
            vendor_value_mean=round(vv, 2), vendor_n_observations=len(vs),
            vendor_value_min=min(vs), vendor_value_max=max(vs),
            difference=round(ov - vv, 2),
            pct_difference=(round(100.0 * (ov - vv) / vv, 2) if vv else ""),
            abs_pct_difference=(round(abs(100.0 * (ov - vv) / vv), 2) if vv else ""),
            pct_difference_bucket=_bucket(ov, vv),
            qa_direction=("not_a_qa_signal_year_gap" if gap != 0 else
                          ("agrees_raises_confidence"
                           if vv and abs(ov - vv) / vv <= 0.05
                           else "differs_recheck_our_official_row")),
            note=("Vendor layer is INTERNAL fact-checking only and never publishes. "
                  "A difference is a lead to re-check the Cedar Press official row, "
                  "not a grade on either source."),
            built_date=TODAY))
    ccols = list(comp[0].keys()) if comp else [
        "facility_id", "facility_name", "state", "metric", "year", "official_value",
        "official_as_of", "official_source_authority", "official_source_url",
        "vendor_value_mean", "vendor_n_observations", "vendor_value_min",
        "vendor_value_max", "difference", "pct_difference", "qa_direction", "note",
        "built_date"]
    write_csv(REVIEW / f"gaming_capacity_vendor_vs_official_{TODAY}.csv", comp, ccols)

    # The distribution as a file of its own. `comparison_kind` splits it because
    # a same-year row is a QA signal and a nearest-year row is not, and pooling
    # the two would report a disagreement rate that is mostly the property
    # changing between two different dates.
    dist_rows = []
    for kind in ("same_year", "nearest_year_not_same_year"):
        sub = [c for c in comp if c["comparison_kind"] == kind]
        if not sub:
            continue
        tot = len(sub)
        for lab in ("pct_diff_exact_0", "pct_diff_band_0_to_1",
                    "pct_diff_band_1_to_5", "pct_diff_band_5_to_10",
                    "pct_diff_band_10_to_25", "pct_diff_band_25_to_50",
                    "pct_diff_band_over_50", "vendor_value_zero_no_ratio"):
            k = sum(1 for c in sub if c["pct_difference_bucket"] == lab)
            dist_rows.append(dict(
                comparison_kind=kind, bucket=lab, n=k, n_in_kind=tot,
                share_of_kind=round(100.0 * k / tot, 1),
                is_qa_signal=("yes" if kind == "same_year" else
                              "no - the year gap mixes measurement disagreement "
                              "with real change in the property"),
                built_date=TODAY))
        for metric in sorted({c["metric"] for c in sub}):
            ms = [c for c in sub if c["metric"] == metric]
            dist_rows.append(dict(
                comparison_kind=kind,
                bucket=f"BY METRIC (not a band; rows in this metric): {metric}",
                n=len(ms),
                n_in_kind=tot, share_of_kind=round(100.0 * len(ms) / tot, 1),
                # This number is in the METRIC'S OWN UNITS, not per cent. An
                # earlier version labelled it "median pct difference" and a
                # square-footage row then read "median pct difference 4800.0".
                is_qa_signal=(
                    "median ABSOLUTE difference in this metric's own units = "
                    + str(sorted(abs(c["difference"]) for c in ms)[len(ms) // 2])
                    + "; median |% difference| = "
                    + (str(sorted(abs(c["pct_difference"]) for c in ms
                                  if c["pct_difference"] != "")[len(ms) // 2])
                       if any(c["pct_difference"] != "" for c in ms) else "n/a")),
                built_date=TODAY))
    write_csv(REVIEW / f"gaming_capacity_vendor_vs_official_distribution_{TODAY}.csv",
              dist_rows,
              ["comparison_kind", "bucket", "n", "n_in_kind", "share_of_kind",
               "is_qa_signal", "built_date"])

    # =====================================================================
    # REPORT
    # =====================================================================
    print()
    print("=" * 78)
    print(f"OFFICIAL OBSERVATIONS: {len(rows):,}")
    print("=" * 78)
    print("\nby measurement status")
    for k, v in collections.Counter(r["measurement_status"] for r in rows).most_common():
        print(f"  {v:7,}  {k}")
    print("\nby state")
    for k, v in collections.Counter(r["state"] for r in rows).most_common(20):
        print(f"  {v:7,}  {k or '(none)'}")
    print("\nby metric")
    for k, v in collections.Counter(r["metric"] for r in rows).most_common(30):
        print(f"  {v:7,}  {k}")

    fids = {r["facility_id"] for r in rows if r["facility_id"]}
    tids = {r["tribe_id"] for r in rows if r["tribe_id"]}
    vendor_fids = {v["facility_id"] for v in vendor if v.get("facility_id")}
    print(f"\nproperties with >=1 NON-VENDOR observation : {len(fids):,} of {len(props):,}")
    print(f"  of which also in the vendor panel        : {len(fids & vendor_fids):,}")
    print(f"  vendor-panel properties still vendor-only: {len(vendor_fids - fids):,}")
    print(f"tribes with >=1 non-vendor observation      : {len(tids):,}")
    print(f"staged to review (unresolved / refused)     : {len(unresolved):,}")
    if class_refusals:
        print()
        print("ENTITY-CLASS REFUSALS (resolver reached a class the source cannot "
              "be about; queued, never published):")
        for (pubname, got, cls), k in class_refusals.most_common():
            print(f"  {k:4}  \"{pubname}\" -> {got} [{cls}]")
    if implausible:
        print()
        print(f"FLAGGED as probable errors IN THE SOURCE DOCUMENT "
              f"(retained, quoted, excluded by flag): {len(implausible)}")
        for m, v, u in implausible:
            print(f"  {m} = {v:g}  {u}")

    same = [c for c in comp if c["year_gap"] == 0]
    near = [c for c in comp if c["year_gap"] != 0]

    def dist(label, subset):
        d = sorted(c["pct_difference"] for c in subset if c["pct_difference"] != "")
        if not d:
            print(f"  {label}: none")
            return
        def q(x):
            return d[min(len(d) - 1, int(x * len(d)))]
        print(f"  {label}: n={len(d)}  min {d[0]:.1f}  p10 {q(.10):.1f}  "
              f"p25 {q(.25):.1f}  median {q(.50):.1f}  p75 {q(.75):.1f}  "
              f"p90 {q(.90):.1f}  max {d[-1]:.1f}   (% difference, official vs vendor)")

    print()
    if same:
        agree = sum(1 for c in same if c["qa_direction"] == "agrees_raises_confidence")
        print(f"VENDOR-vs-OFFICIAL, SAME YEAR: {len(same):,} property-metric-years")
        print(f"  agree within 5%: {agree:,} ({100.0*agree/len(same):.1f}%)")
        dist("same-year", same)
    else:
        print("VENDOR-vs-OFFICIAL, SAME YEAR: 0 property-metric-years.")
        print("  This is a FINDING, not a build failure. The two layers barely")
        print("  intersect by construction: regulators publish money and ceilings,")
        print("  not capacity counts; the one regulator publishing per-casino")
        print("  device counts (Arizona) publishes only a CURRENT snapshot; and")
        print("  the vendor panel stops in 2023 and holds ZERO Connecticut rows.")
    if near:
        print()
        print(f"  nearest-year rows (year gap disclosed, NOT a QA signal): {len(near):,}")
        dist("nearest-year", near)
        print("  A nearest-year difference mixes measurement disagreement with")
        print("  real change in the property between the two dates. It is")
        print("  published so the near-misses are visible, and it settles nothing.")


if __name__ == "__main__":
    main()
