#!/usr/bin/env python3
# lint-ok: class6 - THE ORDERING IS WRITTEN DOWN, BY A PERSON, IN THE ENRICHER.
# This script FULL-REBUILDS entity_aliases.csv and
# 418_build_entity_alias_layer.py ENRICHES it in place; the enricher runs LAST.
# 418's docstring carries the canonical statement under "ORDERING - CLASS 6,
# DECLARED BECAUSE THE DETECTOR CANNOT INFER IT", and it backs up to
# `.bak_<date>_pre_418_build_entity_alias_layer` (the signal that it has
# touched the file) and writes `.part`-then-rename.
# RE-RUN 418 AFTER ANY RUN OF THIS SCRIPT, or 97 reverts every row and column
# 418 added - the same collision that reverted 168's 931 FERC entity links four
# minutes after they were written, while printing a larger row count that read
# as progress.
"""
Cedar Press - 97: alias table and typed relationships. SPEC v2, 5.3 and 5.4.

WHAT THIS REPLACES
------------------
`entity_hierarchy.csv` is a FLAT file: one row per entity, with
`parent_entity_id`, `ultimate_parent_entity_id` and `ancsa_region_entity_id`
sitting beside each other as though they were the same kind of fact. They are
not. A parent is an owner; an ANCSA region is a PLACE. Putting them in adjacent
columns is what let a region be read as a parent, and reading a region as a
parent is the same class of error that booked $27.59B onto the wrong legal
persons (spec 6.2). This script turns each column into a TYPED edge whose type
answers, by itself, whether a dollar may travel along it -
`cedar_domain.bears_ownership()`.

The alias table exists for the mirror-image reason. The spine stores SHORT
names ("Sleetmute"); federal systems file LONG ones ("Village of Sleetmute").
Neither is wrong and neither can be matched to the other by normalisation, so
the variants have to be stored. Two measured failures drive the two generated
alias families here:

  * `full_form_federal_filing` - "Village of Sleetmute" failed to match spine
    "Sleetmute" because the long form existed nowhere in Cedar.
  * `diacritic_folded` - a normaliser that turned a diacritic into a SPACE gave
    "ukpea vik" for `Ukpeaġvik` and cost 8 Hawaiian organisations their EINs.
    The fold here never inserts a space; it is `33_apply_party_rulings.norm`,
    imported, not re-implemented (regression rule 8).

WHAT THIS SCRIPT REFUSES TO DO
------------------------------
  * It never mints an ID inline. Every `alias_id` and `relationship_id` comes
    from `cedar_ids.allocate` (spec 13.2).
  * It never invents an entity. A TDHE, a brand family and a tribally owned
    firm are all real, and none of them is on the spine; each is recorded by
    NAME with a null id rather than resolved onto the nearest tribe. Resolving
    them onto the nearest tribe is exactly the containment defect (AGENTS.md).
  * It never promotes an association to an ownership. `associated_with_region`
    is asserted non-ownership-bearing before a single row is written.
  * It never writes a generic `related_to`. Every type is checked against
    `cedar_domain.ALL_RELATIONSHIPS`.

Reads   data/spine/cedar_entity_spine.csv                    (never written)
        data/clean/entity_hierarchy.csv                      (never written)
        data/clean/brand_family_registry.csv                 (never written)
        data/clean/cedar_identifier_ledger_final.csv         (never written)
        data/clean/admin_region_assignments.csv              (never written)
        data/clean/prime_contracts.csv                       (never written)
        review/village_corp_namesake_pairs.csv               (never written)

Writes  data/clean/entity_aliases.csv
        data/clean/entity_relationships.csv
        data/clean/codebook_master.csv        (its own rows only, refreshed)
        review/relationship_migration_issues_<date>.csv
        data/interim/_place_names.json        (cache)
"""

import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
INTERIM = CEDAR / "data" / "interim"
REVIEW = CEDAR / "review"

sys.path.insert(0, str(CODE))
import cedar_domain as D          # noqa: E402
import cedar_ids                  # noqa: E402


