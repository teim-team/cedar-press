#!/usr/bin/env python3
"""
Cedar Press - 433: apply the owner's TWO reconciliation-tool ruling exports back
to the source tables, IN PLACE.

    review/elijah_rulings_2026-08-26_recon.csv          (5 rulings)
    review/elijah_rulings_2026-08-27_recon_batch2.csv   (88 identifier rows,
                                                         33 clusters)

**A ruling that is not applied back to its source table is not a ruling, it is a
note.** Measured earlier: 492 clusters carrying $17.5B had a ruling recorded
somewhere and never written back, so they resurfaced as unresolved and the owner
was asked to re-adjudicate entities he had already decided. These 38 clusters
were on their way to the same place - neither export appears anywhere in
`cedar_ruling_ledger_consolidated.csv` (built 17:52, both exports written after),
and all 88 identifiers that reach the ledger sit at tier C `unmatched`/`need_v6`.

THE TWO FILES HAVE DIFFERENT HEADERS. Neither shape is assumed.

  2026-08-26: identifier,identifier_type,firm_name,ruling,entity,ruled_by,
              ruled_date,note,cedar_note      <- `identifier` is SEMICOLON-JOINED
  2026-08-27: identifier,identifier_type,ruled_by,ruled_date,cluster_key,name,
              ruling,entity,note,obligations,my_guess,my_confidence

`my_guess` / `my_confidence` are CEDAR's algorithmic prior on the card, not the
owner's - `docs/RECONCILIATION_TOOL.md` records that 301 of 400 cards score under
20% by design. They are carried into the applied-record file, never into a
decision: where the prior disagrees with the ruling, the ruling wins and the
disagreement is reported.

WHAT IS WRITTEN, AND WHAT DELIBERATELY IS NOT
----------------------------------------------
| ruling       | ledger                              | prime_contracts            |
|--------------|-------------------------------------|----------------------------|
| tribe/anc/nho| tribe_id, canonical_name, tier A,   | attributed, tier A,        |
| + entity     | is_authority YES, method            | ruling_status=             |
|              | elijah_ruling[_redirect]            | RULED_ATTRIBUTED           |
| not_native   | tier X, method elijah_ruling        | RULED_NOT_NATIVE, no       |
|              | (an exclusion, tribe_id untouched)  | attribution                |
| individual   | tier_rationale ONLY - the class is  | RULED_CLASS_ONLY, no       |
|              | recorded, nothing is attributed     | attribution                |

**`individual` does not mint a spine entity.** AGENTS.md 2026-08-07 makes
individually Native-owned business its own `entity_class` with `parent_native_
entity` NULL and no ownership edge; the 42 rows already in the ledger carry
minted `CEDAR-ENT-*` ids. Minting is a SPINE write and HANDOFF.md files "2,289
new individual-Native candidates, $6.83B" as an OPEN DECISION FOR THE OWNER.
So the ruling is recorded here and the mint request is staged for him.

**subawards.csv is deliberately NOT written.** Its `sub_native_tier` /
`prime_native_tier` are COPIES of a ledger tier taken at promotion time
(`41_match_subawards_to_ledger.py` -> `45_promote_subawards.py`), and
docs/ANCSA_OWNERSHIP_RULING.md settles the direction: "that direction is a
PROMOTION and must not be done by hand. Re-running 41 then 45 is the route."
The rows these rulings now owe a promotion to are COUNTED and reported instead.

THE TRAPS THIS SCRIPT IS BUILT AGAINST - each one previously paid for
--------------------------------------------------------------------
1. **The tier is INHERITED from the ruling, not computed from the method.**
   `148_resolve_schedule_i_recipients.py` published 317 tier-X EXCLUSIONS as
   tier-A ATTRIBUTIONS on exactly that mistake. Here the ruling's OUTCOME
   (ENTITY / NEGATIVE / CLASS) chooses the tier, never the fact that a ruling
   exists. `status` says a ruling was processed; `outcome` says what it decided.
   The tier for a positive owner ruling that names an owner is A, and the reason
   is RECORDED not invented: it is the 09/124 hand-ruling grammar, which
   `173_consolidate_rulings_ledger.py` names as tier source #4 for a hand inbox,
   and `docs/RECONCILIATION_TOOL.md` states the tool exists "to turn a human's
   knowledge into tier-A attributions". `tier_source` is written onto every row.
2. **A name is not a key.** Every write keys on (identifier_type, identifier)
   from the ruling row. `firm_name` / `name` are carried for reporting only. The
   2026-08-26 file's `cedar_note` mentions "CAGE 1U7W6" in prose; it is NOT in
   the identifier column and is therefore NOT written.
3. **A corporate family stem is not a firm identity** - `{asrc, federal}`
   matched 18 distinct subsidiaries. No stem, substring or containment match is
   used anywhere in this script.
4. **ANCSA: a village government is not a village corporation.** The spine holds
   228 Alaska Native Villages against 173 village corporations and they are named
   for each other by construction. Two guards run on every resolved entity:
   (a) a CLASS guard - a ruling of `anc` must land on an ANCSA corporation class,
       `nho` on a Native Hawaiian Organization, `tribe` on a government class.
       A mismatch is REFUSED and reported, never quietly accepted.
   (b) an ANCSA RULE guard - where the owner names an Alaska village GOVERNMENT
       as the owner of an operating company, docs/ANCSA_OWNERSHIP_RULING.md rule
       1 presumes the village CORPORATION and rule 3 permits the government only
       on evidence. The ruling is applied - the owner is the authority and rule 3
       is real - and the departure from the presumption is RECORDED as a conflict
       for him. **The owner is never silently corrected, and never silently
       rubber-stamped either.**

SAFETY
------
- Backs every shared table up to `.bak_<date>_pre_433_apply_elijah_recon_
  rulings_in_place` - the SCRIPT NAME, never a number.
- Writes `.part` then `os.replace`. An interruption never looks like completion.
- Captures each target's mtime before the read and re-checks it before the
  rename; a concurrent agent's write aborts this one instead of clobbering it.
- Re-READS each file from disk afterwards and re-counts rows and columns rather
  than trusting the run log.
- Reads and writes with an EXPLICIT encoding. This machine defaults to cp1252.

    py -3 code/433_apply_elijah_recon_rulings_in_place.py --check
    py -3 code/433_apply_elijah_recon_rulings_in_place.py
"""

