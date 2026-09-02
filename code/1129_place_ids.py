#!/usr/bin/env python3
# lint-ok: class6 - `migrate` IS an in-place enricher, by design and by the
# mandate ("migrate, do not break"). Every table it touches keeps its source
# `facility_id` and GAINS `cedar_place_id` beside it. A rebuild of any of those
# tables drops the added column; re-run `1129 migrate --apply` after one.
"""
Cedar Press - 1129: THE PLACE IDENTIFIER. One id for every physical place a
Cedar entity operates, with a `place_class`. One id type, four classes.

    py -3 code/1129_place_ids.py adjudicate          # the duplicate worksheet, read-only
    py -3 code/1129_place_ids.py mint     [--apply]  # append-only register + place directory
    py -3 code/1129_place_ids.py migrate  [--apply]  # cedar_place_id BESIDE facility_id
    py -3 code/1129_place_ids.py verify              # exits 1 on breach
    py -3 code/1129_place_ids.py selftest            # proves verify FIRES
    py -3 code/1129_place_ids.py all      [--apply]

WHY A PLACE ID EXISTS AND (almost) NOTHING ELSE DOES
----------------------------------------------------
The owner's test, applied in `docs/ARCHITECTURE_DECISIONS.md` ADR-030:

  1. the thing recurs across two or more sources that key it differently, AND
  2. Cedar must assert that two records are the same thing, AND
  3. no stable external identifier already exists.

A physical place passes all three, twice over, and the evidence is on disk:

  * `gaming_facilities.facility_id` is SOURCE-SCOPED - `CCP-` (Casino City
    Press), `VP-` (a second vintage), `TPL-` and `CED-`. 24 clean tables key on
    it. That split is exactly WHY there are 58 same-name candidate groups:
    `Casino Del Sol` / `Casino Del Sol Resort` is one property held twice.
  * `bia_offices.OFFICEID` IS NOT UNIQUE. `OFID0038` is BOTH Salt River Agency
    (33.4662, -111.8655) and San Carlos Agency (33.3537, -110.4528). 93 rows,
    92 ids. A "stable external identifier" that collides is not one.

WHAT THE ID PROMISES - the D-U-N-S property, in the owner's own words
---------------------------------------------------------------------
    "it's like our own D-U-N-S number, basically."

A D-U-N-S names an operating unit and survives a rename, an ownership change
and a relocation, because it names the THING, not the current facts about it.
A Cedar place id promises the same, and that is the whole reason it is worth
minting:

    permanent   - never changes, for any reason
    never reused- even after a place closes; a closed casino keeps its id
    check-digited - two characters, from 503_identity.check_chars
    minted once - bound append-only in its own register, so a rebuild mints
                  ZERO and reproduces identical keys
    a SUB-HUB   - of the entity that OPERATES it, never a peer of it, and the
                  operator can change without the place changing

    CEDAR-PLACE-000123-K7
    │           │      └─ two check chars over two independent weightings (503)
    │           └─ 6-digit ordinal, allocated under an exclusive lock (cedar_ids)
    └─ namespace: what kind of thing this id names

`place_class` is a COLUMN, never the prefix. `cedar_ids.id_type()` reads the
registry and never infers from a string, for the same reason `cedar_uid`
encodes nothing: a gaming property that stops gaming and becomes a conference
centre must not have to be re-keyed.

WHAT IT READS
    data/clean/gaming_facilities.csv          787 rows  (GAMING_PROPERTY)
    data/clean/bia_offices.csv                 93 rows  (BIA_OFFICE)
    data/raw/external/bie_uio/bie_schools_featureserver.json
                                              187 feat. (BIE_SCHOOL)
    data/spine/cedar_place_id_register.csv    read FIRST, always

WHAT IT WRITES
    data/spine/cedar_place_id_register.csv    APPEND-ONLY. one row per SOURCE
                                              KEY; several source keys may
                                              share one cedar_place_id, which
                                              is what a merge IS
    data/clean/cedar_places.csv               the place directory, one row per
                                              distinct place
    review/place_gaming_adjudication_2026-09-02.csv
                                              58 groups, one verdict each
    review/place_non_place_rows_2026-09-02.csv
                                              the 16 rows that are not places
    + `cedar_place_id` on 24 gaming tables and `bia_offices.csv`

IHS_FACILITY IS DECLARED AND UNPOPULATED, ON PURPOSE
-----------------------------------------------------
There is no IHS facility table on this machine - `1050 ondisk ihs` returns
area-office HTML and a self-governance compact list, no facility directory. It
is NOT_ACQUIRED, not CONSTRAINED and not a Cedar deficiency of this pass.
`verify` prints it as UNPOPULATED and does NOT count it as a pass, because
"a verify that passes on an empty target set is the defect of the night".
"""
from __future__ import annotations

import argparse
import csv
import importlib
import io
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
csv.field_size_limit(10_000_000)

import cedar_ids                                        # noqa: E402
m503 = importlib.import_module("503_identity")          # noqa: E402

TODAY = date.today().isoformat()
SCRIPT = "code/1129_place_ids.py"
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
REVIEW = ROOT / "review"

REGISTER = SPINE / "cedar_place_id_register.csv"
PLACES = CLEAN / "cedar_places.csv"
GAMING = CLEAN / "gaming_facilities.csv"
BIA_OFFICES = CLEAN / "bia_offices.csv"
BIE_JSON = ROOT / "data" / "raw" / "external" / "bie_uio" / "bie_schools_featureserver.json"

ADJ_CSV = REVIEW / "place_gaming_adjudication_2026-09-02.csv"
NONPLACE_CSV = REVIEW / "place_non_place_rows_2026-09-02.csv"

BACKUP_TAG = f".bak_{TODAY}_pre_1129_place_ids"

