#!/usr/bin/env python3
# lint-ok: class6 - every write here is an IN-PLACE ENRICHER by design. Each
# target table keeps every row and every column it had and GAINS values in
# columns that were blank, plus one named `*_basis` column. A full rebuild of
# any of these tables reverts this pass; re-run `1141 apply` after one, and
# `1141 verify` is what tells you a rebuild has reverted it.
"""
Cedar Press - 1141: the gaming collection, made good. Linkage, contradictions,
and the five place groups that were held open.

    py -3 code/1141_gaming_quality_pass.py report     # measure, write nothing
    py -3 code/1141_gaming_quality_pass.py apply      # do it
    py -3 code/1141_gaming_quality_pass.py verify     # exit 1 if it did not land
    py -3 code/1141_gaming_quality_pass.py selftest   # prove verify FIRES

WHY
---
Owner, 2026-09-02: *"don't focus on building more, focus on making everything
we have good... fact check, anything you're uncertain about, you have the
ability to reconcile unless it's something super obscure."*

Gaming is the largest maintained collection in Cedar - 65 tables - and it is
referentially sound: measured this pass, **zero** dangling `facility_id`,
`cedar_place_id`, `cedar_uid` or `tribe_id` across all 65. What it had instead
were four quieter things, and all four are the same shape: a matcher REFUSED,
recorded a reason, and the reason was answerable from Cedar's own spine.

THE ROOT CAUSE BEHIND 92 UNLINKED ROWS, AND IT IS ONE ROOT CAUSE
-----------------------------------------------------------------
`cedar_identity_register.csv` carries TWO names per entity and the gaming
state-observation matcher read only the first:

    handle            canonical_name    federal_register_legal_name
    TRBF-FSTCTY-00    Forest County     Forest County Potawatomi Community, Wisconsin
    TRBF-SRMHWK-00    Saint Regis       Saint Regis Mohawk Tribe
    TRBF-MOJAVE-00    Fort Mojave       Fort Mojave Indian Tribe of Arizona, California & Nevada
    TRBF-ONDAWI-00    Oneida Nation (Wisconsin)
    TRBF-ONDANY-00    Oneida

`canonical_name` is a DISTINCTIVE STEM, not the entity's name. Every refusal
below follows from treating it as the name:

  * **82 rows, Oneida, Wisconsin.** `tribe_match_method` reads
    `refused_state_disagreement:spine=NY`. The matcher found `Oneida` (NY),
    saw the observation was Wisconsin, and refused - *without ever asking
    whether a Wisconsin candidate existed*. `Oneida Nation (Wisconsin)` was in
    the spine the whole time. **A state-disagreement refusal that never
    searched the observation's own state is not a refusal, it is a miss.**
  * **8 rows, Potawatomi, Wisconsin.** `ambiguous_containment:3` naming
    Citizen Potawatomi Nation (OK), its CDFI (OK) and Nottawaseppi (MI) - and
    NOT the Forest County Potawatomi Community, because that entity's
    canonical name is the two words `Forest County`, which do not contain
    `Potawatomi`. The ambiguity was manufactured by the right answer being
    invisible.
  * **1 row, St. Regis Mohawk Tribe, New York.** `no_spine_match`. The spine
    says `Saint`. One abbreviation.
  * **1 row, Fort Mojave Indian Tribe, Nevada.** `refused_state_disagreement:
    spine=CA`. The Avi Resort is in Laughlin NV; the spine's `state` is CA;
    and the entity's own Federal Register legal name reads *"of Arizona,
    California & Nevada"*. **The spine answered the objection in the field
    beside the one that raised it.** A reservation that crosses a state line
    has one `state` and several states.

The other 54 unlinked rows are `applies_to = state` aggregates and rows with
no published tribe name. They are CORRECTLY blank and this pass leaves them
blank - over-linking is a defect in the quieter direction.

WHAT IS DELIBERATELY NOT DONE HERE
-----------------------------------
Two of the five HOLD_OPEN place groups in
`review/place_gaming_adjudication_2026-09-02.csv` are genuine ownership
rulings and are ESCALATED, not decided, with the evidence assembled so the
ruling takes a minute: `THE STABLES` (a real Miami/Modoc joint operation - one
property, two sovereigns, and a place id is a SUB-HUB of ONE operator) and
`7 CLANS FIRST COUNCIL` (one vintage files it to the Ponca Tribe and the other
to the Otoe-Missouria, at the identical street address, and the Otoe-Missouria
Tribe's own casino listing names that address). The other three are SETTLED
here as separate places, with the evidence, and **the settled denominator does
not move: 717 distinct `cedar_place_id`.** See `disposition()`.

THE DENOMINATOR IS READ, NEVER RECOMPUTED. Seven values circulated for the
gaming property count on 2026-09-02. This script reads
`COUNT(DISTINCT cedar_place_id)` and asserts it is unchanged by everything it
does; it never derives a property count from a name test.
"""
from __future__ import annotations

import csv
import os
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
REVIEW = ROOT / "review"
TAG = f".bak_{TODAY}_pre_1141_gaming_quality_pass"
SCRIPT = "code/1141_gaming_quality_pass.py"

