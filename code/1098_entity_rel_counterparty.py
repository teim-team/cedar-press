#!/usr/bin/env python3
"""
Cedar Press - 1098: THE BLANK ENDPOINT IN entity_relationships IS NOT MISSING
                    DATA. IT IS AN ENTITY CEDAR DECIDED NOT TO MINT, WHOSE
                    IDENTITY IS RECORDED ONLY IN AN ENGLISH SENTENCE.

    py -3 code/1098_entity_rel_counterparty.py            # enrich in place
    py -3 code/1098_entity_rel_counterparty.py verify     # exit 1 on breach
    py -3 code/1098_entity_rel_counterparty.py selftest   # prove verify FIRES

WHAT WAS MEASURED, AND WHERE THE STANDING NUMBER IS WRONG
----------------------------------------------------------
`AGENTS.md` names `entity_relationships.csv` as the ownership source of truth.
1,772 of its 2,292 rows (77.3%) carry a blank endpoint, and the standing read of
that is *"996 recover a UEI only from prose; 466 recover nothing."*

**The 466 recover a CAGE code.** Measured on the live file, every one of the
1,462 `owned_by` rows parses cleanly:

    firm '<LEGAL NAME>' (UEI <12 chars>)  is owned by ...      996
    firm '<LEGAL NAME>' (CAGE <5 chars>)  is owned by ...      466
    unparsed                                                     0

So the recovery rate on the ownership edges is **1,462 of 1,462, 100%** - a firm
name AND a published federal identifier on every row. Nothing is unrecoverable;
it was unREADABLE, which is a different defect with a much cheaper fix.

The other three families are the same shape:

    owned_by          1,462  blank source  firm name + UEI or CAGE in prose
    affiliated_with     148  blank target  TDHE published name in prose
                                           (7 of the 148 also have a blank
                                            source - the tribe did not resolve)
    brand_of            106  blank source  brand family + CEDAR-ALIAS id
    operated_by          56  blank target  "the United States (Dept of the
                                            Interior, BIE)" - a DECLARED
                                            non-entity, not a hole
    ------------------------------------
    1,772 rows / 1,779 blank endpoint cells

WHY THE FIX IS NOT "MINT THE MISSING ENTITIES"
-----------------------------------------------
`docs/IDENTIFIER_STANDARD.md` §2 settles it: **a UEI or a CAGE identifies a
REGISTRATION, and a registration is a sub-hub, never a spine row.** The blank
`source_entity_id` on an `owned_by` edge is therefore CORRECT - the notes say so
in as many words ("No spine entity for the firm and no intermediate holding
layer invented"). Minting 1,462 spine entities to fill the column would put
1,462 non-entities into the entity namespace and invert the hub model.

A brand family is likewise "a name family, not a legal person", and the federal
government is deliberately absent from a register of Native entities.

The defect is that the identity of the counterparty is only in prose. So this
pass promotes it into declared columns, verbatim, and links it to the sub-hub
register that DOES have ids for enterprises - NEST.

WHAT THE NEST LINK IS, AND WHAT IT IS NOT
------------------------------------------
`data/spine/cedar_nest_id_register.csv` holds 1,610 `CEDAR-NEST-` ids. It is
**not a parallel entity space**: an owned enterprise is a sub-hub of its owning
nation, exactly like a facility or a registration, and `CEDAR-NEST-` is the
sub-hub prefix for the enterprise level. The spine register keys HUBS; the NEST
register keys one class of SUB-HUB under them. Every NEST row already carries
`owner_hub_cedar_uid` pointing into the spine, which is the whole relation.

This pass makes the bridge visible in the other direction. A firm on an
`owned_by` edge is resolved to a NEST enterprise only when BOTH sides agree on
the owner:

    rung 1  the firm's PUBLISHED UEI equals a NEST enterprise's published UEI
    rung 2  the firm's PUBLISHED CAGE equals a NEST enterprise's published CAGE
    rung 3  the normalised firm name is UNIQUE among the NEST enterprises whose
            `owner_hub_handle` is this edge's own owner

Rung 3 is a name method and would be weak alone; it is admitted only because the
owner hub is fixed by the edge, which is the independent corroborator
`ENTITY_MATCH_RULES` step 3 asks for. A name matching two enterprises under one
hub resolves to neither.

**NEST's own `uei_candidate` is NOT used to link.** It is an exact-name proposal
into the SBA DSBS extract, not a published identifier. 23 further edges would
resolve through it; they are counted in the report and deliberately not written,
because a candidate on one side plus a candidate on the other is not evidence.

**AND WHERE THE TWO SIDES DISAGREE ABOUT THE OWNER, NEITHER WINS.** A published
UEI matching a NEST enterprise whose owner hub is NOT this edge's owner is
refused, the refusal is written into `counterparty_nest_basis`, and the case
goes to `review/entity_rel_nest_owner_conflicts_<date>.csv`. One fired, and it
is the first cross-source ownership disagreement the entity layer has produced:

    Laulima Government Solutions, LLC   UEI QTJZT9K41S61
      entity_relationships  ->  Bering Straits Native Corporation  ANRC-BERSTR-00
                                tier A, "Ruled by Elijah 2026-08-06:
                                re-attributed ... the earlier claim was wrong"
      nest / shard-H        ->  Alaka'ina Foundation               NHO-ALAKAI-00
                                parent_declared_subsidiary_list,
                                source http://beringalakaina.com/

The source host names BOTH parents. `ENTITY_MATCH_RULES` rule 11 - a joint
venture genuinely has two parents - so this is very likely a JV recorded as sole
ownership on each side independently, which is precisely the defect NEST names
itself most exposed to. It is REFUSED, not reconciled, and no row on either side
was altered.

MEASURED
--------
    counterparty promoted from prose                 1,772 / 1,772  100.0%
      with a published federal identifier            1,462  (UEI 996, CAGE 466)
      with a Cedar alias id                            106
      named but with no identifier (TDHE)              148
      declared non-entity (the United States)           56
      UNPARSED                                           0
    resolved to a NEST enterprise sub-hub              262  of 1,462  17.9%
      rung 1  published UEI                             29
      rung 2  published CAGE                             0
      rung 3  unique name under the same owner hub     233
      refused, owner disagreement                        1
      not resolved                                   1,200
      (23 more would resolve through NEST's
       uei_candidate and are REFUSED - see above)

THE NAMED INVARIANTS
--------------------
  I1  every blank-endpoint row carries a `counterparty_kind` from the declared
      vocabulary and a non-blank `counterparty_name_as_recorded`.
  I2  ANTI-FABRICATION. every promoted name and identifier appears VERBATIM as
      a substring of that row's own `notes`. A value that does not survive that
      test is not written.
  I3  every `counterparty_nest_enterprise_id` exists in nest_enterprises.csv AND
      its `owner_hub_handle` equals the edge's populated endpoint. A NEST link
      that crosses owners is refused, not reconciled.
  I4  a row with BOTH endpoints populated carries no counterparty columns. This
      enricher may not describe an edge that is already complete.
  I5  CONSERVE. row count unchanged, no column lost, and the md5 of the 16 base
      fields is unchanged - so no endpoint, tier or evidence cell was touched.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

TABLE = ROOT / "data" / "clean" / "entity_relationships.csv"
NEST = ROOT / "data" / "clean" / "nest_enterprises.csv"
MANIFEST = ROOT / "docs" / "ENTITY_REL_COUNTERPARTY.json"
BAK_TAG = f".bak_{TODAY}_pre_1098_entity_rel_counterparty"
CONFLICTS = ROOT / "review" / f"entity_rel_nest_owner_conflicts_{TODAY}.csv"

NEW = [
    "counterparty_side",
    "counterparty_kind",
    "counterparty_name_as_recorded",
    "counterparty_identifier_type",
    "counterparty_identifier",
    "counterparty_identity_state",
    "counterparty_nest_enterprise_id",
    "counterparty_nest_basis",
    "counterparty_extraction_basis",
]

KINDS = {
    "firm_registration",
    "brand_family",
    "tribal_designated_housing_entity",
    "federal_government",
}
STATES = {
    "NAMED_SUB_HUB_WITH_PUBLISHED_IDENTIFIER",
    "NAMED_SUB_HUB_NO_IDENTIFIER",
    "NAMED_NAME_FAMILY_NOT_A_LEGAL_PERSON",
    "DECLARED_NON_ENTITY_OUT_OF_SCOPE",
}

# -- the four prose shapes, each anchored so a partial sentence cannot match --
RE_FIRM = re.compile(r"^firm '(?P<name>.+)' \((?P<ityp>UEI|CAGE) "
                     r"(?P<ival>[A-Z0-9]+)\) is owned by ")
RE_BRAND = re.compile(r"^brand family '(?P<name>.+?)' has no spine entity"
                      r".*?Identified by alias_id (?P<alias>CEDAR-ALIAS-\d+)\.")
RE_TDHE = re.compile(r"^TDHE published name: '(?P<name>.+?)'\. ")
RE_FED = re.compile(r"^Operated by (?P<name>the United States "
                    r"\(Dept of the Interior, Bureau of Indian Education\))\.")

TOK = re.compile(r"[^A-Z0-9]+")
#: Company-form and article words. Stripped before a name is compared so
#: `Ho-Chunk, Inc.` and `HO CHUNK INC` are one name - and NOTHING else is
#: stripped, because stripping a distinctive word is how a name match starts
#: winning on nothing (ENTITY_MATCH_RULES rule 1).
FORMS = {"INC", "INCORPORATED", "LLC", "L", "C", "LTD", "LIMITED", "CO",
         "CORP", "CORPORATION", "COMPANY", "LP", "LLP", "PC", "PLLC", "THE",
         "PLC"}


def norm(s: str) -> str:
    return " ".join(t for t in TOK.split((s or "").upper())
                    if t and t not in FORMS)


def read_table(p: Path):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        r = csv.DictReader(fh)
        return [dict(x) for x in r], list(r.fieldnames or [])


def write_table(p: Path, rows, fields, tag=None):
    if p.exists() and tag:
        b = p.with_name(p.name + tag)
        if not b.exists():
            shutil.copy2(p, b)
    tmp = p.with_suffix(p.suffix + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(p)


def base_digest(rows, base_fields):
    h = hashlib.md5()
    for r in rows:
        for c in base_fields:
            h.update((r.get(c) or "").encode("utf-8"))
            h.update(b"\x1f")
        h.update(b"\x1e")
    return h.hexdigest()


def nest_index():
    """(by published UEI, by published CAGE, by (owner handle, norm name))."""
    if not NEST.exists():
        return {}, {}, {}, {}, {}, {}, {}, {}, {}
    rows, _ = read_table(NEST)
    byuei, bycage, byname, cand = {}, {}, {}, {}
    owner, oname, orel, oev, ourl = {}, {}, {}, {}, {}
    for r in rows:
        eid = (r.get("enterprise_id") or "").strip()
        hub = (r.get("owner_hub_handle") or "").strip()
        u = (r.get("uei") or "").strip().upper()
        c = (r.get("cage_code") or "").strip().upper()
        uc = (r.get("uei_candidate") or "").strip().upper()
        if u:
            byuei.setdefault(u, set()).add(eid)
        if c and c != "NAN":
            bycage.setdefault(c, set()).add(eid)
        if uc:
            cand.setdefault(uc, set()).add(eid)
        byname.setdefault((hub, norm(r.get("enterprise_name"))),
                          set()).add(eid)
        owner[eid] = hub
        oname[eid] = (r.get("owner_hub_name") or "").strip()
        orel[eid] = (r.get("relationship") or "").strip()
        oev[eid] = (r.get("evidence_class") or "").strip()
        ourl[eid] = (r.get("source_url") or "").strip()
    return byuei, bycage, byname, cand, owner, oname, orel, oev, ourl


def classify(r: dict):
    """Return the counterparty fields for one row, or None if the edge is
    complete. Every value returned is a VERBATIM substring of `notes`."""
    src = (r.get("source_entity_id") or "").strip()
    tgt = (r.get("target_entity_id") or "").strip()
    if src and tgt:
        return None
    if src and not tgt:
        side = "target"
    elif tgt and not src:
        side = "source"
    else:
        side = "both"
    notes = r.get("notes") or ""

    m = RE_FIRM.match(notes)
    if m:
        return dict(side=side, kind="firm_registration",
                    name=m.group("name"),
                    ityp=m.group("ityp"), ival=m.group("ival"),
                    state="NAMED_SUB_HUB_WITH_PUBLISHED_IDENTIFIER",
                    basis="notes:firm '<name>' (<UEI|CAGE> <id>) is owned by")
    m = RE_BRAND.match(notes)
    if m:
        return dict(side=side, kind="brand_family", name=m.group("name"),
                    ityp="CEDAR_ALIAS_ID", ival=m.group("alias"),
                    state="NAMED_NAME_FAMILY_NOT_A_LEGAL_PERSON",
                    basis="notes:brand family '<name>' ... alias_id <id>")
    m = RE_TDHE.match(notes)
    if m:
        return dict(side=side, kind="tribal_designated_housing_entity",
                    name=m.group("name"), ityp="", ival="",
                    state="NAMED_SUB_HUB_NO_IDENTIFIER",
                    basis="notes:TDHE published name: '<name>'")
    m = RE_FED.match(notes)
    if m:
        return dict(side=side, kind="federal_government",
                    name=m.group("name"), ityp="", ival="",
                    state="DECLARED_NON_ENTITY_OUT_OF_SCOPE",
                    basis="notes:Operated by the United States (...BIE)")
    return dict(side=side, kind="", name="", ityp="", ival="",
                state="", basis="UNPARSED")


def build(dry_run=False) -> int:
    rows, fields = read_table(TABLE)
    base_fields = [c for c in fields if c not in NEW]
    before_digest = base_digest(rows, base_fields)
    n_before = len(rows)

    (byuei, bycage, byname, cand, nest_owner, nest_owner_name,
     nest_rel, nest_ev, nest_url) = nest_index()
    conflicts = []

    out_fields = list(fields) + [c for c in NEW if c not in fields]
    stats = {"rows": n_before, "blank_endpoint_rows": 0, "unparsed": 0,
             "kind": {}, "identifier_type": {}, "identity_state": {},
             "nest_rung1_published_uei": 0, "nest_rung2_published_cage": 0,
             "nest_rung3_unique_name_under_owner": 0,
             "nest_unresolved": 0,
             "nest_refused_ambiguous_under_owner": 0,
             "nest_refused_owner_disagreement": 0,
             "nest_would_resolve_via_nest_uei_candidate_REFUSED": 0}

    for r in rows:
        for c in NEW:
            r.setdefault(c, "")
        cp = classify(r)
        if cp is None:
            for c in NEW:
                r[c] = ""
            continue
        stats["blank_endpoint_rows"] += 1
        if cp["basis"] == "UNPARSED":
            stats["unparsed"] += 1
        r["counterparty_side"] = cp["side"]
        r["counterparty_kind"] = cp["kind"]
        r["counterparty_name_as_recorded"] = cp["name"]
        r["counterparty_identifier_type"] = cp["ityp"]
        r["counterparty_identifier"] = cp["ival"]
        r["counterparty_identity_state"] = cp["state"]
        r["counterparty_extraction_basis"] = cp["basis"]
        stats["kind"][cp["kind"] or "(unparsed)"] = \
            stats["kind"].get(cp["kind"] or "(unparsed)", 0) + 1
        stats["identifier_type"][cp["ityp"] or "(none)"] = \
            stats["identifier_type"].get(cp["ityp"] or "(none)", 0) + 1
        stats["identity_state"][cp["state"] or "(unparsed)"] = \
            stats["identity_state"].get(cp["state"] or "(unparsed)", 0) + 1

        if cp["kind"] != "firm_registration":
            continue
        owner = (r.get("target_entity_id") or "").strip()
        eid, basis = "", ""
        if cp["ityp"] == "UEI":
            s = byuei.get(cp["ival"], set())
            if len(s) == 1:
                c_eid = next(iter(s))
                if nest_owner.get(c_eid) == owner:
                    eid, basis = c_eid, \
                        "rung1_published_uei_equals_nest_published_uei"
                    stats["nest_rung1_published_uei"] += 1
                else:
                    basis = ("REFUSED_owner_disagreement_on_published_uei:"
                             f"{c_eid}:nest_owner={nest_owner.get(c_eid)}")
                    stats["nest_refused_owner_disagreement"] += 1
                    conflicts.append({
                        "relationship_id": r.get("relationship_id"),
                        "firm_name_as_recorded": cp["name"],
                        "identifier_type": cp["ityp"],
                        "identifier": cp["ival"],
                        "entity_relationships_owner": owner,
                        "entity_relationships_evidence":
                            r.get("evidence_text") or "",
                        "entity_relationships_tier": r.get("tier") or "",
                        "nest_enterprise_id": c_eid,
                        "nest_owner_hub_handle": nest_owner.get(c_eid, ""),
                        "nest_owner_hub_name": nest_owner_name.get(c_eid, ""),
                        "nest_relationship": nest_rel.get(c_eid, ""),
                        "nest_evidence_class": nest_ev.get(c_eid, ""),
                        "nest_source_url": nest_url.get(c_eid, ""),
                        "disposition": "UNRESOLVED_TWO_DECLARED_OWNERS",
                        "note": ("Both sides assert sole ownership of one "
                                 "registration. ENTITY_MATCH_RULES rule 11: a "
                                 "joint venture genuinely has two parents, so "
                                 "two owners is not automatically one error. "
                                 "Refused rather than reconciled; no link "
                                 "written, neither side altered."),
                    })
        if not eid and cp["ityp"] == "CAGE":
            s = bycage.get(cp["ival"], set())
            if len(s) == 1:
                c_eid = next(iter(s))
                if nest_owner.get(c_eid) == owner:
                    eid, basis = c_eid, \
                        "rung2_published_cage_equals_nest_published_cage"
                    stats["nest_rung2_published_cage"] += 1
                else:
                    basis = ("REFUSED_owner_disagreement_on_published_cage:"
                             f"{c_eid}:nest_owner={nest_owner.get(c_eid)}")
                    stats["nest_refused_owner_disagreement"] += 1
        if not eid and not basis:
            s = byname.get((owner, norm(cp["name"])), set())
            if len(s) == 1:
                eid, basis = next(iter(s)), \
                    ("rung3_normalised_name_unique_among_nest_enterprises_"
                     "of_this_same_owner_hub")
                stats["nest_rung3_unique_name_under_owner"] += 1
            elif len(s) > 1:
                stats["nest_refused_ambiguous_under_owner"] += 1
        if not eid:
            stats["nest_unresolved"] += 1
            if cp["ityp"] == "UEI" and len(cand.get(cp["ival"], ())) == 1:
                stats["nest_would_resolve_via_nest_uei_candidate_REFUSED"] += 1
        r["counterparty_nest_enterprise_id"] = eid
        r["counterparty_nest_basis"] = basis

    if base_digest(rows, base_fields) != before_digest:
        print("  [1098] FATAL: a base field changed. Refusing to write.")
        return 1
    if len(rows) != n_before:
        print("  [1098] FATAL: row count moved. Refusing to write.")
        return 1

    if not dry_run:
        write_table(TABLE, rows, out_fields, tag=BAK_TAG)
    gained = [c for c in out_fields if c not in fields]
    print(f"  [1098] rows {len(rows):,} unchanged | md5(base "
          f"{len(base_fields)} fields) {before_digest}")
    print(f"  [1098] COLUMN DIFF   gained {len(gained)}: {gained}")
    print(f"  [1098]               lost   0: []")
    for k in ("kind", "identifier_type", "identity_state"):
        print(f"  [1098] {k}")
        for a, b in sorted(stats[k].items(), key=lambda kv: -kv[1]):
            print(f"          {a:<48} {b:>6,}")
    print("  [1098] NEST sub-hub resolution, owned_by firms only")
    for k in ("nest_rung1_published_uei", "nest_rung2_published_cage",
              "nest_rung3_unique_name_under_owner",
              "nest_refused_ambiguous_under_owner",
              "nest_refused_owner_disagreement", "nest_unresolved",
              "nest_would_resolve_via_nest_uei_candidate_REFUSED"):
        print(f"          {k:<56} {stats[k]:>6,}")
    print(f"  [1098] blank-endpoint rows {stats['blank_endpoint_rows']:,} | "
          f"UNPARSED {stats['unparsed']:,}")

    if conflicts and not dry_run:
        CONFLICTS.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFLICTS, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(conflicts[0].keys()))
            w.writeheader()
            w.writerows(conflicts)
        print(f"  [1098] {len(conflicts)} owner disagreement(s) -> "
              f"{CONFLICTS.relative_to(ROOT)}")

    MANIFEST.write_text(json.dumps(
        {"built": TODAY, "script": "1098_entity_rel_counterparty.py",
         "table": "data/clean/entity_relationships.csv",
         "columns_added": NEW, "base_fields_md5": before_digest,
         **stats}, indent=2), encoding="utf-8")
    print(f"  [1098] wrote {MANIFEST.relative_to(ROOT)}")
    return 0


def verify(path: Path | None = None) -> int:
    p = path or TABLE
    rows, fields = read_table(p)
    missing = [c for c in NEW if c not in fields]
    if missing:
        print(f"  [1098] verify: columns absent {missing} - run the enricher")
        return 1
    nest_rows, _ = read_table(NEST) if NEST.exists() else ([], [])
    nest_hub = {(r.get("enterprise_id") or "").strip():
                (r.get("owner_hub_handle") or "").strip() for r in nest_rows}
    fails = []
    n_blank = 0
    for r in rows:
        src = (r.get("source_entity_id") or "").strip()
        tgt = (r.get("target_entity_id") or "").strip()
        rid = r.get("relationship_id")
        notes = r.get("notes") or ""
        complete = bool(src and tgt)
        if complete:
            # I4
            if any((r.get(c) or "").strip() for c in NEW):
                fails.append(("I4", rid,
                              "complete edge carries counterparty columns"))
            continue
        n_blank += 1
        kind = (r.get("counterparty_kind") or "").strip()
        name = (r.get("counterparty_name_as_recorded") or "").strip()
        state = (r.get("counterparty_identity_state") or "").strip()
        # I1
        if kind not in KINDS:
            fails.append(("I1", rid, f"counterparty_kind {kind!r} not in "
                                     "the declared vocabulary"))
        if not name:
            fails.append(("I1", rid, "blank counterparty_name_as_recorded"))
        if state not in STATES:
            fails.append(("I1", rid,
                          f"counterparty_identity_state {state!r} off-vocab"))
        # I2 anti-fabrication
        if name and name not in notes:
            fails.append(("I2", rid, "promoted name is not a verbatim "
                                     "substring of this row's notes"))
        ival = (r.get("counterparty_identifier") or "").strip()
        if ival and ival not in notes:
            fails.append(("I2", rid, "promoted identifier is not a verbatim "
                                     "substring of this row's notes"))
        # I3
        eid = (r.get("counterparty_nest_enterprise_id") or "").strip()
        if eid:
            if eid not in nest_hub:
                fails.append(("I3", rid, f"NEST id {eid} not in "
                                         "nest_enterprises.csv"))
            elif nest_hub[eid] != tgt:
                fails.append(("I3", rid, f"NEST id {eid} owner hub "
                                         f"{nest_hub[eid]} != edge owner "
                                         f"{tgt}"))
    print(f"  [1098] verify: {len(rows):,} rows | {n_blank:,} blank-endpoint "
          f"| {len(fails)} breach(es)")
    for f in fails[:20]:
        print(f"          {f[0]}  {f[1]}  {f[2]}")
    if len(fails) > 20:
        print(f"          ... and {len(fails)-20} more")
    return 1 if fails else 0


def selftest() -> int:
    """Inject each violation into a COPY and assert verify exits 1 naming it."""
    import tempfile
    rows, fields = read_table(TABLE)
    if not any(c in fields for c in NEW):
        print("  [1098] selftest: run the enricher first")
        return 1
    tmp = Path(tempfile.mkdtemp()) / "entity_relationships.csv"
    cases = []

    def run_case(label, mutate):
        rs = [dict(r) for r in rows]
        mutate(rs)
        write_table(tmp, rs, fields)
        rc = verify(tmp)
        ok = rc == 1
        cases.append((label, ok))
        print(f"          {'FIRES ' if ok else 'SILENT'}  {label}")

    def first_blank(rs):
        for r in rs:
            if not ((r.get("source_entity_id") or "").strip()
                    and (r.get("target_entity_id") or "").strip()):
                return r
        raise SystemExit("no blank-endpoint row to mutate")

    def first_complete(rs):
        for r in rs:
            if ((r.get("source_entity_id") or "").strip()
                    and (r.get("target_entity_id") or "").strip()):
                return r
        raise SystemExit("no complete row to mutate")

    def first_nest(rs):
        for r in rs:
            if (r.get("counterparty_nest_enterprise_id") or "").strip():
                return r
        return None

    print("  [1098] selftest - inject the violation, assert exit 1")
    run_case("I1 off-vocabulary counterparty_kind",
             lambda rs: first_blank(rs).__setitem__("counterparty_kind",
                                                    "misc"))
    run_case("I1 blank counterparty_name_as_recorded",
             lambda rs: first_blank(rs).__setitem__(
                 "counterparty_name_as_recorded", ""))
    run_case("I2 fabricated name not present in notes",
             lambda rs: first_blank(rs).__setitem__(
                 "counterparty_name_as_recorded", "Acme Fabricated Holdings"))
    run_case("I2 fabricated identifier not present in notes",
             lambda rs: first_blank(rs).__setitem__(
                 "counterparty_identifier", "ZZZZZZZZZZZZ"))
    run_case("I4 counterparty column on a complete edge",
             lambda rs: first_complete(rs).__setitem__("counterparty_kind",
                                                       "firm_registration"))
    if first_nest(rows) is not None:
        run_case("I3 NEST id that is not in nest_enterprises.csv",
                 lambda rs: first_nest(rs).__setitem__(
                     "counterparty_nest_enterprise_id",
                     "CEDAR-NEST-999999-ZZ"))

        def cross(rs):
            r = first_nest(rs)
            r["target_entity_id"] = "TRBF-NOTTHEOWNER-00"
        run_case("I3 NEST id whose owner hub is not the edge's owner", cross)

    write_table(tmp, rows, fields)
    rc = verify(tmp)
    print(f"          {'PASS  ' if rc == 0 else 'FAIL  '}  restored copy "
          f"verifies clean (exit {rc})")
    ok = all(c[1] for c in cases) and rc == 0
    print(f"  [1098] selftest {sum(c[1] for c in cases)}/{len(cases)} "
          f"invariants proved to fire; clean copy exit {rc}")
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "verify":
        sys.exit(verify())
    if cmd == "selftest":
        sys.exit(selftest())
    if cmd == "dry":
        sys.exit(build(dry_run=True))
    sys.exit(build())