import csv
import importlib.util
import os
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"

TODAY = date.today().isoformat()
SCRIPT = "433_apply_elijah_recon_rulings_in_place"
BAK = f".bak_{TODAY}_pre_{SCRIPT}"

LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
PRIME = CLEAN / "prime_contracts.csv"
SUBAWARDS = CLEAN / "subawards.csv"

EXPORTS = (
    REVIEW / "elijah_rulings_2026-08-26_recon.csv",
    REVIEW / "elijah_rulings_2026-08-27_recon_batch2.csv",
)

# `ruling_applied_` is in 173's SELF_PREFIX, so these outputs are NOT swept back
# in as rulings on the next consolidation run. Deliberate: a record of what was
# applied must not re-enter as evidence for itself.
OUT_APPLIED = REVIEW / f"ruling_applied_elijah_recon_{TODAY}.csv"
OUT_CONFLICTS = REVIEW / f"ruling_conflicts_elijah_recon_{TODAY}.csv"
OUT_MINT = REVIEW / f"ruling_applied_individual_native_mint_requests_{TODAY}.csv"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

RULED_BY = "Elijah Moreno"
TIER_SOURCE = ("09/124 hand-ruling grammar; owner hand ruling naming an owner, "
               "exported from the reconciliation tool "
               "(docs/RECONCILIATION_TOOL.md)")

# ---------------------------------------------------------------------------
# The class guard. A ruling states a CLASS as well as an owner; the resolved
# spine entity has to be of that class or the resolution is wrong.
# ---------------------------------------------------------------------------
ANCSA_CORPORATION_CLASSES = {
    "Alaska Native Village Corporation",
    "Alaska Native Regional Corporation",
    "ANC_REGIONAL",
    "Alaska Native Urban Corporation",
    "Alaska Native Group Corporation",
}
ALASKA_VILLAGE_GOVERNMENT_CLASSES = {
    "Federally recognized Alaska Native Village",
    "FEDERAL_AK_VILLAGE",
}
GOVERNMENT_CLASSES = ALASKA_VILLAGE_GOVERNMENT_CLASSES | {
    "Federally recognized tribe",
    "FEDERAL_TRIBE_LOWER48",
    "State-recognized tribe",
    "STATE_TRIBE",
}
NHO_CLASSES = {"Native Hawaiian Organization"}

CLASS_GUARD = {
    "anc": ANCSA_CORPORATION_CLASSES,
    "nho": NHO_CLASSES,
    "tribe": GOVERNMENT_CLASSES,
}


def load(p, required=True):
    p = Path(p)
    if not p.exists():
        if required:
            print(f"  MISSING: {p}")
            sys.exit(1)
        return []
    with open(p, encoding="utf-8", errors="replace", newline="") as fh:
        # utf-8 explicitly; this machine defaults to cp1252.
        return list(csv.DictReader(fh))


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, CODE / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def money(r, col="total_obligations"):
    try:
        return float(r.get(col) or 0)
    except (TypeError, ValueError):
        return 0.0