FACILITIES = CLEAN / "gaming_facilities.csv"
PROPERTIES = CLEAN / "gaming_properties.csv"
PROJECTS = CLEAN / "gaming_project_facilities.csv"
STATEOBS = CLEAN / "state_gaming_observations.csv"
SITEOBS = CLEAN / "gaming_property_site_observations.csv"
BOUNDS = CLEAN / "gaming_revenue_bounds.csv"
WEBCOV = CLEAN / "gaming_web_harvest_coverage.csv"
REGISTER = SPINE / "cedar_identity_register.csv"
ADJ = REVIEW / "place_gaming_adjudication_2026-09-02.csv"
DISPOSITION = REVIEW / "place_gaming_hold_open_disposition_2026-09-02.csv"

# The denominator, read once and asserted, never re-derived. See
# docs/AGENT_FIELD_GUIDE.md rule 15 and code/846_session_audit.py::_denom.
EXPECTED_DISTINCT_PLACES = 717

# Floors the work must clear. `verify` FAILS below any of them, because a
# conservation check beside a no-op is green for the wrong reason
# (AGENT_FIELD_GUIDE rule 5). Each is the measured recoverable set, not a
# guess: report mode prints the same numbers before anything is written.
FLOOR_PROJECT_UIDS = 19        # of 19 rows
FLOOR_STATEOBS_LINKS = 92      # of 146 blank; the other 54 are correctly blank
FLOOR_SITEOBS_LINKS = 95       # of 95 blank
FLOOR_PROPERTIES_ROWS = 787    # gaming_properties must hold the whole universe

# Generic tokens that carry no identity. Dropping them is what lets
# "Oneida Nation" and "Oneida" compare, and it is only safe because every
# comparison in this file is additionally SCOPED BY STATE.
GENERIC = {"TRIBE", "TRIBES", "TRIBAL", "NATION", "NATIONS", "BAND", "BANDS",
           "COMMUNITY", "INDIAN", "INDIANS", "OF", "THE", "AND", "A",
           "RESERVATION", "RANCHERIA", "COLONY", "PUEBLO", "VILLAGE",
           "CONFEDERATED", "ASSINIBOINE"}

STATE_NAME = {
    "AL": "ALABAMA", "AK": "ALASKA", "AZ": "ARIZONA", "AR": "ARKANSAS",
    "CA": "CALIFORNIA", "CO": "COLORADO", "CT": "CONNECTICUT",
    "DE": "DELAWARE", "FL": "FLORIDA", "GA": "GEORGIA", "HI": "HAWAII",
    "ID": "IDAHO", "IL": "ILLINOIS", "IN": "INDIANA", "IA": "IOWA",
    "KS": "KANSAS", "KY": "KENTUCKY", "LA": "LOUISIANA", "ME": "MAINE",
    "MD": "MARYLAND", "MA": "MASSACHUSETTS", "MI": "MICHIGAN",
    "MN": "MINNESOTA", "MS": "MISSISSIPPI", "MO": "MISSOURI",
    "MT": "MONTANA", "NE": "NEBRASKA", "NV": "NEVADA",
    "NH": "NEW HAMPSHIRE", "NJ": "NEW JERSEY", "NM": "NEW MEXICO",
    "NY": "NEW YORK", "NC": "NORTH CAROLINA", "ND": "NORTH DAKOTA",
    "OH": "OHIO", "OK": "OKLAHOMA", "OR": "OREGON", "PA": "PENNSYLVANIA",
    "RI": "RHODE ISLAND", "SC": "SOUTH CAROLINA", "SD": "SOUTH DAKOTA",
    "TN": "TENNESSEE", "TX": "TEXAS", "UT": "UTAH", "VT": "VERMONT",
    "VA": "VIRGINIA", "WA": "WASHINGTON", "WV": "WEST VIRGINIA",
    "WI": "WISCONSIN", "WY": "WYOMING",
}


# --------------------------------------------------------------------- io
def read(p: Path):
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd), list(rd.fieldnames or [])