def _load_numbered(stem):
    """Numbered modules are not importable by name; load them by path so the
    ONE resolver is imported rather than re-implemented (regression rule 8)."""
    spec = importlib.util.spec_from_file_location(
        "m_" + stem.split("_")[0], CODE / f"{stem}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M33 = _load_numbered("33_apply_party_rulings")
norm = M33.norm            # the diacritic fold that does NOT insert a space
core = M33.core
CB41 = _load_numbered("41_build_codebooks")

TODAY = date.today().isoformat()
SCRIPT = "97_build_aliases_and_relationships.py"

ALIAS_FIELDS = [
    "alias_id", "entity_id", "alias_name", "normalized_alias", "alias_type",
    "source_system", "start_date", "end_date", "first_observed_date",
    "last_observed_date", "verification_status", "confidence", "tier",
    "source_id", "created_at",
]
REL_FIELDS = [
    "relationship_id", "source_entity_id", "relationship_type",
    "target_entity_id", "start_date", "end_date", "is_current",
    "legal_or_informal", "direct_or_inferred", "verification_status",
    "confidence", "tier", "source_id", "evidence_text", "notes", "created_at",
]

# ONE map from an INHERITED ledger tier to the confidence this file writes.
# It was already inline at the alias site; the ownership-edge site hardcoded
# 0.90 next to a hardcoded tier A, so a demoted source row would have shipped a
# tier-B edge claiming tier-A confidence - the same over-statement in a second
# column. Declared once so the two sites cannot drift.
LEDGER_TIER_CONFIDENCE = {"A": 0.90, "B": 0.60, "C": 0.40}
#: Strongest first. Used only to break a dedupe tie deterministically; it never
#: creates a tier, it picks among tiers the ledger already states.
LEDGER_TIER_RANK = {"A": 0, "B": 1, "C": 2}

# Government classes get the federal LONG-form treatment. A corporation does
# not: "Village of Afognak Native Corporation" is not a name anyone files.
VILLAGE_GOV_CLASSES = {"Federally recognized Alaska Native Village"}
TRIBE_CLASSES = {
    "Federally recognized tribe", "State-recognized tribe",
    "Federal-level constituency entity", "State-level constituency entity",
}

# A canonical name ending in one of these already carries its governmental
# unit; appending another produces a name no source files.
GOV_UNIT_WORDS = {
    "tribe", "tribes", "nation", "nations", "band", "bands", "community",
    "communities", "pueblo", "rancheria", "colony", "village", "villages",
    "council", "reservation", "indians", "town", "corporation",
}

# Not a domain enum - a formatting utility for the "X Tribe of <state>" form,
# which federal filings spell out ("...Tribe of Indians of Oklahoma").
STATE_NAMES = {
    "AK": "Alaska", "AL": "Alabama", "AR": "Arkansas", "AZ": "Arizona",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut",
    "DC": "District of Columbia", "DE": "Delaware", "FL": "Florida",
    "GA": "Georgia", "HI": "Hawaii", "IA": "Iowa", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "KS": "Kansas", "KY": "Kentucky",
    "LA": "Louisiana", "MA": "Massachusetts", "MD": "Maryland", "ME": "Maine",
    "MI": "Michigan", "MN": "Minnesota", "MO": "Missouri", "MS": "Mississippi",
    "MT": "Montana", "NC": "North Carolina", "ND": "North Dakota",
    "NE": "Nebraska", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NV": "Nevada", "NY": "New York", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VA": "Virginia",
    "VT": "Vermont", "WA": "Washington", "WI": "Wisconsin",
    "WV": "West Virginia", "WY": "Wyoming",
}


# ---------------------------------------------------------------------------
# io
# ---------------------------------------------------------------------------


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        bak = p.with_suffix(p.suffix + f".bak_{TODAY}_pre97")
        if not bak.exists():
            bak.write_bytes(p.read_bytes())
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


# ---------------------------------------------------------------------------
# the ASCII fold that federal systems actually file
# ---------------------------------------------------------------------------

# `norm` folds for COMPARISON (lowercase, no punctuation). A federal filing
# keeps case and spacing but loses the marks, so a readable fold is stored as
# its own alias. Two forms are produced where they differ, because the IRS
# dropped the okina entirely ("Hui O Kuapa") while other systems keep an
# ASCII apostrophe ("Tohono O'odham").
_OKINA = "\u02bb\u02bc\u2018\u2019\u0060\u00b4"
_DASHES = "\u2013\u2014\u2012\u2015"
_EXPLICIT = {"\u0142": "l", "\u0141": "L", "\u00f8": "o", "\u00d8": "O",
             "\u0111": "d", "\u0110": "D", "\u00e6": "ae", "\u00c6": "AE",
             "\u0153": "oe", "\u0152": "OE", "\u014b": "ng", "\u00df": "ss"}


def ascii_fold(s, keep_apostrophe=True):
    """NFKD, drop combining marks, map what does not decompose. NEVER inserts
    a space - that bug produced "ukpea vik" and is the reason this exists."""
    import unicodedata
    out = []
    for ch in unicodedata.normalize("NFKD", s or ""):
        if unicodedata.combining(ch):
            continue
        if ch in _OKINA:
            out.append("'" if keep_apostrophe else "")
            continue
        if ch in _DASHES:
            out.append("-")
            continue
        out.append(_EXPLICIT.get(ch, ch))
    return " ".join("".join(out).split())


def is_ascii(s):
    return all(ord(c) < 128 for c in s or "")


def has_diacritic(s):
    """True where a mark carries linguistic weight - a combining accent, an
    okina, or a letter that NFKD leaves alone (l-with-stroke). False for a
    name whose only non-ASCII character is a typographic dash."""
    import unicodedata
    for ch in unicodedata.normalize("NFKD", s or ""):
        if unicodedata.combining(ch) or ch in _OKINA or ch in _EXPLICIT:
            return True
    return False


# ---------------------------------------------------------------------------
# municipality look-alike guard
# ---------------------------------------------------------------------------


def place_names():
    """City/town names observed in federal award data, per state.

    A generated "Village of X" can land on a municipality of the same name -
    "Village of Eagle", "Village of Wells". No gazetteer is fetched (see
    docs/PULL_DISCIPLINE.md); the local prime-contract file already carries a
    national recipient-city and place-of-performance list, which is a proxy
    and is labelled as one. Cached because the file is 240 MB.
    """
    cache = INTERIM / "_place_names.json"
    if cache.exists():
        return {k: set(v) for k, v in
                json.loads(cache.read_text(encoding="utf-8")).items()}
    print("  building place-name cache from prime_contracts.csv "
          "(one pass, cached afterwards)...")
    places = defaultdict(set)
    src = CLEAN / "prime_contracts.csv"
    if src.exists():
        with open(src, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                for c, st in ((r.get("recipient_city_name"),
                               r.get("recipient_state_code")),
                              (r.get("place_of_perform_city"),
                               r.get("place_of_perform_state"))):
                    c = norm(c)
                    st = (st or "").strip().upper()
                    if c and st and len(st) == 2:
                        places[c].add(st)
    for r in read_csv(SPINE / "cedar_entity_spine.csv"):
        c, st = norm(r.get("city")), (r.get("state") or "").strip().upper()
        if c and len(st) == 2:
            places[c].add(st)
    INTERIM.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({k: sorted(v) for k, v in places.items()}),
                     encoding="utf-8")
    return {k: set(v) for k, v in places.items()}


def municipal_collision(base, entity_state, places):
    """Why a generated variant must not auto-link.

    Two ways it goes wrong: the identifying word is a known name trap
    (`cedar_domain.NAME_TRAPS`, every entry of which cost a real
    misattribution), or the name is a municipality somewhere other than the
    entity's own state - the cross-state failure that put an Albuquerque
    cultural centre onto a Hawaii learning centre.
    """
    n = norm(base)
    toks = [t for t in n.split() if t]
    if any(t in D.NAME_TRAPS for t in toks):
        return "name_trap:" + ",".join(t for t in toks if t in D.NAME_TRAPS)
    states = places.get(n, set())
    st = (entity_state or "").strip().upper()
    elsewhere = states - {st}
    if len(states) >= 2:
        return f"municipality_in_{len(states)}_states"
    if elsewhere:
        return "municipality_in_" + ",".join(sorted(elsewhere))
    return ""


# ---------------------------------------------------------------------------
# TASK A - aliases
# ---------------------------------------------------------------------------


def build_aliases(spine, brands, ledger, places, issues):
    rows = []
    seen = set()          # (entity_id, normalized_alias)
    seen_exact = set()    # (entity_id, alias_name.lower())

    def add(entity_id, name, atype, source_system, source_id, tier,
            confidence, verification, note_first="", exact_dedupe=False):
        name = " ".join((name or "").split())
        if not name:
            return False
        assert atype in D.ALIAS_TYPES, f"unknown alias_type {atype!r}"
        # A folded form normalises IDENTICALLY to the accented form - that is
        # what a correct fold does. Deduping it on the normalised key would
        # therefore delete every diacritic_folded row, so those dedupe on the
        # literal string: the ASCII spelling is what a source actually files.
        if not norm(name):
            return False
        if exact_dedupe:
            if (entity_id, name.lower()) in seen_exact:
                return False
        elif (entity_id, norm(name)) in seen:
            return False
        seen.add((entity_id, norm(name)))
        seen_exact.add((entity_id, name.lower()))
        rows.append({
            "alias_id": "", "entity_id": entity_id, "alias_name": name,
            "normalized_alias": norm(name), "alias_type": atype,
            "source_system": source_system, "start_date": "", "end_date": "",
            "first_observed_date": note_first, "last_observed_date": "",
            "verification_status": verification,
            "confidence": f"{confidence:.2f}", "tier": tier,
            "source_id": source_id, "created_at": TODAY,
        })
        return True

    # -- 1. the spine's own canonical name and `aliases` column --------------
    for r in spine:
        eid, cname = r["tribe_id"], r["canonical_name"]
        add(eid, cname, "common", "cedar_spine", "cedar_entity_spine.csv",
            D.Tier.A.value, 0.99, "SPINE_CANONICAL")
        fr = (r.get("fr_official_name") or "").strip()
        if fr:
            add(eid, fr, "legal", "federal_register",
                "cedar_entity_spine.csv:fr_official_name",
                D.Tier.A.value, 0.98, "OFFICIAL")
        for a in (r.get("aliases") or "").split("|"):
            a = a.strip()
            if not a:
                continue
            if norm(a) == norm(fr):
                continue                       # already stored as `legal`
            atype = "common"
            if a.isupper() and len(a) <= 8:
                atype = "acronym"              # script 51's ANC acronyms
            elif len(core(a)) < len(core(cname)):
                atype = "shortened"
            add(eid, a, atype, "cedar_spine", "cedar_entity_spine.csv:aliases",
                D.Tier.A.value, 0.90, "RECORDED")

    # -- 2. brand families: 106, learned from Elijah's rulings ---------------
    brand_alias_id = {}
    for b in brands:
        eid = (b.get("tribe_id") or "").strip()
        if not eid:
            continue
        ok = add(eid, b["brand"], "brand", "cedar_brand_registry",
                 "brand_family_registry.csv", D.Tier.A.value, 0.95, "RULED")
        brand_alias_id[(eid, norm(b["brand"]))] = ok

    # -- 3. the identifier ledger's legal_business_name ----------------------
    # A registered legal name is an ALIAS only when it is a name of the SAME
    # legal person. "Petro Star, Inc." under Arctic Slope Regional Corporation
    # is a SUBSIDIARY - calling it an alias would merge a company into its
    # owner. Variants become aliases here; distinct firms become `owned_by`
    # edges in Task B. This split is a deviation from a literal reading of the
    # instruction and is reported.
    by_id = {r["tribe_id"]: r for r in spine}
    ledger_firms, n_lbn_variant = [], 0
    for r in ledger:
        if r.get("confidence_tier") == D.Tier.X.value:
            continue                          # Tier X never resurfaces
        eid = (r.get("tribe_id") or "").strip()
        lbn = " ".join((r.get("legal_business_name") or "").split())
        if not eid or not lbn or eid not in by_id:
            continue
        ent = by_id[eid]
        alias_norms = {norm(a) for a in (ent.get("aliases") or "").split("|")}
        alias_norms.add(norm(ent["canonical_name"]))
        alias_norms.add(norm(ent.get("fr_official_name") or ""))
        variant = (norm(lbn) in alias_norms
                   or (core(lbn) and core(lbn) == core(ent["canonical_name"])))
        if variant:
            if add(eid, lbn, "legal", r.get("identifier_type") or "ledger",
                   "cedar_identifier_ledger_final.csv",
                   r.get("confidence_tier") or D.Tier.C.value,
                   LEDGER_TIER_CONFIDENCE.get(
                       r.get("confidence_tier"), 0.40),
                   "REGISTERED"):
                n_lbn_variant += 1
        else:
            ledger_firms.append(r)

    # -- 4. generated full-form federal filing variants ----------------------
    n_generated, n_guarded = 0, 0
    for r in spine:
        eid, cname = r["tribe_id"], r["canonical_name"]
        cls, st = r["entity_class"], (r.get("state") or "").strip().upper()
        toks = set(norm(cname).split())
        # A canonical name that already ENDS in a governmental-unit word must
        # not have a second one bolted on: "Accohannock Indian Tribe" + Nation
        # is not a name anybody files, and a bad alias is worse than none.
        tail = (norm(cname).split() or [""])[-1]
        if tail in GOV_UNIT_WORDS:
            continue
        names_blob = norm(" ".join([cname, r.get("aliases") or "",
                                    r.get("fr_official_name") or ""]))
        variants = []
        if cls in VILLAGE_GOV_CLASSES:
            if "village" not in toks:
                variants += [f"Native Village of {cname}",
                             f"Village of {cname}"]
            if "tribe" not in toks and "tribes" not in toks:
                variants.append(f"{cname} Tribe")
        elif cls in TRIBE_CLASSES:
            if "tribe" not in toks and "tribes" not in toks:
                variants.append(f"{cname} Tribe")
                if st in STATE_NAMES:
                    variants.append(f"{cname} Tribe of {STATE_NAMES[st]}")
            if "indian" not in toks and "tribe" not in toks:
                variants.append(f"{cname} Indian Tribe")
            if "nation" not in toks and "nations" not in toks:
                variants.append(f"{cname} Nation")
            # Only where the entity's OWN official names already say
            # "Confederated". Generating it for every tribe would invent
            # "Confederated Tribes of Chickasaw", which is not a name.
            if "confederated" in names_blob.split() \
                    and "confederated" not in toks:
                variants.append(f"Confederated Tribes of {cname}")
        for v in variants:
            hit = municipal_collision(cname, st, places)
            tier = D.Tier.B.value
            conf = 0.40 if hit else 0.60
            ok = add(eid, v, "full_form_federal_filing", "cedar_generated",
                     f"{SCRIPT}:generated", tier, conf,
                     "GENERATED_UNCONFIRMED" if not hit
                     else "GENERATED_MUNICIPAL_LOOKALIKE")
            if ok:
                n_generated += 1
                if hit:
                    n_guarded += 1
                    issues.append({
                        "issue_type": "generated_alias_municipal_lookalike",
                        "entity_id": eid, "name": v, "detail": hit,
                        "resolution": "confidence 0.40, tier B - cannot "
                                      "auto-link", "needs_ruling": "0"})

    # -- 5. diacritic-folded forms ------------------------------------------
    # An en dash folded to a hyphen is a PUNCTUATION fold, not a diacritic one,
    # and is typed `source_specific` so the diacritic_folded count means what
    # it says: names carrying Inupiaq, Hawaiian, Navajo or Tohono O'odham
    # orthography, which is where the money was actually lost.
    n_folded = n_punct = 0
    for r in spine:
        eid = r["tribe_id"]
        sources = [r["canonical_name"], r.get("fr_official_name") or ""]
        sources += [a.strip() for a in (r.get("aliases") or "").split("|")]
        for s in sources:
            if not s or is_ascii(s):
                continue
            atype = "source_specific" if not has_diacritic(s) \
                else "diacritic_folded"
            for keep in (True, False):
                f = ascii_fold(s, keep_apostrophe=keep)
                if not f or f == s:
                    continue
                if add(eid, f, atype, "cedar_generated",
                       f"{SCRIPT}:ascii_fold", D.Tier.A.value, 0.92,
                       "FOLDED", exact_dedupe=True):
                    if atype == "diacritic_folded":
                        n_folded += 1
                    else:
                        n_punct += 1

    ids = cedar_ids.allocate("CEDAR-ALIAS", len(rows),
                             note=f"{SCRIPT} {TODAY}")
    for row, aid in zip(rows, ids):
        row["alias_id"] = aid
    return rows, ledger_firms, {
        "ledger_name_variants": n_lbn_variant,
        "generated": n_generated, "generated_guarded": n_guarded,
        "diacritic_folded": n_folded, "punctuation_folded": n_punct,
    }


# ---------------------------------------------------------------------------
# TASK B - typed relationships
# ---------------------------------------------------------------------------


def build_relationships(spine, hier, brands, ledger_firms, namesake,
                        tdhe_rows, alias_rows, issues):
    rows = []

    def add(src, rtype, tgt, **kw):
        assert rtype in D.ALL_RELATIONSHIPS, \
            f"{rtype!r} is not in cedar_domain.ALL_RELATIONSHIPS"
        rows.append({
            "relationship_id": "", "source_entity_id": src or "",
            "relationship_type": rtype, "target_entity_id": tgt or "",
            "start_date": kw.get("start_date", ""),
            "end_date": kw.get("end_date", ""),
            "is_current": kw.get("is_current", "1"),
            "legal_or_informal": kw.get("legal_or_informal", "legal"),
            "direct_or_inferred": kw.get("direct_or_inferred", "direct"),
            "verification_status": kw.get("verification_status", "RECORDED"),
            "confidence": f"{kw.get('confidence', 0.6):.2f}",
            "tier": kw.get("tier", D.Tier.B.value),
            "source_id": kw.get("source_id", ""),
            "evidence_text": kw.get("evidence_text", ""),
            "notes": kw.get("notes", ""), "created_at": TODAY,
        })

    by_id = {r["tribe_id"]: r for r in spine}
    cls = {r["tribe_id"]: r["entity_class"] for r in spine}

    # -- 1. parent_entity_id -------------------------------------------------
    # The instruction maps parent -> subsidiary_of. Applied literally it would
    # declare 22 constituent BANDS to be corporate subsidiaries of their
    # umbrella tribe, and `subsidiary_of` is ownership-bearing - Bois Forte's
    # contracts would roll up to the Minnesota Chippewa. A band is a
    # government, not a subsidiary. Typed by class; reported as a deviation.
    src_rows = {r["tribe_id"]: ("entity_hierarchy.csv", r) for r in hier}
    for r in spine:                       # the 358 rows the flat file predates
        if r["tribe_id"] not in src_rows:
            src_rows[r["tribe_id"]] = ("cedar_entity_spine.csv", r)
    n_parent = Counter()
    for eid, (src_file, r) in sorted(src_rows.items()):
        pid = (r.get("parent_entity_id") or "").strip()
        if not pid or pid == eid:
            continue
        c = cls.get(eid, "")
        basis = (by_id.get(eid, {}).get("ownership_basis") or "")
        inferred = "containment" in basis
        if c in ("Federal-level constituency entity",
                 "State-level constituency entity"):
            rtype, note = "constituent_band_of", (
                "Governmental constituency, NOT corporate subsidiarity. The "
                "flat file put this in the same column as corporate parents; "
                "typing it subsidiary_of would roll this band's dollars up to "
                "its umbrella tribe.")
            tier, conf = D.Tier.A.value, 0.95
        elif c in ("Tribal College or University",
                   "Native Community Development Financial Institution",
                   "Native Financial Institution"):
            rtype, note = "chartered_by", (
                "Charter, not ownership. `chartered_by` bears no roll-up "
                f"dollar. ownership_basis: {basis or 'not recorded'}")
            tier = D.Tier.B.value if inferred else D.Tier.A.value
            conf = 0.55 if inferred else 0.85
        else:
            rtype, note = "subsidiary_of", "migrated from parent_entity_id"
            tier, conf = D.Tier.B.value, 0.55
        n_parent[rtype] += 1
        add(eid, rtype, pid, source_id=src_file, tier=tier, confidence=conf,
            direct_or_inferred="inferred" if inferred else "direct",
            verification_status="MIGRATED", notes=note,
            evidence_text=(r.get("hierarchy_basis") or "").strip())

    # -- 2. ultimate_parent_entity_id ---------------------------------------
    # Emitted only where it names something the parent edge does not. On this
    # data it never does - see the log.
    n_ultimate = 0
    for eid, (src_file, r) in sorted(src_rows.items()):
        uid = (r.get("ultimate_parent_entity_id") or "").strip()
        pid = (r.get("parent_entity_id") or "").strip()
        if not uid or uid == eid or uid == pid:
            continue
        add(eid, "owned_by", uid, source_id=src_file, tier=D.Tier.B.value,
            confidence=0.55, verification_status="MIGRATED",
            notes="migrated from ultimate_parent_entity_id; no intermediate "
                  "holding layer is invented between the two")
        n_ultimate += 1

    # -- 3. ancsa_region_entity_id -> associated_with_region -----------------
    # THE correction this migration exists for. Asserted, not asserted-later.
    assert D.bears_ownership("associated_with_region") is False, \
        "associated_with_region must never bear ownership"
    n_region = 0
    for eid, (src_file, r) in sorted(src_rows.items()):
        rid = (r.get("ancsa_region_entity_id") or "").strip()
        if not rid or rid == eid:
            continue
        add(eid, "associated_with_region", rid, source_id=src_file,
            tier=D.Tier.A.value, confidence=0.95,
            verification_status="STATUTORY",
            evidence_text=(r.get("hierarchy_basis") or "").strip(),
            notes="ANCSA region is a PLACE, not an owner. The flat file put "
                  "this column beside parent_entity_id; that adjacency is the "
                  "structural error this migration corrects. No dollar "
                  "travels along this edge (cedar_domain.bears_ownership).")
        n_region += 1

    # -- 4. brand families -> brand_of, Tier A ------------------------------
    alias_by_key = {}
    for a in alias_rows:            # any type: a brand may already be on file
        alias_by_key.setdefault((a["entity_id"], a["normalized_alias"]),
                                a["alias_id"])
    n_brand = 0
    for b in brands:
        eid = (b.get("tribe_id") or "").strip()
        if not eid:
            continue
        aid = alias_by_key.get((eid, norm(b["brand"])), "")
        add("", "brand_of", eid, source_id="brand_family_registry.csv",
            tier=D.Tier.A.value, confidence=0.95,
            legal_or_informal="informal", verification_status="RULED",
            evidence_text=f"{b.get('learned_from', '')}; "
                          f"{b.get('n_confirmed_firms', '')} confirmed firms: "
                          f"{b.get('example_firms', '')}",
            notes=f"brand family '{b['brand']}' has no spine entity - a brand "
                  f"is a name family, not a legal person. Identified by "
                  f"alias_id {aid or 'unassigned'}.")
        n_brand += 1

    # -- 5. direct tribe -> company ownership (Chickasaw Nation Industries) --
    # Owned by the tribe, full stop. No intermediate holding layer is invented,
    # because AGENTS.md is explicit that below the top level only the tribe can
    # verify the structure. Ruled/Tier-A ledger attributions only.
    # THE TIER IS INHERITED FROM THE SOURCE ROW. Fixed 2026-08-26.
    #
    # This loop used to admit a row on `tier != A and not ruled: continue` -
    # i.e. METHOD MEMBERSHIP ALONE was enough - and then mint the edge at
    # `tier=D.Tier.A.value` regardless of what the source row actually said.
    # That is the consumer assigning a tier, and `owned_by` is in
    # `D.OWNERSHIP_BEARING`, so the edge can carry money.
    #
    # It is NOT the negative-ruling bug: `ledger_firms` drops
    # `confidence_tier == X` above, so no exclusion can reach here. It is the
    # OTHER half of the same rule - `attribution_method` says WHO decided,
    # `confidence_tier` says WHAT was decided, and a human deciding "B" is
    # still a B.
    #
    # Measured exposure on cedar_identifier_ledger_final.csv, 2026-08-26:
    # **36 rows** - 34 tier-B `elijah_ruling_redirect`, 2 tier-C
    # `web_verified` (Kijik, Paskenta, Paug-Vik, Sitnasuak, Tlingit & Haida).
    # The ENTITY is right on all 36; only the TIER was over-stated. Five of
    # the 36 were already live in entity_relationships.csv and were corrected
    # in place by `code/310_correct_overstated_owned_by_edge_tiers.py`; the
    # other 31 are ledger rows added since this build last ran, and this fix
    # is what stops the next run minting them at A.
    #
    # STRONGEST TIER FIRST. The dedupe key is (entity, normalised legal name)
    # and several ledger rows can share it - CAGE 3BVB7 carries both a tier-B
    # `elijah_ruling_redirect` and a tier-A `bgov_manual` row for Executive
    # Protection Systems LLC. Taking whichever happened to come first in file
    # order would make the edge's tier depend on ledger ROW ORDER, which is
    # the non-deterministic-key defect wearing a different hat. Sorting picks
    # the strongest tier the ledger actually carries for that firm, which is
    # still INHERITING - it never invents a tier no source row states.
    n_owned, seen_firm = 0, set()
    n_owned_by_tier = Counter()
    for r in sorted(ledger_firms,
                    key=lambda x: LEDGER_TIER_RANK.get(
                        (x.get("confidence_tier") or "").strip(), 99)):
        tier = (r.get("confidence_tier") or "").strip()
        ruled = D.is_ruling(r.get("attribution_method"))
        if tier != D.Tier.A.value and not ruled:
            continue
        if tier not in LEDGER_TIER_CONFIDENCE:
            continue          # no tier on the source row = nothing to inherit
        eid, lbn = r["tribe_id"], " ".join(r["legal_business_name"].split())
        key = (eid, norm(lbn))
        if key in seen_firm:
            continue
        seen_firm.add(key)
        add("", "owned_by", eid,
            source_id="cedar_identifier_ledger_final.csv",
            tier=tier, confidence=LEDGER_TIER_CONFIDENCE[tier],
            verification_status=("RULED" if ruled else "TIER_" + tier),
            evidence_text=(r.get("tier_rationale") or "").strip(),
            notes=f"firm '{lbn}' ({r.get('identifier_type')} "
                  f"{r.get('identifier')}) is owned by this Native entity "
                  f"directly. No spine entity for the firm and no intermediate "
                  f"holding layer invented. Tier {tier} INHERITED verbatim "
                  f"from the ledger row (method "
                  f"{(r.get('attribution_method') or '?').strip()}); a ruled "
                  f"METHOD is not a tier-A OUTCOME.")
        n_owned += 1
        n_owned_by_tier[tier] += 1

    # -- 6. village corporation <-> namesake village government -------------
    # 77 pairs, $27.59B booked wrong on the confusion. The typed edge states
    # the relation WITHOUT stating ownership in either direction.
    n_pair = 0
    for p in namesake:
        add(p["corporation_tribe_id"], "village_corporation_for",
            p["government_tribe_id"],
            source_id="village_corp_namesake_pairs.csv",
            tier=D.Tier.A.value, confidence=0.95,
            verification_status="RULED",
            evidence_text=p.get("warning", ""),
            notes="Separate legal persons. NEITHER is the parent of the "
                  "other; `village_corporation_for` bears no ownership.")
        n_pair += 1

    # -- 7. federally operated BIE schools ----------------------------------
    # Native-serving is not tribally owned. Their blank parent is a ruling.
    n_bie = 0
    for r in spine:
        if r.get("bie_operation_type") != "bie_operated":
            continue
        add(r["tribe_id"], "operated_by", "",
            source_id="cedar_entity_spine.csv:bie_operation_type",
            tier=D.Tier.A.value, confidence=0.95,
            verification_status="RULED",
            evidence_text=(r.get("entity_source_quote") or "").strip(),
            notes="Operated by the United States (Dept of the Interior, "
                  "Bureau of Indian Education). No Cedar spine entity exists "
                  "for the federal government, so target_entity_id is null. "
                  "ultimate_native_owner stays NULL: the school may serve a "
                  "tribe's children and sit on its land, and it is still not "
                  "tribally owned. Do not roll up (AGENTS.md).")
        n_bie += 1

    # -- 8. TDHEs -----------------------------------------------------------
    # 148 of them, every one of which previously "resolved" onto its own tribe.
    n_tdhe = 0
    for t in tdhe_rows:
        tribe_name = (t.get("related_subject_name") or "").strip()
        tid, tname, how = M33.resolve_entity(tribe_name, spine) \
            if tribe_name else (None, None, "no_name")
        add(tid or "", "affiliated_with", "",
            source_id="admin_region_assignments.csv",
            tier=D.Tier.B.value, confidence=0.45,
            verification_status="OFFICIAL_UNLINKED",
            evidence_text=t.get("source_url", ""),
            notes=f"TDHE published name: '{t['subject_name']}'. HUD ONAP "
                  f"prints it beneath '{tribe_name}'. The TDHE has NO spine "
                  f"entity and takes no entity id: every one of the 148 "
                  f"'resolved' onto its own tribe by containment, which "
                  f"asserts the grantee and the government are one legal "
                  f"person. Precise semantic is <TDHE> authority_of <tribe>; "
                  f"the 51-type vocabulary has no reciprocal of authority_of, "
                  f"so the tribe-side edge is recorded as affiliated_with "
                  f"(non-ownership) pending a spine entity. "
                  f"tribe resolution: {how}")
        n_tdhe += 1
        issues.append({
            "issue_type": "tdhe_no_spine_entity",
            "entity_id": tid or "", "name": t["subject_name"],
            "detail": f"HUD ONAP lists this TDHE beneath '{tribe_name}' "
                      f"(resolution: {how})",
            "resolution": "recorded by name only, no target_entity_id",
            "needs_ruling": "1"})

    ids = cedar_ids.allocate("CEDAR-REL", len(rows), note=f"{SCRIPT} {TODAY}")
    for row, rid in zip(rows, ids):
        row["relationship_id"] = rid
    return rows, {
        "parent": dict(n_parent), "ultimate": n_ultimate, "region": n_region,
        "brand": n_brand, "owned": n_owned, "namesake": n_pair,
        # The tier breakdown is reported, not just the total. A single "owned"
        # count is exactly what let 100% of these ship at tier A unnoticed.
        "owned_by_inherited_tier": dict(sorted(n_owned_by_tier.items())),
        "bie": n_bie, "tdhe": n_tdhe,
    }


# ---------------------------------------------------------------------------
# the verification that makes this worth doing
# ---------------------------------------------------------------------------


def dollars_by_entity():
    """total_obligations by tribe_id. `total_obligations` SUMS; award value
    would have to be MAXed (cedar_domain.SUM_COLUMNS)."""
    out = defaultdict(float)
    src = CLEAN / "prime_contracts.csv"
    if not src.exists():
        return out
    with open(src, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            t = (r.get("tribe_id") or "").strip()
            if t:
                try:
                    out[t] += float(r.get("total_obligations") or 0)
                except ValueError:
                    pass
    return out


def verify(rels, hier, spine, namesake, issues):
    results = []

    def check(name, ok, detail):
        results.append((name, "PASS" if ok else "FAIL", detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")

    # 1 -- every type is in the shared enum
    bad = Counter(r["relationship_type"] for r in rels
                  if r["relationship_type"] not in D.ALL_RELATIONSHIPS)
    check("every relationship_type in ALL_RELATIONSHIPS", not bad,
          f"{len(set(r['relationship_type'] for r in rels))} distinct types "
          f"used of {len(D.ALL_RELATIONSHIPS)} defined; "
          f"{sum(bad.values())} out of vocabulary")
    generic = sum(1 for r in rels if r["relationship_type"] == "related_to")
    check("no generic related_to", generic == 0, f"{generic} rows")

    # 2 -- no non-ownership edge carries a roll-up dollar
    #
    # The roll-up is DEFINED as the sum over ownership-bearing edges, so the
    # zero below is structural rather than lucky. What is worth reporting is
    # the counterfactual: the dollars a flat parent column would have moved
    # along these same edges, which is the size of the bug being removed.
    #
    # THE CLASS ARGUMENTS ARE NOW PASSED (2026-08-26,
    # `code/441_make_ancsa_class_guard_load_bearing.py`, taxonomy Gap 1).
    #
    # This line read `D.bears_ownership(r["relationship_type"])` - CLASS-BLIND
    # - and it is the ONLY production caller that walks a real edge table.
    # `bears_ownership`'s ANCSA branch fires rules 2 and 4 **only when both
    # class arguments are passed**, so across 2,292 relationship rows the
    # owner's $24.52B ruling evaluated exactly zero edges here. The ruling was
    # applied - by `191_apply_ancsa_ownership_ruling.py`, from its own local
    # copy of the class sets - so the DATA was right and the GUARD was inert,
    # which is the worse of the two states: the next author reads the constant
    # and believes they are protected.
    #
    # A guard that silently no-ops on a missing argument is the same failure
    # as `setdefault` on a pre-initialised dict.
    #
    # `class_of` is the spine's `entity_class`, read from the column, never
    # inferred from the id prefix - `ANVC-` spans village AND group
    # corporations and `CDFI-` spans two classes (taxonomy Gap 5).
    class_of = {r["tribe_id"]: r["entity_class"] for r in spine}
    money = dollars_by_entity()
    rolled_through_nonownership = 0.0
    at_risk_by_type = defaultdict(float)
    n_nonown_money = 0
    n_class_checked = 0
    n_ancsa_refused = 0
    ancsa_refusals = []
    for r in rels:
        src, tgt = r["source_entity_id"], r["target_entity_id"]
        if not src or not tgt:
            continue
        amt = money.get(src, 0.0)
        # An endpoint that is not on the spine has no class, and a guard must
        # not answer for an edge it could not check. Gap 2 is the reason this
        # can still happen at all; until the blanks are TYPED, an unresolvable
        # endpoint falls back to the class-blind read and is counted, never
        # silently treated as checked.
        sc, tc = class_of.get(src), class_of.get(tgt)
        if sc and tc:
            n_class_checked += 1
            bears = D.bears_ownership_checked(r["relationship_type"], sc, tc)
            if not bears and D.ancsa_refusal_reason(
                    r["relationship_type"], sc, tc) is not None:
                n_ancsa_refused += 1
                if len(ancsa_refusals) < 12:
                    ancsa_refusals.append(
                        f"{src} ({sc}) -{r['relationship_type']}-> {tgt} ({tc})")
        else:
            bears = D.bears_ownership(r["relationship_type"])
        if bears:
            continue
        if amt > 0:
            n_nonown_money += 1
            at_risk_by_type[r["relationship_type"]] += amt
    at_risk = sum(at_risk_by_type.values())
    # NAME what was refused, never only count it (defect class 2c). An ANCSA
    # refusal here is a rule-2 or rule-4 edge that reached the relationship
    # table, and it is a task.
    check("ANCSA class guard is LOAD-BEARING on this edge table",
          n_class_checked > 0,
          f"{n_class_checked:,} of {len(rels):,} edges evaluated WITH both "
          f"entity classes (was 0 before 2026-08-26 - the guard existed and "
          f"was never called); {n_ancsa_refused} refused by ANCSA rule 2/4"
          + (" - " + "; ".join(ancsa_refusals) if ancsa_refusals else ""))
    check("no non-ownership edge carries a roll-up dollar",
          rolled_through_nonownership == 0.0,
          f"${rolled_through_nonownership:,.2f} rolled; {n_nonown_money} "
          f"non-ownership edges sit on entities holding ${at_risk:,.2f} that "
          f"a flat parent column WOULD have moved ("
          + "; ".join(f"{k} ${v:,.0f}"
                      for k, v in sorted(at_risk_by_type.items(),
                                         key=lambda x: -x[1])) + ")")

    # 3 -- no ANCSA region is a parent anywhere
    #
    # An ANRC id plays TWO roles in this spine and the check has to know the
    # difference. `ANRC-ARCSLO-00` is Arctic Slope Regional Corporation, a
    # company that really does own Petro Star; it is ALSO the Arctic Slope
    # ANCSA region, a place that 17 village corporations sit in and that owns
    # none of them. So the violation is an ownership edge pointing at an ANRC
    # FROM an entity for which that ANRC is a region - not any ownership edge
    # pointing at an ANRC at all. Self-references are not parents either.
    anrc = {r["tribe_id"] for r in spine if r["tribe_id"].startswith("ANRC-")}
    region_of = {r["tribe_id"]: (r.get("ancsa_region_entity_id") or "").strip()
                 for r in spine}
    region_sited = {"Alaska Native Village Corporation",
                    "Federally recognized Alaska Native Village",
                    "ANCSA Group Corporation"}
    scls = {r["tribe_id"]: r["entity_class"] for r in spine}
    parentish = {"subsidiary_of", "indirect_subsidiary_of"} | D.OWNERSHIP_BEARING
    viol = [r for r in rels
            if r["relationship_type"] in parentish
            and r["target_entity_id"] in anrc
            and (region_of.get(r["source_entity_id"]) == r["target_entity_id"]
                 or scls.get(r["source_entity_id"]) in region_sited)]
    flat_viol = [r for r in hier
                 if r["tribe_id"] != (r.get("parent_entity_id") or "").strip()
                 and (r.get("parent_entity_id") or "").strip() in anrc
                 or (r["tribe_id"]
                     != (r.get("ultimate_parent_entity_id") or "").strip()
                     and (r.get("ultimate_parent_entity_id") or "").strip()
                     in anrc)]
    firm_owned = sum(1 for r in rels if r["relationship_type"] == "owned_by"
                     and r["target_entity_id"] in anrc)
    check("no ANCSA region appears as a parent", not viol,
          f"{len(viol)} typed edges make a region a parent of something it is "
          f"the region for; the flat file had {len(flat_viol)} "
          f"region-as-parent cells (excluding self-references); "
          f"{sum(1 for r in rels if r['relationship_type'] == 'associated_with_region')}"
          f" associated_with_region edges point at an ANRC, and {firm_owned} "
          f"owned_by edges point at one AS A CORPORATION owning a firm, which "
          f"is a different role of the same id")
    if firm_owned:
        issues.append({
            "issue_type": "anrc_id_plays_two_roles",
            "entity_id": "", "name": "ANRC-* entity ids",
            "detail": f"One id is both the ANCSA REGION (a place, on "
                      f"{sum(1 for v in region_of.values() if v)} entities) "
                      f"and the REGIONAL CORPORATION (an owner, on "
                      f"{firm_owned} owned_by edges). Only the edge type and "
                      f"the source's class tell them apart.",
            "resolution": "typed edges keep them separate; a flat parent "
                          "column cannot",
            "needs_ruling": "0"})

    # 4 -- namesake pairs: neither is the other's parent
    pairs = set()
    for p in namesake:
        pairs.add((p["corporation_tribe_id"], p["government_tribe_id"]))
        pairs.add((p["government_tribe_id"], p["corporation_tribe_id"]))
    npv = [r for r in rels
           if (r["source_entity_id"], r["target_entity_id"]) in pairs
           and r["relationship_type"] in parentish]
    check("no village corp/government parent edge in the 77 namesake pairs",
          not npv, f"{len(npv)} violations across {len(namesake)} pairs")

    # 5 -- round trip on ultimate_parent_entity_id
    edges = defaultdict(list)
    for r in rels:
        if r["source_entity_id"] and r["target_entity_id"]:
            edges[r["source_entity_id"]].append(
                (r["target_entity_id"], r["relationship_type"]))
    reach_self = reach_typed = explained = unreach = 0
    for r in hier:
        eid = r["tribe_id"]
        uid = (r.get("ultimate_parent_entity_id") or "").strip()
        if not uid:
            explained += 1
            continue
        if uid == eid:
            reach_self += 1
            continue
        seen, stack, hit = {eid}, [eid], False
        while stack:
            cur = stack.pop()
            for tgt, _t in edges.get(cur, []):
                if tgt == uid:
                    hit = True
                if tgt not in seen:
                    seen.add(tgt)
                    stack.append(tgt)
        if hit:
            reach_typed += 1
        else:
            unreach += 1
            issues.append({
                "issue_type": "ultimate_parent_unreachable",
                "entity_id": eid, "name": r.get("canonical_name", ""),
                "detail": f"flat ultimate_parent_entity_id={uid} is not "
                          f"reachable through any typed edge",
                "resolution": "", "needs_ruling": "1"})
    check("round-trip: every flat ultimate_parent is reachable or explained",
          unreach == 0,
          f"{reach_self} self-parent (no owner above them), {reach_typed} "
          f"reachable through typed edges, {explained} blank, {unreach} "
          f"unreachable")

    return results


# ---------------------------------------------------------------------------
# codebook - VARIABLES ONLY
# ---------------------------------------------------------------------------


def _coltype(values):
    vals = [v for v in values if v]
    if not vals:
        return "text"
    try:
        nums = [float(v) for v in vals]
    except ValueError:
        return "date" if all(len(v) == 10 and v[4] == v[7] == "-"
                             for v in vals) else "text"
    return "integer" if all(n.is_integer() for n in nums) else "numeric"


def codebook(alias_rows, rel_rows):
    """Document the new VARIABLES in codebook_master.csv - variables only, no
    methodology (that is what the migration log is for).

    Descriptions live in `41_build_codebooks.DESCRIPTIONS` so there is exactly
    one source for them and a later run of script 41 reproduces these rows
    instead of fighting them. Variable names follow 41's convention (bare
    column name, one row per column per dataset), and fill rates are computed
    from the rows just written - regression rule 10: a number in a doc that is
    not recomputed from the data is a claim, not a fact.
    """
    path = CLEAN / "codebook_master.csv"
    existing = read_csv(path)
    if not existing:
        return 0
    fields = list(existing[0].keys())

    # Which 05_entities columns belong to the OTHER files in that dataset.
    # Anything outside this set and inside our two tables is ours to refresh,
    # so a re-run corrects its own fill rates instead of leaving stale ones.
    theirs = set()
    for f in ("../spine/cedar_entity_spine.csv", "intertribal_orgs.csv",
              "nho_register.csv", "entity_hierarchy.csv"):
        p = CLEAN / f
        if p.exists():
            with open(p, encoding="utf-8-sig", newline="") as fh:
                theirs.update(next(csv.reader(fh), []))

    cols = {}
    for rows, flds in ((alias_rows, ALIAS_FIELDS), (rel_rows, REL_FIELDS)):
        for col in flds:
            cols.setdefault(col, []).append(rows)
    mine = {c for c in cols if c not in theirs}
    out = [r for r in existing
           if not (r["dataset"] == "05_entities" and r["variable"] in mine)]
    added = 0
    for col, row_sets in cols.items():
        if col not in mine:
            continue
        vals = [str(r.get(col, "")) for rows in row_sets for r in rows]
        filled = sum(1 for v in vals if v.strip())
        desc, units = CB41.describe(col, "05_entities")
        out.append({
            "dataset": "05_entities", "variable": col,
            "type": _coltype(vals), "units": units or "",
            "pct_filled": f"{100.0 * filled / max(len(vals), 1):.1f}",
            "n_rows": str(len(vals)), "published": "1",
            "access_tier": CB41.access_tier(col),
            "description": desc, "generated": TODAY,
        })
        added += 1
    write_csv(path, out, fields)
    return added


# ---------------------------------------------------------------------------


def main():
    print(f"=== Cedar Press {SCRIPT} ===\n")
    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    hier = read_csv(CLEAN / "entity_hierarchy.csv")
    brands = read_csv(CLEAN / "brand_family_registry.csv")
    ledger = read_csv(CLEAN / "cedar_identifier_ledger_final.csv")
    namesake = read_csv(REVIEW / "village_corp_namesake_pairs.csv")
    assigns = read_csv(CLEAN / "admin_region_assignments.csv")
    tdhe_all = [r for r in assigns if r.get("subject_type") == "TDHE"]
    tdhe = {}
    for t in tdhe_all:                     # 361 assignment rows, 148 entities
        tdhe.setdefault(t["subject_name"], t)
    tdhe = list(tdhe.values())
    print(f"  spine {len(spine):,} | hierarchy {len(hier):,} | brands "
          f"{len(brands)} | ledger {len(ledger):,} | namesake pairs "
          f"{len(namesake)} | TDHEs {len(tdhe)} of {len(tdhe_all)} rows\n")

    issues = []
    if len(hier) != len(spine):
        issues.append({
            "issue_type": "flat_hierarchy_stale",
            "entity_id": "", "name": "entity_hierarchy.csv",
            "detail": f"{len(hier)} rows against a {len(spine)}-entity spine; "
                      f"{len(spine) - len(hier)} entities have no row in the "
                      f"flat file at all",
            "resolution": "hierarchy columns read from the spine for those "
                          "entities; source_id records which file each edge "
                          "came from",
            "needs_ruling": "0"})

    places = place_names()
    print(f"  place-name proxy: {len(places):,} distinct city names\n")

    alias_rows, ledger_firms, astats = build_aliases(
        spine, brands, ledger, places, issues)
    print(f"  aliases built: {len(alias_rows):,}")
    print("  by type: " + ", ".join(
        f"{k}={v}" for k, v in
        Counter(r["alias_type"] for r in alias_rows).most_common()))
    print(f"  ledger legal_business_name: {astats['ledger_name_variants']} "
          f"were name variants (alias); {len(ledger_firms):,} ledger rows name "
          f"a DISTINCT firm and are not aliases\n")

    rel_rows, rstats = build_relationships(
        spine, hier, brands, ledger_firms, namesake, tdhe, alias_rows, issues)
    print(f"  relationships built: {len(rel_rows):,}")
    print("  by type: " + ", ".join(
        f"{k}={v}" for k, v in
        Counter(r["relationship_type"] for r in rel_rows).most_common()))
    print()

    print("  --- verification ---")
    results = verify(rel_rows, hier, spine, namesake, issues)
    print()

    write_csv(CLEAN / "entity_aliases.csv", alias_rows, ALIAS_FIELDS)
    write_csv(CLEAN / "entity_relationships.csv", rel_rows, REL_FIELDS)
    write_csv(REVIEW / f"relationship_migration_issues_{TODAY}.csv", issues,
              ["issue_type", "entity_id", "name", "detail", "resolution",
               "needs_ruling"])
    n_cb = codebook(alias_rows, rel_rows)
    print(f"  codebook: {n_cb} variables documented")

    summary = {
        "generated": TODAY, "script": SCRIPT,
        "aliases": len(alias_rows),
        "aliases_by_type": dict(Counter(r["alias_type"] for r in alias_rows)),
        "alias_stats": astats,
        "relationships": len(rel_rows),
        "relationships_by_type": dict(
            Counter(r["relationship_type"] for r in rel_rows)),
        "relationship_stats": rstats,
        "assertions": [{"check": a, "result": b, "detail": c}
                       for a, b, c in results],
        "issues": len(issues),
    }
    (CLEAN / "_97_summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8")
    print("\n  wrote data/clean/_97_summary.json")
    if any(b == "FAIL" for _a, b, _c in results):
        print("\n  ONE OR MORE ASSERTIONS FAILED - this is a finding, "
              "reported, not silently fixed.")


if __name__ == "__main__":
    main()
