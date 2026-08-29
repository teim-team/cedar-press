#!/usr/bin/env python3
"""
Cedar Press - 419: codebook fragments for the identity layer.

WHY A FRAGMENT AND NOT `41_build_codebooks.py`
-----------------------------------------------
**41 is on the never-run list.** It writes `codebook_master.csv` in `"w"` mode
and `docs/INDIVIDUAL_NATIVE_OWNERSHIP_VERIFICATION_BUILD_LOG.md` §10 records
that a run today would delete 21 of the 43 blocks the master holds. The
supported route is a FRAGMENT plus `cedar_register_codebook.py` - the pattern
`156_refresh_deals_codebook_fragment.py` set - and `25_build_publication_layer.py`
then picks the table up automatically through `CB.registered_tables()`, so no
edit to `25::TABLES` or `27::SPEC` is needed and neither of those live files is
touched.

WHAT IT REGISTERS
-----------------
1. `00d_cedar_entity_identity_crosswalk` - NEW table, written by
   `code/417_build_entity_identity_crosswalk.py`. Mine, so I describe it.

2. `00e_entity_aliases` - `data/clean/entity_aliases.csv` has existed since
   2026-08-07 with **NO codebook block at all**, so it has never shipped a row.
   It is not a contested measure - it is a name index - and `code/418` enriched
   it and added three columns, so leaving it unregistered would be leaving a
   gate metric worse than it was found. Described here, and the fact that the
   original fifteen columns were authored by `97_build_aliases_and_relationships.py`
   rather than by this pass is stated on the block.

WHAT IT DOES NOT DO
-------------------
It does not describe the spine's six new columns in `05_entities`.
`05_entities` is another build's block and `156`'s rule holds: a fragment is
re-measured by its owner, never rewritten by a neighbour. The six columns are
documented in `docs/CEDAR_ID_SYSTEM.md` and named here so the omission is
deliberate rather than forgotten:
`canonical_entity_id_column`, `cedar_entity_id_scheme`,
`entity_master_register_id`, `entity_master_register_id_basis`,
`constituent_band_of_entity_id`, `constituent_band_of_basis`.

    py -3 code/419_register_identity_layer_codebooks.py           # dry run
    py -3 code/419_register_identity_layer_codebooks.py --apply
"""

import csv
import sys
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
CBDIR = CLEAN / "codebook"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
          "published", "access_tier", "description", "generated"]