REGISTER_COLS = [
    "cedar_place_id", "place_class", "source_scheme", "source_key",
    "binding_role", "place_name_at_mint", "operator_cedar_uid_at_mint",
    "minted", "minted_by", "minted_basis",
]

PLACE_COLS = [
    "cedar_place_id", "place_class", "place_name", "city", "state",
    "postal_code", "latitude", "longitude", "operator_cedar_uid",
    "operator_name", "operator_basis", "source_scheme", "source_keys",
    "n_source_keys", "adjudication_verdict", "adjudication_basis",
    "minted", "built_by", "built_date",
]

PLACE_CLASSES = ("GAMING_PROPERTY", "BIA_OFFICE", "BIE_SCHOOL", "IHS_FACILITY")

# The floors `verify` asserts. A mint that did not land must turn the gate RED,
# not merely fail to move anything - field guide rule 5. These are the measured
# counts of 2026-09-02, and they are FLOORS, so a later acquisition raises them
# rather than breaking the gate.
FLOOR = {"GAMING_PROPERTY": 717, "BIA_OFFICE": 93, "BIE_SCHOOL": 187}
UNPOPULATED = {"IHS_FACILITY": "no IHS facility directory on this machine; "
                              "NOT_ACQUIRED (docs/AGENT_FIELD_GUIDE.md §5)"}

# The gated ladder in code/846_session_audit.py::_denom, and the three groups
# by which an ADJUDICATED count must differ from it. See `reconcile()`.
LADDER_ROWS, LADDER_NONPLACE, LADDER_MECHANICAL_EXTRAS = 787, 16, 57


# ---------------------------------------------------------------- io helpers

def read_rows(p):
    p = Path(p)
    if not p.exists():
        return [], []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as f:
        rd = csv.DictReader(f)
        return list(rd), list(rd.fieldnames or [])


def write_rows(p, rows, cols, backup=False):
    """Header is DERIVED from `cols`; `62` rule 17. Writes .part then renames,
    so a crash never leaves a half table."""
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    if backup and p.exists():
        b = Path(str(p) + BACKUP_TAG)
        if not b.exists():
            shutil.copy2(p, b)
    tmp = str(p) + ".part"
    with io.open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, restval="", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, p)


def norm_name(s):
    s = re.sub(r"[^A-Z0-9 ]", " ", (s or "").upper())
    return " ".join(s.split())


# ------------------------------------------------------- gaming adjudication

def _loose(x):
    """The SAME normalisation `846::_denom` uses, on purpose. Two detectors for
    one class drift (that is why `248` is a retired stub), so the candidate
    grouping here is byte-for-byte the gate's, and only the VERDICT is mine."""
    x = re.sub(r"[^A-Z0-9 ]", " ", (x or "").upper())
    x = re.sub(r"(CASINO|RESORT|HOTEL|AND|THE|LLC|INC|GAMING|CENTER|CENTRE)",
               " ", x)
    return " ".join(x.split())


def is_non_place(r):
    """SUBSTRING, never equality. `facility_name == "no casino"` finds 7 rows;
    16 rows' names SAY it, nine of them inside a longer name
    (`Grand Canyon West - no casino`). Field guide rule 15 - an exact-string
    test on a free-text column measures the string, not the fact."""
    return "NO CASINO" in (r.get("facility_name") or "").upper()


def gaming_groups():
    """(placeholder_rows, singleton_rows, candidate_groups) over the live file.

    A candidate group is a (loose name, state) collision among NON-placeholder
    rows. It is a QUESTION, not an answer."""
    rows, _ = read_rows(GAMING)
    ph = [r for r in rows if is_non_place(r)]
    ph_ids = {r["facility_id"] for r in ph}
    g = defaultdict(list)
    for r in rows:
        if r["facility_id"] in ph_ids:
            continue
        k = (_loose(r.get("facility_name")), (r.get("state") or "").upper())
        if k[0]:
            g[k].append(r)
    groups = {k: v for k, v in g.items() if len(v) > 1}
    singles = [v[0] for k, v in g.items() if len(v) == 1]
    # a row whose loose name is empty is still a facility row and still a place
    named = {r["facility_id"] for v in g.values() for r in v}
    for r in rows:
        if r["facility_id"] not in ph_ids and r["facility_id"] not in named:
            singles.append(r)
    return ph, singles, groups


