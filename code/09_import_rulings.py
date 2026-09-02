#!/usr/bin/env python3
"""
Cedar Press - 09: Import Elijah's rulings and propagate them.

A ruling is not one decision - it is a seed. Three propagation channels:

  1. DIRECT      the ruled identifier is settled and re-tiered.
  2. STRUCTURAL  a confirmed parent validates the whole UEI family sharing
                 that ultimate_parent_uei - inherited, not guessed.
  3. PATTERN     a rejected attribution indicts the METHOD that produced it.
                 Nine "hand-checked wins" rulings against the same source is
                 evidence about that source, not nine isolated facts.

Reads  review/rulings_inbox_*.csv
Writes data/spine/cedar_rulings.csv                 (appended, permanent)
       data/clean/cedar_identifier_ledger_final.csv (re-tiered IN PLACE)
       review/pattern_flags_<date>.csv              (method-level suspicion)


THIS SCRIPT NOW RE-TIERS `_final` IN PLACE. IT USED TO REBUILD IT FROM A
STALE UPSTREAM. (2026-09-01, workstream C8)
=======================================================================
The destruction had one cause and it was not the re-tiering logic, which was
right. It was these two lines:

    ledger = read_csv(CLEAN / "cedar_identifier_ledger_tiered.csv")   # 19,232
    ...
    write_csv(CLEAN / "cedar_identifier_ledger_final.csv", ledger, fields)

It READ `_tiered` and WROTE `_final`. Those are not the same table.
`_final` is `_tiered` plus everything later scripts appended straight to it -
measured 2026-09-01, exactly 1,345 rows, with every one of `_tiered`'s 19,232
(key, occurrence) pairs present in `_final` and none missing. So the write
deleted the 1,345, of which **18 are tier A** `elijah_ruling` and
`nho_verified_entities.csv` rows: OWNER ADJUDICATIONS, the one class of fact
in this project that cannot be re-derived from any source. Running it on
2026-08-08 cost 1,327 rows and 451 village-corporation links the same way.

The hardcoded 17-column `fields` list was the second half of the same defect:
live `_final` carries 22 columns, so the write also dropped
`joint_ownership_flag`, `joint_ownership_note`, `evidence_source_file`,
`evidence_url_integrity` and `cedar_uid` - the project's most repeated defect,
committed by the script whose job is to preserve rulings.

Both are fixed the same way. The base is now LIVE `_final`, unioned with any
`_tiered` row not already in it (`cedar_pipeline.merge_table`, keyed on
identifier_type + identifier + occurrence ordinal, because 86 of those pairs
recur and collapsing them would be a row loss called deduplication). The
column set is read off the live file, never typed. The write asserts that no
row and no column was lost before it happens, and takes a `.bak_<date>_pre09`.

`--dry-run` does the whole computation and writes nothing.

Removed from `cedar_pipeline.NEVER_RUN` on 2026-09-01, after the fix and after
`812_c8_rebuild_proof.py` proved it. `124_apply_rulings_in_place.py` remains a
perfectly good narrower route; this one is no longer a trap.
"""

import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cedar_pipeline import merge_table, read_table, write_table  # noqa: E402

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

FINAL = CLEAN / "cedar_identifier_ledger_final.csv"
TIERED = CLEAN / "cedar_identifier_ledger_tiered.csv"

#: 86 (identifier_type, identifier) pairs recur in `_final`. `ordinal_key`
#: inside `merge_table` disambiguates them by occurrence, which is the same
#: repair HUB applied to the ruling map on 2026-09-01.
LEDGER_KEY = ["identifier_type", "identifier"]

#: An owner adjudication. These are the rows that cannot be re-derived, so
#: any tier-A loss among them is reported by name, never as a count.
ADJUDICATION_METHODS = ("elijah_ruling", "elijah_ruling_redirect",
                        "nho_verified_entities")

SCOPE_RE = re.compile(r"^\s*scope artifact\s*-\s*keep\s+(?P<entity>.+?)\s*$", re.I)
DROP_RE = re.compile(r"^\s*exclusion applies", re.I)