# ---------------------------------------------------------------------------
# THE RESOLVER RESCUE - narrow, exact, unique, and REPORTED every time it fires
# ---------------------------------------------------------------------------
# `33_apply_party_rulings.resolve_entity` is the ONE resolver and nothing here
# re-implements it. But it returns early on `ambiguous_core`, which means its
# own alias leg is never reached for a name whose CORE is ambiguous while its
# ALIAS is exact and unique. That is not hypothetical - it is the Eyak case
# docs/ANCSA_OWNERSHIP_RULING.md already quotes verbatim:
#
#     "owner is Native Village of Eyak ... but Native Village of Eyak is not in
#      the spine (ambiguous_core:2_spine_entities), so this could not be
#      re-attributed."
#
# The village IS in the spine (AKNF-NVEYAK-00-CHGCCO-CHGCMT) carrying the alias
# `Native Village of Eyak`, and `Eyak Corporation` is separately ANVC-EYAKXX-00.
# The core sets collide on {eyak} because `native`, `village` and `corporation`
# are all STRUCTURAL tokens; the aliases do not collide at all.
#
# So this runs ONLY after resolve_entity has REFUSED, and accepts only:
#   1. an EXACT normalised alias hit that is unique across the whole spine, then
#   2. an alias CORE-SET equality that is unique across the whole spine.
# Order matters: exact alias is tried first precisely so that `NATIVE VILLAGE OF
# EYAK` lands on the village and not on a {eyak} core shared with the ANC.
#
# No containment, no substring, no stem, no best-effort. If either leg returns
# anything other than exactly one entity, the ruling is REFUSED and the spine
# gap is reported. Every rescue is written into the conflicts file as
# RESOLVER_RESCUE_USED so the dollars resting on it are one filter away.

def rescue_resolve(name, spine, m33):
    n = m33.norm(name)
    hits = {}
    for r in spine:
        for a in (r.get("aliases") or "").split("|"):
            if a.strip() and m33.norm(a) == n:
                hits[r["tribe_id"]] = r
    if len(hits) == 1:
        r = next(iter(hits.values()))
        return r["tribe_id"], r["canonical_name"], "rescue_exact_alias_unique"

    c = m33.core(name)
    if c:
        hits = {}
        for r in spine:
            for a in (r.get("aliases") or "").split("|"):
                if a.strip() and m33.core(a) == c:
                    hits[r["tribe_id"]] = r
        if len(hits) == 1:
            r = next(iter(hits.values()))
            return r["tribe_id"], r["canonical_name"], "rescue_alias_core_unique"
    return None, None, "rescue_failed"


# ---------------------------------------------------------------------------
# 1. READ BOTH EXPORTS. Different headers; neither shape assumed.
# ---------------------------------------------------------------------------

def read_exports():
    out = []
    for path in EXPORTS:
        rows = load(path)
        if not rows:
            continue
        hdr = set(rows[0])
        shape = "batch2" if "cluster_key" in hdr else "batch1"
        for r in rows:
            raw = (r.get("identifier") or "").strip()
            itype = (r.get("identifier_type") or "").strip().upper()
            # batch1 semicolon-joins several identifiers into one cell.
            idents = [t.strip().upper() for t in raw.split(";") if t.strip()]
            if not idents:
                continue
            cluster = (r.get("cluster_key") or idents[0]).strip().upper()
            out.append({
                "source_file": path.name,
                "shape": shape,
                "cluster_key": cluster,
                "identifier_type": itype,
                "identifiers": idents,
                "firm_name": (r.get("firm_name") or r.get("name") or "").strip(),
                "ruling": (r.get("ruling") or "").strip().lower(),
                "entity": (r.get("entity") or "").strip(),
                "note": (r.get("note") or "").strip(),
                "cedar_note": (r.get("cedar_note") or "").strip(),
                "ruled_by": (r.get("ruled_by") or "").strip(),
                "ruled_date": (r.get("ruled_date") or "").strip(),
                "obligations": (r.get("obligations") or "").strip(),
                "my_guess": (r.get("my_guess") or "").strip(),
                "my_confidence": (r.get("my_confidence") or "").strip(),
            })
    return out


# ---------------------------------------------------------------------------
# 2. TURN RULINGS INTO DECISIONS, keyed on (identifier_type, identifier).
# ---------------------------------------------------------------------------