def adjudicate_group(members):
    """ONE group, ONE verdict, with the evidence that decided it.

    THE THREE RULES, in order. Each was written from the rows it fires on, and
    each is stated as a refusal so that the default is NOT to merge.

    P0  DIFFERENT OPERATORS -> HOLD_OPEN.
        Two rows naming two different sovereigns are not adjudicable as one
        place by a name test, whatever their addresses say. `7 Clans First
        Council` is filed to the Ponca Tribe in one vintage and the
        Otoe-Missouria in the other, at the identical street address; `The
        Stables` is filed to the Modoc Nation and the Miami Tribe of Oklahoma,
        and is in fact JOINTLY owned by both. Merging either would settle an
        ownership question by way of a duplicate sweep. They stay two, and the
        contradiction is written to the review file for the owner.

    P1  THE SOURCE ITSELF MINTED TWO PROPERTY IDS -> HOLD_OPEN.
        Where BOTH rows carry a distinct non-blank `casino_city_id`, the one
        vendor that mints property ids has recorded two properties. Cedar does
        not overrule a source's own property-level distinction with a name
        test. Three groups: `Cities of Gold Casino`/`Cities of Gold Hotel`,
        `Glacier Peaks Casino`/`Glacier Peaks Hotel` - a casino and its hotel,
        which the mandate names as legitimately two places - and `Three Rivers
        Casino` (Coos Bay, 97420) / `Three Rivers Casino Resort` (Florence,
        97439), which are 67 km apart and are simply two different casinos
        with one brand. THIS RULE IS WHY THE ADJUDICATED COUNT IS 717 AND NOT
        714; see `reconcile()`.

    P2  otherwise, same operator + a name that differs only in the generic
        facility vocabulary -> MERGE. One property, two vintages.

    Note what is deliberately NOT used: the coordinate pair. Measured on these
    groups, rows at an IDENTICAL street address sit 519 m (Seneca Niagara),
    758 m (Pala) and 1,583 m (Casino Del Sol) apart, while the one pair 6 m
    apart (Glacier Peaks) is a casino and a hotel that are NOT one place. The
    coordinates in this table are geocoded at varying precision, so a distance
    threshold here would measure the geocoder, not the place."""
    tribes = {(m.get("tribe_canonical_name") or "").strip() for m in members}
    ccids = [(m.get("casino_city_id") or "").strip() for m in members]
    live = [c for c in ccids if c]

    if len(tribes) > 1:
        return ("HOLD_OPEN", "P0_different_operators",
                "members name %d different operators (%s); a duplicate sweep "
                "may not settle an ownership question"
                % (len(tribes), "; ".join(sorted(t for t in tribes if t))))
    if len(set(live)) > 1:
        return ("HOLD_OPEN", "P1_source_minted_two_property_ids",
                "the vendor that mints property ids assigned %d distinct ids "
                "(%s); Cedar does not overrule a source's own property-level "
                "distinction with a name test"
                % (len(set(live)), ", ".join(sorted(set(live)))))
    return ("MERGE", "P2_one_operator_one_property_two_vintages",
            "one operator (%s); names differ only in the generic facility "
            "vocabulary; source vintages %s"
            % (sorted(tribes)[0] or "(blank)",
               "/".join(sorted({m["facility_id"].split("-")[0]
                                for m in members}))))


def cmd_adjudicate(args):
    ph, singles, groups = gaming_groups()
    out, counts = [], Counter()
    for k, members in sorted(groups.items()):
        verdict, rule, basis = adjudicate_group(members)
        counts[verdict] += 1
        out.append({
            "normalised_name": k[0], "state": k[1], "n_rows": len(members),
            "facility_ids": ";".join(m["facility_id"] for m in members),
            "facility_names": " | ".join(m["facility_name"] for m in members),
            "operators": " | ".join(sorted({(m.get("tribe_canonical_name") or "")
                                            for m in members})),
            "casino_city_ids": ";".join((m.get("casino_city_id") or "-")
                                        for m in members),
            "id_schemes": "/".join(m["facility_id"].split("-")[0] for m in members),
            "source_datasets": " | ".join(sorted({(m.get("source_datasets") or "")
                                                  for m in members})),
            "addresses": " | ".join((m.get("address") or "") for m in members),
            "verdict": verdict, "rule": rule, "basis": basis,
            "adjudicated_date": TODAY, "adjudicated_by": SCRIPT,
        })
    write_rows(ADJ_CSV, out, list(out[0].keys()) if out else ["normalised_name"])

    npl = [{"facility_id": r["facility_id"], "facility_name": r["facility_name"],
            "tribe": r.get("tribe", ""), "state": r.get("state", ""),
            "disposition": "NO_PLACE_ID",
            "reason": "the row is an assertion that this entity operates NO "
                      "gaming property; it is not a record of a place. It is "
                      "not merged into anything and it is not given an id.",
            "recorded_date": TODAY}
           for r in ph]
    write_rows(NONPLACE_CSV, npl, list(npl[0].keys()) if npl else ["facility_id"])

    merged_extras = sum(len(v) - 1 for k, v in groups.items()
                        if adjudicate_group(v)[0] == "MERGE")
    held_extras = sum(len(v) - 1 for k, v in groups.items()
                      if adjudicate_group(v)[0] == "HOLD_OPEN")
    rows, _ = read_rows(GAMING)
    print(f"  gaming: {len(rows)} rows - {len(ph)} non-places = "
          f"{len(rows) - len(ph)} facility rows")
    print(f"  {len(groups)} candidate groups: "
          f"{counts['MERGE']} MERGE ({merged_extras} extras collapse), "
          f"{counts['HOLD_OPEN']} HOLD_OPEN ({held_extras} extras kept)")
    print(f"  -> {len(rows) - len(ph) - merged_extras} distinct gaming places")
    print(f"  wrote {ADJ_CSV.relative_to(ROOT)}")
    print(f"  wrote {NONPLACE_CSV.relative_to(ROOT)}  ({len(npl)} rows)")
    # ONE WORKED EXAMPLE ROW, always. Field guide rule 3.
    if out:
        ex = next((o for o in out if o["verdict"] == "HOLD_OPEN"), out[0])
        print(f"  worked example (HOLD_OPEN): {ex['facility_names']}"
              f"  ->  {ex['rule']}")
    return 0


def reconcile():
    """The measured ladder, and every unit by which an adjudication differs.

    COMPUTED, never typed. `846::_denom` is a MECHANICAL name-collision count
    and it is correct about what it measures: 787 - 16 = 771 facility rows,
    57 same-operator extras, 714. It is not an adjudication, and the mandate
    staged those groups unmerged precisely because it is not. The three groups
    P1 holds are the whole of the difference, and they are named here so the
    number cannot rot into a bare literal."""
    rows, _ = read_rows(GAMING)
    ph, singles, groups = gaming_groups()
    mech_extras = sum(len(v) - 1 for v in groups.values()
                      if len({(m.get("tribe_canonical_name") or "") for m in v}) == 1)
    merged_extras, held = 0, []
    for k, v in sorted(groups.items()):
        verdict, rule, _b = adjudicate_group(v)
        if verdict == "MERGE":
            merged_extras += len(v) - 1
        elif rule == "P1_source_minted_two_property_ids":
            held.append((k[0], k[1], len(v) - 1))
    fac = len(rows) - len(ph)
    return {
        "rows": len(rows), "non_places": len(ph), "facility_rows": fac,
        "mechanical_extras": mech_extras, "mechanical_count": fac - mech_extras,
        "adjudicated_extras": merged_extras,
        "adjudicated_count": fac - merged_extras,
        "p1_held_groups": held,
        "p1_held_extras": sum(n for _a, _b, n in held),
    }


