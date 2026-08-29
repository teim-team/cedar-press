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
       data/clean/cedar_identifier_ledger_final.csv (re-tiered)
       review/pattern_flags_<date>.csv              (method-level suspicion)
"""

import csv
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

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
    r"^\s*(not a native|non-native|no|named for a place|place[- ]name)", re.I)
ORG_RE = re.compile(r"^\s*native organi[sz]ation\s*[-:]", re.I)
MULTI_RE = re.compile(r"^\s*(multi-entity|two-sided|aggregate)", re.I)
HOLD_RE = re.compile(r"^\s*(unresolved|hold|held|needs|verify|uncertain)", re.I)


def read_csv(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields, append=False):
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if (append and p.exists()) else "w"
    with open(p, mode, encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        if mode == "w":
            w.writeheader()
        w.writerows(rows)
    print(f"  {'appended to' if mode=='a' else 'wrote'} {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


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


def main():
    print("=== Cedar Press: import rulings + propagate ===\n")

    inbox = []
    for p in sorted(REVIEW.glob("rulings_inbox_*.csv")):
        rows = read_csv(p)
        print(f"  inbox {p.name}: {len(rows)} rulings")
        inbox.extend(rows)
    if not inbox:
        raise SystemExit("No rulings_inbox_*.csv found in review/")

    ledger = read_csv(CLEAN / "cedar_identifier_ledger_tiered.csv")
    excl = read_csv(SPINE / "cedar_exclusion_rulings.csv")
    hier = read_csv(CEDAR / "data" / "raw" / "external" / "uei_hierarchy_graph.csv")
    print(f"\nledger links : {len(ledger):,}")

    # ---- 1. DIRECT --------------------------------------------------------
    print("\n[1] Direct application")
    settled = {}          # (idtype, identifier) -> chosen entity name
    scope_reclass = set() # exclusion_ids demoted from ownership to scope
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
    print("\n[2] Re-tiering the ledger")
    promoted = demoted = restored = redirected = 0
    unresolved_owner = []
    grammar = Counter()
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
        if MULTI_RE.match(chosen) or HOLD_RE.match(chosen):
            # Real but unresolved. Attributing to one entity would be false;
            # excluding would discard a true row. Leave it where it is.
            grammar["held"] += 1
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
    if inherited:
        write_csv(CLEAN / f"cedar_inherited_from_rulings_{TODAY}.csv", inherited,
                  ["identifier_type", "identifier", "legal_business_name",
                   "inherited_owner", "via_confirmed_uei", "ultimate_parent_uei",
                   "confidence_tier", "basis", "date"])
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
        write_csv(REVIEW / f"pattern_flags_{TODAY}.csv", flags,
                  ["attribution_method", "rulings_against", "rulings_upholding",
                   "rejection_rate", "links_still_relying_on_it", "recommendation"])
        for f in flags:
            print(f"  {f['attribution_method']}: {f['rulings_against']} against / "
                  f"{f['rulings_upholding']} for ({f['rejection_rate']}) -> "
                  f"{f['links_still_relying_on_it']:,} links affected")

    # ---- 5. persist -------------------------------------------------------
    print("\n[5] Writing outputs")
    fields = ["identifier_type", "identifier", "tribe_id", "canonical_name",
              "legal_business_name", "entity_class", "attribution_method",
              "confidence_tier", "tier_rationale", "is_authority",
              "exclusion_id", "exclusion_evidence", "evidence_url",
              "verified_date", "state", "prime_dollars_M", "source_file"]
    write_csv(CLEAN / "cedar_identifier_ledger_final.csv", ledger, fields)

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


if __name__ == "__main__":
    main()