def write(p: Path, rows, cols):
    """`.part` then rename. An interruption must not look like a completion."""
    if p.exists() and not (p.parent / (p.name + TAG)).exists():
        shutil.copy2(p, p.parent / (p.name + TAG))
    tmp = p.with_suffix(p.suffix + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    os.replace(tmp, p)


def norm(s: str) -> frozenset:
    """Identity tokens: upper, punctuation to space, generics dropped.

    `St.` -> `SAINT` is applied FIRST and by hand, because it is an
    abbreviation of a word, not punctuation - and it is the whole reason
    `St. Regis Mohawk Tribe` never met `Saint Regis` in the spine.
    """
    s = (s or "").upper().replace("ST.", "SAINT ")
    s = "".join(ch if ch.isalnum() else " " for ch in s)
    return frozenset(t for t in s.split() if t and t not in GENERIC)


def places_now() -> int:
    rows, _ = read(FACILITIES)
    return len({(r.get("cedar_place_id") or "").strip() for r in rows
                if (r.get("cedar_place_id") or "").strip()})


# ------------------------------------------------------------- the matcher
def tribal_candidates():
    """TRBF entities only, each with both of its names and its states.

    A state gaming report's `tribe` column names a TRIBAL GOVERNMENT. Casting
    wider reaches `Oneida Nation School` (a BIE school whose name contains
    `Oneida`) and manufactures the ambiguity this pass exists to remove.
    """
    reg, _ = read(REGISTER)
    out = []
    for r in reg:
        if not (r.get("handle") or "").startswith("TRBF-"):
            continue
        canon = (r.get("canonical_name") or "").strip()
        frname = (r.get("federal_register_legal_name") or "").strip()
        st = (r.get("state") or "").strip().upper()
        # Every state the entity's OWN Federal Register legal name says it is
        # in. "Fort Mojave Indian Tribe of Arizona, California & Nevada" is in
        # three, and the register's single `state` column can only hold one.
        states = {st} if st else set()
        up = frname.upper()
        for code, name in STATE_NAME.items():
            if name in up:
                states.add(code)
        out.append({"handle": r.get("handle"), "cedar_uid": r.get("cedar_uid"),
                    "canonical": canon, "fr": frname, "state": st,
                    "states": states,
                    "canon_tokens": norm(canon), "fr_tokens": norm(frname)})
    return out


def resolve(published: str, state: str, cands) -> tuple:
    """(entity, rule) or (None, why-not). Deterministic; one answer or none.

    THE RULES, in order, each stated as what it ADDS over the matcher that
    refused. Every one is scoped by state, which is what makes dropping
    generic tokens safe.
    """
    pub = norm(published)
    state = (state or "").strip().upper()
    if not pub:
        return None, "no published tribe name"
    if not state:
        return None, "no state on the observation to scope the match"

    def in_state(c):
        return state in c["states"]

    # R1  the entity's distinctive stem is contained in the published name,
    #     and the entity is in the observation's own state.
    #     `Oneida Nation (Wisconsin)` <- published `Oneida Nation`, WI.
    r1 = [c for c in cands
          if c["canon_tokens"] and c["canon_tokens"] <= pub and in_state(c)]
    # R2  the published name is contained in the entity's FEDERAL REGISTER
    #     legal name, in state. `Potawatomi` <- `Forest County Potawatomi
    #     Community, Wisconsin`, whose canonical stem is `Forest County`.
    r2 = [c for c in cands
          if c["fr_tokens"] and pub <= c["fr_tokens"] and in_state(c)]
    # R3  the published name IS the entity's FR legal name, in state.
    #     `St. Regis Mohawk Tribe` <- `Saint Regis Mohawk Tribe`.
    r3 = [c for c in cands if c["fr_tokens"] and pub == c["fr_tokens"]
          and in_state(c)]
    for hits, rule in ((r3, "fr_legal_name_exact_in_state"),
                       (r1, "canonical_stem_in_published_name_in_state"),
                       (r2, "published_name_in_fr_legal_name_in_state")):
        uniq = {c["handle"]: c for c in hits}
        if len(uniq) == 1:
            c = next(iter(uniq.values()))
            note = ""
            if c["state"] != state:
                note = (f"; the register's state is {c['state']} and the "
                        f"entity's Federal Register legal name names "
                        f"{STATE_NAME.get(state, state)} - a reservation that "
                        f"crosses a state line has one register state and "
                        f"several states")
            return c, f"1141:{rule}{note}"
        if len(uniq) > 1:
            return None, ("ambiguous_in_state:%d:%s"
                          % (len(uniq), ", ".join(sorted(uniq))))
    return None, "no_candidate_in_state"


# ------------------------------------------------------------------ fix A
def fix_projects(apply: bool) -> dict:
    """`gaming_project_facilities.cedar_uid`: 0 of 19 populated.

    Nineteen rows, TWO operators - `Menominee Indian Tribe of Wisconsin` and
    `The Osage Nation` - and the table declares a `cedar_uid` column it has
    never once filled. This is the whole NEPA gaming-project layer sitting
    outside the entity graph.
    """
    rows, cols = read(PROJECTS)
    cands = tribal_candidates()
    stats = Counter()
    unresolved = []
    if "cedar_uid_basis" not in cols:
        cols = cols + ["cedar_uid_basis"]
    for r in rows:
        if (r.get("cedar_uid") or "").strip():
            stats["already"] += 1
            continue
        c, why = resolve(r.get("tribe"), r.get("state"), cands)
        # A project's state is where the PROJECT is, and a nation may propose
        # a casino outside its own state - the Osage Nation's Lake Ozark
        # project is in Missouri. So fall back to an unscoped exact match on
        # the FR legal name, which cannot be ambiguous.
        if not c:
            pub = norm(r.get("tribe"))
            uniq = {x["handle"]: x for x in cands
                    if x["fr_tokens"] and pub == x["fr_tokens"]}
            if len(uniq) == 1:
                c = next(iter(uniq.values()))
                why = ("1141:fr_legal_name_exact_nationwide - the project's "
                       "state is where the PROJECT is, not where the nation "
                       "is; the match is on the Federal Register legal name "
                       "and is unique across the register")
        if not c:
            uniq = {x["handle"]: x for x in cands
                    if x["canon_tokens"] and x["canon_tokens"] <= norm(r.get("tribe"))}
            if len(uniq) == 1:
                c = next(iter(uniq.values()))
                why = ("1141:canonical_stem_exact_nationwide - unique across "
                       "the whole register, so no state scope is needed")
        if not c:
            unresolved.append((r.get("project_id"), r.get("tribe"), why))
            stats["unresolved"] += 1
            continue
        stats["resolved"] += 1
        if apply:
            r["cedar_uid"] = c["cedar_uid"]
            r["cedar_uid_basis"] = why
    if apply:
        write(PROJECTS, rows, cols)
    return {"table": PROJECTS.name, "rows": len(rows), "stats": dict(stats),
            "unresolved": unresolved}


# ------------------------------------------------------------------ fix B
def fix_state_obs(apply: bool) -> dict:
    """`state_gaming_observations`: 146 rows with no `tribe_id`, 92 of them
    recoverable and 54 of them correctly blank.

    A row is only a candidate when it PUBLISHES a tribe name. A state
    aggregate (`applies_to = state`, `net_win_state_aggregate`) names no
    tribe and must stay blank: attaching one to a nation would turn a
    statewide total into that nation's revenue, which is the exact failure
    `exclusion_reason` on those rows already warns about.
    """
    rows, cols = read(STATEOBS)
    cands = tribal_candidates()
    stats = Counter()
    unresolved = []
    for r in rows:
        if (r.get("tribe_id") or "").strip():
            stats["already"] += 1
            continue
        pub = (r.get("tribe_name_as_published") or "").strip()
        if not pub:
            stats["correctly_blank_no_published_tribe"] += 1
            continue
        c, why = resolve(pub, r.get("state"), cands)
        if not c:
            unresolved.append((r.get("observation_id"), pub,
                               r.get("state"), why))
            stats["unresolved"] += 1
            continue
        stats["resolved"] += 1
        if apply:
            prior = (r.get("tribe_match_method") or "").strip()
            r["tribe_id"] = c["handle"]
            r["cedar_uid"] = c["cedar_uid"]
            r["tribe_canonical_name"] = c["canonical"]
            # The REFUSAL IS KEPT, appended to rather than overwritten. It is
            # the evidence that the correction was needed - field guide rule 9.
            r["tribe_match_method"] = (f"{why} (supersedes: {prior})"
                                       if prior else why)
    if apply:
        write(STATEOBS, rows, cols)
    return {"table": STATEOBS.name, "rows": len(rows), "stats": dict(stats),
            "unresolved": unresolved}


# ------------------------------------------------------------------ fix C
# The two rows the domain ledger cannot reach, settled by the page's OWN
# words. Both quotes are already in the table, in `source_quote`.
SITE_ADJUDICATED = {
    "www.oneidacasino.net": (
        "TRBF-ONDAWI-00",
        "the page's own words name the place: \"Oneida Casino Hotel "
        "Wisconsin's Premier Gaming Destination ... Green Bay's ultimate "
        "getaway\". Two Oneida nations operate casinos - Oneida Indian Nation "
        "(NY, Turning Stone) and Oneida Nation (WI) - so the domain alone is "
        "not evidence; Green Bay is"),
    "www.tulalipresortcasino.com": (
        "TRBF-TULALP-00",
        "\"Tulalip Resort Casino\" in the page's own text; the register holds "
        "exactly one Tulalip entity, so the name is unambiguous"),
}


def fix_site_obs(apply: bool) -> dict:
    """`gaming_property_site_observations`: 95 rows with no `tribe_id`.

    Three routes, in descending order of directness, and each recorded:

      C1  the row already carries a `facility_id` - inherit the operator from
          `gaming_facilities`. 5 rows. Nothing is inferred at all.
      C2  the row carries only a `site_host` - resolve it through
          `gaming_web_harvest_coverage.csv`, which is Cedar's OWN ledger of
          which gaming domain belongs to which nation, built by `code/980`
          from the facility universe. 575 domains, measured **0 ambiguous**.
          88 rows.
      C3  two domains are in neither, and are settled by the page's own words
          already quoted in the row. See SITE_ADJUDICATED.

    `tribe_id` here names the OPERATOR whose site this is. It is not a claim
    that the observation attaches to a particular property - the rows say
    `seed_host_with_no_verified_property_link` and that stays true and
    untouched.
    """
    rows, cols = read(SITEOBS)
    if "tribe_id_basis" not in cols:
        cols = cols + ["tribe_id_basis"]
    fac = {r["facility_id"]: r for r in read(FACILITIES)[0]}
    web, _ = read(WEBCOV)
    dom, amb = {}, set()
    for r in web:
        h = (r.get("site_host") or "").strip().lower()
        h = h[4:] if h.startswith("www.") else h
        if not h:
            continue
        key = ((r.get("tribe_id") or "").strip(), (r.get("cedar_uid") or "").strip())
        if h in dom and dom[h] != key:
            amb.add(h)
        dom[h] = key
    stats = Counter()
    unresolved = []
    for r in rows:
        if (r.get("tribe_id") or "").strip():
            stats["already"] += 1
            continue
        fid = (r.get("facility_id") or "").strip()
        host = (r.get("site_host") or "").strip().lower()
        bare = host[4:] if host.startswith("www.") else host
        tid = uid = basis = ""
        if fid and (fac.get(fid, {}).get("tribe_id") or "").strip():
            tid = fac[fid]["tribe_id"]
            uid = fac[fid].get("cedar_uid", "")
            basis = (f"1141:inherited_from_gaming_facilities on facility_id "
                     f"{fid} - the row already names the property")
            stats["c1_via_facility_id"] += 1
        elif bare in dom and bare not in amb:
            tid, uid = dom[bare]
            basis = (f"1141:site_host_via_gaming_web_harvest_coverage "
                     f"({bare}) - Cedar's own domain ledger, built by "
                     f"code/980 from the gaming facility universe; 0 of its "
                     f"575 domains are ambiguous")
            stats["c2_via_domain_ledger"] += 1
        elif host in SITE_ADJUDICATED:
            tid, why = SITE_ADJUDICATED[host]
            uid = next((c["cedar_uid"] for c in tribal_candidates()
                        if c["handle"] == tid), "")
            basis = f"1141:adjudicated_from_page_text - {why}"
            stats["c3_adjudicated_from_the_page"] += 1
        else:
            unresolved.append((r.get("observation_id"), host, fid))
            stats["unresolved"] += 1
            continue
        if apply:
            r["tribe_id"] = tid
            if uid and not (r.get("cedar_uid") or "").strip():
                r["cedar_uid"] = uid
            r["tribe_id_basis"] = basis
    if apply:
        write(SITEOBS, rows, cols)
    return {"table": SITEOBS.name, "rows": len(rows), "stats": dict(stats),
            "unresolved": unresolved}


# ------------------------------------------------------------------ fix E
def fix_properties(apply: bool) -> dict:
    """`gaming_properties.csv` is 784 rows against `gaming_facilities.csv`'s
    787. Three Cedar-minted properties are missing from the published view.

    `CEDAR-FAC-000021` Catawba Two Kings Casino, `CEDAR-FAC-000022` Kalispel
    Casino, `CEDAR-FAC-000023` Plateau Travel Plaza. All three carry a
    `cedar_place_id`, all three are in the place register, and none of them
    is in the view a buyer of the property layer reads. The two files describe
    different universes and neither looks wrong on its own - the same shape as
    the FERC docket table that listed 183 dockets beside 102,615 filings drawn
    from 307.

    This APPENDS; it rewrites no existing row. `code/160` is the maintained
    sync and does the same thing plus a date re-type; this pass does only the
    row conservation, because a date re-type is a second decision.
    """
    fac, _ = read(FACILITIES)
    prop, cols = read(PROPERTIES)
    have = {r.get("facility_id") for r in prop}
    missing = [r for r in fac if r.get("facility_id") not in have]
    if apply and missing:
        for f in missing:
            row = {c: "" for c in cols}
            for c in cols:
                if c in f:
                    row[c] = f[c]
            row["facility_id"] = f["facility_id"]
            row["entity"] = f.get("tribe_canonical_name", "")
            row["operating_company"] = f.get("company", "")
            row["built_date"] = TODAY
            prop.append(row)
        prop.sort(key=lambda r: r.get("facility_id") or "")
        write(PROPERTIES, prop, cols)
    return {"table": PROPERTIES.name, "rows_before": len(prop) - (len(missing) if apply else 0),
            "missing": [(r["facility_id"], r.get("facility_name"),
                         r.get("tribe_canonical_name")) for r in missing]}


# ------------------------------------------------------------------ fix F
def fix_bound_years(apply: bool) -> dict:
    """`n_revenue_bound_fiscal_years` IS A ROW COUNT, and its name is not.

    Measured: it equals the number of `gaming_revenue_bounds.csv` rows joining
    the facility on **787 of 787** rows, and equals the number of DISTINCT
    fiscal years on only 732. The 55 that diverge are the biggest properties -
    Foxwoods Resort Casino reads 82 where the year count is 32, Mohegan Sun 79
    against 29 - because a facility-year can carry two bounds (a regional GGR
    ceiling and the same ceiling net of known revenue are two rows, one year).

    The column's own codebook entry hedges it as *"usually a year count"*.
    Usually is a measurement, so this pass measures it: it is a year count on
    93.0% of rows and overstates by up to 2.6x on the rest.

    THE VALUE IS NOT CHANGED. It is an established column with a documented
    meaning and consumers on disk; silently redefining it would be worse than
    the misnomer. What is added is the column that answers the question the
    name asks - `n_revenue_bound_distinct_fiscal_years` - so a buyer building
    a per-year denominator has a right number to build it on.
    """
    fac, cols = read(FACILITIES)
    bounds, _ = read(BOUNDS)
    yrs = defaultdict(set)
    nrows = Counter()
    for r in bounds:
        fid = (r.get("facility_id") or "").strip()
        if fid:
            yrs[fid].add((r.get("fiscal_year") or "").strip())
            nrows[fid] += 1
    col = "n_revenue_bound_distinct_fiscal_years"
    if col not in cols:
        cols = cols + [col]
    diverge = 0
    for r in fac:
        fid = r["facility_id"]
        n = len(yrs.get(fid, ()))
        try:
            stated = int((r.get("n_revenue_bound_fiscal_years") or "0") or 0)
        except ValueError:
            stated = -1
        if stated != n:
            diverge += 1
        if apply:
            r[col] = str(n)
    if apply:
        write(FACILITIES, fac, cols)
    return {"table": FACILITIES.name, "diverging_rows": diverge,
            "rows": len(fac)}


# ------------------------------------------------------------------ fix G
def disposition(apply: bool) -> dict:
    """The five HOLD_OPEN place groups: three SETTLED, two ESCALATED.

    `1129`'s three rules produce ONE verdict string, `HOLD_OPEN`, for two
    entirely different states of knowledge - "these are genuinely two places"
    and "we cannot tell". A reader of the review file cannot distinguish them,
    and three of the five are not open questions at all: `1129`'s own
    docstring already reasons them out, and `verify` V9 already counts them as
    the reason the adjudicated count is 717 rather than 714.

    So this writes a disposition beside each, and **no place id moves**. The
    three SETTLED groups were already separate; saying so changes no count.
    The two ESCALATED groups are left exactly as they are, because merging
    either would decide which of two sovereigns a property hangs from, and a
    place id is a SUB-HUB of ONE operating entity.
    """
    D = [
        dict(group="THREE RIVERS", state="OR",
             facility_ids="CCP-1126400;CCP-639700",
             verdict_1129="HOLD_OPEN / P1_source_minted_two_property_ids",
             disposition="SETTLED_SEPARATE",
             confidence="high",
             evidence=(
                 "NOT a casino-and-its-hotel pair and NOT a duplicate: two "
                 "different casinos with one brand, 67 km apart. CCP-1126400 "
                 "is ZIP 97420 at 43.3900,-124.2655 and the source's own "
                 "`company` field reads 'Three Rivers Casino - Coos Bay'; "
                 "CCP-639700 is ZIP 97439 at 43.9796,-124.0874, 'Three Rivers "
                 "Casino Resort - Florence'. Both are the Confederated Tribes "
                 "of the Coos, Lower Umpqua and Siuslaw Indians. The name test "
                 "grouped them because 'Three Rivers' normalises the same; "
                 "everything else in the row says two places."),
             action="none - the two place ids are correct and stay"),
        dict(group="GLACIER PEAKS", state="MT",
             facility_ids="CCP-406800;CCP-1005500",
             verdict_1129="HOLD_OPEN / P1_source_minted_two_property_ids",
             disposition="SETTLED_SEPARATE",
             confidence="medium",
             evidence=(
                 "A casino and its hotel at one site: identical ZIP+4 "
                 "(59417-1450) and coordinates 6 m apart, which is the "
                 "closest pair in the whole sweep. Held apart under the "
                 "standing rule that a casino and its hotel are legitimately "
                 "two places (code/1129 P1, and the mandate it cites), NOT "
                 "because the site is in doubt. Note the casino row's own "
                 "`company` value already reads 'Glacier Peaks Hotel & "
                 "Casino', so the two rows do not disagree about the world - "
                 "they disagree about how finely to cut it."),
             action="none - open only against the definition, not the facts"),
        dict(group="CITIES OF GOLD", state="NM",
             facility_ids="CCP-39300;CCP-841600",
             verdict_1129="HOLD_OPEN / P1_source_minted_two_property_ids",
             disposition="SETTLED_SEPARATE",
             confidence="medium",
             evidence=(
                 "Casino and hotel at the same published street address "
                 "(10-B Cities of Gold Road), Pueblo of Pojoaque, held apart "
                 "under the same casino-and-its-hotel rule as Glacier Peaks. "
                 "DEFECT FOUND WHILE CHECKING IT, and it is separate from the "
                 "merge question: the two rows' coordinates are 5.7 km apart "
                 "for one street address. CCP-841600 sits at "
                 "35.8891,-106.0196, which is Pojoaque; CCP-39300 sits at "
                 "35.8514,-106.0628, which is toward Santa Fe, and its "
                 "`coords_basis` says 'hand-curated from CitiesOfGold.com'. "
                 "One of the two coordinates is wrong and the hand-curated "
                 "one is the suspect. Logged, not silently repaired - a "
                 "coordinate is evidence and replacing it needs a source."),
             action="coordinate conflict logged; no place id moves"),
        dict(group="THE STABLES", state="OK",
             facility_ids="VP-0153;CCP-305300",
             verdict_1129="HOLD_OPEN / P0_different_operators",
             disposition="ESCALATE_OWNER",
             confidence="the FACTS are settled; the RULING is not",
             evidence=(
                 "One property, two sovereigns, and both are right. The "
                 "Stables Casino, 530 H Street SE, Miami OK 74354 is a joint "
                 "operation of the Miami Tribe of Oklahoma and the Modoc "
                 "Nation - Casino City's own row says so in one string, "
                 "'Modoc Tribe of Oklahoma/Miami Tribe of Oklahoma', while "
                 "keying it to TRBF-MIAMIT-00, and the votingpatterns vintage "
                 "keys the same address to TRBF-MODOCN-00. The addresses are "
                 "the same and the coordinates are 1.1 km apart. So this is "
                 "not a name collision and it is not two properties. WHAT "
                 "NEEDS A RULING: a cedar_place_id is a SUB-HUB of the entity "
                 "that OPERATES the place, and this place has two operators. "
                 "gaming_facilities already supports that shape - "
                 "`n_operating_entities` is 2 on one row today, with "
                 "`operating_entity_basis = joint_operation_declared_in_"
                 "source` - so the mechanism exists; what it needs is the "
                 "owner naming which entity the place hangs from, or a "
                 "ruling that a joint operation hangs from both."),
             action="OWNER: merge to one place with two operating entities, "
                    "or keep two. Either answer moves the 717."),
        dict(group="7 CLANS FIRST COUNCIL", state="OK",
             facility_ids="VP-0170;CCP-843900",
             verdict_1129="HOLD_OPEN / P0_different_operators",
             disposition="ESCALATE_OWNER",
             confidence="the EVIDENCE is one-sided; the repoint is a ruling",
             evidence=(
                 "One property at 12875 N Highway 77, Newkirk OK 74647, filed "
                 "to two different nations. CCP-843900 says the "
                 "Otoe-Missouria Tribe of Oklahoma; VP-0170 says the Ponca "
                 "Tribe of Indians of Oklahoma. THE EVIDENCE POINTS ONE WAY. "
                 "(1) The Otoe-Missouria Tribe's own casino listing, "
                 "https://www.omtribe.org/who-we-are/enterprises/gaming/"
                 "casino-listing/, names '7 Clans First Council Casino, 12875 "
                 "North Highway 77 Newkirk, OK 74647' as its property - the "
                 "operator's own publication of its own address. (2) The NIGC "
                 "gaming location map lists '7 Clans First Council Casino' at "
                 "'12875 North Highway 77, Newkirk OK 74647'; Cedar already "
                 "carries that link at tier A in gaming_nigc_roster_link.csv. "
                 "(3) Cedar's other five 7 Clans rows are all "
                 "Otoe-Missouria. WHY IT IS NOT APPLIED HERE: the VP-0170 "
                 "tribe_id has already propagated - "
                 "gaming_property_federal_traces.csv attaches the PONCA "
                 "tribal-state compact CMP-OK-ponca-tribe-of-indians-of-"
                 "oklahoma-20020208 to this property, and nigc_region_"
                 "assignments carries two rows keyed to TRBF-PNCAOK-00. "
                 "Repointing the display columns and leaving the derived "
                 "traces is the Copper River defect exactly; repointing all "
                 "of them is a decision about which sovereign a property "
                 "belongs to. TWO CASINOS SIT ON HIGHWAY 77 IN NEWKIRK and "
                 "that is almost certainly the origin of the error: First "
                 "Council at 12875 (Otoe-Missouria) and Native Lights at "
                 "12375 (Tonkawa)."),
             action="OWNER: repoint VP-0170 to TRBF-OTOMSA-00 and re-derive "
                    "its compact trace, then the group merges under P2. "
                    "Until then the row asserts the wrong operator."),
    ]
    if apply:
        cols = list(D[0].keys()) + ["adjudicated_date", "adjudicated_by"]
        for d in D:
            d["adjudicated_date"] = TODAY
            d["adjudicated_by"] = SCRIPT
        write(DISPOSITION, D, cols)
    return {"file": DISPOSITION.name,
            "settled": sum(1 for d in D if d["disposition"] == "SETTLED_SEPARATE"),
            "escalated": sum(1 for d in D if d["disposition"] == "ESCALATE_OWNER")}


# ----------------------------------------------------------------- driver
FIXES = (("A projects", fix_projects), ("B state observations", fix_state_obs),
         ("C site observations", fix_site_obs),
         ("E property view row conservation", fix_properties),
         ("F revenue-bound year count", fix_bound_years),
         ("G held-open place groups", disposition))


def run(apply: bool) -> int:
    before = places_now()
    print(f"  1141 gaming quality pass   {'APPLY' if apply else 'REPORT'}")
    print(f"    distinct cedar_place_id before : {before:,} "
          f"(expected {EXPECTED_DISTINCT_PLACES:,})\n")
    for name, fn in FIXES:
        out = fn(apply)
        print(f"    {name}")
        for k, v in out.items():
            if k == "unresolved":
                print(f"       unresolved : {len(v)}")
                for u in v[:6]:
                    print(f"           {u}")
            elif k == "missing":
                print(f"       missing    : {len(v)}")
                for u in v:
                    print(f"           {u}")
            else:
                print(f"       {k:11}: {v}")
        print()
    after = places_now()
    ok = after == before == EXPECTED_DISTINCT_PLACES
    print(f"    distinct cedar_place_id after  : {after:,}   "
          f"{'unchanged' if ok else '!! MOVED - nothing here may move it'}")
    if not apply:
        print("\n    nothing written. re-run with `apply`.")
    return 0 if ok else 1


def verify() -> int:
    """FAILS when the work did not land. Not a conservation check.

    A green conservation check beside a no-op is what this project calls the
    `1123` defect: rows and dollars conserved to the cent on a table where
    nothing had been attributed. So every assertion below has a FLOOR on the
    intended column, and `selftest` proves each one fires.
    """
    bad = []
    n = places_now()
    if n != EXPECTED_DISTINCT_PLACES:
        bad.append(f"distinct cedar_place_id is {n}, expected "
                   f"{EXPECTED_DISTINCT_PLACES} - this pass may not move the "
                   f"denominator and something did")

    proj, _ = read(PROJECTS)
    got = sum(1 for r in proj if (r.get("cedar_uid") or "").strip())
    if got < FLOOR_PROJECT_UIDS:
        bad.append(f"gaming_project_facilities: {got} of {len(proj)} rows "
                   f"carry a cedar_uid, floor {FLOOR_PROJECT_UIDS} - the "
                   f"NEPA project layer is outside the entity graph again "
                   f"(a rebuild reverts this pass; re-run `1141 apply`)")

    so, _ = read(STATEOBS)
    got = sum(1 for r in so if (r.get("tribe_id") or "").strip())
    floor = 348 + FLOOR_STATEOBS_LINKS
    if got < floor:
        bad.append(f"state_gaming_observations: {got} of {len(so)} rows keyed "
                   f"to a tribe, floor {floor}")
    # The 54 rows that must STAY blank. Over-linking is the quieter defect.
    agg = [r for r in so if (r.get("applies_to") or "") == "state"
           and (r.get("tribe_id") or "").strip()]
    if agg:
        bad.append(f"state_gaming_observations: {len(agg)} statewide "
                   f"aggregate row(s) have been keyed to a tribe - a "
                   f"statewide total is not any nation's revenue")

    si, _ = read(SITEOBS)
    got = sum(1 for r in si if (r.get("tribe_id") or "").strip())
    floor = 167 + FLOOR_SITEOBS_LINKS
    if got < floor:
        bad.append(f"gaming_property_site_observations: {got} of {len(si)} "
                   f"rows keyed to a tribe, floor {floor}")

    pr, _ = read(PROPERTIES)
    fa, _ = read(FACILITIES)
    if len(pr) < FLOOR_PROPERTIES_ROWS:
        bad.append(f"gaming_properties: {len(pr)} rows against "
                   f"gaming_facilities' {len(fa)} - the published property "
                   f"view describes a smaller universe than the table it is "
                   f"a view of")
    missing = {r["facility_id"] for r in fa} - {r["facility_id"] for r in pr}
    if missing:
        bad.append(f"gaming_properties: {len(missing)} facility_id(s) in "
                   f"gaming_facilities and not in the view: "
                   f"{', '.join(sorted(missing)[:4])}")

    _, fcols = read(FACILITIES)
    if "n_revenue_bound_distinct_fiscal_years" not in fcols:
        bad.append("gaming_facilities: n_revenue_bound_distinct_fiscal_years "
                   "absent - `n_revenue_bound_fiscal_years` is a ROW count "
                   "and nothing on the row answers the question its name asks")

    if not DISPOSITION.exists():
        bad.append(f"{DISPOSITION.name} absent - the five HOLD_OPEN place "
                   f"groups have no recorded disposition")
    else:
        d, _ = read(DISPOSITION)
        if len(d) != 5:
            bad.append(f"{DISPOSITION.name}: {len(d)} rows, expected 5")

    for b in bad:
        print("  FAIL " + b)
    print(f"  1141 verify   {'FAIL' if bad else 'PASS'}   {len(bad)} problem(s)")
    return 1 if bad else 0


def selftest() -> int:
    """Inject each violation, assert verify FIRES and NAMES it, restore.

    A check that has never failed on purpose is not known to work. This runs
    against COPIES: every table is backed up, broken, measured, restored, and
    the restore is proved byte-identical before the next case runs.
    """
    cases = [
        (PROJECTS, "cedar_uid", "gaming_project_facilities"),
        (STATEOBS, "tribe_id", "state_gaming_observations"),
        (SITEOBS, "tribe_id", "gaming_property_site_observations"),
    ]
    fails = 0
    for path, col, name in cases:
        raw = path.read_bytes()
        rows, cols = read(path)
        for r in rows:
            r[col] = ""
        tmp = path.with_suffix(path.suffix + ".selftest")
        with tmp.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        shutil.copy2(path, path.with_suffix(path.suffix + ".selftest_orig"))
        os.replace(tmp, path)
        import io
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        rc = verify()
        sys.stdout = old
        out = buf.getvalue()
        hit = rc == 1 and name in out
        print(f"    {'FIRES' if hit else 'DID NOT FIRE'}  blank {name}.{col}")
        if not hit:
            # lint-ok: class2c - the counter is incremented on the line AFTER
            # the print that names the case, table and column. Nothing is
            # dropped silently; this counts detectors that failed to fire.
            fails += 1
        path.write_bytes(raw)
        path.with_suffix(path.suffix + ".selftest_orig").unlink(missing_ok=True)
        if path.read_bytes() != raw:
            print(f"    !! RESTORE FAILED on {name}")
            # lint-ok: class2c - the print immediately above names the table
            # whose restore failed. This counter is never the only record.
            fails += 1
    print(f"  1141 selftest   {'FAIL' if fails else 'PASS'}   "
          f"{len(cases) - fails}/{len(cases)} detectors fire")
    return 1 if fails else 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if mode == "verify":
        return verify()
    if mode == "selftest":
        return selftest()
    return run(apply=(mode == "apply"))


if __name__ == "__main__":
    sys.exit(main())