# ------------------------------------------------------------- place sources

def gaming_places():
    """Distinct GAMING_PROPERTY places, plus the source keys bound to each."""
    ph, singles, groups = gaming_groups()
    places = []
    for r in singles:
        places.append(_gaming_place([r], "SINGLETON",
                                    "no same-name collision in this state"))
    for k, members in sorted(groups.items()):
        verdict, rule, basis = adjudicate_group(members)
        if verdict == "MERGE":
            places.append(_gaming_place(members, rule, basis))
        else:
            for m in members:
                places.append(_gaming_place([m], rule, basis))
    return places, ph


def _pick(members, col):
    for m in members:
        v = (m.get(col) or "").strip()
        if v:
            return v
    return ""


def _gaming_place(members, verdict_rule, basis):
    # the PRIMARY source key is the longest-named member's id, tie-broken
    # lexicographically, so the choice is deterministic across rebuilds.
    primary = sorted(members,
                     key=lambda m: (-len(m.get("facility_name") or ""),
                                    m["facility_id"]))[0]
    return {
        "place_class": "GAMING_PROPERTY",
        "source_scheme": "GAMING_FACILITY_ID",
        "source_keys": [m["facility_id"] for m in members],
        "primary_source_key": primary["facility_id"],
        "place_name": primary.get("facility_name", ""),
        "city": _pick(members, "city"), "state": _pick(members, "state"),
        "postal_code": _pick(members, "postal_code"),
        "latitude": _pick(members, "latitude"),
        "longitude": _pick(members, "longitude"),
        "operator_cedar_uid": _pick(members, "cedar_uid"),
        "operator_name": _pick(members, "tribe_canonical_name"),
        "operator_basis": ("gaming_facilities.cedar_uid, as keyed by the "
                           "gaming entity layer" if _pick(members, "cedar_uid")
                          else "no operator resolved on any member row"),
        "adjudication_verdict": verdict_rule,
        "adjudication_basis": basis,
    }


def bia_places():
    """BIA_OFFICE. Keyed on GlobalID, NOT on OFFICEID.

    `OFFICEID` is the field that LOOKS like the identifier and it collides:
    OFID0038 is Salt River Agency AND San Carlos Agency, two agencies 130 km
    apart. It is kept on the row as evidence of where the record came from and
    it is never the binding key."""
    rows, _ = read_rows(BIA_OFFICES)
    out = []
    for r in rows:
        gid = (r.get("GlobalID") or "").strip()
        out.append({
            "place_class": "BIA_OFFICE",
            "source_scheme": "BIA_OFFICES_GLOBALID",
            "source_keys": [gid],
            "primary_source_key": gid,
            "place_name": (r.get("OFFICENAME") or "").strip(),
            "city": "", "state": "",
            "postal_code": "",
            "latitude": (r.get("LATITUDE") or "").strip(),
            "longitude": (r.get("LONGITUDE") or "").strip(),
            "operator_cedar_uid": "",
            "operator_name": "Bureau of Indian Affairs",
            "operator_basis": ("a federal agency office. The operator is not a "
                               "Cedar entity, so the sub-hub link is BLANK and "
                               "stated, never guessed."),
            "adjudication_verdict": "SINGLETON",
            "adjudication_basis": ("one place per BIA ArcGIS feature. OFFICEID "
                                   "%s is carried as evidence and is NOT the "
                                   "key - it is not unique."
                                   % (r.get("OFFICEID") or "")),
        })
    return out


def bie_places():
    """BIE_SCHOOL, from the feature service already on disk.

    NO STABLE EXTERNAL ID EXISTS - the service publishes `OBJECTID`, which is
    an ArcGIS row ordinal and is not stable across a republish, and nothing
    else. So the binding key is the normalised school name plus state, which
    IS unique across all 187 features (measured), and `OBJECTID` rides along as
    evidence only. This is condition 3 of the test being true in its strongest
    form, and it is stated rather than hidden."""
    if not BIE_JSON.exists():
        return []
    feats = json.loads(BIE_JSON.read_text(encoding="utf-8")).get("features", [])
    out = []
    for f in feats:
        a = f.get("attributes", {})
        nm = (a.get("School_Name") or "").strip()
        st = (a.get("State") or "").strip()
        if not nm:
            continue
        out.append({
            "place_class": "BIE_SCHOOL",
            "source_scheme": "BIE_SCHOOL_NAME_STATE",
            "source_keys": [f"{norm_name(nm)}|{norm_name(st)}"],
            "primary_source_key": f"{norm_name(nm)}|{norm_name(st)}",
            "place_name": nm,
            "city": (a.get("City") or "").strip(), "state": st,
            "postal_code": str(a.get("Zip_Code") or "").strip(),
            "latitude": str(a.get("Latitude") or "").strip(),
            "longitude": str(a.get("Longitude") or "").strip(),
            "operator_cedar_uid": "",
            "operator_name": "",
            "operator_basis": ("Operation_Type = %s. NOT resolved to a Cedar "
                               "hub in this pass: 129 of 187 are "
                               "tribally-controlled and matching a school name "
                               "to a nation by name is the containment defect. "
                               "Blank means unresolved, never 'no operator'."
                               % (a.get("Operation_Type") or "unstated")),
            "adjudication_verdict": "SINGLETON",
            "adjudication_basis": ("one place per BIE feature; School_Name is "
                                   "unique across all 187 features (measured). "
                                   "OBJECTID %s is evidence only - an ArcGIS "
                                   "row ordinal is not a stable key."
                                   % a.get("OBJECTID")),
        })
    return out