# ---------------------------------------------------------------------------
# (variable, type, units, published, access_tier, description)
# ---------------------------------------------------------------------------
XWALK = ("00d_cedar_entity_identity_crosswalk",
         CLEAN / "cedar_entity_identity_crosswalk.csv", [
    ("crosswalk_id", "text", "code", 1, "public",
     "Deterministic surrogate key: a blake2b digest of (external_scheme, "
     "external_identifier, cedar_entity_id, mapping_direction) via "
     "cedar_keys.surrogate_id. Never positional, never hash(), so it is the "
     "same value in every build on every machine."),
    ("cedar_entity_id", "text", "code", 1, "public",
     "THE CANONICAL KEY. One Cedar id per real-world Native entity, permanent "
     "and never reused. Equals cedar_entity_spine.csv::tribe_id - a "
     "grandfathered column name, not a claim that the row is a tribe."),
    ("cedar_entity_name", "text", "text", 1, "public",
     "Cedar's canonical name for that entity, copied from the spine."),
    ("cedar_entity_class", "text", "category", 1, "public",
     "The entity's class. THE AUTHORITY FOR CLASS IS THIS COLUMN, never the "
     "id prefix: ANVC carries both village and group corporations and CDFI "
     "carries both Native CDFIs and Native Financial Institutions, 273 "
     "entities between them."),
    ("external_scheme", "text", "category", 1, "public",
     "Which identifier system the external value belongs to: UEI, CAGE, EIN, "
     "CICD_NEID, ENTITY_MASTER or LEGACY_ASSISTANCE_INT. Declared in "
     "cedar_ids.EXTERNAL_IDENTIFIER_SCHEMES with its assigning authority."),
    ("external_identifier", "text", "code", 1, "public",
     "The external value. An ATTRIBUTE of the Cedar id, never a competing "
     "key. Suppressed in any published extract where identifier_publishes = N."),
    ("mapping_direction", "text", "category", 1, "public",
     "ATTRIBUTE_OF_CEDAR_ID (the identifier belongs to this entity), "
     "ALIAS_OF_CEDAR_ID (another system's id for the same entity), or REFUSED "
     "(a NEGATIVE ruling - this identifier is NOT this entity's, and it must "
     "never be read as an attribution)."),
    ("mapping_status", "text", "category", 1, "public",
     "APPLIED, PROPOSED_NOT_APPLIED, or NEGATIVE_RULING_DO_NOT_ATTRIBUTE. "
     "Every LEGACY_ASSISTANCE_INT row is PROPOSED_NOT_APPLIED: scripts 152 "
     "and 24 decline to apply that crosswalk in writing because 122 of its "
     "344 candidates rest on a containment match, and that refusal is "
     "honoured here."),
    ("confidence_tier", "text", "category", 1, "public",
     "A/B/C/X, INHERITED VERBATIM from the source row and never assigned by "
     "this build. Only A publishes. The exactness of the KEY says nothing "
     "about the correctness of the LINK."),
    ("tier_source", "text", "text", 1, "public",
     "The file and column the tier was copied from. A consumer that copies a "
     "tier owes the source a re-read: an inherited tier is correct only as of "
     "the moment it was copied."),
    ("attribution_method", "text", "category", 1, "public",
     "How the link was made. A RULED method says a HUMAN decided; it NEVER "
     "says the answer was yes. Read confidence_tier for the sign."),
    ("asserting_authority", "text", "text", 1, "public",
     "Who assigns the external identifier - GSA/SAM for a UEI, DLA for a "
     "CAGE, the IRS for an EIN, CICD for an NEID. Never Cedar Press."),
    ("source_file", "text", "path", 1, "public",
     "The file this mapping was read from."),
    ("basis", "text", "text", 1, "public",
     "Why this mapping is asserted, in prose, including any refusal it "
     "honours. A refusal that does not say why gets re-litigated."),
    ("identifier_publishes", "text", "flag", 1, "public",
     "Y/N. N for DUNS at any tier (D&B licensed) and for a UEI or CAGE held "
     "by an Individually Native-owned business - SAM's public search resolves "
     "a UEI to a legal name and street address, so publishing it publishes "
     "the person by one hop."),
    ("publish_restriction", "text", "text", 1, "public",
     "The rule that withholds the value, quoted, or blank where it "
     "publishes."),
    ("n_entities_for_this_identifier", "integer", "count", 1, "public",
     "How many Cedar entities this identifier resolves to. ALWAYS 1 in this "
     "file BY CONSTRUCTION: many identifiers per entity is expected and "
     "normal (a large ANC family holds over a hundred registrations), but one "
     "identifier held by many entities is a DEFECT and is written to "
     "review/identity_crosswalk_refused_*.csv with every candidate named "
     "instead of being resolved by a guess."),
    ("built_by", "text", "path", 0, "internal", "Producing script."),
    ("built_date", "date", "ISO date", 0, "internal",
     "Build date. NOT a vintage and never a source as-of date."),
])

ALIASES = ("00e_entity_aliases", CLEAN / "entity_aliases.csv", [
    ("alias_id", "text", "code", 0, "internal",
     "Cedar-internal alias row id, minted by cedar_ids.allocate under the "
     "CEDAR-ALIAS prefix with a file lock."),
    ("entity_id", "text", "code", 1, "public",
     "The canonical Cedar entity id this name refers to. One entity, many "
     "names; a name never refers to two entities in this file."),
    ("alias_name", "text", "text", 1, "public",
     "The name as it is written by whoever asserted it."),
    ("normalized_alias", "text", "text", 1, "public",
     "Case-folded, whitespace-collapsed match form. Folding is for "
     "punctuation, corporate forms and diacritics ONLY - never for a word "
     "that carries identity. Dropping `indian` once resolved the National "
     "Education Association onto the National Indian Education Association."),
    ("alias_type", "text", "category", 1, "public",
     "One of cedar_domain.ALIAS_TYPES. `legal` and `common` are the entity's "
     "current names; `former_legal` is a name it no longer uses; `acronym` "
     "covers an initialism such as MHA; `full_form_federal_filing` is a "
     "machine-generated permutation and is weak evidence by construction."),
    ("alias_type_normalized", "text", "category", 1, "public",
     "alias_type mapped onto the single declared vocabulary by "
     "cedar_domain.canonical_alias_type. Blank-mapping is impossible: an "
     "unrecognised type surfaces at the write. Added 2026-08-26 by code/418."),
    ("alias_role", "text", "category", 1, "public",
     "current / historical / unknown, from cedar_domain.alias_type_role. A "
     "matcher may PREFER a current name but must still RESOLVE a historical "
     "one - that is what a rename requires, and a rename never mints a new "
     "Cedar id. `unknown` is the honest value for a generated permutation "
     "nobody has confirmed anyone uses. Added 2026-08-26 by code/418."),
    ("alias_layer_basis", "text", "text", 0, "internal",
     "Why the row exists and what its blank date columns mean. Added "
     "2026-08-26 by code/418."),
    ("source_system", "text", "category", 1, "public",
     "Who asserted the name: cedar_spine, federal_register, UEI, CAGE, EIN, "
     "cedar_generated, cedar_brand_registry, elijah_ruling."),
    ("start_date", "date", "ISO date", 1, "public",
     "First date the name is evidenced. BLANK MEANS NOT RECORDED, never that "
     "the name was not in use. Deliberately not backfilled with a build "
     "date."),
    ("end_date", "date", "ISO date", 1, "public",
     "Date the name was superseded, where a source dates it. Written for "
     "former_legal rows from the publication date of the Federal Register "
     "notice carrying the '(previously listed as ...)' parenthetical. Blank "
     "elsewhere and blank means NOT RECORDED."),
    ("first_observed_date", "date", "ISO date", 1, "public",
     "First observation of the name in a source. BLANK MEANS NOT RECORDED."),
    ("last_observed_date", "date", "ISO date", 1, "public",
     "Most recent observation. BLANK MEANS NOT RECORDED."),
    ("verification_status", "text", "category", 1, "public",
     "SPINE_CANONICAL, OFFICIAL (a Federal Register name), RECORDED, RULED "
     "(an owner ruling), REGISTERED (from an identifier registration), "
     "FOLDED, or GENERATED_* for a machine permutation."),
    ("confidence", "number", "0-1", 1, "public",
     "Confidence in the alias, from its asserting source. 0.40 on a generated "
     "municipal look-alike; 0.98-0.99 on an official or spine name."),
    ("tier", "text", "category", 1, "public",
     "A/B/C/X, INHERITED from the asserting source row."),
    ("source_id", "text", "text", 1, "public",
     "The file, column or citation that asserted the name. For a former_legal "
     "row this is the Federal Register citation - e.g. 81 FR 5019 for Tolowa "
     "Dee-ni' Nation, previously the Smith River Rancheria."),
    ("created_at", "date", "ISO date", 0, "internal",
     "When the row was written. A build date, NOT an observation date and "
     "never a vintage."),
])


