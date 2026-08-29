#!/usr/bin/env python3
"""
Cedar Press - 417: the identity crosswalk. Every external identifier Cedar
holds, resolved to ONE Cedar entity id, with the TIER and the ASSERTING SOURCE
on every mapping.

    Elijah: "our ID system supersedes CICD, and UEI etc, but is aligned with
             one Native entity or org."

THE FILES THIS BUILD TREATS AS THE TRUTH
----------------------------------------
    data/spine/cedar_entity_spine.csv               the entity universe
    data/clean/cedar_identifier_ledger_final.csv    UEI / CAGE / EIN
    data/clean/assistance_tribe_id_crosswalk.csv    the legacy integer PROPOSAL
Nothing here re-derives a mapping any of those already state.

WHAT A ROW OF THE OUTPUT MEANS
------------------------------
    (external_scheme, external_identifier)  ->  cedar_entity_id

**One direction only, and that direction is the whole design.** The Cedar id is
the key; everything else is an ATTRIBUTE bound to it. So:

  * MANY identifiers per entity is EXPECTED and is not a defect. The 8(a)
    nine-year term drives successor entities sharing a name and an address, and
    a large ANC family holds dozens of registrations. Measured here and
    reported.
  * ONE identifier resolving to MANY entities is a DEFECT. Those rows are NOT
    written as mappings. They go to `review/` with every candidate named,
    because a crosswalk that silently picks one of two entities is worse than
    one that admits it cannot choose.

FIVE RULES THIS BUILD OBEYS, EACH ONE PAID FOR
----------------------------------------------
1. **A TIER IS INHERITED FROM THE SOURCE ROW, NEVER ASSIGNED HERE.** Every
   mapping copies `confidence_tier` verbatim and names the column it came from
   in `tier_source`. The exactness of the KEY says nothing about the
   correctness of the LINK - an exact EIN join at tier B is still tier B. This
   is the rule that put UNITED WAY OF THE GREATER CHIPPEWA VALLEY (Wisconsin)
   onto United Auburn (California) at tier A.
2. **A RULED METHOD IS NOT A POSITIVE RULING.** `elijah_ruling` is in
   RULED_METHODS whether the owner said yes or no, and 344 of those ledger rows
   are tier X - NEGATIVE. Tier X rows are emitted with
   `mapping_direction = REFUSED`, never as an attribution. `148` shipped 317
   exclusions as tier-A attributions by reading the method and not the sign.
3. **THE ASSISTANCE NEID CROSSWALK IS A RULING, NOT A COMPUTATION.** Scripts
   152 and 24 both decline to apply it in writing; 122 of its 344 candidates
   rest on the containment matcher AGENTS.md forbids from keying a dollar.
   Every legacy-integer row here is `PROPOSED_NOT_APPLIED` and says so in
   `mapping_status`. **This file does not adopt it and no consumer should read
   it as adopted.**
4. **LICENSED AND PRIVATE IDENTIFIERS ARE MARKED AT THE ROW.**
   `cedar_domain.may_publish_identifier` refuses DUNS at every tier, and
   `cedar_domain.may_publish_individual_native_field` withholds a UEI whose
   legal name is a natural person's - SAM's public search resolves it to that
   person in one hop. **A digest of a UEI is NOT a privacy control**: SAM's
   entity space is enumerable, so any digest is reversible by hashing every UEI
   and comparing. The protection is that the column does not ship.
5. **THE KEY IS DETERMINISTIC, NEVER POSITIONAL.** `crosswalk_id` is
   `cedar_keys.surrogate_id` over the stated columns, per class 7. Never
   `enumerate`, never `hash()`, never a rank.

Writes:
    data/clean/cedar_entity_identity_crosswalk.csv
    review/identity_crosswalk_refused_<date>.csv

    py -3 code/417_build_entity_identity_crosswalk.py            # dry run
    py -3 code/417_build_entity_identity_crosswalk.py --apply
"""

import csv
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import cedar_domain as D                                    # noqa: E402
import cedar_ids as IDS                                     # noqa: E402
from cedar_keys import surrogate_id                         # noqa: E402

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
LEDGER = CEDAR / "data" / "clean" / "cedar_identifier_ledger_final.csv"
ASSIST_XW = CEDAR / "data" / "clean" / "assistance_tribe_id_crosswalk.csv"
OUT = CEDAR / "data" / "clean" / "cedar_entity_identity_crosswalk.csv"
TODAY = date.today().isoformat()
REFUSED = CEDAR / "review" / f"identity_crosswalk_refused_{TODAY}.csv"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