def all_places():
    g, ph = gaming_places()
    return g + bia_places() + bie_places(), ph


# --------------------------------------------------------------------- mint

def read_register():
    rows, _ = read_rows(REGISTER)
    return rows


def binding_map(reg_rows):
    """(place_class, source_scheme, source_key) -> cedar_place_id. Read FIRST,
    always: an existing binding is IMMUTABLE and a rebuild mints zero."""
    return {(r["place_class"], r["source_scheme"], r["source_key"]):
            r["cedar_place_id"] for r in reg_rows}


def render(ordinal):
    """`CEDAR-PLACE-000123-K7`. Allocation is permanent and locked in
    cedar_ids; transcription safety comes from 503 - the same split NEST
    uses, so there is one check-character implementation in the project."""
    return "CEDAR-PLACE-%06d-%s" % (ordinal,
                                    m503.check_chars(m503.encode(ordinal)))


def valid_place_id(v):
    m = re.match(r"^CEDAR-PLACE-(\d{6})-([0-9A-Z]{2})$", (v or "").strip())
    if not m:
        return False
    return m.group(2) == m503.check_chars(m503.encode(int(m.group(1))))


def cmd_mint(args):
    apply = args.apply
    places, ph = all_places()
    reg_rows = read_register()
    bind = binding_map(reg_rows)
    before = len(reg_rows)

    # A place already bound through ANY of its source keys keeps that id. This
    # is what makes a merge additive: a new vintage's key joins the place, and
    # the place's id does not move.
    # `resolved` is keyed on the place's ORDINAL POSITION in `places`, never
    # on `id(p)`. A memory address is a non-deterministic key (defect class 7
    # in code/293_lint_bug_classes.py) and it is only accidentally safe even
    # in-process: the moment a place object is rebuilt rather than reused,
    # the map silently misses.
    need, resolved = [], {}
    for i, p in enumerate(places):
        found = ""
        for k in p["source_keys"]:
            found = bind.get((p["place_class"], p["source_scheme"], k)) or found
        if found:
            resolved[i] = found
        else:
            need.append(i)

    minted = 0
    if need:
        if not apply:
            print(f"  DRY RUN - would mint {len(need):,} place id(s).")
        else:
            got = cedar_ids.allocate("CEDAR-PLACE", len(need),
                                     note="Cedar place sub-hubs, 1129")
            for i, raw in zip(need, got):
                pid = render(int(raw.rsplit("-", 1)[1]))
                resolved[i] = pid
                minted += 1
    if need and not apply:
        for i in need:
            resolved[i] = "(unminted)"

    # append-only: every source key of every place gets a register row, and an
    # existing row is never rewritten.
    seen = {(r["place_class"], r["source_scheme"], r["source_key"])
            for r in reg_rows}
    for i, p in enumerate(places):
        pid = resolved[i]
        for k in p["source_keys"]:
            key = (p["place_class"], p["source_scheme"], k)
            if key in seen:
                continue
            seen.add(key)
            reg_rows.append({
                "cedar_place_id": pid, "place_class": p["place_class"],
                "source_scheme": p["source_scheme"], "source_key": k,
                "binding_role": ("primary" if k == p["primary_source_key"]
                                 else "merged_duplicate"),
                "place_name_at_mint": p["place_name"],
                "operator_cedar_uid_at_mint": p["operator_cedar_uid"],
                "minted": TODAY, "minted_by": SCRIPT,
                "minted_basis": ("ordinal allocated by code/cedar_ids.py under "
                                 "an exclusive lock; two check characters "
                                 "appended by 503_identity.check_chars; "
                                 "binding is append-only and immutable"),
            })

    dirrows = []
    for i, p in enumerate(places):
        dirrows.append({
            "cedar_place_id": resolved[i], "place_class": p["place_class"],
            "place_name": p["place_name"], "city": p["city"],
            "state": p["state"], "postal_code": p["postal_code"],
            "latitude": p["latitude"], "longitude": p["longitude"],
            "operator_cedar_uid": p["operator_cedar_uid"],
            "operator_name": p["operator_name"],
            "operator_basis": p["operator_basis"],
            "source_scheme": p["source_scheme"],
            "source_keys": ";".join(p["source_keys"]),
            "n_source_keys": len(p["source_keys"]),
            "adjudication_verdict": p["adjudication_verdict"],
            "adjudication_basis": p["adjudication_basis"],
            "minted": TODAY, "built_by": SCRIPT, "built_date": TODAY,
        })

    by_class = Counter(p["place_class"] for p in places)
    print(f"  {len(places):,} distinct places: "
          + ", ".join(f"{k} {v:,}" for k, v in sorted(by_class.items())))
    for k, why in UNPOPULATED.items():
        print(f"    {k} 0  UNPOPULATED - {why}")
    print(f"  register: {before:,} rows before -> {len(reg_rows):,} after; "
          f"{minted:,} ids minted this run "
          f"({len(places) - len(need):,} preserved from the register)")
    print(f"  non-places excluded, no id: {len(ph)}")
    r = reconcile()
    print("  LADDER  %d rows - %d non-places = %d facility rows"
          % (r["rows"], r["non_places"], r["facility_rows"]))
    print("          - %d mechanical extras = %d  (846::_denom)"
          % (r["mechanical_extras"], r["mechanical_count"]))
    print("          - %d adjudicated extras = %d  (this pass)"
          % (r["adjudicated_extras"], r["adjudicated_count"]))
    print("          the whole difference is %d group(s) held by P1: %s"
          % (len(r["p1_held_groups"]),
             "; ".join(f"{a} ({b})" for a, b, _n in r["p1_held_groups"])))
    if dirrows:
        ex = dirrows[0]
        print(f"  worked example: {ex['cedar_place_id']}  {ex['place_class']}  "
              f"{ex['place_name']}  keys={ex['source_keys']}")

    if not apply:
        print("\n  DRY RUN - pass --apply to write the register and directory.")
        return 0

    bad = [x["cedar_place_id"] for x in reg_rows
           if not valid_place_id(x["cedar_place_id"])]
    assert not bad, f"invalid place id minted: {bad[:3]}"
    ids = [x["cedar_place_id"] for x in dirrows]
    assert len(set(ids)) == len(ids), "one place id on two directory rows"

    write_rows(REGISTER, reg_rows, REGISTER_COLS, backup=True)
    write_rows(PLACES, dirrows, PLACE_COLS, backup=True)
    print(f"  wrote {REGISTER.relative_to(ROOT)}")
    print(f"  wrote {PLACES.relative_to(ROOT)}")
    return 0