def build_decisions(rulings, spine, m33):
    by_class = {r["canonical_name"]: r for r in spine}
    dec, conflicts = {}, []
    clusters = {}

    for r in rulings:
        rule = r["ruling"]
        key_note = f"{r['cluster_key']} / {r['firm_name']}"

        if rule in ("not_native", "not native"):
            outcome, tier, tid, cname, ecls = "NEGATIVE", "X", "", "", ""
            action = "RULED_NOT_NATIVE"
        elif rule in ("individual", "individual_native"):
            outcome, tier, tid, cname, ecls = "CLASS", "", "", "", \
                "Individually Native-owned business"
            action = "RULED_CLASS_ONLY"
        elif rule in ("tribe", "anc", "nho"):
            if not r["entity"]:
                conflicts.append(_conf(
                    r, "CLASS_RULED_NO_OWNER_NAMED",
                    "the ruling states a class and names no entity; a class "
                    "without an owner is a category, not an attribution "
                    "(docs/RECONCILIATION_TOOL.md, the completion rule)",
                    "", "", ""))
                continue
            tid, cname, how = m33.resolve_entity(r["entity"], spine)
            if not tid:
                rtid, rcname, rhow = rescue_resolve(r["entity"], spine, m33)
                if rtid:
                    tid, cname = rtid, rcname
                    how = f"{rhow} (after resolve_entity returned '{how}')"
                    conflicts.append(_conf(
                        r, "RESOLVER_RESCUE_USED",
                        f"`resolve_entity` refused '{r['entity']}'; rescued by "
                        f"{rhow}. The spine holds it as "
                        f"'{cname}' ({tid}) under a RECORDED ALIAS that is "
                        f"EXACT and UNIQUE. Applied on that basis. Recorded so "
                        f"the dollars resting on the rescue are one filter "
                        f"away, and because the same shortfall is quoted "
                        f"verbatim in docs/ANCSA_OWNERSHIP_RULING.md "
                        f"('ambiguous_core:2_spine_entities, so this could not "
                        f"be re-attributed').",
                        tid, cname, how))
            if not tid:
                conflicts.append(_conf(
                    r, "OWNER_NOT_IN_SPINE",
                    f"resolver could not place '{r['entity']}' on the spine "
                    f"({how}); refusing to write a dollar on an owner we "
                    f"cannot identify - the row is left untouched and the "
                    f"spine gap stays visible",
                    "", "", how))
                continue
            ecls = (by_class.get(cname) or {}).get("entity_class", "")
            allowed = CLASS_GUARD[rule]
            if ecls not in allowed:
                conflicts.append(_conf(
                    r, "RULED_CLASS_DOES_NOT_MATCH_SPINE_CLASS",
                    f"ruling says '{rule}' but '{cname}' is class '{ecls}' on "
                    f"the spine. REFUSED - not applied. The spine holds 228 "
                    f"Alaska Native Villages against 173 village corporations "
                    f"and they are named for each other by construction, so a "
                    f"class mismatch is the shape of the ANCSA defect, not a "
                    f"vocabulary quibble.",
                    tid, cname, how))
                continue
            outcome, tier, action = "ENTITY", "A", "RULED_ATTRIBUTED"

            # ANCSA rule guard - applied, and recorded as a departure.
            if ecls in ALASKA_VILLAGE_GOVERNMENT_CLASSES:
                conflicts.append(_conf(
                    r, "ANCSA_RULE_1_PRESUMPTION_DEPARTURE_APPLIED_AS_RULED",
                    f"the owner names the Alaska village GOVERNMENT "
                    f"'{cname}' as owner of an operating company. "
                    f"docs/ANCSA_OWNERSHIP_RULING.md rule 1 PRESUMES the "
                    f"village CORPORATION; rule 3 permits the government "
                    f"directly but says the exception must be EVIDENCED, not "
                    f"assumed, and no evidence source is carried on the ruling "
                    f"row. Rule 2 is NOT violated - the subject is an "
                    f"operating company, not an ANC - so the ruling is "
                    f"APPLIED AS RULED and this is recorded for the owner "
                    f"rather than silently corrected. Cedar's own prior on "
                    f"this card was '{r['my_guess'] or 'none'}' at "
                    f"{r['my_confidence'] or 'n/a'}%.",
                    tid, cname, how))
        else:
            conflicts.append(_conf(
                r, "UNRECOGNISED_RULING_VERB",
                f"ruling '{r['ruling']}' is not in the reconciliation tool's "
                f"vocabulary (tribe / anc / nho / individual / not_native); "
                f"refused rather than guessed",
                "", "", ""))
            continue

        # Cedar's prior disagreeing with the ruling is reported, never obeyed.
        if r["my_guess"] and r["my_guess"] not in ("unsure", "") \
                and r["my_guess"] != rule:
            conflicts.append(_conf(
                r, "CEDAR_PRIOR_DISAGREES_WITH_RULING_RULING_WINS",
                f"the card's algorithmic prior was '{r['my_guess']}' at "
                f"{r['my_confidence']}%; the owner ruled '{rule}'. The ruling "
                f"is applied. Recorded because a prior that loses is still "
                f"evidence about the matcher.",
                tid, cname, ""))

        clusters[r["cluster_key"]] = {
            "cluster_key": r["cluster_key"], "firm_name": r["firm_name"],
            "ruling": rule, "entity": r["entity"], "outcome": outcome,
            "action": action, "tribe_id": tid, "canonical_name": cname,
            "tier": tier, "entity_class": ecls, "note": r["note"],
            "cedar_note": r["cedar_note"], "source_file": r["source_file"],
            "obligations_on_card": r["obligations"],
            "my_guess": r["my_guess"], "my_confidence": r["my_confidence"],
            "ruled_date": r["ruled_date"], "n_identifiers": 0,
        }
        for ident in r["identifiers"]:
            k = (r["identifier_type"], ident)
            if k in dec and dec[k]["cluster_key"] != r["cluster_key"]:
                conflicts.append(_conf(
                    r, "IDENTIFIER_RULED_TWICE",
                    f"{k[0]}:{k[1]} carries two rulings "
                    f"({dec[k]['cluster_key']} and {r['cluster_key']}); "
                    f"NEITHER applied",
                    tid, cname, ""))
                dec[k]["action"] = "RULING_CONFLICT"
                continue
            dec[k] = dict(clusters[r["cluster_key"]])
            dec[k]["identifier_type"], dec[k]["identifier"] = k
            clusters[r["cluster_key"]]["n_identifiers"] += 1

    # One conflict per (cluster, kind). A cluster carries one ruling across
    # many identifier rows; reporting it once per row would make a single
    # disagreement look like eleven.
    seen, deduped = set(), []
    for c in conflicts:
        k = (c["cluster_key"], c["conflict_kind"])
        if k in seen:
            continue
        seen.add(k)
        deduped.append(c)
    return dec, clusters, deduped


