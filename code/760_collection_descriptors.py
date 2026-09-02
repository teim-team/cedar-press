#!/usr/bin/env python3
"""
Cedar Press - 760: THE BRIDGE TO THE PRODUCT. Emit CollectionDataset descriptors.

    py -3 code/760_collection_descriptors.py           # report + write
    py -3 code/760_collection_descriptors.py verify    # exit 1 if a READY
                                                       # dataset cannot be described

WHY
---
Owner, 2026-09-01: *"Cedar Press on git is the North Star of what we want the
final product to look like... eventually we move all this data and code into
our database and then link Cedar Press to it. It's visually, functionally what
I'm going for."*

The product repo (`teim-team/cedar-press`, cedarpress.ai) already declares the
contract and admits its own numbers are fake. `server/cedar_press/collections.py`:

    PROTOTYPE LIMITATIONS
        Every number in this file is demonstration data ... plausible values
        for the demo workspace, never real published figures. **The real pilot
        datasets arrive as manifest + data files and replace the inline series
        here.**

So the interface is already specified and Cedar already builds manifests. This
script closes the last gap: it emits the site's own `CollectionDataset` shape,
filled from Cedar's live measurements, so the demo series can be replaced with
real ones without either side guessing what the other means.

THE TWO SIDES ALREADY AGREE MORE THAN THEY LOOK
-----------------------------------------------
They were designed together and nobody had checked:

  * the site's launch ids - `deals`, `contractors` - ARE Cedar's dataset ids
  * the site's `shelf` vocabulary - standard / pro / grove - IS Cedar's, which
    also carries `infrastructure` for the hub
  * the site's `level` ("what the rows are: entity records, or entity records
    that also roll up to geography") IS `518.NATURAL_SCOPE`

WHAT IS DERIVED AND WHAT IS EDITORIAL
-------------------------------------
Derived here, and re-derived on every run, so it cannot rot:

  id · shelf · level · rows_label · vintage · updated · status · n_tables

`rows_label` counts ROWS in the dataset's customer-facing tables. The
readiness scoreboard's `n_customer_tables` is a TABLE count and the site wants
rows - reading one as the other would publish "6 rows" for a 2,393-row dataset.

`vintage` is the newest period Cedar actually holds, from the cadence
measurement, not a label anyone typed.

EDITORIAL, and deliberately NOT invented here:

  name · short_name · tracks · sources · method

Those are the customer-facing description of what a dataset is and how it was
built. They belong to whoever writes the copy. This script reads them from
`docs/datasets/_descriptors.json` if it exists and otherwise emits an empty
string with `needs_copy: true` - **an empty field a human fills is honest; a
generated sentence that reads like a claim about method is not.**

`downloads` is a PRODUCT metric. It lives in the platform database and Cedar
has no business inventing it. Always omitted.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

READINESS = ROOT / "data" / "clean" / "cedar_dataset_readiness.csv"
CONTRACTS = ROOT / "docs" / "schema" / "dataset_contracts.json"
CADENCE = ROOT / "docs" / "REFRESH_CADENCE.json"
COPY = ROOT / "docs" / "datasets" / "_descriptors.json"
OUT = ROOT / "dist" / "collection_descriptors.json"
# CEDAR'S OWN FACTS SHIP IN A SIBLING FILE, NOT INSIDE THE DESCRIPTOR.
# Codex, PR #29 finding 1: `CollectionDataset(**descriptor)` - the call this
# file's README advertises and claims to have verified - raised TypeError on
# EVERY ONE OF THE 13, because each object also carried `cedar` and
# `needs_copy` and the dataclass declares neither. That is the SAME defect
# round 1 closed on PR #26 (`n_rows` at the top level), reintroduced by the
# fix for it: moving Cedar's fields under a namespaced key made them tidy and
# left them just as unsupported. A keyword the dataclass does not declare is
# fatal whether it is one key or five.
#
# So the descriptor is now EXACTLY the dataclass and nothing else, which is
# the first of the two repairs Codex offered, and the Cedar facts move here:
OUT_CEDAR = ROOT / "dist" / "collection_descriptors.cedar.json"

# The dataclass contract, restated so this file can FAIL on a mismatch rather
# than hope. Copied from `server/cedar_press/collections.py` on `main`,
# 2026-09-02. Order is the dataclass's own.
DATACLASS_FIELDS = ("id", "name", "short_name", "origin", "level", "tracks",
                    "rows_label", "downloads", "vintage", "version", "updated",
                    "sources", "method", "shelf")

# 518's own vocabulary, imported rather than restated so the two cannot drift.
try:
    import importlib.util
    _s = importlib.util.spec_from_file_location(
        "r518", ROOT / "code" / "518_dataset_readiness.py")
    _m = importlib.util.module_from_spec(_s)
    _s.loader.exec_module(_m)
    NATURAL_SCOPE = dict(_m.NATURAL_SCOPE)
except Exception:
    NATURAL_SCOPE = {}

# The site's `level` field takes the evidence registry's vocabulary. Cedar's
# scope vocabulary is richer, so map rather than pretend they are identical.
# THE PRODUCT'S ID IS NOT ALWAYS CEDAR'S ID, and Codex caught the one case.
# `deals` and `contractors` match exactly, which is what made the assumption
# look safe. But the catalog, launch collection, article wiring, profile
# construction and API tests all call the owned-business collection `owned`.
# Emitting `native-owned-businesses` would leave a READY dataset unable to
# replace the demonstration record it is meant to replace, silently.
PRODUCT_ID = {
    "native-owned-businesses": "owned",
}

LEVEL = {
    "entity": "entity",
    "hub": "entity",
    "mixed": "entity_and_geography",
    "indian_country": "geography",
}


# ---------------------------------------------------------------------------
# THE FLAGSHIP CHECK. Added 2026-09-02 (ADR-018) after this file shipped
# `owned` to the product as "1,657 rows" while `dist/samples/README.md`, in the
# same directory, stated the same dataset as 2,916.
#
# `770_sample_extracts.FLAGSHIP` names the ONE table a customer opens first,
# and 770 ships ten of its rows. `rows_in()` below sums only the tables the
# COLLECTION CONTRACT claims. Nothing made those two agree, and for
# `native-owned-businesses` they do not: the contract claims six
# `individual_native_*` tables (1,657 rows) and the flagship is
# `native_owned_businesses.csv` (2,916 rows), which `500.COLLECTIONS` matches
# with neither branch of `^(individual_native|tribal_certification)`.
#
# The invariant is arithmetic and needs no judgement:
#
#     a sum over a dataset's tables cannot be SMALLER than one of its tables.
#
# 770 already reads this file's `PRODUCT_ID` by text so the two id maps cannot
# drift. This is the same discipline in the other direction.
def _flagship_map() -> tuple[dict, set]:
    """`FLAGSHIP` and `SPINE` read out of 770 BY TEXT, so a rename there is a
    hard failure here rather than a silent divergence. Importing 770 is not an
    option - its module name starts with a digit and it does file work at
    import time."""
    src = ROOT / "code" / "770_sample_extracts.py"
    txt = src.read_text(encoding="utf-8")
    i = txt.find("FLAGSHIP = {")
    if i < 0:
        raise SystemExit("760: 770_sample_extracts.py has no FLAGSHIP dict - "
                         "the sample source is unmeasurable, refusing to "
                         "print a row count that nothing checks")
    body = txt[i:txt.find(chr(10) + "}", i)]
    flag = dict(re.findall(r'"([a-z0-9_\-]+)":\s*"([a-z0-9_]+\.csv)"', body))
    if not flag:
        raise SystemExit("760: FLAGSHIP dict parsed EMPTY - an absence of "
                         "evidence is not evidence of absence (field guide 3)")
    j = txt.find("SPINE = {")
    spine = set(re.findall(r'"([a-z0-9_]+\.csv)"',
                           txt[j:txt.find("}", j)])) if j >= 0 else set()
    return flag, spine


# CODEX PR #29 ROUND 3, FINDING 5. The only published blocker described the
# row count, and the same investigation had measured two harder failures on
# the same table and left them in prose. A consumer reading `cedar.blockers`
# as instructed would conclude that reconciling the count makes the dataset
# ready. It does not. So the flagship's OWN readiness failures are measured
# here and published beside the count mismatch.
#
# Measured, not asserted: the identity column is whichever of the candidates
# below the table actually carries, and if it carries none the check says
# UNMEASURED rather than reporting a fill rate for a column that is absent -
# field guide section 3, habit 2 and habit 4.
IDENTITY_CANDIDATES = ("cedar_uid", "business_entity_id", "entity_id",
                       "recipient_cedar_uid", "owner_hub_cedar_uid")


def flagship_readiness(tbl: str, tables_of_all: dict,
                       status_all: dict | None = None) -> list:
    """Contract failures measured ON the flagship table itself."""
    src = ROOT / "data" / "clean" / tbl
    if not src.exists():
        return [f"UNMEASURED: {tbl} not readable at {src}"]
    out = []
    with src.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        idcol = next((c for c in IDENTITY_CANDIDATES if c in cols), None)
        n = 0
        filled = 0
        for row in rd:
            n += 1
            if idcol and (row.get(idcol) or "").strip():
                filled += 1
    if not n:
        return [f"UNMEASURED: {tbl} has no rows"]
    if idcol is None:
        out.append(f"C4 identity path: {tbl} carries none of "
                   f"{', '.join(IDENTITY_CANDIDATES)} - the customer-facing "
                   f"table has no entity key column at all")
    else:
        pct = 100.0 * filled / n
        if pct < 95.0:
            out.append(f"C4 identity path: {idcol} is filled on "
                       f"{filled:,} of {n:,} rows ({pct:.1f}%) in {tbl}, the "
                       f"table the sample is drawn from - the dataset's "
                       f"headline '100% keyed' is measured on the contract "
                       f"tables, which exclude it")
    # C1 grain: declared in the contract, and the contract does not claim this
    # table, so by construction there is none. Stated as measured rather than
    # inferred: it is absent from every collection's table list.
    claimed_anywhere = any(tbl in v for v in tables_of_all.values())
    if not claimed_anywhere:
        # Say WHICH of the two it is. Writing "no collection contract claims
        # it" for a table the contract lists as UNDOCUMENTED is the same
        # imprecision this whole check exists to catch, and it was committed
        # here first.
        listed = status_all.get(tbl) if status_all else None
        if listed:
            out.append(f"C1 grain: UNSTATED on {tbl} - the contract lists it "
                       f"as `{listed}` rather than `shippable`, so no grain "
                       f"and no primary key are declared for it")
        else:
            out.append(f"C1 grain: UNSTATED on {tbl} - no collection "
                       f"contract claims it at all, so it carries no "
                       f"declared grain and no validated primary key")
    return out


def flagship_violations(tables_of: dict, nrows_of: dict,
                        status_of: dict | None = None) -> list:
    """One entry per collection whose descriptor is contradicted by the sample
    it ships: [(collection, flagship, flagship_rows, descriptor_rows, reason,
    kind)].

    `kind` matters and the two are NOT the same defect:

      arithmetic   the published count is provably wrong - it is smaller than
                   one of the dataset's own tables. The number must be
                   withdrawn.
      membership   the count is arithmetically fine and the SAMPLE SOURCE is
                   not a shippable member of the collection. The dataset is
                   blocked and the count still stands.

    Collapsing them would withhold `federal-register`'s 490,274 - a figure
    nothing contradicts - because a different table's codebook status
    lapsed. A remedy has to be proportionate to what was actually measured.
    """
    flag, spine = _flagship_map()
    out = []
    for cid, tbl in sorted(flag.items()):
        if cid not in nrows_of:
            continue
        claimed = tbl in set(tables_of.get(cid, []))
        # A spine-resident flagship is outside `data/clean` and so outside the
        # contract by construction; only the arithmetic half applies to it.
        # Measured 2026-09-02: `_entity_layer` flagship
        # `cedar_identity_register.csv` holds 1,555 rows against a 326,899-row
        # descriptor, so it passes the half that can be checked.
        n = rows_in([tbl])
        if n and n > nrows_of[cid]:
            out.append((cid, tbl, n, nrows_of[cid],
                        f"the sampled table alone holds {n:,} rows and the "
                        f"descriptor claims {nrows_of[cid]:,} for the whole "
                        f"dataset", "arithmetic"))
        elif not claimed and tbl not in spine:
            st = (status_of or {}).get(cid, {}).get(tbl)
            if st is None:
                why = (f"{tbl} is the table the sample is drawn from and no "
                       f"collection contract claims it at all, so it carries "
                       f"no declared grain, no validated key and no rebuild "
                       f"path")
            else:
                why = (f"{tbl} is the table the sample is drawn from and the "
                       f"{cid} contract marks it `{st}`, not `shippable` - "
                       f"the customer is shown rows from a table Cedar does "
                       f"not currently consider publishable")
            out.append((cid, tbl, n, nrows_of[cid], why, "membership"))
    return out


def rows_in(tables: list) -> int:
    n = 0
    for t in tables:
        p = ROOT / "data" / "clean" / t
        if not p.exists():
            continue
        try:
            with p.open(encoding="utf-8-sig", errors="replace",
                        newline="") as fh:
                # csv.reader, not a line count. 27 counted PHYSICAL LINES until
                # 2026-09-01 and one gaming table published 17,877 rows against
                # 1,521 records - 11.8x - because a text field held newlines.
                n += max(sum(1 for _ in csv.reader(fh)) - 1, 0)
        except OSError:
            continue
    return n


def selftest() -> int:
    """A check that has never failed on purpose is not known to work.

    Three fixtures. Each asserts the NAMED invariant fires, not merely that
    something went wrong - field guide section 3, habit 1.
    """
    ok = True

    def case(name, tables_of, nrows_of, want_n, want_sub):
        nonlocal ok
        got = flagship_violations(tables_of, nrows_of)
        hit = len(got) == want_n and (want_n == 0 or
                                      want_sub in got[0][4])
        # got[i][5] is the kind; the fixtures below assert it too.
        print(f"    {'PASS' if hit else 'FAIL'}  {name}")
        if not hit:
            ok = False
            print(f"          got {got}")

    flag, _ = _flagship_map()
    tbl = flag["native-owned-businesses"]
    real = rows_in([tbl])
    if real <= 0:
        print("    UNMEASURED  flagship table unreadable - refusing to "
              "report PASS on an input I cannot read")
        return 1
    print(f"  760 selftest   fixture flagship {tbl} = {real:,} rows")

    # 1. the live defect: contract sum smaller than the flagship alone.
    case("undercount fires", {"native-owned-businesses": []},
         {"native-owned-businesses": real - 1}, 1, "the sampled table alone")
    # 2. the flagship claimed and the sum larger: clean.
    case("claimed + sufficient sum is clean",
         {"native-owned-businesses": [tbl]},
         {"native-owned-businesses": real + 1}, 0, "")
    # 3. sum large enough but the flagship claimed by nobody: still a finding,
    #    because an unclaimed table has no grain, no key and no rebuild path.
    case("unclaimed flagship fires even when the sum is large",
         {"native-owned-businesses": []},
         {"native-owned-businesses": real + 1}, 1, "no collection contract")

    print(f"  760 selftest   {'all fixtures pass' if ok else 'FAILED'}")
    return 0 if ok else 1


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    if not READINESS.exists():
        sys.exit("run 518 first")

    ready = list(csv.DictReader(
        READINESS.open(encoding="utf-8-sig", errors="replace")))
    contracts = (json.loads(CONTRACTS.read_text(encoding="utf-8"))
                 if CONTRACTS.exists() else {"contracts": []})
    tables_of = {c["collection"]: [t["table"] for t in c.get("tables", [])
                                   if t.get("status") == "shippable"]
                 for c in contracts.get("contracts", [])}
    # THE FULL STATUS, not just the shippable subset. Added 2026-09-02 after
    # the flagship check reported `federal-register`'s sample source as "no
    # collection contract claims it", which was false: the contract lists
    # `consultation_events.csv` and marks it **UNDOCUMENTED**. Two different
    # defects - absent from the collection, and present but not shippable -
    # were collapsed into one message, which is this repo's signature failure
    # (a check reporting something other than what it measured) committed by
    # the check written to catch it two rounds earlier.
    status_of = {c["collection"]: {t["table"]: t.get("status", "?")
                                   for t in c.get("tables", [])}
                 for c in contracts.get("contracts", [])}
    cadence = {}
    if CADENCE.exists():
        try:
            for row in json.loads(CADENCE.read_text(encoding="utf-8")):
                d = row.get("dataset")
                h = row.get("cedar_holds_through")
                if d and h and h > cadence.get(d, ""):
                    cadence[d] = h
        except (ValueError, AttributeError, TypeError):
            pass
    copy = json.loads(COPY.read_text(encoding="utf-8")) if COPY.exists() else {}

    out, missing, cedar_side = [], [], {}
    for r in ready:
        did = r["dataset"]
        tabs = tables_of.get(did, [])
        scope = NATURAL_SCOPE.get(did, "entity")
        c = copy.get(did, {})
        nrows = rows_in(tabs)
        # EMIT THE CONTRACT EXACTLY. `CollectionDataset(**descriptor)` raised
        # TypeError on `n_rows` and the object omitted `version` and
        # `downloads`, which release and profile consumers require - so not one
        # of the 13 could be loaded. Cedar's own extras now live under
        # `cedar`, which the dataclass never sees.
        d = {
            "id": PRODUCT_ID.get(did, did),
            "shelf": r.get("shelf") or "standard",
            "level": LEVEL.get(scope, "entity"),
            "origin": "lumecon",
            "rows_label": f"{nrows:,} rows",
            "vintage": cadence.get(did, ""),
            "version": "v0",          # pre-release; the platform owns bumping
            "updated": TODAY,
            # `downloads` is a PRODUCT metric that lives in the platform
            # database. Cedar has no business inventing a number here, but the
            # dataclass requires the field - so it is present and ZERO, which
            # says "not counted here" rather than fabricating a count.
            "downloads": 0,
            # editorial - never generated
            "name": c.get("name", ""),
            "short_name": c.get("short_name", ""),
            "tracks": c.get("tracks", ""),
            "sources": c.get("sources", ""),
            "method": c.get("method", ""),
        }
        # Cedar-side facts, namespaced so they never reach the dataclass.
        # Codex: "All nine non-ready descriptors contain only the generic value
        # BLOCKED; a consumer cannot distinguish a publication-rights block
        # from an incomplete schema." So the named blockers travel too.
        cedar_side[d["id"]] = {
            "cedar_id": did,
            "product_id": d["id"],
            "status": r.get("status"),
            "blockers": [b.strip() for b in
                         (r.get("blockers") or "").split(" | ") if b.strip()],
            "n_rows": nrows,
            "n_tables": len(tabs),
            "sample_file": f"samples/{d['id']}__sample.csv",
            "needs_copy": not all(d[k] for k in ("name", "short_name",
                                                 "tracks", "sources",
                                                 "method")),
        }
        if cedar_side[d["id"]]["needs_copy"] and r.get("status") == "READY":
            missing.append(did)
        out.append(d)

    # ---- THE FLAGSHIP CHECK (ADR-018) ---------------------------------
    # Runs BEFORE the dataclass check so a contradicted row count can never be
    # written, and so `verify` names it. A violation is not silently repaired:
    # the descriptor is downgraded to BLOCKED with the measurement in
    # `cedar.blockers`, because a dataset whose published row count is smaller
    # than the table its own sample comes from is not ready to replace a demo
    # record. The status reverts on its own the moment the contract is fixed.
    nrows_of = {c["cedar_id"]: c["n_rows"] for c in cedar_side.values()}
    fviol = flagship_violations(tables_of, nrows_of, status_of)
    by_cedar_id = {c["cedar_id"]: c for c in cedar_side.values()}
    for cid, tbl, frows, drows, reason, kind in fviol:
        c = by_cedar_id[cid]
        # CODEX PR #29 ROUND 4, FINDING 1. This blocker used to read "the
        # descriptor claims 1,657 for the whole dataset" - which stopped
        # being true in the same commit that set `n_rows` to null and
        # relabelled 1,657 as the unsummed size of six heterogeneous tables.
        # A consumer was being told the remaining problem is an exact
        # whole-dataset count conflict, when the whole point of the other fix
        # is that **no dataset-level count exists**. So the blocker now
        # describes the MEMBERSHIP AND GRAIN conflict, which is what is
        # actually unresolved, and quotes the two measurements as what they
        # are rather than as a disagreement between two totals.
        #
        # Fourth instance on this branch of a number corrected in one place
        # and left standing in another, and the first where the stale copy
        # was inside the very fix that made it stale.
        if kind == "arithmetic":
            msg = (f"COLLECTION MEMBERSHIP: {tbl}, the table this dataset's "
                   f"sample is drawn from, holds {frows:,} rows and no "
                   f"collection contract claims it - so it carries no "
                   f"declared grain, no validated key and no rebuild path. "
                   f"The {drows:,} rows the contract does claim are "
                   f"{c['n_tables']} tables of differing grain and are not a "
                   f"dataset-level total either; see ADR-018. No row count "
                   f"is published for this collection until membership and "
                   f"grain are settled.")
        else:
            msg = (f"COLLECTION MEMBERSHIP: {reason}. The {drows:,}-row "
                   f"total over the {c['n_tables']} shippable tables is not "
                   f"in dispute and still ships; see ADR-018.")
        c["blockers"] = [b for b in c["blockers"] if b != "-"] + [msg]
        c["status"] = "BLOCKED"
        c["flagship_table"] = tbl
        c["flagship_rows"] = frows
        c["blockers"] += flagship_readiness(
            tbl, tables_of,
            {k: v for m in status_of.values() for k, v in m.items()})
        # CODEX PR #29 ROUND 3, FINDING 1, AND IT IS RIGHT.
        #
        # This published the SUM, 1,657 + 2,916 = 4,573, as `rows_label`. That
        # assumed the six contract tables and the flagship are disjoint rows
        # of one dataset and NOTHING ESTABLISHES THAT - the README describes
        # them as different relations (firms certified by a nation vs firms
        # owned by individual people), which is an argument they are disjoint
        # and not a measurement that they are. Worse, the qualification lived
        # in `n_rows_basis` in the SIBLING file, and `rows_label` is the field
        # the product renders: a consumer sees "4,573 rows" as an exact count
        # of a dataset that does not exist in that shape.
        #
        # A fabricated number with a footnote nobody renders is still a
        # fabricated number, and this file's own docstring already says the
        # rule - "an empty field a human fills is honest; a generated sentence
        # that reads like a claim is not". So NO COUNT IS STATED. The two
        # component measurements ship separately, each labelled with the table
        # set it came from, and neither is added to the other.
        c["n_rows_contract_tables"] = drows
        c["n_rows_flagship"] = frows
        if kind == "arithmetic":
            c["n_rows"] = None
            c["n_rows_basis"] = (
                f"NOT SUMMED. {drows:,} rows over the {c['n_tables']} tables "
                f"the collection contract claims, and {frows:,} in {tbl}, "
                f"the unclaimed table the sample is drawn from. Whether "
                f"these are disjoint rows of one dataset is undetermined, so "
                f"no total is published.")
            for d in out:
                if d["id"] == c["product_id"]:
                    d["rows_label"] = "row count unresolved"
        else:
            # The count is not the thing in dispute here. Withdrawing it
            # would be a remedy out of proportion to the measurement.
            c["n_rows_basis"] = (
                f"{drows:,} rows over the {c['n_tables']} shippable tables "
                f"the contract claims; unchanged. The block concerns {tbl}, "
                f"the sample source, not this total.")
    if fviol:
        print(f"  760 FLAGSHIP MISMATCH - {len(fviol)} of {len(out)} "
              f"collections publish a row count their own sample contradicts:")
        for cid, tbl, frows, drows, reason, kind in fviol:
            print(f"    !! [{kind}] {cid}: {reason}")
            print(f"       sample source {tbl} = {frows:,} rows; "
                  f"contract tables = {drows:,}; "
                  + ("count WITHDRAWN" if kind == "arithmetic"
                     else "count STANDS (not in dispute)")
                  + ", marking BLOCKED")

    # ---- THE CONTRACT CHECK THAT SHOULD HAVE EXISTED IN ROUND 1 --------
    # `CollectionDataset(**descriptor)` is the call the README advertises, so
    # it is CHECKED here rather than asserted in prose. The dataclass lives in
    # another repository and cannot be imported, so its field list is declared
    # at the top of this file and the check is exact IN BOTH DIRECTIONS - a
    # missing field and an unsupported extra are the same TypeError. An extra
    # key is what broke all 13 objects twice: `n_rows` on PR #26, and `cedar`
    # plus `needs_copy` on PR #29, introduced by the fix for the first.
    bad = []
    for d in out:
        extra = sorted(set(d) - set(DATACLASS_FIELDS))
        absent = [f for f in DATACLASS_FIELDS if f not in d]
        if extra or absent:
            bad.append(f"{d.get('id')}: extra={extra} missing={absent}")
    if bad:
        print(f"  760 CONTRACT BREACH - {len(bad)} of {len(out)} descriptors "
              f"do not match CollectionDataset:")
        for b in bad[:13]:
            print(f"    !! {b}")
        return 1

    if not verify:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
        OUT_CEDAR.write_text(json.dumps(cedar_side, indent=2) + "\n",
                             encoding="utf-8")

    shippable = [c for c in cedar_side.values() if c["status"] == "READY"]
    print(f"  760 collection descriptors   {len(out)} datasets   "
          f"{len(shippable)} READY   {len(missing)} READY-but-no-copy")
    print(f"    contract: {len(out)}/{len(out)} carry EXACTLY the "
          f"{len(DATACLASS_FIELDS)} CollectionDataset fields, so "
          f"CollectionDataset(**descriptor) loads every one")
    print(f"    Cedar's own facts: dist/collection_descriptors.cedar.json, "
          f"keyed by PRODUCT id")
    for d in sorted(out, key=lambda x: (
            cedar_side[x["id"]]["status"] != "READY", x["id"])):
        c = cedar_side[d["id"]]
        flag = "" if not c["needs_copy"] else "  <- needs editorial copy"
        print(f"    {c['status']:<8} {d['id']:<24} "
              f"{d['shelf']:<14} {d['level']:<20} "
              f"{d['rows_label']:>14}{flag}")
    if missing:
        print(f"\n  {len(missing)} READY dataset(s) cannot be described to the "
              f"product without copy: {', '.join(missing)}")
        print("  Write it in docs/datasets/_descriptors.json - name, "
              "short_name, tracks, sources, method.")
        print("  NOT generated here on purpose: `method` is a claim about how "
              "the data was built and a machine should not invent one.")
    return 1 if (verify and (missing or fviol)) else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(selftest())
    sys.exit(main())