# ------------------------------------------------------------------ migrate

def gaming_tables():
    """Every clean table that keys on `facility_id`, measured, never listed."""
    out = []
    for p in sorted(CLEAN.glob("*.csv")):
        if p.name.endswith(".part"):
            continue
        try:
            with p.open(encoding="utf-8-sig", errors="replace", newline="") as f:
                hdr = next(csv.reader(f), [])
        except OSError:
            continue
        if "facility_id" in [h.strip() for h in hdr]:
            out.append(p)
    return out


def _numeric_sums(rows, cols):
    """Sum every column that parses as a number on at least one row. Used to
    prove money conservation TO THE CENT across the write."""
    tot = {}
    for c in cols:
        s, n = 0.0, 0
        for r in rows:
            v = (r.get(c) or "").strip().replace(",", "").replace("$", "")
            if not v:
                continue
            try:
                s += float(v)
                n += 1
            except ValueError:
                s, n = 0.0, 0
                break
        if n:
            tot[c] = round(s, 2)
    return tot


def migrate_one(path, keycol, mapping, apply, absent_reason_for):
    """Add `cedar_place_id` BESIDE the source key. Never overwrites the source
    key - it is the evidence of where the row came from."""
    rows, cols = read_rows(path)
    if not cols:
        return None
    before_rows, before_cols = len(rows), list(cols)
    before_sums = _numeric_sums(rows, cols)

    newcols = list(cols)
    for c in ("cedar_place_id", "cedar_place_id_absent_reason"):
        if c not in newcols:
            i = newcols.index(keycol) + 1 if keycol in newcols else len(newcols)
            newcols.insert(i, c)
            i += 1
    # A DROP COUNTER MUST NAME WHAT IT DROPPED (293 class 2c, the "87 defect":
    # the number goes in the log and the key does not, and twenty days pass).
    # So every unmapped key is collected, printed and written out, not tallied.
    hit = blank = 0
    unmapped = Counter()
    for r in rows:
        k = (r.get(keycol) or "").strip()
        if not k:
            r["cedar_place_id"] = ""
            r["cedar_place_id_absent_reason"] = "no %s on this row" % keycol
            blank += 1
            continue
        pid = mapping.get(k, "")
        r["cedar_place_id"] = pid
        r["cedar_place_id_absent_reason"] = "" if pid else absent_reason_for(k)
        if pid:
            hit += 1
        else:
            unmapped[k] += 1
    miss = sum(unmapped.values())

    after_sums = _numeric_sums(rows, before_cols)
    assert len(rows) == before_rows, "row count moved"
    assert before_sums == after_sums, (
        "a numeric column changed: "
        + str({k: (before_sums[k], after_sums.get(k))
               for k in before_sums if before_sums[k] != after_sums.get(k)}))
    assert all(c in newcols for c in before_cols), "a column was dropped"

    if apply:
        write_rows(path, rows, newcols, backup=True)
    return (path.name, before_rows, len(before_cols), len(newcols),
            hit, miss, blank, len(before_sums), unmapped)


def cmd_migrate(args):
    apply = args.apply
    reg = read_register()
    if not reg:
        print("  REFUSING: the place register is empty. Run "
              "`1129 mint --apply` first.")
        return 1
    gmap = {r["source_key"]: r["cedar_place_id"] for r in reg
            if r["place_class"] == "GAMING_PROPERTY"}
    bmap = {r["source_key"]: r["cedar_place_id"] for r in reg
            if r["place_class"] == "BIA_OFFICE"}
    _ph, _s, _g = gaming_groups()
    nonplace = {r["facility_id"] for r in _ph}

    def why_gaming(k):
        if k in nonplace:
            return ("NOT_A_PLACE: this facility_id names a row asserting the "
                    "entity operates no gaming property")
        return "facility_id not in the place register"

    total = Counter()
    reports, unmapped_keys = [], Counter()
    for p in gaming_tables():
        rep = migrate_one(p, "facility_id", gmap, apply, why_gaming)
        if rep:
            reports.append(rep)
            total["rows"] += rep[1]; total["hit"] += rep[4]
            total["miss"] += rep[5]; total["blank"] += rep[6]
            unmapped_keys.update(rep[8])
    rep = migrate_one(BIA_OFFICES, "GlobalID", bmap, apply,
                      lambda k: "GlobalID not in the place register")
    if rep:
        reports.append(rep)
        total["rows"] += rep[1]; total["hit"] += rep[4]
        total["miss"] += rep[5]; total["blank"] += rep[6]
        unmapped_keys.update(rep[8])

    print(f"  {len(reports)} tables{' MIGRATED' if apply else ' (DRY RUN)'}")
    print("  %-48s %8s %5s %5s %8s %6s %6s %5s"
          % ("table", "rows", "col-", "col+", "keyed", "unmap", "blank", "num"))
    for nm, nr, cb, ca, hit, miss, blank, nnum, _u in reports:
        print("  %-48s %8d %5d %5d %8d %6d %6d %5d"
              % (nm, nr, cb, ca, hit, miss, blank, nnum))
    print(f"  TOTAL rows {total['rows']:,} · keyed {total['hit']:,} · "
          f"unmapped {total['miss']:,} · no source key {total['blank']:,}")
    # NAME every key that did not map, and say what it is.
    print(f"  {len(unmapped_keys)} distinct source key(s) did not map, "
          f"{sum(unmapped_keys.values()):,} row(s):")
    for k, n in sorted(unmapped_keys.items()):
        print(f"      {k:<12} {n:>7,} row(s)   {why_gaming(k)[:78]}")
    if not unmapped_keys:
        print("      none")
    print("  row and money conservation asserted per table across the write "
          "(row count identical; every numeric column's sum identical to the "
          "cent) - an assertion failure raises, it does not warn.")
    if not apply:
        print("\n  DRY RUN - pass --apply to write.")
    return 0