def _conf(r, kind, why, tid, cname, how):
    return {
        "conflict_kind": kind,
        "cluster_key": r["cluster_key"],
        "identifier_type": r["identifier_type"],
        "identifiers": ";".join(r["identifiers"]),
        "firm_name": r["firm_name"],
        "ruling": r["ruling"],
        "ruled_entity": r["entity"],
        "resolved_tribe_id": tid,
        "resolved_canonical_name": cname,
        "resolver_how": how,
        "cedar_prior_guess": r["my_guess"],
        "cedar_prior_confidence": r["my_confidence"],
        "obligations_on_card": r["obligations"],
        "owner_note": r["note"],
        "cedar_note": r["cedar_note"],
        "why": why,
        "resolution": "FOR THE OWNER - not resolved by this script",
        "source_file": r["source_file"],
        "flagged_date": TODAY,
    }


# ---------------------------------------------------------------------------
# 3. WRITE
# ---------------------------------------------------------------------------

def rewrite(path, rows, fields, mtime0, label):
    if path.stat().st_mtime != mtime0:
        print(f"  *** {label} changed while we read it - ABORTED, nothing written")
        return False
    bak = Path(str(path) + BAK)
    if not bak.exists():
        shutil.copy2(path, bak)
        print(f"  backed up -> {bak.name}")
    tmp = Path(str(path) + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    if path.stat().st_mtime != mtime0:
        tmp.unlink(missing_ok=True)
        print(f"  *** {label} changed DURING the write - ABORTED")
        return False
    os.replace(tmp, path)
    # concurrency rule 4: re-read from disk, do not trust the run log
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames)
        n = sum(1 for _ in rd)
    ok = (n == len(rows) and cols == fields)
    print(f"  wrote {path.name}; VERIFY re-read {n:,} rows (expected "
          f"{len(rows):,}), {len(cols)} cols -> {'OK' if ok else 'MISMATCH'}")
    return ok


