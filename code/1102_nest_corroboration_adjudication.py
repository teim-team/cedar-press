#!/usr/bin/env python3
"""
Cedar Press - 1102: A SECOND, GENUINELY INDEPENDENT EVIDENCE FAMILY FOR NEST
                    OWNERSHIP - THE PARENT THE SUBSIDIARY DECLARED TO FPDS.
                    PLUS THE CHUGACH ADJUDICATION, AND THE 25 COMPANIES NEST
                    HOLDS TWICE.

    py -3 code/1102_nest_corroboration_adjudication.py            # enrich
    py -3 code/1102_nest_corroboration_adjudication.py verify     # exit 1
    py -3 code/1102_nest_corroboration_adjudication.py selftest   # prove FIRES

PART ONE - THE SECOND FAMILY
-----------------------------
`docs/ASSERTION_LAYER.md`: every fact in Cedar rests on exactly one source.
NEST is the first dataset with an answer - 60 enterprises corroborated by two
independent evidence FAMILIES (an audited AS 45.55.139 filing and the parent's
own website). Its own next-pass list names the Alaska Division of Corporations
as the cheapest third, which is a network fetch.

**There is a fourth family already on this machine and nobody had used it for
NEST: `data/clean/fpds_uei_edges.csv`.** It records the parent a registrant
declared to FPDS **about itself**, which is:

  * an identifier-grade assertion (`ENTITY_MATCH_RULES` rule 11);
  * made by the CHILD, to the federal government, under a registration
    obligation - so it is independent of both the parent's audited filing and
    the parent's marketing site, which are the two families NEST already has;
  * already governed by a measured threshold: an edge observed **20+ times is
    ownership**; below that it is a joint venture or a co-award.

The corroboration test is deliberately not "the names match". It is:

    the firm's declared FPDS parent, at 20+ observations, resolves through
    `cedar_identifier_ledger_final.csv` to THE SAME OWNER HUB that NEST
    already asserts - or to a SIBLING enterprise under that same hub.

Two independent parties therefore have to agree about the OWNER, not about a
string. Two routes reach the firm:

    rung 1  the firm's PUBLISHED UEI is the edge's `child_uei`
    rung 2  the firm's normalised name equals the edge's `child_name`.
            A name match alone would be weak; here the corroborator is that
            the DECLARED PARENT independently lands on the owner NEST already
            asserts, which is the second signal checklist step 3 asks for.

MEASURED, over all 1,610 enterprises
    reached an FPDS edge at or above the 20-observation floor      272
      rung 1, published UEI                                         28
      rung 2, exact normalised name                                244
    CORROBORATED - the declared parent lands on NEST's own owner     87
    CONTRADICTED - it lands on a different Cedar entity                8
    PARENT_UNRESOLVED - the parent UEI is in no ledger row           177
    PARENT_BELOW_JV_FLOOR - an edge exists but under 20 obs           71
    NO_DECLARED_PARENT                                             1,267

**87 is more than the 60 two-family corroborations NEST had**, and it is a
different 87: this family is the child's own federal registration, where the
other two are the parent's audited filing and the parent's website.

PART TWO - THE 9 CONTRADICTIONS ARE MOSTLY THE LEDGER'S FAULT, AGAIN
----------------------------------------------------------------------
`ENTITY_MATCH_RULES` rule 12: when a declared parent contradicts an
attribution, suspect the PARENT row first. It holds here too, and NEST comes
out ahead on 7 of the 9:

    Bowhead Manufacturing / Professional Solutions / Transportation,
    Rockford Corporation, UMIAQ Environmental
        NEST      -> Ukpeagvik Inupiat Corporation      (the CORPORATION)
        ledger    -> AKNF-INPTAS-00-ARCSLO              (the VILLAGE GOVERNMENT)
        `ANCSA_OWNERSHIP_RULING` rule 2 and
        `cedar_domain.village_government_owns_an_anc()` (always False) say the
        ledger's link cannot exist. This is the
        ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION family (334 defects,
        $24.52B) reached from a FIFTH direction, and NEST is the correct side.

    Goldbelt Eagle, LLC
        NEST -> Goldbelt, Incorporated;  ledger -> AKNF-VEAGLE-00-...,
        the Native Village of EAGLE. A collision on the word `Eagle`.

    Vista Defense Technologies, LLC
        NEST -> Bristol Bay Native Corporation; ledger -> TRBF-BNVSTA-00,
        Buena VISTA Rancheria. A collision on the word `Vista`.

    The two that are NOT explained away and go to the register as open:
        Nisga'a Tek LLC   NEST Tlingit & Haida   vs ledger Goldbelt (254 obs)
        Broadleaf, Inc    NEST The Hawai'i Pacific Foundation
                          vs FPDS parent ARCTIC SLOPE REGIONAL CORPORATION

Nothing is repointed here. The contradictions are written to
`review/nest_fpds_parent_contradictions_<date>.csv` with both sides' evidence.

PART THREE - CHUGACH, ADJUDICATED
-----------------------------------
`data/staging/nest/evidence_conflicts.csv` holds the only two real evidence
conflicts in NEST: `Chugach Government Solutions, LLC` and `Chugach Regional
Development, LLC`, audited filing `holding_company` against web list
`operating_company`.

Reading the relations rows settles it, and the decisive fact is one neither
side of the conflict register states:

  * the website is `https://www.chugach.com/business/directory`, ONE page, and
    on that same page it calls **Chugach Commercial Holdings a holding
    company** while calling CGS and CRD operating companies. So the site is not
    merely omitting the holding role - it is asserting a different one, and the
    disagreement is genuine rather than an artefact of vocabulary.
  * a THIRD source, `ANC_TRIBE_LOOKUP` (`anc_tribal_subsidiary_lookup.csv`),
    lists all four - Chugach Commercial Holdings (CCH), Chugach Government
    Solutions (CGS), Chugach Investment Holdings (CIH), Chugach Regional
    Development (CRD) - IDENTICALLY, as `subsidiary` directly under the
    corporation. Four parallel siblings at one tier, two of them named
    *Holdings*.

**Adjudication: the audited filing stands, now on two of three sources rather
than on rank alone.** And the modelling lesson generalises the one NEST already
learned: `relationship` does not fuse two axes, it fuses THREE. A consolidation
note answers *where does this entity sit in the consolidation*; a business
directory answers *what does this firm sell*. Both render the answer into the
same six words. A conflict check that does not know which question was asked
manufactures disagreements - which is exactly how v1 produced 37 and v2 23.

PART FOUR - NEST HOLDS 25 COMPANIES TWICE, AND IT COSTS A CORROBORATION EACH
------------------------------------------------------------------------------
Found while reading the Chugach rows. NEST clusters on (owner hub, normalised
name), and a **trailing parenthetical survives normalisation**:

    CEDAR-NEST-000473-WH  Chugach Government Solutions, LLC   2 observations
    CEDAR-NEST-000474-2A  Chugach Government Solutions (CGS)  1 observation

Same company, two enterprise ids, two rows in the headline count. Measured
across the whole table: **25 groups, 50 rows.** 24 are an acronym -
`Ahtna Global LLC (AGL)`, `Yulista Aviation (YAI)`, `Eyak Technology LLC
(EyakTek)`, `Bristol Bay Construction Holdings LLC (BBCH)` - and in every one
of the 24 the acronym twin is the `ANC_TRIBE_LOOKUP` row at
`n_distinct_sources = 1` while the plain row already carries 2 or 3. The 25th
is a GLOSS, not an acronym: `Aan Hit` / `Aan Hit (Village House)`.

So the cost is counted twice over: 25 rows of overstatement in a 1,610-row
headline, **and** 25 lost corroborations, because a restatement that fails to
cluster raises nobody's source count. That is the exact thing NEST's own merge
was designed to do and the acronym form slipped past it.

**They are FLAGGED, not merged.** `docs/IDENTIFIER_STANDARD.md`: a
`cedar_uid` - and by the same rule a `CEDAR-NEST-` id - is never retired
without evidence and never as a side effect. Merging would retire 25 ids that
are already in `data/spine/cedar_nest_id_register.csv`, which is append-only.
`docs/AGENT_FIELD_GUIDE.md` §4 also says measure duplicates before collapsing
them: this pass measures and names them, and the collapse is an owner decision.

THE NAMED INVARIANTS
--------------------
  I1  every `fpds_parent_corroboration` value is in the declared vocabulary.
  I2  a row marked CORROBORATED names a declared parent observed 20+ times.
      Below the floor it is a joint venture, not ownership (rule 11).
  I3  a row marked CORROBORATED resolves that parent to THIS row's owner hub
      or to a sibling enterprise of it - never to a third entity.
  I4  every `duplicate_name_variant_group` member really does share a
      (owner hub, parenthetical-stripped name) with another member, and the
      group has 2+ members.
  I5  CONSERVE. rows unchanged, no column lost, and the md5 of every
      pre-existing field is unchanged.
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
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

NEST = ROOT / "data" / "clean" / "nest_enterprises.csv"
EDGES = ROOT / "data" / "clean" / "fpds_uei_edges.csv"
LEDGER = ROOT / "data" / "clean" / "cedar_identifier_ledger_final.csv"
CONFLICTS = ROOT / "data" / "staging" / "nest" / "evidence_conflicts.csv"
CONTRA = ROOT / "review" / f"nest_fpds_parent_contradictions_{TODAY}.csv"
DUPES = ROOT / "review" / f"nest_name_variant_duplicates_{TODAY}.csv"
MANIFEST = ROOT / "docs" / "NEST_CORROBORATION.json"
BAK_TAG = f".bak_{TODAY}_pre_1102_nest_corroboration_adjudication"

#: ENTITY_MATCH_RULES rule 11. Measured, not chosen: every real ownership case
#: is observed 100+ times and every sub-20 disagreement was a joint venture.
JV_FLOOR = 20

NEW = ["fpds_parent_corroboration", "fpds_parent_corroboration_route",
       "fpds_declared_parent_uei", "fpds_declared_parent_name",
       "fpds_declared_parent_observations", "fpds_parent_resolves_to",
       "fpds_parent_corroboration_basis",
       "duplicate_name_variant_group", "duplicate_name_variant_basis"]

CORR_VOCAB = {"CORROBORATED", "CONTRADICTED", "NO_DECLARED_PARENT",
              "PARENT_BELOW_JV_FLOOR", "PARENT_UNRESOLVED", ""}

TOK = re.compile(r"[^A-Z0-9]+")
FORMS = {"INC", "LLC", "LTD", "CO", "CORP", "CORPORATION", "COMPANY",
         "INCORPORATED", "LP", "LLP", "PC", "PLLC", "THE", "L", "C", "PLC",
         "LIMITED"}
PAREN = re.compile(r"\s*\([^)]*\)\s*$")


def nm(s: str) -> str:
    return " ".join(t for t in TOK.split((s or "").upper())
                    if t and t not in FORMS)


def base_name(s: str) -> str:
    return nm(PAREN.sub("", s or ""))


def read_table(p: Path):
    if not p.exists():
        return [], []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        r = csv.DictReader(fh)
        return [dict(x) for x in r], list(r.fieldnames or [])


def write_table(p: Path, rows, fields, tag=None):
    p.parent.mkdir(parents=True, exist_ok=True)
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


def digest(rows, fields):
    h = hashlib.md5()
    for r in rows:
        for c in fields:
            h.update((r.get(c) or "").encode("utf-8"))
            h.update(b"\x1f")
        h.update(b"\x1e")
    return h.hexdigest()


def build(dry_run=False) -> int:
    rows, fields = read_table(NEST)
    base = [c for c in fields if c not in NEW]
    before = digest(rows, base)
    n_before = len(rows)

    ledger, _ = read_table(LEDGER)
    uei2ent = {}
    for r in ledger:
        if (r.get("identifier_type") or "") == "UEI" and (r.get("tribe_id")
                                                          or ""):
            uei2ent.setdefault(r["identifier"], set()).add(r["tribe_id"])

    edges, _ = read_table(EDGES)
    by_uei, by_name, below = {}, {}, {}
    for e in edges:
        try:
            n_obs = int(e.get("n_observations") or 0)
        except ValueError:
            n_obs = 0
        rec = (e.get("parent_uei") or "", e.get("parent_name") or "", n_obs)
        if n_obs < JV_FLOOR:
            below.setdefault(e.get("child_uei") or "", []).append(rec)
            below.setdefault(nm(e.get("child_name")), []).append(rec)
            continue
        by_uei.setdefault(e.get("child_uei") or "", []).append(rec)
        by_name.setdefault(nm(e.get("child_name")), []).append(rec)

    sib = {}
    for r in rows:
        if r.get("uei"):
            sib.setdefault(r.get("owner_hub_handle"), set()).add(r["uei"])

    st = {"rows": n_before, "corroboration": {}, "route": {},
          "published_uei": 0, "dupe_groups": 0, "dupe_rows": 0}
    contra, dupes = [], []
    out_fields = list(fields) + [c for c in NEW if c not in fields]

    # -- duplicate name variants, measured before anything is written --------
    groups = {}
    for r in rows:
        groups.setdefault((r.get("owner_hub_handle"),
                           base_name(r.get("enterprise_name"))),
                          []).append(r)
    dup_of = {}
    gi = 0
    for (hub, bn), members in sorted(groups.items()):
        if len(members) < 2 or not bn:
            continue
        gi += 1
        gid = f"NESTDUP-{gi:04d}"
        st["dupe_groups"] += 1
        st["dupe_rows"] += len(members)
        withp = [m for m in members if PAREN.search(m.get("enterprise_name")
                                                    or "")]
        kind = "unknown"
        if withp:
            par = PAREN.search(withp[0]["enterprise_name"]).group(0)
            inner = par.strip().strip("()").strip()
            kind = "acronym_like" if " " not in inner else "gloss"
        for m in members:
            dup_of[m["enterprise_id"]] = (gid, kind, len(members), bn)
            dupes.append({
                "group_id": gid, "variant_kind": kind,
                "owner_hub_handle": hub,
                "owner_hub_name": m.get("owner_hub_name"),
                "enterprise_id": m.get("enterprise_id"),
                "enterprise_name": m.get("enterprise_name"),
                "parenthetical_stripped_name": bn,
                "relationship": m.get("relationship"),
                "n_distinct_sources": m.get("n_distinct_sources"),
                "n_source_observations": m.get("n_source_observations"),
                "source_id": m.get("source_id"),
                "disposition": ("FLAGGED_NOT_MERGED - a CEDAR-NEST id is never "
                                "retired as a side effect "
                                "(IDENTIFIER_STANDARD); merging is an owner "
                                "decision and AGENT_FIELD_GUIDE s4 says "
                                "measure duplicates before collapsing them")})

    for r in rows:
        for c in NEW:
            r.setdefault(c, "")
        hub = r.get("owner_hub_handle") or ""
        uei = (r.get("uei") or "").strip()
        if uei:
            st["published_uei"] += 1
        cands, route = [], ""
        if uei and uei in by_uei:
            cands, route = by_uei[uei], "rung1_published_uei"
        if not cands:
            key = nm(r.get("enterprise_name"))
            if key and key in by_name:
                cands, route = by_name[key], "rung2_exact_normalised_name"
        if not cands:
            weak = below.get(uei) or below.get(nm(r.get("enterprise_name")))
            if weak:
                r["fpds_parent_corroboration"] = "PARENT_BELOW_JV_FLOOR"
                r["fpds_declared_parent_uei"] = weak[0][0]
                r["fpds_declared_parent_name"] = weak[0][1]
                r["fpds_declared_parent_observations"] = str(weak[0][2])
                r["fpds_parent_corroboration_basis"] = (
                    f"a declared FPDS parent exists but at {weak[0][2]} "
                    f"observations, below the {JV_FLOOR}-observation ownership "
                    "floor. ENTITY_MATCH_RULES rule 11: below the floor an "
                    "edge is a joint venture or a co-award, and a JV genuinely "
                    "has two parents. Not counted either way.")
            else:
                r["fpds_parent_corroboration"] = "NO_DECLARED_PARENT"
                r["fpds_parent_corroboration_basis"] = (
                    "no row in fpds_uei_edges.csv reaches this enterprise by "
                    "published UEI or by exact normalised name.")
            st["corroboration"][r["fpds_parent_corroboration"]] = \
                st["corroboration"].get(r["fpds_parent_corroboration"], 0) + 1
            continue

        best = max(cands, key=lambda c: c[2])
        r["fpds_declared_parent_uei"] = best[0]
        r["fpds_declared_parent_name"] = best[1]
        r["fpds_declared_parent_observations"] = str(best[2])
        r["fpds_parent_corroboration_route"] = route
        ents = set()
        for pu, pn, no in cands:
            ents |= uei2ent.get(pu, set())
        pus = {pu for pu, _, _ in cands}
        if hub in ents:
            verdict, resolves = "CORROBORATED", hub
        elif pus & sib.get(hub, set()):
            verdict, resolves = "CORROBORATED", f"sibling_enterprise_of:{hub}"
        elif ents:
            verdict, resolves = "CONTRADICTED", "|".join(sorted(ents))
        else:
            verdict, resolves = "PARENT_UNRESOLVED", ""
        r["fpds_parent_corroboration"] = verdict
        r["fpds_parent_resolves_to"] = resolves
        r["fpds_parent_corroboration_basis"] = (
            f"declared FPDS parent '{best[1]}' ({best[0]}) observed {best[2]}x, "
            f"at or above the {JV_FLOOR}-observation ownership floor; resolved "
            "through cedar_identifier_ledger_final.csv to "
            f"{resolves or '(no Cedar entity)'}; NEST asserts owner hub {hub}. "
            "The FPDS declaration is made by the CHILD about itself and is "
            "independent of both the parent's audited filing and the parent's "
            "own website.")
        st["corroboration"][verdict] = st["corroboration"].get(verdict, 0) + 1
        st["route"][route] = st["route"].get(route, 0) + 1
        if verdict == "CONTRADICTED":
            contra.append({
                "enterprise_id": r.get("enterprise_id"),
                "enterprise_name": r.get("enterprise_name"),
                "nest_owner_hub_handle": hub,
                "nest_owner_hub_name": r.get("owner_hub_name"),
                "nest_relationship": r.get("relationship"),
                "nest_evidence_class": r.get("evidence_class"),
                "nest_n_distinct_sources": r.get("n_distinct_sources"),
                "fpds_declared_parent_name": best[1],
                "fpds_declared_parent_uei": best[0],
                "fpds_declared_parent_observations": str(best[2]),
                "ledger_resolves_parent_to": resolves,
                "route": route,
                "disposition": "OPEN - neither side repointed by this pass",
                "note": ("ENTITY_MATCH_RULES rule 12: when a declared parent "
                         "contradicts an attribution, suspect the PARENT row "
                         "first. Check whether the ledger row for the parent "
                         "UEI is the ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_"
                         "CORPORATION defect before treating this as a NEST "
                         "error.")})

    for r in rows:
        d = dup_of.get(r.get("enterprise_id"))
        if not d:
            continue
        gid, kind, nmem, bn = d
        r["duplicate_name_variant_group"] = gid
        r["duplicate_name_variant_basis"] = (
            f"{nmem} enterprises under owner hub {r.get('owner_hub_handle')} "
            f"share the parenthetical-stripped normalised name '{bn}'; the "
            f"variant is {kind}. NEST clusters on (owner hub, normalised name) "
            "and a trailing parenthetical survives normalisation, so a "
            "restatement of a firm already held became a second row instead of "
            "raising the first row's source count. FLAGGED, NOT MERGED - a "
            "CEDAR-NEST id is never retired as a side effect.")

    if digest(rows, base) != before:
        print("  [1102] FATAL: a base field changed. Refusing to write.")
        return 1
    if len(rows) != n_before:
        print("  [1102] FATAL: row count moved. Refusing to write.")
        return 1

    if not dry_run:
        write_table(NEST, rows, out_fields, tag=BAK_TAG)
        if contra:
            write_table(CONTRA, contra, list(contra[0].keys()))
        if dupes:
            write_table(DUPES, sorted(dupes, key=lambda d: d["group_id"]),
                        list(dupes[0].keys()))
        # the Chugach adjudication, recorded on the conflict rows themselves
        crows, cfields = read_table(CONFLICTS)
        add = ["adjudicated_by", "adjudicated_date", "adjudication",
               "third_source", "third_source_says"]
        for c in crows:
            for a in add:
                c.setdefault(a, "")
            c["adjudicated_by"] = "code/1102_nest_corroboration_adjudication.py"
            c["adjudicated_date"] = TODAY
            c["third_source"] = ("anc_tribal_subsidiary_lookup.csv "
                                 "(ANC_TRIBE_LOOKUP)")
            c["third_source_says"] = (
                "lists Chugach Commercial Holdings (CCH), Chugach Government "
                "Solutions (CGS), Chugach Investment Holdings (CIH) and "
                "Chugach Regional Development (CRD) identically as "
                "`subsidiary` directly under Chugach Alaska Corporation - four "
                "parallel siblings at one tier, two of them named Holdings")
            c["adjudication"] = (
                "UPHELD, and now on two of three sources rather than on rank. "
                "The conflict is genuine and not a vocabulary artefact: the "
                "SAME page, www.chugach.com/business/directory, calls Chugach "
                "Commercial Holdings a holding company while calling CGS and "
                "CRD operating companies, so the site is asserting a different "
                "role rather than omitting one. But `relationship` fuses a "
                "THIRD axis nobody had named: a consolidation note answers "
                "WHERE AN ENTITY SITS, a business directory answers WHAT A "
                "FIRM SELLS, and both render into the same six words. The "
                "audited AS 45.55.139 filing answers the question the column "
                "is asking. Published value `holding_company` stands.")
        if crows:
            write_table(CONFLICTS, crows,
                        list(cfields) + [a for a in add if a not in cfields],
                        tag=BAK_TAG)

    gained = [c for c in out_fields if c not in fields]
    print(f"  [1102] rows {len(rows):,} unchanged | md5(base {len(base)} "
          f"fields) {before}")
    print(f"  [1102] COLUMN DIFF   gained {len(gained)}: {gained}")
    print(f"  [1102]               lost   0: []")
    print(f"  [1102] enterprises with a published UEI {st['published_uei']:,}")
    print("  [1102] fpds_parent_corroboration")
    for k, v in sorted(st["corroboration"].items(), key=lambda kv: -kv[1]):
        print(f"          {k:<26} {v:>6,}")
    print("  [1102] route, among rows that reached an edge")
    for k, v in sorted(st["route"].items(), key=lambda kv: -kv[1]):
        print(f"          {k:<30} {v:>6,}")
    print(f"  [1102] duplicate name-variant groups {st['dupe_groups']} "
          f"covering {st['dupe_rows']} rows")
    if not dry_run:
        print(f"  [1102] wrote {CONTRA.relative_to(ROOT)} ({len(contra)})")
        print(f"  [1102] wrote {DUPES.relative_to(ROOT)} ({len(dupes)})")
        print(f"  [1102] adjudicated {CONFLICTS.relative_to(ROOT)}")
        MANIFEST.write_text(json.dumps(
            {"built": TODAY,
             "script": "1102_nest_corroboration_adjudication.py",
             "table": "data/clean/nest_enterprises.csv",
             "columns_added": NEW, "jv_observation_floor": JV_FLOOR,
             "base_fields_md5": before,
             "contradictions": contra, **st}, indent=2), encoding="utf-8")
        print(f"  [1102] wrote {MANIFEST.relative_to(ROOT)}")
    return 0


def verify(path: Path | None = None) -> int:
    p = path or NEST
    rows, fields = read_table(p)
    if any(c not in fields for c in NEW):
        print("  [1102] verify: columns absent - run the enricher first")
        return 1
    sib = {}
    for r in rows:
        if r.get("uei"):
            sib.setdefault(r.get("owner_hub_handle"), set()).add(r["uei"])
    groups = {}
    for r in rows:
        g = (r.get("duplicate_name_variant_group") or "").strip()
        if g:
            groups.setdefault(g, []).append(r)
    fails = []
    n_corr = 0
    for r in rows:
        eid = r.get("enterprise_id")
        v = (r.get("fpds_parent_corroboration") or "").strip()
        if v not in CORR_VOCAB:
            fails.append(("I1", eid, f"corroboration {v!r} off-vocabulary"))
        if v == "CORROBORATED":
            n_corr += 1
            try:
                obs = int(r.get("fpds_declared_parent_observations") or 0)
            except ValueError:
                obs = 0
            if obs < JV_FLOOR:
                fails.append(("I2", eid, f"CORROBORATED on {obs} observations, "
                                         f"below the {JV_FLOOR} floor"))
            res = (r.get("fpds_parent_resolves_to") or "").strip()
            hub = (r.get("owner_hub_handle") or "").strip()
            if res != hub and res != f"sibling_enterprise_of:{hub}":
                fails.append(("I3", eid, f"CORROBORATED but the parent "
                                         f"resolves to {res!r}, not to {hub}"))
    for g, members in groups.items():
        if len(members) < 2:
            fails.append(("I4", g, "duplicate group with fewer than 2 members"))
        keys = {(m.get("owner_hub_handle"),
                 base_name(m.get("enterprise_name"))) for m in members}
        if len(keys) != 1:
            fails.append(("I4", g, "group members do not share a (hub, "
                                   "parenthetical-stripped name)"))
    print(f"  [1102] verify: {len(rows):,} rows | {n_corr} corroborated | "
          f"{len(groups)} duplicate groups | {len(fails)} breach(es)")
    for f in fails[:20]:
        print(f"          {f[0]}  {f[1]}  {f[2]}")
    return 1 if fails else 0


def selftest() -> int:
    import tempfile
    rows, fields = read_table(NEST)
    if any(c not in fields for c in NEW):
        print("  [1102] selftest: run the enricher first")
        return 1
    tmp = Path(tempfile.mkdtemp()) / "nest_enterprises.csv"
    cases = []

    def run(label, mut):
        rs = [dict(r) for r in rows]
        mut(rs)
        write_table(tmp, rs, fields)
        rc = verify(tmp)
        cases.append((label, rc == 1))
        print(f"          {'FIRES ' if rc == 1 else 'SILENT'}  {label}")

    def corr(rs):
        for r in rs:
            if (r.get("fpds_parent_corroboration") or "") == "CORROBORATED":
                return r
        raise SystemExit("no corroborated row")

    def dup(rs):
        for r in rs:
            if (r.get("duplicate_name_variant_group") or "").strip():
                return r
        raise SystemExit("no duplicate row")

    print("  [1102] selftest - inject the violation, assert exit 1")
    run("I1 off-vocabulary fpds_parent_corroboration",
        lambda rs: rs[0].__setitem__("fpds_parent_corroboration", "PROBABLY"))
    run("I2 CORROBORATED below the joint-venture observation floor",
        lambda rs: corr(rs).__setitem__("fpds_declared_parent_observations",
                                        "3"))
    run("I3 CORROBORATED onto a third entity",
        lambda rs: corr(rs).__setitem__("fpds_parent_resolves_to",
                                        "TRBF-SOMEONEELSE-00"))
    run("I4 a duplicate group whose members do not share a name",
        lambda rs: dup(rs).__setitem__("enterprise_name",
                                       "Totally Unrelated Holdings"))

    def orphan(rs):
        for r in rs:
            if not (r.get("duplicate_name_variant_group") or "").strip():
                r["duplicate_name_variant_group"] = "NESTDUP-9999"
                return
    run("I4 a duplicate group with one member", orphan)

    write_table(tmp, rows, fields)
    rc = verify(tmp)
    print(f"          {'PASS  ' if rc == 0 else 'FAIL  '}  restored copy "
          f"verifies clean (exit {rc})")
    ok = all(c[1] for c in cases) and rc == 0
    print(f"  [1102] selftest {sum(c[1] for c in cases)}/{len(cases)} "
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