# ------------------------------------------------------------------- verify

def _checks():
    """Every check returns (name, ok, detail). A check that cannot MEASURE
    returns ok=False with an UNMEASURED detail - an absence of evidence is
    never evidence of absence (field guide rule 4)."""
    out = []
    reg = read_register()
    places, _place_cols = read_rows(PLACES)

    # V0 THE MINT LANDED. This is the check that fails when the work did NOT
    # happen, rather than when something moved. An empty target set is a
    # FAILURE here, not a pass.
    if not reg:
        out.append(("V0 the register exists and is non-empty", False,
                    "UNMEASURED: no cedar_place_id_register.csv"))
        return out
    by_class = Counter(r["place_class"] for r in reg)
    place_by_class = Counter(r["place_class"] for r in places)
    for cls, floor in sorted(FLOOR.items()):
        n = place_by_class.get(cls, 0)
        out.append((f"V0 {cls} minted at or above its floor ({floor})",
                    n >= floor, f"{n} distinct places, {by_class.get(cls,0)} "
                                f"source keys bound"))
    for cls, why in sorted(UNPOPULATED.items()):
        n = place_by_class.get(cls, 0)
        out.append((f"V0 {cls} is declared UNPOPULATED, and says so",
                    n == 0, f"{n} places - {why}"))

    # V1 every id is well-formed and its check characters verify
    bad = [r["cedar_place_id"] for r in reg
           if not valid_place_id(r["cedar_place_id"])]
    out.append(("V1 every place id is check-digit valid", not bad,
                f"{len(bad)} malformed" + (f", e.g. {bad[0]}" if bad else "")))

    # V2 the register is a FUNCTION: one source key -> one id, forever
    seen, coll = {}, []
    for r in reg:
        k = (r["place_class"], r["source_scheme"], r["source_key"])
        if k in seen and seen[k] != r["cedar_place_id"]:
            coll.append(f"{k[2]}: {seen[k]} and {r['cedar_place_id']}")
        seen[k] = r["cedar_place_id"]
    out.append(("V2 a source key is bound to exactly one place id", not coll,
                f"{len(coll)} double-bound" + (f": {coll[0]}" if coll else "")))

    # V3 an id is never reused across classes, and never re-minted
    cls_of = defaultdict(set)
    for r in reg:
        cls_of[r["cedar_place_id"]].add(r["place_class"])
    mixed = [k for k, v in cls_of.items() if len(v) > 1]
    out.append(("V3 a place id names one class only", not mixed,
                f"{len(mixed)} ids span classes"))

    # V4 the directory and the register agree
    dir_ids = {r["cedar_place_id"] for r in places}
    reg_ids = {r["cedar_place_id"] for r in reg}
    out.append(("V4 directory and register carry the same id set",
                dir_ids == reg_ids,
                f"directory {len(dir_ids)}, register {len(reg_ids)}, "
                f"symmetric difference {len(dir_ids ^ reg_ids)}"))

    # V5 exactly one primary binding per place
    prim = Counter(r["cedar_place_id"] for r in reg
                   if r["binding_role"] == "primary")
    off = [k for k in reg_ids if prim.get(k, 0) != 1]
    out.append(("V5 exactly one primary source key per place", not off,
                f"{len(off)} places with {'' if not off else prim.get(off[0],0)}"
                f" primaries" if off else "all 1"))

    # V6 the migration landed on every table that keys on facility_id
    tabs = gaming_tables()
    unmigrated, keyed_total, unmapped_total = [], 0, 0
    gmap = {r["source_key"] for r in reg if r["place_class"] == "GAMING_PROPERTY"}
    for p in tabs:
        rows, cols = read_rows(p)
        if "cedar_place_id" not in cols:
            unmigrated.append(p.name)
            continue
        for r in rows:
            k = (r.get("facility_id") or "").strip()
            if not k:
                continue
            if (r.get("cedar_place_id") or "").strip():
                keyed_total += 1
            elif k in gmap:
                unmapped_total += 1
    out.append((f"V6 all {len(tabs)} facility_id tables carry cedar_place_id",
                not unmigrated,
                f"{len(unmigrated)} unmigrated"
                + (f": {unmigrated[0]}" if unmigrated else "")))
    out.append(("V6b no row carries a registered facility_id and a blank "
                "place id", unmapped_total == 0,
                f"{unmapped_total:,} rows blank on a registered key; "
                f"{keyed_total:,} rows keyed"))

    # V7 the source key is never overwritten - it is the evidence
    lost = [p.name for p in tabs if "facility_id" not in read_rows(p)[1]]
    out.append(("V7 every migrated table still carries its source "
                "facility_id", not lost, f"{len(lost)} lost it"))

    # V8 bia_offices: the collision is now resolvable
    brows, bcols = read_rows(BIA_OFFICES)
    if "cedar_place_id" not in bcols:
        out.append(("V8 OFID0038 resolves to two distinct place ids", False,
                    "UNMEASURED: bia_offices.csv not migrated"))
    else:
        d = {r["cedar_place_id"] for r in brows
             if (r.get("OFFICEID") or "").strip() == "OFID0038"}
        n_off = len({(r.get("OFFICEID") or "") for r in brows})
        n_pid = len({(r.get("cedar_place_id") or "") for r in brows})
        out.append(("V8 OFID0038 resolves to two distinct place ids",
                    len(d) == 2 and "" not in d,
                    f"{len(d)} place id(s) on OFID0038; table-wide "
                    f"{n_off} OFFICEIDs vs {n_pid} place ids over "
                    f"{len(brows)} rows"))

    # V9 the ladder still reconciles, COMPUTED
    r = reconcile()
    ok = (r["rows"] == LADDER_ROWS and r["non_places"] == LADDER_NONPLACE
          and r["mechanical_extras"] == LADDER_MECHANICAL_EXTRAS
          and r["adjudicated_count"] == r["mechanical_count"] + r["p1_held_extras"])
    out.append(("V9 the adjudicated count reconciles to 846::_denom", ok,
                "%d - %d = %d facility rows; mechanical %d -> %d; "
                "adjudicated %d -> %d; difference = %d P1-held group(s)"
                % (r["rows"], r["non_places"], r["facility_rows"],
                   r["mechanical_extras"], r["mechanical_count"],
                   r["adjudicated_extras"], r["adjudicated_count"],
                   r["p1_held_extras"])))

    # V10 no non-place row was given an id
    _p, _s2, _g = gaming_groups()
    npl = {x["facility_id"] for x in _p}
    got = [k for k in npl if k in gmap]
    out.append(("V10 no non-place row was given a place id", not got,
                f"{len(got)} of {len(npl)} non-place rows carry an id"))
    return out