# RULING GRAMMAR - the shapes that are NOT an owner name.
#
# Script 33 has parsed these since it was written; script 09 never did, and the
# omission was expensive in a quiet way. Every one of these phrases was handed
# to the spine resolver as though it were a company name, failed to match, and
# was then reported as "the owner Elijah named is not in the spine" - which sent
# a search for 67 missing entities when only 8 were real. 42 of them were the
# single phrase "Named for a place - demote".
#
# Getting the OUTCOME right by accident is not the same as getting it right.
# A place-name demotion and an unfindable owner both end at tier X, but only one
# of them means the spine has a hole, and conflating them manufactures work.
NOT_NATIVE_RE = re.compile(
    r"^\s*(not a native|non-native|no\b|not_native|named for a place|"
    r"place[- ]name)", re.I)
ORG_RE = re.compile(r"^\s*native organi[sz]ation\s*[-:]", re.I)
MULTI_RE = re.compile(r"^\s*(multi-entity|two-sided|aggregate)", re.I)
HOLD_RE = re.compile(
    r"^\s*(unresolved|hold|held|needs|verify|uncertain)|"
    r"(control unclear|unclear)\s*$", re.I)
REINSTATE_RE = re.compile(r"\b(reinstate|restore)\b", re.I)

#: A VERDICT TOKEN IS NOT AN OWNER NAME.
#:
#: The inbox carries two review-page dialects. One names an owner ("Chenega
#: Corporation"); the other returns a verdict from a fixed vocabulary
#: (`NATIVE`, `NOT_NATIVE`, `OWNER_NAMED`, `INDIVIDUAL_NATIVE`). Until
#: 2026-09-01 this script had grammar for the first dialect only, so a verdict
#: was handed to the spine resolver as a company name, failed to match, and
#: took the `owner not in the spine` branch - which sets tier X. Measured by
#: dry run on 2026-09-01: that demoted **12 rows that were already tier A
#: owner adjudications**, and reported 28 non-existent "spine gaps".
#:
#: This is the identical defect the NOT_NATIVE_RE comment above describes
#: ("42 of them were the single phrase 'Named for a place - demote'"), one
#: dialect later. The fix is the same: parse the grammar before resolving.
#: An ALL-CAPS underscored token is never a legal business name.
VERDICT_TOKEN_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
KNOWN_VERDICTS = {
    "NOT_NATIVE": "not_native",
    "NATIVE": "affirm",
    "OWNER_NAMED": "hold",        # the owner is named in another column, not here
    "INDIVIDUAL_NATIVE": "hold",  # in scope, but not owned by a spine entity
}


def read_csv(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def resolve_to_spine(name, spine):
    """Resolve a ruled owner name to a spine entity.

    Delegates to 33_apply_party_rulings.resolve_entity so there is ONE resolver
    in the project. That function already carries the diacritic fold, the
    containment match for the spine's truncated canonical names, the
    corporate-form guard that keeps a company off a village government, and the
    word-order tie-break that separates Shoshone-Paiute from Paiute-Shoshone.
    Re-implementing any of that here would guarantee the two drift apart.
    """
    global _M33
    if _M33 is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "m33", CEDAR / "code" / "33_apply_party_rulings.py")
        _M33 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_M33)
    return _M33.resolve_entity(name, spine)


_M33 = None


def load_base():
    """The ledger this script re-tiers: LIVE `_final`, unioned with `_tiered`.

    Returns (rows, fields, report). The union is the whole C8 fix - see the
    module docstring. When `_final` does not yet exist, `_tiered` IS the base
    and there is nothing to preserve.
    """
    final_rows, final_fields = read_table(FINAL)
    tiered_rows, tiered_fields = read_table(TIERED)
    if not final_rows:
        return tiered_rows, tiered_fields, None
    rows, fields, rep = merge_table(
        FINAL, tiered_rows, tiered_fields, LEDGER_KEY,
        dry_run=True)          # merged in memory; the single write is at [5]
    return rows, fields, rep