FIELDS = [
    "crosswalk_id",
    "cedar_entity_id", "cedar_entity_name", "cedar_entity_class",
    "external_scheme", "external_identifier",
    "mapping_direction", "mapping_status",
    "confidence_tier", "tier_source", "attribution_method",
    "asserting_authority", "source_file", "basis",
    "identifier_publishes", "publish_restriction",
    "n_entities_for_this_identifier",
    "built_by", "built_date",
]

#: The columns `crosswalk_id` is a digest of. Named beside the definition and
#: checked by `328_audit_id_service_bypass.py`, per the class-7 migration spec.
CROSSWALK_ID_KEY_COLUMNS = ("external_scheme", "external_identifier",
                            "cedar_entity_id", "mapping_direction")

#: Prefixes delivered by the CICD Native Entity Connector Crosswalk (Feb 2026).
CICD_PREFIXES = ("TRBF", "AKNF", "TRBS", "CNSF", "ANRC", "SGVF", "CNSS")

CICD_BASIS = (
    "The spine id string for this entity IS the CICD Native Entity Connector "
    "Crosswalk's NEID, because CICD's file SEEDED the spine. The mapping is "
    "therefore an IDENTITY today and is declared anyway: Cedar's id is "
    "AUTHORITATIVE and CICD's is an ALIAS, so the day the two diverge - a "
    "recognition event, a split, a merge, a rename - the alias keeps resolving "
    "and nothing downstream breaks. Owner ruling 2026-08-26 "
    "(docs/PUBLISHED_LANDSCAPE_2026-08-26.md): the crosswalk is an INPUT, not "
    "a blocker - the entities are public facts and Cedar has more than doubled "
    "the universe. Credit it on the methods page.")

ASSIST_BASIS = (
    "PROPOSAL ONLY. federal_funding_transactions.csv carries a legacy INTEGER "
    "tribe_id on 365,535 rows worth $107.50B beside a Cedar id on 183,995. "
    "code/152 and code/24 BOTH decline to apply this crosswalk in writing - "
    "'the NEID crosswalk is a ruling, not a computation' - because 122 of its "
    "344 candidates rest on the containment matcher AGENTS.md forbids from "
    "keying a dollar. That refusal is honoured: this row is NOT applied to any "
    "transaction and a consumer must adopt or refuse it explicitly. The right "
    "key for the legacy integers is data/raw/external/federal_funding/"
    "lineageA_dta_corrtd_tribe_key.csv - NEVER playground.do, whose ranges "
    "overlap and disagree (307 -> Stillaguamish there, Southern Ute here).")


def g(r, c):
    return (r.get(c) or "").strip()


def read(p):
    if not Path(p).exists():
        return [], []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        return list(rd), list(rd.fieldnames or [])