def write_report(dest, recs, label):
    if not recs:
        print(f"  {label}: none")
        return
    tmp = Path(str(dest) + ".part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(recs[0]))
        w.writeheader()
        w.writerows(recs)
    os.replace(tmp, dest)
    print(f"  wrote {dest.name}  ({len(recs):,} rows) - {label}")


def apply_ledger(dec, check, applied_log):
    print("\n[cedar_identifier_ledger_final.csv]")
    mtime0 = LEDGER.stat().st_mtime
    rows = load(LEDGER)
    fields = list(rows[0])
    stats, changed, refused = Counter(), 0, []

    for r in rows:
        k = ((r.get("identifier_type") or "").strip().upper(),
             (r.get("identifier") or "").strip().upper())
        d = dec.get(k)
        if not d or d["action"] == "RULING_CONFLICT":
            continue
        cur_tier = (r.get("confidence_tier") or "").strip().upper()
        cur_tid = (r.get("tribe_id") or "").strip()

        if d["action"] == "RULED_ATTRIBUTED":
            # never overwrite an established attribution naming a DIFFERENT
            # entity - a ruling that disagrees with the table is a finding.
            if cur_tier in ("A", "B") and cur_tid and cur_tid != d["tribe_id"]:
                refused.append({**d, "why": f"ledger already tier {cur_tier} to "
                                            f"{cur_tid}; ruling names "
                                            f"{d['tribe_id']}"})
                stats["REFUSED - ledger already attributed elsewhere"] += 1
                continue
            confirming = (cur_tid == d["tribe_id"])
            r["tribe_id"] = d["tribe_id"]
            r["canonical_name"] = d["canonical_name"]
            if d["entity_class"]:
                r["entity_class"] = d["entity_class"]
            r["confidence_tier"] = d["tier"]
            r["attribution_method"] = ("elijah_ruling" if confirming
                                       else "elijah_ruling_redirect")
            r["is_authority"] = "YES"
            r["tier_rationale"] = (
                f"Ruled by {RULED_BY} {d['ruled_date']}, applied in place "
                f"{TODAY} by {SCRIPT} from {d['source_file']}: owner is "
                f"{d['canonical_name']} (class ruled '{d['ruling']}'"
                + (f"; {'confirms' if confirming else 'redirects'} the prior "
                   f"row" if cur_tid else "") + "). "
                f"Tier {d['tier']} INHERITED from the ruling, not computed from "
                f"the method - tier_source: {TIER_SOURCE}."
                + (f" Owner note: {d['note']}" if d["note"] else ""))
            changed += 1
            stats[f"-> tier A attributed ({'confirm' if confirming else 'redirect'})"] += 1
            applied_log.append(_log(d, "cedar_identifier_ledger_final.csv",
                                    "attributed tier A", 1, 0.0))

        elif d["action"] == "RULED_NOT_NATIVE" and cur_tier != "X":
            r["confidence_tier"] = "X"
            r["attribution_method"] = "elijah_ruling"
            r["tier_rationale"] = (
                f"Ruled by {RULED_BY} {d['ruled_date']}, applied in place "
                f"{TODAY} by {SCRIPT} from {d['source_file']}: NOT a Native "
                f"entity. Tier X is an EXCLUSION - it is the ruling's outcome, "
                f"not a by-product of a ruled method."
                + (f" Owner note: {d['note']}" if d["note"] else "")
                + (f" Cedar note: {d['cedar_note']}" if d["cedar_note"] else ""))
            changed += 1
            stats["-> tier X exclusion"] += 1
            applied_log.append(_log(d, "cedar_identifier_ledger_final.csv",
                                    "excluded tier X", 1, 0.0))

        elif d["action"] == "RULED_CLASS_ONLY":
            # The class is RECORDED. Nothing is attributed and no tier moves:
            # an individually Native-owned firm has no tribal owner to name,
            # and minting its CEDAR-ENT entity is a spine write the owner owns.
            r["tier_rationale"] = (
                f"Ruled by {RULED_BY} {d['ruled_date']}, recorded in place "
                f"{TODAY} by {SCRIPT} from {d['source_file']}: INDIVIDUALLY "
                f"NATIVE-OWNED FIRM. This is NOT a tribal, ANC or NHO "
                f"attribution and carries no ownership edge to any entity "
                f"(AGENTS.md 2026-08-07). Tier and attribution_method "
                f"deliberately UNCHANGED - the ruling settles the class, not an "
                f"owner. Spine entity not minted: see "
                f"{OUT_MINT.name}."
                + (f" Owner note: {d['note']}" if d["note"] else "")
                + " || " + (r.get("tier_rationale") or ""))
            changed += 1
            stats["-> individual-Native class recorded (nothing attributed)"] += 1
            applied_log.append(_log(d, "cedar_identifier_ledger_final.csv",
                                    "individual-Native class recorded", 1, 0.0))

    print(f"  rows changed: {changed:,}")
    for k, v in stats.most_common():
        print(f"    {k:60s} {v:>5}")
    if check:
        print("  --check: nothing written")
        return changed, refused
    if changed:
        rewrite(LEDGER, rows, fields, mtime0, "cedar_identifier_ledger_final.csv")
    return changed, refused


def apply_prime(dec, check, applied_log):
    print("\n[prime_contracts.csv]")
    mtime0 = PRIME.stat().st_mtime
    rows = load(PRIME)
    fields = list(rows[0])
    for c in ("ruling_status", "ruling_source_file", "ruling_applied_date"):
        if c not in fields:
            fields.append(c)

    stats = Counter()
    status_rows, status_usd = Counter(), Counter()
    moved_rows, moved_usd = 0, 0.0
    per_cluster = defaultdict(lambda: {"rows": 0, "usd": 0.0,
                                       "rows_moved": 0, "usd_moved": 0.0})
    contradictions = {}

    for r in rows:
        u = (r.get("awardee_uei") or "").strip().upper()
        c = (r.get("cage_code") or "").strip().upper()
        d = None
        for k in (("UEI", u) if u else None, ("CAGE", c) if c else None):
            if k and k in dec:
                d = dec[k]
                break
        if d is None:
            continue

        act = d["action"]
        pc = per_cluster[d["cluster_key"]]
        pc["rows"] += 1
        pc["usd"] += money(r)
        already = (r.get("attributed_flag") or "0").strip() == "1"
        cur_tid = (r.get("tribe_id") or "").strip()

        if already and act == "RULED_ATTRIBUTED" and cur_tid \
                and cur_tid != d["tribe_id"]:
            act = "RULING_CONFLICT"
            contradictions.setdefault(d["cluster_key"], {
                "cluster_key": d["cluster_key"],
                "conflict_kind": "TABLE_ATTRIBUTES_ELSEWHERE",
                "firm_name": d["firm_name"],
                "table_tribe_id": cur_tid,
                "table_canonical_name": r.get("canonical_name", ""),
                "table_tier": r.get("confidence_tier", ""),
                "ruling_tribe_id": d["tribe_id"],
                "ruling_canonical_name": d["canonical_name"],
                "why": "prime_contracts already attributes this identifier to "
                       "a different entity. NEITHER side overwritten.",
                "resolution": "FOR THE OWNER - not resolved by this script",
                "flagged_date": TODAY,
            })
        elif already and act in ("RULED_NOT_NATIVE", "RULED_CLASS_ONLY"):
            contradictions.setdefault(d["cluster_key"] + "|attr", {
                "cluster_key": d["cluster_key"],
                "conflict_kind": "TABLE_ATTRIBUTES_A_RULED_NON_ATTRIBUTION",
                "firm_name": d["firm_name"],
                "table_tribe_id": cur_tid,
                "table_canonical_name": r.get("canonical_name", ""),
                "table_tier": r.get("confidence_tier", ""),
                "ruling_tribe_id": "", "ruling_canonical_name": "",
                "why": f"the table attributes this identifier; the ruling is "
                       f"{act}. Attribution left in place, not erased.",
                "resolution": "FOR THE OWNER - not resolved by this script",
                "flagged_date": TODAY,
            })

        r["ruling_status"] = act
        r["ruling_source_file"] = d["source_file"]
        r["ruling_applied_date"] = TODAY
        status_rows[act] += 1
        status_usd[act] += money(r)

        if act == "RULED_ATTRIBUTED" and not already:
            r["tribe_id"] = d["tribe_id"]
            r["canonical_name"] = d["canonical_name"]
            r["attribution_method"] = "ruling_applied"
            r["confidence_tier"] = d["tier"]
            r["attributed_flag"] = "1"
            moved_rows += 1
            moved_usd += money(r)
            pc["rows_moved"] += 1
            pc["usd_moved"] += money(r)
            stats[f"attributed at tier {d['tier']}"] += 1

    print(f"  rows given an explicit ruling status: {sum(status_rows.values()):,}")
    print(f"    {'status':40s} {'rows':>8s}  {'dollars':>18s}")
    for k in sorted(status_rows, key=lambda x: -status_usd[x]):
        print(f"    {k:40s} {status_rows[k]:>8,}  ${status_usd[k]:>17,.0f}")
    print(f"\n  ROWS MOVED unattributed -> attributed: {moved_rows:,}")
    print(f"  DOLLARS MOVED (total_obligations)    : ${moved_usd:,.2f}")

    for cl, v in sorted(per_cluster.items(), key=lambda kv: -kv[1]["usd"]):
        d = next(x for x in dec.values() if x["cluster_key"] == cl)
        for e in applied_log:
            if e["cluster_key"] == cl and e["table"] == "prime_contracts.csv":
                break
        else:
            applied_log.append(_log(d, "prime_contracts.csv", d["action"],
                                    v["rows"], v["usd"], v["rows_moved"],
                                    v["usd_moved"]))

    if check:
        print("  --check: nothing written")
        return moved_rows, moved_usd, status_rows, status_usd, \
            list(contradictions.values()), per_cluster
    rewrite(PRIME, rows, fields, mtime0, "prime_contracts.csv")
    return moved_rows, moved_usd, status_rows, status_usd, \
        list(contradictions.values()), per_cluster


def count_subawards(dec):
    """subawards.csv is NOT written. Count what it now owes a promotion."""
    print("\n[subawards.csv] - COUNTED, NOT WRITTEN")
    if not SUBAWARDS.exists():
        print("  absent")
        return {}
    owed = Counter()
    amt = Counter()
    with open(SUBAWARDS, encoding="utf-8", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            for side in ("sub", "prime"):
                for col, typ in ((f"{side}_uei", "UEI"), (f"{side}_cage", "CAGE")):
                    k = (typ, (r.get(col) or "").strip().upper())
                    if k[1] and k in dec:
                        owed[(dec[k]["cluster_key"], side)] += 1
                        try:
                            amt[(dec[k]["cluster_key"], side)] += float(
                                r.get("subaward_amount") or 0)
                        except (TypeError, ValueError):
                            pass
                        break
    total = sum(owed.values())
    print(f"  {total:,} subaward rows sit on a ruled identifier across "
          f"{len({k[0] for k in owed})} clusters.")
    print("  NOT written by hand: `sub_native_tier`/`prime_native_tier` are "
          "COPIES of a ledger tier taken at promotion time. "
          "docs/ANCSA_OWNERSHIP_RULING.md: 'that direction is a PROMOTION and "
          "must not be done by hand. Re-running 41 then 45 is the route.'")
    for (cl, side), n in owed.most_common(12):
        print(f"    {cl:16s} {side:6s} {n:>6,} rows  ${amt[(cl, side)]:>15,.0f}")
    return {f"{k[0]}|{k[1]}": v for k, v in owed.items()}


def _log(d, table, what, rows, usd, rows_moved=None, usd_moved=None):
    return {
        "cluster_key": d["cluster_key"],
        "identifier_type": d.get("identifier_type", ""),
        "identifier": d.get("identifier", ""),
        "firm_name": d["firm_name"],
        "ruling": d["ruling"],
        "ruled_entity_as_written": d["entity"],
        "resolved_tribe_id": d["tribe_id"],
        "resolved_canonical_name": d["canonical_name"],
        "resolved_entity_class": d["entity_class"],
        "outcome": d["outcome"],
        "action": d["action"],
        "tier_written": d["tier"],
        "tier_source": TIER_SOURCE if d["tier"] else "n/a - nothing attributed",
        "table": table,
        "what_was_written": what,
        "rows_touched": rows,
        "usd_on_rows": round(usd, 2),
        "rows_moved_to_attributed": rows_moved if rows_moved is not None else "",
        "usd_moved_to_attributed": (round(usd_moved, 2)
                                    if usd_moved is not None else ""),
        "cedar_prior_guess": d["my_guess"],
        "cedar_prior_confidence": d["my_confidence"],
        "owner_note": d["note"],
        "ruling_source_file": d["source_file"],
        "applied_date": TODAY,
    }


def main():
    check = "--check" in sys.argv
    print(f"=== Cedar Press {SCRIPT} ===")
    print("  A ruling that is not applied back to its source table is not a "
          "ruling, it is a note.\n")

    m33 = load_module("m33", "33_apply_party_rulings.py")
    spine = load(SPINE)
    print(f"  spine   : {len(spine):,} entities")

    rulings = read_exports()
    print(f"  rulings : {len(rulings):,} export rows from "
          f"{len({r['source_file'] for r in rulings})} files")

    dec, clusters, conflicts = build_decisions(rulings, spine, m33)
    print(f"  clusters: {len(clusters):,}   identifier keys: {len(dec):,}")
    print(f"  by action: {dict(Counter(d['action'] for d in dec.values()))}")
    print(f"  conflicts recorded FOR THE OWNER: {len(conflicts):,}")
    for c in conflicts:
        print(f"    !! {c['conflict_kind']:52s} {c['cluster_key']:14s} "
              f"{c['firm_name'][:34]}")

    applied_log = []
    n_led, refused = apply_ledger(dec, check, applied_log)
    moved_rows, moved_usd, srows, susd, prime_conf, per_cluster = \
        apply_prime(dec, check, applied_log)
    owed = count_subawards(dec)

    conflicts += prime_conf
    mint = [{
        "cluster_key": c["cluster_key"], "firm_name": c["firm_name"],
        "identifiers": ";".join(sorted(
            f"{k[0]}:{k[1]}" for k, v in dec.items()
            if v["cluster_key"] == c["cluster_key"])),
        "ruling": c["ruling"],
        "prime_rows": per_cluster.get(c["cluster_key"], {}).get("rows", 0),
        "prime_usd": round(per_cluster.get(c["cluster_key"], {}).get("usd", 0), 2),
        "owner_note": c["note"],
        "request": "mint a CEDAR-ENT-* Individually Native-owned business "
                   "entity, or decline. A spine write is the owner's decision "
                   "(HANDOFF.md OPEN DECISIONS); the ruling is already "
                   "recorded on the ledger row.",
        "ruled_date": c["ruled_date"], "source_file": c["source_file"],
        "staged_date": TODAY,
    } for c in clusters.values() if c["action"] == "RULED_CLASS_ONLY"]

    print("\n[reports]")
    if check:
        print(f"  --check: would write {len(applied_log)} applied rows, "
              f"{len(conflicts)} conflicts, {len(mint)} mint requests")
    else:
        write_report(OUT_APPLIED, applied_log, "what was applied, per table")
        write_report(OUT_CONFLICTS, conflicts, "FOR THE OWNER - not resolved here")
        write_report(OUT_MINT, mint, "individual-Native spine mint requests")

    print("\n=== SUMMARY ===")
    print(f"  clusters ruled            : {len(clusters)}")
    print(f"  identifier keys           : {len(dec)}")
    print(f"  ledger rows changed       : {n_led:,}")
    print(f"  prime rows given a status : {sum(srows.values()):,}")
    print(f"  prime rows newly attributed: {moved_rows:,}")
    print(f"  DOLLARS MOVED             : ${moved_usd:,.2f}")
    print(f"  subaward rows owed a 41->45 promotion: {sum(owed.values()):,}")
    print(f"  conflicts for the owner   : {len(conflicts)}")
    print("\n  now run:  py -3 code/62_no_regression_check.py")


if __name__ == "__main__":
    main()