def main(dry_run=False):
    print("=== Cedar Press: import rulings + propagate ===")
    if dry_run:
        print("    DRY RUN - nothing will be written\n")
    else:
        print()

    inbox = []
    for p in sorted(REVIEW.glob("rulings_inbox_*.csv")):
        rows = read_csv(p)
        print(f"  inbox {p.name}: {len(rows)} rulings")
        inbox.extend(rows)
    if not inbox:
        raise SystemExit("No rulings_inbox_*.csv found in review/")

    ledger, fields, union = load_base()
    excl = read_csv(SPINE / "cedar_exclusion_rulings.csv")
    hier = read_csv(CEDAR / "data" / "raw" / "external" / "uei_hierarchy_graph.csv")
    rows_before = len(ledger)
    fields_before = list(fields)
    print(f"\nledger base : {rows_before:,} rows, {len(fields)} columns "
          f"(LIVE cedar_identifier_ledger_final.csv, not the stale _tiered)")
    if union:
        print(f"  union with _tiered: +{union.rows_appended:,} rows not "
              f"already in _final, {union.rows_matched:,} matched")

    # Tier-A adjudications going in. Counted by name so a loss cannot hide.
    adj_before = {
        (r["identifier_type"], r["identifier"].upper())
        for r in ledger
        if r.get("confidence_tier") == "A"
        and (any(m in (r.get("attribution_method") or "")
                 for m in ADJUDICATION_METHODS)
             or "nho_verified_entities" in (r.get("source_file") or ""))
    }
    print(f"  tier-A owner adjudications carried in : {len(adj_before)}")

    # ---- 1. DIRECT --------------------------------------------------------
    print("\n[1] Direct application")
    settled = {}          # (idtype, identifier) -> chosen entity name
    scope_reclass = set()  # exclusion_ids demoted from ownership to scope
    dropped = set()

    excl_by_ident = {(r["identifier_type"], r["identifier"].upper()): r for r in excl}

    for r in inbox:
        rid = (r.get("review_id") or "").strip()
        ruling = (r.get("YOUR_RULING") or "").strip()
        if not rid or not ruling:
            continue
        idtype, _, ident = rid.partition(":")
        key = (idtype, ident.upper())

        m = SCOPE_RE.match(ruling)
        if m:
            settled[key] = m.group("entity").strip()
            hit = excl_by_ident.get(key)
            if hit:
                scope_reclass.add(hit["exclusion_id"])
        elif DROP_RE.match(ruling):
            dropped.add(key)
        else:
            settled[key] = ruling

    print(f"  identifiers settled to an owner : {len(settled)}")
    print(f"  exclusions reclassified to SCOPE: {len(scope_reclass)}  {sorted(scope_reclass)}")
    print(f"  identifiers confirmed dropped   : {len(dropped)}")

    # ---- 2. RE-TIER -------------------------------------------------------
    print("\n[2] Re-tiering the ledger IN PLACE")
    promoted = demoted = restored = redirected = 0
    unresolved_owner = []
    unparsed_verdicts = []
    protected_adjudications = []
    grammar = Counter()

    def is_adjudication(r):
        return (any(m in (r.get("attribution_method") or "")
                    for m in ADJUDICATION_METHODS)
                or "nho_verified_entities" in (r.get("source_file") or ""))

    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    for row in ledger:
        key = (row["identifier_type"], row["identifier"].upper())
        if key in dropped:
            row["confidence_tier"] = "X"
            row["tier_rationale"] = f"Ruled excluded by Elijah {TODAY}"
            continue
        if key not in settled:
            continue
        chosen = settled[key]

        # Parse the grammar BEFORE trying to resolve a name, or a sentence like
        # "Named for a place - demote" becomes a search for a company called
        # "Named for a place".
        if NOT_NATIVE_RE.match(chosen):
            if row["confidence_tier"] in ("A", "B"):
                demoted += 1
            row["confidence_tier"] = "X"
            row["tier_rationale"] = f"Ruled by Elijah {TODAY}: not a Native entity"
            grammar["not_native"] += 1
            continue
        if ORG_RE.match(chosen):
            # In scope as a Native ORGANISATION, but owned by no single entity.
            row["confidence_tier"] = "A"
            row["is_authority"] = "YES"
            row["tier_rationale"] = (f"Ruled by Elijah {TODAY}: Native organisation, "
                                     f"not owned by a single entity")
            grammar["native_org"] += 1
            continue
        if MULTI_RE.match(chosen) or HOLD_RE.search(chosen):
            # Real but unresolved. Attributing to one entity would be false;
            # excluding would discard a true row. Leave it where it is.
            grammar["held"] += 1
            continue
        if REINSTATE_RE.search(chosen):
            # "Tribally controlled / Native-controlled - reinstate" is an
            # instruction, and until today it was read as the name of a
            # company called "Tribally controlled / Native-controlled",
            # failed to resolve, and DEMOTED the row it was meant to restore.
            # A ruling that says reinstate must not end in exclusion.
            if row["confidence_tier"] != "A":
                restored += 1
            row["confidence_tier"] = "A"
            row["is_authority"] = "YES"
            row["tier_rationale"] = (
                f"Ruled by Elijah {TODAY}: reinstated - {chosen}")
            grammar["reinstate"] += 1
            continue
        if VERDICT_TOKEN_RE.match(chosen) or chosen.upper() in KNOWN_VERDICTS:
            verdict = KNOWN_VERDICTS.get(chosen.upper())
            if verdict == "affirm":
                # In scope, and the existing attribution is not disputed.
                if row["confidence_tier"] not in ("A",):
                    promoted += 1
                row["confidence_tier"] = "A"
                row["is_authority"] = "YES"
                row["tier_rationale"] = (
                    f"Ruled by Elijah {TODAY}: NATIVE - in scope, existing "
                    f"attribution upheld")
                grammar["verdict:affirm"] += 1
            else:
                # A token this script cannot read is HELD and NAMED. It is
                # never converted into a demotion: an unreadable verdict is
                # not evidence against the row it lands on.
                unparsed_verdicts.append(
                    (row["identifier_type"], row["identifier"], chosen,
                     row.get("confidence_tier", ""),
                     row.get("attribution_method", "")))
                grammar[f"verdict:{verdict or 'UNREAD'}"] += 1
            continue

        same = norm(row["canonical_name"]) == norm(chosen)
        if same:
            if row["confidence_tier"] == "X":
                restored += 1
            elif row["confidence_tier"] != "A":
                promoted += 1
            row["confidence_tier"] = "A"
            row["tier_rationale"] = f"Ruled by Elijah {TODAY}: confirmed owner"
            row["is_authority"] = "YES"
        else:
            # A RULING THAT NAMES A DIFFERENT OWNER IS A REDIRECT, NOT A DELETION.
            #
            # This branch used to set tier X, write "owner is <chosen>, not
            # <canonical_name>", and leave the WRONG tribe_id in place. The
            # rejection was recorded and the answer was thrown away.
            #
            # Cost, measured 2026-08-05: 138 UEIs carrying $17.83B sat at tier X
            # with the correct owner written in their own tier_rationale -
            # Njvc LLC excluded against the Native Village of Chenega while the
            # rationale read "owner is Chenega Corporation". Afognak $4,050.2M,
            # Chenega $4,023.3M, Eyak $1,952.9M, Choggiung $1,561.4M all sat
            # there needing no research whatsoever.
            #
            # It is the same failure Elijah named on the review page: a bare
            # "No" only rules out a guess, while naming the entity captures the
            # attribution. When he names an owner, we must BOOK it.
            tid, canon, how = resolve_to_spine(chosen, spine)
            if tid:
                if row["confidence_tier"] != "A":
                    promoted += 1
                redirected += 1
                row["tribe_id"] = tid
                row["canonical_name"] = canon
                row["confidence_tier"] = "A"
                row["is_authority"] = "YES"
                row["attribution_method"] = "elijah_ruling_redirect"
                row["tier_rationale"] = (
                    f"Ruled by Elijah {TODAY}: re-attributed to {canon} "
                    f"(matched by {how}); the earlier claim was wrong.")
            elif row.get("confidence_tier") == "A" and is_adjudication(row):
                # AN UNRESOLVABLE STRING IS NOT EVIDENCE AGAINST AN
                # ADJUDICATION THAT ALREADY EXISTS.
                #
                # The branch below is right for an unreviewed algorithmic
                # claim: if a ruling rejects it and names an owner nobody can
                # find, the claim should not keep shipping at tier A. It is
                # wrong for a row that is ALREADY tier A because an owner
                # adjudicated it - there, the only thing the failure proves is
                # that this script could not read the string. Demoting on that
                # basis destroys the one class of fact in this project that
                # cannot be re-derived, and it destroys it on the strength of
                # a parse failure.
                protected_adjudications.append(
                    (row["identifier_type"], row["identifier"], chosen, how))
                unresolved_owner.append((row["identifier"], chosen, how))
            else:
                # Only when the named owner cannot be found in the spine is
                # exclusion the honest outcome - and it is reported, so the
                # spine gap is visible rather than silently eating a ruling.
                if row["confidence_tier"] in ("A", "B"):
                    demoted += 1
                unresolved_owner.append((row["identifier"], chosen, how))
                row["confidence_tier"] = "X"
                row["tier_rationale"] = (
                    f"Ruled by Elijah {TODAY}: owner is {chosen}, not "
                    f"{row['canonical_name']} - but {chosen} is not in the "
                    f"spine ({how}), so this could not be re-attributed.")
    if grammar:
        print("  ruling grammar parsed (not owner names):")
        for k, v in grammar.most_common():
            print(f"      {v:5d}  {k}")
    print(f"  promoted to A : {promoted}")
    print(f"  RE-ATTRIBUTED to the owner Elijah named : {redirected}")
    if unresolved_owner:
        print(f"  named owner NOT in the spine : {len(unresolved_owner)}"
              f"  <- spine gaps, not bad rulings")
        for ident, chosen, how in unresolved_owner[:8]:
            print(f"      {ident:14s} -> {chosen[:38]:38s} ({how})")
    print(f"  restored from X : {restored}")
    print(f"  demoted to X (rejected claim) : {demoted}")
    if protected_adjudications:
        print(f"  HELD, not demoted - {len(protected_adjudications)} existing "
              f"tier-A owner adjudication(s) whose ruling text this script "
              f"could not resolve. A parse failure is not evidence:")
        for t, i, chosen, how in protected_adjudications[:10]:
            print(f"      {t} {i:14s} ruling={chosen[:34]!r} ({how})")
    if unparsed_verdicts:
        print(f"  verdict tokens this script cannot act on : "
              f"{len(unparsed_verdicts)} (held, named, written to review/)")
        if not dry_run:
            write_table(REVIEW / f"ruling_verdicts_unparsed_{TODAY}.csv",
                        [dict(zip(("identifier_type", "identifier", "verdict",
                                   "current_tier", "attribution_method"), v))
                         for v in unparsed_verdicts],
                        ["identifier_type", "identifier", "verdict",
                         "current_tier", "attribution_method"],
                        backup_tag="pre09")

    # ---- 3. STRUCTURAL propagation ---------------------------------------
    print("\n[3] Structural propagation from confirmed parents")
    family = defaultdict(set)   # ultimate_parent_uei -> {child ueis}
    node = {}
    for r in hier:
        u = (r.get("uei") or "").strip().upper()
        up = (r.get("ultimate_parent_uei") or "").strip().upper()
        if u:
            node[u] = (r.get("name") or "").strip()
        if u and up and up != u:
            family[up].add(u)

    confirmed_ueis = {ident for (t, ident) in settled if t == "UEI"}
    known = {r["identifier"].upper() for r in ledger
             if r["identifier_type"] == "UEI" and r["confidence_tier"] in ("A", "B", "X")}

    inherited = []
    for uei in confirmed_ueis:
        owner = settled[("UEI", uei)]
        # The confirmed firm's own ultimate parent, and its siblings.
        for parent, kids in family.items():
            if uei not in kids and parent != uei:
                continue
            for kid in kids | {parent}:
                if kid == uei or kid in known:
                    continue
                inherited.append({
                    "identifier_type": "UEI",
                    "identifier": kid,
                    "legal_business_name": node.get(kid, ""),
                    "inherited_owner": owner,
                    "via_confirmed_uei": uei,
                    "ultimate_parent_uei": parent,
                    "confidence_tier": "A_INHERITED",
                    "basis": "Shares ultimate_parent_uei with a firm Elijah confirmed",
                    "date": TODAY,
                })
    if inherited and not dry_run:
        write_table(CLEAN / f"cedar_inherited_from_rulings_{TODAY}.csv", inherited,
                    ["identifier_type", "identifier", "legal_business_name",
                     "inherited_owner", "via_confirmed_uei", "ultimate_parent_uei",
                     "confidence_tier", "basis", "date"], backup_tag="pre09")
    print(f"  new identifiers inherited structurally : {len(inherited)}")

    # ---- 4. PATTERN indictment -------------------------------------------
    print("\n[4] Method-level pattern flags")
    rejected_methods = Counter()
    upheld_methods = Counter()
    for row in ledger:
        key = (row["identifier_type"], row["identifier"].upper())
        if key not in settled:
            continue
        if norm(row["canonical_name"]) == norm(settled[key]):
            upheld_methods[row["attribution_method"]] += 1
        else:
            rejected_methods[row["attribution_method"]] += 1

    flags = []
    for method, nrej in rejected_methods.most_common():
        nup = upheld_methods.get(method, 0)
        total = nrej + nup
        rate = nrej / total if total else 0
        affected = sum(1 for r in ledger
                       if r["attribution_method"] == method
                       and r["confidence_tier"] in ("A", "B"))
        flags.append({
            "attribution_method": method,
            "rulings_against": nrej,
            "rulings_upholding": nup,
            "rejection_rate": f"{rate:.0%}",
            "links_still_relying_on_it": affected,
            "recommendation": ("QUARANTINE - every link from this method needs review"
                               if rate >= 0.8 else
                               "Elevated suspicion - prioritize in the review queue"),
        })
    if flags:
        if not dry_run:
            write_table(REVIEW / f"pattern_flags_{TODAY}.csv", flags,
                        ["attribution_method", "rulings_against", "rulings_upholding",
                         "rejection_rate", "links_still_relying_on_it",
                         "recommendation"], backup_tag="pre09")
        for f in flags:
            print(f"  {f['attribution_method']}: {f['rulings_against']} against / "
                  f"{f['rulings_upholding']} for ({f['rejection_rate']}) -> "
                  f"{f['links_still_relying_on_it']:,} links affected")

    # ---- 5. persist, with the loss check BEFORE the write -----------------
    print("\n[5] Writing outputs")
    lost_cols = [c for c in fields_before if c not in fields]
    if lost_cols:
        raise RuntimeError(f"REFUSING to write: would drop columns {lost_cols}")
    if len(ledger) < rows_before:
        raise RuntimeError(
            f"REFUSING to write: {rows_before:,} rows in, {len(ledger):,} out")

    adj_after = {
        (r["identifier_type"], r["identifier"].upper())
        for r in ledger
        if r.get("confidence_tier") == "A"
        and (any(m in (r.get("attribution_method") or "")
                 for m in ADJUDICATION_METHODS)
             or "nho_verified_entities" in (r.get("source_file") or ""))
    }
    lost_adj = sorted(adj_before - adj_after)
    if lost_adj:
        # Not fatal - a NEW ruling may legitimately supersede an old one - but
        # it is never a number. An owner adjudication that stops being tier A
        # is named, so the change can be read and disputed.
        print(f"  !! {len(lost_adj)} tier-A owner adjudication(s) no longer "
              f"tier A. Each is named, none was dropped:")
        for t, i in lost_adj[:20]:
            print(f"       {t} {i}")
    else:
        print(f"  tier-A owner adjudications preserved : "
              f"{len(adj_after)} / {len(adj_before)}")

    print(f"  rows {rows_before:,} -> {len(ledger):,}   "
          f"columns {len(fields_before)} -> {len(fields)}   "
          f"(nothing lost)")
    if not dry_run:
        write_table(FINAL, ledger, fields, backup_tag="pre09")
        print(f"  wrote {FINAL.relative_to(CEDAR)}  ({len(ledger):,} rows, "
              f"{len(fields)} cols)")

    tiers = Counter(r["confidence_tier"] for r in ledger)
    print("\n=== FINAL TIERS ===")
    for t in ("A", "B", "C", "X"):
        print(f"  tier {t}: {tiers[t]:>6,}")

    val = 0.0
    for r in ledger:
        if r["confidence_tier"] == "A":
            try:
                val += float(r["prime_dollars_M"] or 0)
            except ValueError:
                pass
    print(f"\n  publishable prime dollars: ${val:,.0f}M")
    if dry_run:
        print("\nDRY RUN: no file was written, no backup was taken.")

    return {"cedar_identifier_ledger_final.csv": {
        "rows_before": rows_before, "rows_after": len(ledger),
        "n_cols_before": len(fields_before), "n_cols_after": len(fields),
        "cols_lost": lost_cols, "rows_lost": max(0, rows_before - len(ledger)),
        "tierA_adjudications_before": len(adj_before),
        "tierA_adjudications_after": len(adj_after),
        "ok": not lost_cols and len(ledger) >= rows_before}}


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