def build_fragment(dataset, path, spec):
    if not path.exists():
        print(f"  SKIP {dataset}: {path.name} does not exist")
        return None
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        rows = list(rd)
    n = len(rows)
    described = {v[0] for v in spec}
    missing = [c for c in cols if c not in described]
    extra = [v[0] for v in spec if v[0] not in cols]
    if missing:
        # A variable in the file with no description is exactly the gap this
        # script exists to close. Refuse rather than ship a partial block.
        raise SystemExit(
            f"FATAL: {path.name} has {len(missing)} column(s) with no "
            f"description: {missing}. A codebook that silently omits a column "
            f"certifies the omission.")
    if extra:
        print(f"  NOTE {dataset}: described but absent from the file: {extra}")
    out = []
    for var, typ, units, pub, tier, desc in spec:
        if var not in cols:
            continue
        filled = sum(1 for r in rows if (r.get(var) or "").strip())
        out.append({
            "dataset": dataset, "variable": var, "type": typ, "units": units,
            "pct_filled": f"{100.0 * filled / n:.1f}" if n else "",
            "n_rows": n, "published": pub, "access_tier": tier,
            "description": desc, "generated": TODAY,
        })
    print(f"  {dataset:42s} {len(out):>3} variables, {n:>7,} rows")
    return out


def main():
    apply = "--apply" in sys.argv
    print("=== 419: identity-layer codebook fragments ===\n")
    made = {}
    for dataset, path, spec in (XWALK, ALIASES):
        frag = build_fragment(dataset, path, spec)
        if frag:
            made[dataset] = frag

    if not apply:
        print("\nDRY RUN - nothing written. Re-run with --apply.")
        return

    CBDIR.mkdir(parents=True, exist_ok=True)
    for dataset, rows in made.items():
        p = CBDIR / f"{dataset}.csv"
        if p.exists():
            bak = p.with_name(p.name + f".bak_{TODAY}_pre_419_register_"
                                        f"identity_layer_codebooks")
            if not bak.exists():
                bak.write_bytes(p.read_bytes())
        tmp = p.with_suffix(".csv.part")
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, FIELDS)
            w.writeheader()
            w.writerows(rows)
        tmp.replace(p)
        # Concurrency rule 4: re-read.
        with open(p, encoding="utf-8-sig", newline="") as fh:
            back = list(csv.DictReader(fh))
        assert len(back) == len(rows)
        print(f"  wrote {p.relative_to(CEDAR)}  ({len(back)} variables, "
              f"re-read OK)")

    print("\nNEXT, in this order (docs/SHIPPING_RUNBOOK.md):")
    print("  py -3 code/cedar_codebook.py build   # fold fragments -> master")
    print("  py -3 code/87_build_dataset_notes.py")
    print("  py -3 code/25_build_publication_layer.py")
    print("  py -3 code/27_build_dataset_manifests.py")
    print("  NEVER 41_build_codebooks.py - it rebuilds the master in 'w' mode")


if __name__ == "__main__":
    main()