def cmd_verify(args):
    checks = _checks()
    bad = 0
    for name, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}\n         {detail}")
        bad += 0 if ok else 1
    print(f"\n  {len(checks) - bad}/{len(checks)} checks pass")
    return 1 if bad else 0


# ----------------------------------------------------------------- selftest

def cmd_selftest(args):
    """PROVE the verify fires. Four synthetic violations, each restored.

    A check that has never failed on purpose is not known to work, and the one
    that matters most here is V0 - a verify that passes on an empty target set
    is worthless, so the FIRST fixture empties the register."""
    if not REGISTER.exists():
        print("  cannot self-test before `mint --apply`"); return 1
    fails = []

    def run():
        return sum(1 for _n, ok, _d in _checks() if not ok)

    base = run()
    print(f"  baseline: {base} failing check(s)")
    if base:
        print("  REFUSING to self-test against a red baseline - fix verify "
              "first, or the fixtures prove nothing.")
        return 1

    saved_reg = REGISTER.read_bytes()
    saved_dir = PLACES.read_bytes() if PLACES.exists() else None
    tabs = gaming_tables()
    saved_tab = tabs[0].read_bytes() if tabs else None

    def fixture(label, mutate, expect):
        n = None
        try:
            mutate()
            got = [nm for nm, ok, _d in _checks() if not ok]
            n = len(got)
            hit = any(expect in g for g in got)
            print(f"  fixture {label}: {n} check(s) fail; "
                  f"{'NAMED ' + expect if hit else 'DID NOT FIRE ' + expect}")
            if not hit:
                fails.append(label)
        finally:
            REGISTER.write_bytes(saved_reg)
            if saved_dir is not None:
                PLACES.write_bytes(saved_dir)
            if saved_tab is not None and tabs:
                tabs[0].write_bytes(saved_tab)

    # 1. THE EMPTY TARGET SET. The defect of the night.
    fixture("empty register", lambda: write_rows(REGISTER, [], REGISTER_COLS),
            "V0")
    # 2. a corrupted check digit
    def bust_check():
        rows, _ = read_rows(REGISTER)
        pid = rows[0]["cedar_place_id"]
        rows[0]["cedar_place_id"] = pid[:-1] + ("Z" if pid[-1] != "Z" else "Y")
        write_rows(REGISTER, rows, REGISTER_COLS)
    fixture("one transcribed check character", bust_check, "V1")
    # 3. one source key bound to two ids - the silent re-keying
    def double_bind():
        rows, _ = read_rows(REGISTER)
        r = dict(rows[0]); r["cedar_place_id"] = render(999999)
        rows.append(r)
        write_rows(REGISTER, rows, REGISTER_COLS)
    fixture("a source key bound twice", double_bind, "V2")
    # 4. the migration reverted on one table - the rebuild/enricher collision
    def drop_col():
        p = tabs[0]
        rows, cols = read_rows(p)
        cols = [c for c in cols if c != "cedar_place_id"]
        write_rows(p, rows, cols)
    if tabs:
        fixture("cedar_place_id dropped by a rebuild", drop_col, "V6")

    after = run()
    print(f"  restored: {after} failing check(s) (was {base})")
    if after != base:
        print("  RESTORE FAILED - the fixtures did not clean up.")
        return 1
    if fails:
        print(f"  SELFTEST FAILED: {fails} did not fire the named check")
        return 1
    print("  selftest OK: verify fires on an empty register, a bad check "
          "digit, a double binding and a reverted migration.")
    return 0


# --------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = ap.add_subparsers(dest="cmd")
    for name, fn in [("adjudicate", cmd_adjudicate), ("mint", cmd_mint),
                     ("migrate", cmd_migrate), ("verify", cmd_verify),
                     ("selftest", cmd_selftest)]:
        p = sub.add_parser(name)
        p.add_argument("--apply", action="store_true")
        p.set_defaults(fn=fn)
    p = sub.add_parser("all")
    p.add_argument("--apply", action="store_true")
    p.set_defaults(fn=None)
    a = ap.parse_args()
    if a.cmd is None:
        ap.print_help(); return 0
    if a.cmd == "all":
        for fn in (cmd_adjudicate, cmd_mint, cmd_migrate, cmd_verify):
            print(f"\n== {fn.__name__} ==")
            rc = fn(a)
            if rc:
                return rc
        return 0
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