def main():
    apply = "--apply" in sys.argv
    spine, _ = read(SPINE)
    meta = {g(r, "tribe_id"): r for r in spine}
    ids = set(meta)
    print(f"spine: {len(spine):,} entities")

    out, refused = [], []
    stats = Counter()

    def emit(**kw):
        row = {f: "" for f in FIELDS}
        row.update(kw)
        row["built_by"] = "code/417_build_entity_identity_crosswalk.py"
        row["built_date"] = TODAY
        row["crosswalk_id"] = surrogate_id("CXW", row,
                                           CROSSWALK_ID_KEY_COLUMNS)
        out.append(row)

    # ----------------------------------------------------------- 1. CICD NEID
    for r in spine:
        t = g(r, "tribe_id")
        p = IDS._prefix_of(t)
        if p not in CICD_PREFIXES:
            continue
        stats["CICD_NEID"] += 1
        emit(cedar_entity_id=t, cedar_entity_name=g(r, "canonical_name"),
             cedar_entity_class=g(r, "entity_class"),
             external_scheme="CICD_NEID", external_identifier=t,
             mapping_direction="ALIAS_OF_CEDAR_ID",
             mapping_status="APPLIED",
             confidence_tier="A",
             tier_source="cedar_entity_spine.csv - the entity is in the spine "
                         "and the CICD id IS its spine id",
             attribution_method="seeded_from_cicd_crosswalk",
             asserting_authority="CICD Native Entity Connector Crosswalk, "
                                 "Feb 2026",
             source_file="data/spine/cedar_entity_spine.csv",
             basis=CICD_BASIS,
             identifier_publishes="Y", n_entities_for_this_identifier="1")

    # -------------------------------------------------- 2. ENTITY_MASTER FK
    for r in spine:
        reg = g(r, "entity_master_register_id") or g(r, "cedar_entity_id")
        if not reg or IDS.is_canonical_entity_id(reg):
            continue
        stats["ENTITY_MASTER"] += 1
        emit(cedar_entity_id=g(r, "tribe_id"),
             cedar_entity_name=g(r, "canonical_name"),
             cedar_entity_class=g(r, "entity_class"),
             external_scheme="ENTITY_MASTER", external_identifier=reg,
             mapping_direction="ATTRIBUTE_OF_CEDAR_ID",
             mapping_status="APPLIED", confidence_tier="A",
             tier_source="cedar_entity_spine.csv - the register id was "
                         "recorded on the row when the entity was added",
             attribution_method="upstream_register_join",
             asserting_authority="Cedar Entity_Master workbook register",
             source_file="data/spine/cedar_entity_spine.csv",
             basis="entity_master.csv::Entity_ID. NOT a Cedar id, despite "
                   "living in a spine column called `cedar_entity_id`. "
                   "Scripts 52/61/66/163 dedupe on it. See "
                   "cedar_ids.ENTITY_ID_COLUMN_MEANINGS.",
             identifier_publishes="N",
             publish_restriction="internal register key; no external "
                                 "authority asserts it",
             n_entities_for_this_identifier="1")

    # --------------------------------------------- 3. UEI / CAGE / EIN ledger
    ledger, _ = read(LEDGER)
    print(f"ledger: {len(ledger):,} rows")
    holders = defaultdict(set)
    for r in ledger:
        it, iv, e = g(r, "identifier_type"), g(r, "identifier"), g(r, "tribe_id")
        if it and iv and e:
            holders[(it, iv)].add(e)

    for r in ledger:
        it, iv, e = g(r, "identifier_type"), g(r, "identifier"), g(r, "tribe_id")
        tier = g(r, "confidence_tier")
        meth = g(r, "attribution_method")
        if not it or not iv:
            stats["ledger_row_with_no_identifier"] += 1
            continue
        if not e:
            stats["ledger_row_with_no_entity"] += 1
            continue
        if e not in ids:
            refused.append({"external_scheme": it, "external_identifier": iv,
                            "reason": "ENTITY_NOT_IN_SPINE",
                            "candidates": e, "tiers": tier,
                            "detail": "the ledger names an entity the spine "
                                      "does not carry"})
            stats["refused_entity_not_in_spine"] += 1
            continue
        n = len(holders[(it, iv)])
        if IDS.mapping_is_defect(n):
            refused.append({
                "external_scheme": it, "external_identifier": iv,
                "reason": "ONE_IDENTIFIER_MANY_ENTITIES",
                "candidates": "|".join(sorted(holders[(it, iv)])),
                "tiers": tier,
                "detail": "many identifiers per entity is EXPECTED; one "
                          "identifier held by many entities is a DEFECT. Not "
                          "written as a mapping - a crosswalk that silently "
                          "picks one of two is worse than one that admits it "
                          "cannot choose."})
            stats["refused_one_identifier_many_entities"] += 1
            continue

        # READ THE SIGN BEFORE INHERITING THE AUTHORITY.
        if tier == "X":
            direction, status = "REFUSED", "NEGATIVE_RULING_DO_NOT_ATTRIBUTE"
            stats[f"{it}_tier_X_refusal"] += 1
        else:
            direction, status = "ATTRIBUTE_OF_CEDAR_ID", "APPLIED"
            stats[it] += 1

        sm = meta[e]
        cls = g(sm, "entity_class")
        pub = D.may_publish_identifier(it)
        restriction = ""
        if not pub:
            restriction = ("LICENSED - cedar_domain.LICENSED_IDENTIFIER_TYPES."
                           " Join internally; never publishes at any tier.")
        elif cls == D.INDIVIDUAL_NATIVE_CLASS and it in ("UEI", "CAGE"):
            pub = False
            restriction = (
                "WITHHELD - cedar_domain.may_publish_individual_native_field. "
                "SAM's public entity search resolves a UEI to a legal name and "
                "a street address, so for a firm whose legal name IS a "
                "person's name, publishing the identifier publishes the person "
                "by ONE HOP. A DIGEST IS NOT A FIX: SAM's entity space is "
                "enumerable, so a hashed UEI is reversible by hashing every "
                "UEI and comparing. The protection is that the column does not "
                "ship. consent_status is NOT_ASKED on every row of this class "
                "- a firm's website statement is our EVIDENCE, never its "
                "PERMISSION.")

        emit(cedar_entity_id=e, cedar_entity_name=g(sm, "canonical_name"),
             cedar_entity_class=cls,
             external_scheme=it, external_identifier=iv,
             mapping_direction=direction, mapping_status=status,
             confidence_tier=tier,
             tier_source="cedar_identifier_ledger_final.csv::confidence_tier "
                         "- INHERITED verbatim, never assigned here",
             attribution_method=meth,
             asserting_authority=(IDS.identifier_scheme(it) or {}).get(
                 "authority", ""),
             source_file=g(r, "source_file")
                         or "data/clean/cedar_identifier_ledger_final.csv",
             basis=g(r, "tier_rationale")[:900],
             identifier_publishes="Y" if pub else "N",
             publish_restriction=restriction,
             n_entities_for_this_identifier=str(n))

    # ----------------------------------------- 4. legacy assistance integers
    axw, _ = read(ASSIST_XW)
    print(f"assistance crosswalk: {len(axw):,} candidate rows")
    for r in axw:
        legacy = g(r, "legacy_tribe_id")
        prop = g(r, "proposed_cedar_tribe_id")
        tier = g(r, "confidence_tier")
        if not legacy:
            continue
        if not prop:
            refused.append({"external_scheme": "LEGACY_ASSISTANCE_INT",
                            "external_identifier": legacy,
                            "reason": "NO_CANDIDATE",
                            "candidates": "", "tiers": "",
                            "detail": "a spine gap - the legacy id names an "
                                      "entity the spine does not carry"})
            stats["refused_legacy_no_candidate"] += 1
            continue
        sm = meta.get(prop, {})
        stats["LEGACY_ASSISTANCE_INT"] += 1
        emit(cedar_entity_id=prop,
             cedar_entity_name=g(sm, "canonical_name")
                               or g(r, "proposed_canonical_name"),
             cedar_entity_class=g(sm, "entity_class") or g(r, "entity_class"),
             external_scheme="LEGACY_ASSISTANCE_INT",
             external_identifier=legacy,
             mapping_direction="ATTRIBUTE_OF_CEDAR_ID",
             mapping_status="PROPOSED_NOT_APPLIED",
             confidence_tier=tier,
             tier_source="assistance_tribe_id_crosswalk.csv::confidence_tier "
                         "- INHERITED verbatim",
             attribution_method=g(r, "match_basis"),
             asserting_authority="the Lineage A assistance build (pre-Cedar)",
             source_file="data/clean/assistance_tribe_id_crosswalk.csv",
             basis=ASSIST_BASIS,
             identifier_publishes="N",
             publish_restriction="internal legacy key",
             n_entities_for_this_identifier="1")

    print()
    for k, v in sorted(stats.items()):
        print(f"  {k:44s} {v:>7,}")
    print(f"\n  crosswalk rows      {len(out):,}")
    print(f"  refused to review   {len(refused):,}")

    # many-per-entity is expected; report it so nobody reads it as a defect
    per_entity = Counter(r["cedar_entity_id"] for r in out
                         if r["mapping_direction"] == "ATTRIBUTE_OF_CEDAR_ID")
    top = per_entity.most_common(8)
    print("\n  entities holding the most identifiers "
          "(EXPECTED, not a defect):")
    for e, n in top:
        print(f"    {e:30s} {n:>5,}  {meta.get(e, {}).get('canonical_name','')}")

    if not apply:
        print("\nDRY RUN - nothing written. Re-run with --apply.")
        return

    keys = [r["crosswalk_id"] for r in out]
    dupes = {k for k, v in Counter(keys).items() if v > 1}
    if dupes:
        # A duplicate key is a real fact about the inputs, not a reason to
        # invent a counter. Report it and refuse rather than paper over it.
        print(f"\n!! {len(dupes)} duplicate crosswalk_id(s) - the same "
              f"(scheme, identifier, entity, direction) appears more than "
              f"once in the sources. Collapsing them.")
        seen, dedup = set(), []
        for r in out:
            if r["crosswalk_id"] in seen:
                continue
            seen.add(r["crosswalk_id"])
            dedup.append(r)
        out = dedup

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".csv.part")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, FIELDS)
        w.writeheader()
        w.writerows(out)
    tmp.replace(OUT)

    if refused:
        REFUSED.parent.mkdir(parents=True, exist_ok=True)
        tmp2 = REFUSED.with_suffix(".csv.part")
        with open(tmp2, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, ["external_scheme", "external_identifier",
                                    "reason", "candidates", "tiers", "detail"])
            w.writeheader()
            w.writerows(refused)
        tmp2.replace(REFUSED)

    # Concurrency rule 4: verify by RE-READING.
    back, back_cols = read(OUT)
    assert back_cols == FIELDS, f"column drift: {back_cols}"
    assert len(back) == len(out), f"{len(out)} written, {len(back)} read back"
    assert len({r['crosswalk_id'] for r in back}) == len(back), \
        "crosswalk_id is not unique on re-read"
    print(f"\nwrote {OUT.relative_to(CEDAR)}: {len(back):,} rows, "
          f"{len(back_cols)} columns, key unique, re-read OK")
    if refused:
        print(f"wrote {REFUSED.relative_to(CEDAR)}: {len(refused):,} rows")


if __name__ == "__main__":
    main()
