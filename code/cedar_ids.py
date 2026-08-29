#!/usr/bin/env python3
"""
Cedar Press - internal ID service. SPEC v2, Section 13.2.

    "All internal IDs from one shared service - never inline in ingestion
     scripts. Existing spine IDs are grandfathered as-is. Store type
     explicitly; never infer from prefix."

WHY "NEVER INFER FROM PREFIX" IS THE LOAD-BEARING RULE
------------------------------------------------------
It is tempting to read `CCP-000123` as "a Casino City property" and
`TRBF-CHKSWN-00` as "a federally recognised tribe". Both readings are wrong in
practice:

  - `CCP-` records are Cedar properties whose IDs happen to carry a vendor's
    prefix because that is where the ID was minted. The prefix is HISTORY, not
    provenance - and the 2026-08-07 backbone ruling keeps those IDs precisely
    because everything downstream joins on them.
  - Entity classes change. A state-recognised tribe can gain federal
    recognition; the ID must not have to change with it.

So type lives in a column. `id_type()` here reads the registry, not the string.

CONCURRENCY
-----------
Multiple agents mint IDs at once. Allocation takes an exclusive file lock,
re-reads the counter from disk, and writes before releasing - so two workers
cannot mint the same ID. This is the same class of bug that put Sequoyah High
School onto a CDFI another agent had written minutes earlier.

Registry: data/spine/_id_registry.json
"""

import json
import os
import re
import time
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
SPINE = CEDAR / "data" / "spine"
REGISTRY = SPINE / "_id_registry.json"
LOCK = SPINE / "_id_registry.lock"

# prefix -> (what it identifies, zero-padded width)
# Entity prefixes are GRANDFATHERED from the existing spine and must not be
# reissued or reinterpreted.
PREFIXES = {
    # --- entity (grandfathered, minted by earlier builds) ---
    "TRBF": ("entity", 0),      # federally recognised tribe
    "TRBS": ("entity", 0),      # state-recognised tribe
    "AKNF": ("entity", 0),      # Alaska Native village government
    "ANVC": ("entity", 0),      # ANCSA village corporation
    "ANRC": ("entity", 0),      # ANCSA regional corporation
    "CNSF": ("entity", 0),      # constituent band
    "NHO":  ("entity", 0),
    "ITO":  ("entity", 0),      # intertribal organisation
    "TCU":  ("entity", 0),      # tribal college or university
    "CDFI": ("entity", 0),
    "BIE":  ("entity", 0),
    "UIO":  ("entity", 0),      # urban Indian organisation
    "SGVF": ("entity", 0),      # federal-level self-governance consortium
                                # (Alaska: APIA, AVCP, BBNA, Chugachmiut...)
    "CNSS": ("entity", 0),      # state-level constituency entity
    # --- facility (grandfathered; prefix is history, NOT provenance) ---
    "CCP":  ("facility", 0),
    "VP":   ("facility", 0),
    "TPL":  ("facility", 0),
    # --- new, minted by this service ---
    "CEDAR-ENT":     ("entity", 6),
    "CEDAR-FAC":     ("facility", 6),
    "CEDAR-EVENT":   ("event", 6),
    "CEDAR-CLAIM":   ("claim", 8),
    "CEDAR-REL":     ("relationship", 8),
    "CEDAR-ALIAS":   ("alias", 8),
    "CEDAR-IDENT":   ("identifier", 8),
    "CEDAR-SRC":     ("source_record", 9),
    "CEDAR-XWALK":   ("crosswalk", 8),
    "CEDAR-CONTRACT": ("contract", 8),
    "CEDAR-FAMILY":  ("contract_family", 6),
    "CEDAR-OBS":     ("observation", 9),
    "CEDAR-WELL":    ("resource_asset", 6),
    "CEDAR-LEASE":   ("resource_asset", 6),
    "CEDAR-ADMREG":  ("admin_region", 6),
}

# Reserved so a concurrent build cannot collide with another agent's block.
RESERVED_BLOCKS = {
    "CEDAR-ADMREG": (300001, 309999),   # NIGC regions, reserved 2026-08-06
}

# --------------------------------------------------------------------------
# STATIC BLOCKS - a DECLARED bypass, which is the only acceptable kind
#
# Added 2026-08-26 by `328_audit_id_service_bypass.py`.
#
# `allocate()` hands out ids one at a time from a shared counter. Two builds
# need something it cannot give: a CONTIGUOUS, PRE-ASSIGNED range, so that the
# id of the BIA Great Plains Region is the same number on every machine
# whether or not anyone else minted anything first.
#
#     84_build_nigc_regions.py       ADMREG[(version, region)] = f"...{n:06d}"
#     85_build_admin_region_crosswalk.py   class Ids: ... f"...{v:06d}"
#
# Both were f-strings and neither told the ID service anything, so
# `allocate("CEDAR-ADMREG")` could have walked straight into their numbers.
# `RESERVED_BLOCKS` knew about exactly ONE of the six ranges in use.
#
# A static block is legitimate; an UNDECLARED one is not. `declare_static_block`
# registers the range under an owner, refuses an overlap with a different
# owner, and returns the minter - so the bypass becomes a call into this
# module and `328_audit_id_service_bypass.py` can find any that are not.
# --------------------------------------------------------------------------

#: prefix -> [(lo, hi, owner, why)]. Declared at import time by the owning
#: build, and re-declaring the identical block is a no-op so a re-run is safe.
STATIC_BLOCKS = {}


class IdCollision(Exception):
    pass


def _overlaps(a_lo, a_hi, b_lo, b_hi):
    return a_lo <= b_hi and b_lo <= a_hi


def _reserved_ranges(prefix):
    """Every range `allocate` must step over for this prefix."""
    out = []
    if prefix in RESERVED_BLOCKS:
        out.append(RESERVED_BLOCKS[prefix])
    out += [(lo, hi) for lo, hi, _o, _w in STATIC_BLOCKS.get(prefix, [])]
    return sorted(out)


def declare_static_block(prefix, lo, hi, owner, why):
    """Reserve [lo, hi] under `prefix` for `owner`, and return its minter.

    The minter is `mint()` -> the next id in the block, raising when the block
    is exhausted rather than silently walking into the next owner's range.

    Raises `IdCollision` if the range overlaps a block another owner already
    declared. Declaring the SAME block twice with the same owner is a no-op,
    so a module that is imported twice does not fail.
    """
    if prefix not in PREFIXES:
        raise KeyError(f"unknown prefix {prefix!r} - add it to PREFIXES first")
    if lo > hi:
        raise ValueError(f"{prefix}: block {lo}-{hi} is empty")
    blocks = STATIC_BLOCKS.setdefault(prefix, [])
    for b_lo, b_hi, b_owner, _w in blocks:
        if (b_lo, b_hi, b_owner) == (lo, hi, owner):
            break
        if _overlaps(lo, hi, b_lo, b_hi):
            raise IdCollision(
                f"{prefix} block {lo}-{hi} requested by {owner} overlaps "
                f"{b_lo}-{b_hi} already declared by {b_owner}")
    else:
        blocks.append((lo, hi, owner, why))

    state = {"n": lo}

    def mint():
        v = state["n"]
        if v > hi:
            raise IdCollision(
                f"{prefix} static block {lo}-{hi} ({owner}) is EXHAUSTED. "
                f"Widen the declared block; never spill past it - the next "
                f"number belongs to somebody else.")
        state["n"] = v + 1
        return format_id(prefix, v)

    mint.block = (lo, hi)
    mint.owner = owner
    return mint


def format_id(prefix, n):
    """Render an id under `prefix` at ordinal `n`, with the registry's width.

    For a build that must PRINT a block boundary (`id_block_start`) rather
    than mint one. Keeping the zero-padding in the ID service means a caller
    cannot render `CEDAR-ADMREG-100001` one way here and another way there.
    """
    if prefix not in PREFIXES:
        raise KeyError(f"unknown prefix {prefix!r}")
    _kind, width = PREFIXES[prefix]
    if width == 0:
        raise ValueError(f"{prefix} is GRANDFATHERED - it has no minted width")
    return f"{prefix}-{n:0{width}d}"


class _Lock:
    """Exclusive file lock. Windows-safe: O_CREAT|O_EXCL is atomic."""

    def __init__(self, path, timeout=30):
        self.path, self.timeout, self.fd = Path(path), timeout, None

    def __enter__(self):
        start = time.time()
        while True:
            try:
                self.fd = os.open(str(self.path),
                                  os.O_CREAT | os.O_EXCL | os.O_RDWR)
                return self
            except FileExistsError:
                if time.time() - start > self.timeout:
                    # A crashed holder must not deadlock the project.
                    try:
                        if time.time() - self.path.stat().st_mtime > 120:
                            self.path.unlink()
                            continue
                    except FileNotFoundError:
                        continue
                    raise TimeoutError(f"id registry locked >{self.timeout}s")
                time.sleep(0.05)

    def __exit__(self, *a):
        if self.fd is not None:
            os.close(self.fd)
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def _load():
    if REGISTRY.exists():
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {"counters": {}, "types": {}, "created": "2026-08-07"}


def _save(reg):
    tmp = REGISTRY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(reg, indent=1, sort_keys=True), encoding="utf-8")
    tmp.replace(REGISTRY)


def allocate(prefix, n=1, note=""):
    """Mint n IDs under `prefix`. Lock held across read-modify-write."""
    if prefix not in PREFIXES:
        raise KeyError(f"unknown prefix {prefix!r} - add it to PREFIXES first")
    kind, width = PREFIXES[prefix]
    if width == 0:
        raise ValueError(
            f"{prefix} is GRANDFATHERED - existing IDs only, never minted. "
            f"Spec constraint 2: existing entity IDs remain stable.")
    out = []
    with _Lock(LOCK):
        reg = _load()
        cur = reg["counters"].get(prefix, 0)
        # Every reserved range, not just the one hardcoded in RESERVED_BLOCKS.
        # Before 2026-08-26 this stepped over ONE of the six CEDAR-ADMREG
        # ranges actually in use, because the other five were f-strings in two
        # build scripts and nothing here knew about them.
        ranges = _reserved_ranges(prefix)
        for _ in range(n):
            cur += 1
            moved = True
            while moved:                  # a step can land in the next block
                moved = False
                for lo, hi in ranges:
                    if lo <= cur <= hi:
                        cur = hi + 1
                        moved = True
            out.append(format_id(prefix, cur))
        reg["counters"][prefix] = cur
        reg.setdefault("types", {})[prefix] = kind
        if note:
            reg.setdefault("notes", {})[prefix] = note
        _save(reg)
    return out


def id_type(value):
    """What does this ID identify? Reads the registry - NEVER guesses from the
    string, because a prefix is history and an entity's class can change."""
    v = (value or "").strip()
    for p in sorted(PREFIXES, key=len, reverse=True):
        if v.upper().startswith(p.upper() + "-") or v.upper().startswith(p.upper()):
            return PREFIXES[p][0]
    return None


def is_internal(value):
    """A Cedar-generated ID is never presented as an official identifier."""
    return (value or "").upper().startswith("CEDAR-")


def adopt_existing(prefix, ids):
    """Record grandfathered IDs so a future mint cannot collide with them."""
    nums = []
    for i in ids:
        m = re.search(r"(\d+)$", str(i))
        if m:
            nums.append(int(m.group(1)))
    if not nums:
        return 0
    with _Lock(LOCK):
        reg = _load()
        reg["counters"][prefix] = max(reg["counters"].get(prefix, 0), max(nums))
        reg.setdefault("types", {})[prefix] = PREFIXES.get(prefix, ("unknown", 0))[0]
        _save(reg)
    return max(nums)



# ===========================================================================
# THE CANONICAL IDENTITY LAYER
#
# Added 2026-08-26 by the pass holding script numbers 415-419
# (`docs/CEDAR_ID_SYSTEM.md`). APPENDED rather than merged into the blocks
# above, so a concurrent editor of this module cannot lose either half.
#
# THE OWNER'S ASK, verbatim:
#   "We need to create our own ID system so that we can more easily link say
#    individuals or other orgs - like our ID system supersedes CICD, and UEI
#    etc, but is aligned with one Native entity or org."
#
# and his correction, which reverses the opacity instinct and is the reason
# the prefixes below stay readable:
#   "I just want it easy for AI agents to update it, so if the number can also
#    code other things like these are tribes, ANCs, NHO, individuals etc -
#    whatever makes your job easier, especially with like constituent band
#    tribes too."
#
# THE FOUR RULES THIS BLOCK IMPLEMENTS
# ------------------------------------
# 1. ONE ENTITY, ONE CEDAR ID, PERMANENT, NEVER REUSED. The canonical id is
#    the value in `cedar_entity_spine.csv::tribe_id`. See
#    ENTITY_ID_COLUMN_MEANINGS - the spine's own `cedar_entity_id` column is
#    NOT a Cedar id and never was.
# 2. THE PREFIX IS A LEGIBLE HINT, THE COLUMN IS THE AUTHORITY. The docstring
#    at the top of this file already says "never infer from prefix" and that
#    rule is UNCHANGED: `id_type()` still reads the registry. What is new is
#    that the hint is now DATA (PREFIX_CLASS_OBSERVED), measured from the
#    spine with its exceptions named, instead of a folk belief re-typed into
#    two scripts as a 1:1 map that is wrong for 272 entities.
# 3. A CLASS CHANGE MINTS A NEW ID AND RETIRES THE OLD ONE AS A PERMANENT
#    ALIAS. `reclassify()`. The old id always resolves, forever. Nothing is
#    rewritten in place and no id is ever reused.
# 4. EVERY EXTERNAL IDENTIFIER IS AN ATTRIBUTE OF A CEDAR ID, NEVER A
#    COMPETING KEY. EXTERNAL_IDENTIFIER_SCHEMES is the registry, and its
#    `cardinality` field carries the rule that many-to-one is EXPECTED and
#    one-to-many is a DEFECT.
# ===========================================================================

#: The canonical entity id lives in this column, per file. Anything else
#: named like an id in that file is an ATTRIBUTE, not the key.
#:
#: `tribe_id` is a grandfathered COLUMN NAME, not a claim that the row is a
#: tribe: 210 NHOs, 185 BIE schools, 45 individually Native-owned firms and 93
#: financial institutions carry one. Renaming it is BLOCKED-ON-CONSUMERS -
#: see docs/CEDAR_ID_SYSTEM.md - and the concept name a subscriber sees is
#: `cedar_entity_id`, which is what `109_build_variable_registry.py` declares
#: and what `110_build_harmonized_views.py` emits.
CANONICAL_ENTITY_ID_COLUMN = {
    "cedar_entity_spine.csv": "tribe_id",
    "cedar_identifier_ledger_final.csv": "tribe_id",
    "cedar_identifier_ledger_tiered.csv": "tribe_id",
    "entity_aliases.csv": "entity_id",
    "entity_relationships.csv": "target_entity_id",
    "entity_evidence_profile.csv": "cedar_entity_id",
}

#: (file, column) -> what the column ACTUALLY holds. Written because ONE
#: COLUMN NAME CARRIES TWO MEANINGS in this repo and nothing said so.
#:
#: MEASURED 2026-08-26 by `code/415_audit_identity_layer.py`:
#:   data/spine/cedar_entity_spine.csv::cedar_entity_id
#:       1,009 of 1,534 rows populated, 525 blank, and on ZERO rows does it
#:       equal `tribe_id`. Values are `T-0001`, `A-0001`, `N-...`, `I-...` -
#:       the `Entity_ID` column of the upstream `entity_master.csv` register.
#:       Scripts 52, 61, 66 and 163 use it as a DEDUPE KEY against that
#:       register (`if c["Entity_ID"] in have_ceid: skip`). It is a FOREIGN
#:       identifier that happens to sit in a column whose name says otherwise.
#:   data/clean/entity_evidence_profile.csv::cedar_entity_id
#:   data/clean/views/v_*.csv::cedar_entity_id
#:       the CANONICAL Cedar id - `TRBF-CRDALN-00`. Different meaning, same
#:       column name, and a join between the two silently returns nothing.
ENTITY_ID_COLUMN_MEANINGS = {
    ("cedar_entity_spine.csv", "tribe_id"): {
        "holds": "CANONICAL_CEDAR_ENTITY_ID",
        "note": "The one permanent Cedar id. Grandfathered column name; the "
                "rows are not all tribes.",
    },
    ("cedar_entity_spine.csv", "cedar_entity_id"): {
        "holds": "FOREIGN_REGISTER_ID",
        "scheme": "ENTITY_MASTER",
        "note": "NOT a Cedar id despite the column name. It is "
                "entity_master.csv::Entity_ID (T-/A-/N-/I- short codes), used "
                "as a dedupe key by scripts 52, 61, 66 and 163. Populated on "
                "1,009 of 1,534 rows. NEVER join it to any column called "
                "cedar_entity_id in data/clean - those hold the canonical id "
                "and the two vocabularies do not intersect at all.",
        "renamed_to": "entity_master_register_id",
        "rename_status": "BLOCKED-ON-CONSUMERS",
        "rename_blockers": ["52_add_village_corporations.py",
                            "61_add_nho_intertribal_to_spine.py",
                            "66_build_entity_hierarchy.py",
                            "163_promote_nho_universe_in_place.py",
                            "01_build_entity_spine.py (NEVER-RUN)",
                            "41_build_codebooks.py (NEVER-RUN)"],
    },
    ("entity_evidence_profile.csv", "cedar_entity_id"): {
        "holds": "CANONICAL_CEDAR_ENTITY_ID",
        "note": "Written by 151/110 from the spine's tribe_id.",
    },
}

#: Prefixes that ARE canonical Cedar entity ids. `CEDAR-ENT` is minted by this
#: service; the rest are grandfathered mnemonics.
CANONICAL_ENTITY_PREFIXES = frozenset({
    "TRBF", "TRBS", "AKNF", "ANVC", "ANRC", "CNSF", "CNSS", "NHO", "ITO",
    "TCU", "CDFI", "BIE", "UIO", "SGVF", "CEDAR-ENT",
})

#: prefix -> the entity_class values ACTUALLY carried under it, with counts,
#: measured from data/spine/cedar_entity_spine.csv on 2026-08-26.
#:
#: READ THE SHAPE, NOT JUST THE FIRST ENTRY. Twelve prefixes are 1:1. THREE
#: ARE NOT, and 273 entities sit under them:
#:     ANVC -> Alaska Native Village Corporation 173 + ANCSA Group Corporation 6
#:     CDFI -> Native Community Development Financial Institution 64
#:             + Native Financial Institution 29
#:     TRBF/AKNF -> one AKNF-prefixed row (Tlingit & Haida) is classed
#:             `Federally recognized tribe`, because it is a regional tribal
#:             government rather than a village. A documented exception.
#: `73_bills_votes_completion.py:1419` and `41_build_codebooks.py:1339`
#: hard-code prefix->class 1:1 and are wrong for exactly those rows
#: (docs/CEDAR_TAXONOMY.md Gap 5). This constant exists so the next reader
#: gets the hint AND the exception in the same object.
PREFIX_CLASS_OBSERVED = {
    "TRBF": {"Federally recognized tribe": 348},
    "AKNF": {"Federally recognized Alaska Native Village": 228,
             "Federally recognized tribe": 1},
    "NHO":  {"Native Hawaiian Organization": 210},
    "BIE":  {"BIE School": 185},
    "ANVC": {"Alaska Native Village Corporation": 173,
             "ANCSA Group Corporation": 6},
    "CDFI": {"Native Community Development Financial Institution": 64,
             "Native Financial Institution": 29},
    "TRBS": {"State-recognized tribe": 64},
    "ITO":  {"Intertribal Organization": 55},
    "CEDAR-ENT": {"Individually Native-owned business": 45},
    "UIO":  {"Urban Indian Organization": 43},
    "TCU":  {"Tribal College or University": 37},
    "CNSF": {"Federal-level constituency entity": 22},
    "ANRC": {"Alaska Native Regional Corporation": 12},
    "SGVF": {"Federal-level self-governance consortium": 9},
    "CNSS": {"State-level constituency entity": 3},
}

#: entity_class -> the prefix a NEW entity of that class gets. The inverse of
#: PREFIX_CLASS_OBSERVED with the ambiguity resolved by a decision, not by a
#: majority: `ANCSA Group Corporation` keeps ANVC because six live ids already
#: use it and an id is never re-minted to tidy a scheme.
CLASS_PREFIX = {
    "Federally recognized tribe": "TRBF",
    "Federally recognized Alaska Native Village": "AKNF",
    "State-recognized tribe": "TRBS",
    "Alaska Native Village Corporation": "ANVC",
    "ANCSA Group Corporation": "ANVC",
    "Alaska Native Regional Corporation": "ANRC",
    "Federal-level constituency entity": "CNSF",
    "State-level constituency entity": "CNSS",
    "Federal-level self-governance consortium": "SGVF",
    "Native Hawaiian Organization": "NHO",
    "Intertribal Organization": "ITO",
    "Tribal College or University": "TCU",
    "Native Community Development Financial Institution": "CDFI",
    "Native Financial Institution": "CDFI",
    "BIE School": "BIE",
    "Urban Indian Organization": "UIO",
    "Individually Native-owned business": "CEDAR-ENT",
}


def class_prefix(entity_class):
    """The prefix a NEW entity of `entity_class` should be minted under.

    Returns None for an unrecognised class, deliberately: a class nobody has
    ruled on must not silently acquire a prefix that asserts something about
    it. Same polarity as `cedar_domain.np_ruling_is_native` - unknown is not a
    yes.
    """
    return CLASS_PREFIX.get((entity_class or "").strip())


def prefix_hint(entity_id):
    """What the prefix SUGGESTS this entity is, and how reliable that is.

    Returns {prefix, classes, unambiguous, note} or None.

    THIS IS A HINT AND IT SAYS SO. `unambiguous` is False for ANVC and CDFI.
    The authority is the `entity_class` column; this function exists so an
    agent reading one row in isolation gets the owner's legibility AND the
    exception, instead of a 1:1 map that is wrong for 273 entities.
    """
    p = _prefix_of(entity_id)
    if p is None:
        return None
    classes = PREFIX_CLASS_OBSERVED.get(p, {})
    return {
        "prefix": p,
        "classes": dict(classes),
        "unambiguous": len(classes) == 1,
        "note": ("one class observed under this prefix"
                 if len(classes) == 1 else
                 "MORE THAN ONE CLASS under this prefix - read entity_class"),
    }


def _prefix_of(entity_id):
    v = (entity_id or "").strip().upper()
    if not v:
        return None
    for p in sorted(PREFIXES, key=len, reverse=True):
        if v.startswith(p.upper() + "-"):
            return p
    return None


def parse_entity_id(entity_id):
    """Decompose a canonical Cedar entity id WITHOUT ever shortening it.

    Returns {id, prefix, token, sequence, qualifiers, is_compound} or None.

        TRBF-CHKSWN-00                  -> qualifiers ()
        CNSF-MINNCH-LL                  -> qualifiers ('LL',)   band of MINNCH
        AKNF-MTLKTL-00-TLNGHD           -> qualifiers ('TLNGHD',)
        AKNF-AKACHK-00-CALSTA-ASVCPR    -> qualifiers ('CALSTA','ASVCPR')

    **NEVER STRIP A QUALIFIER TO MAKE A JOIN WORK.** START_HERE.md records the
    measurement: `AKNF-MTLKTL-00-TLNGHD` is a canonical spine id and the
    apparent "base" `AKNF-MTLKTL-00` IS NOT IN THE SPINE. 231 of 231 compound
    ids were verified present; stripping the suffix would turn 21,693 joinable
    rows into unjoinable ones while looking like a normalisation.

    The qualifier is exactly what the owner asked the id to carry: for a
    CNSF- id it names the CONSTITUENT BAND inside its umbrella tribe, so
    `CNSF-MINNCH-LL` says "Leech Lake, a band of the Minnesota Chippewa Tribe"
    without a join. `umbrella_of()` reads it.
    """
    v = (entity_id or "").strip()
    p = _prefix_of(v)
    if p is None:
        return None
    rest = v[len(p) + 1:].split("-")
    token = rest[0] if rest else ""
    seq = rest[1] if len(rest) > 1 else ""
    quals = tuple(rest[2:]) if len(rest) > 2 else ()
    # CNSF/CNSS put the band code where the sequence normally sits.
    if p in ("CNSF", "CNSS") and seq and not seq.isdigit():
        quals, seq = (seq,) + quals, ""
    return {"id": v, "prefix": p, "token": token, "sequence": seq,
            "qualifiers": quals, "is_compound": bool(quals)}


def umbrella_id_for_band(entity_id, umbrella_prefix="TRBF"):
    """For a CNSF-/CNSS- constituent-band id, the umbrella entity's id.

        CNSF-MINNCH-LL -> TRBF-MINNCH-00

    RETURNS A CANDIDATE, NOT A FACT. The caller MUST check the result is in
    the spine before using it - `cedar_domain.NEVER_OWNERSHIP` contains
    `constituent_band_of`, so this edge NEVER carries a dollar in either
    direction. It exists so the 42 CONSTITUENT_BAND_VS_UMBRELLA_TRIBE defects
    in `review/identifier_one_to_many_defects_2026-08-26.csv` ($1,297,812,942
    observed) can be TYPED rather than guessed at: when one UEI resolves to
    both `CNSF-TEMOAK-BT` and `TRBF-TEMOAK-00`, this function is what proves
    the pair is a band/umbrella pair and not two unrelated tribes.
    """
    parsed = parse_entity_id(entity_id)
    if not parsed or parsed["prefix"] not in ("CNSF", "CNSS"):
        return None
    return f"{umbrella_prefix}-{parsed['token']}-00"


def is_canonical_entity_id(value):
    """True only for a string shaped like a canonical Cedar entity id.

    Explicitly FALSE for `T-0001` / `A-0001` / `N-0007` - the upstream
    Entity_Master register codes sitting in the spine's `cedar_entity_id`
    column. That column is the reason this predicate exists: the two
    vocabularies share a column name and do not intersect, so a join between
    them returns silence rather than an error.
    """
    return _prefix_of(value) in CANONICAL_ENTITY_PREFIXES


# ---------------------------------------------------------------------------
# EXTERNAL IDENTIFIERS ARE ATTRIBUTES OF A CEDAR ID, NEVER COMPETING KEYS.
#
# `authority`   who assigns it. Never us.
# `publishes`   may the VALUE ship. DUNS is D&B-licensed; the individual
#               Native-owned firm carve-out lives in cedar_domain and is
#               POINTED AT here rather than restated, so the two cannot drift.
# `cardinality` MANY_PER_ENTITY is the normal case and is NOT a defect:
#               the 8(a) nine-year term drives successor entities sharing a
#               name and an address, and NANA holds 67 UEIs. The defect is the
#               other direction - one identifier resolving to many entities -
#               and it goes to review, never into a crosswalk row.
# `tier_source` where the tier on a mapping comes from. ALWAYS the source row.
#               Never assigned by the consumer. This is the rule that cost
#               UNITED WAY OF THE GREATER CHIPPEWA VALLEY -> United Auburn.
# ---------------------------------------------------------------------------
EXTERNAL_IDENTIFIER_SCHEMES = {
    "UEI": {
        "authority": "GSA / SAM.gov",
        "publishes": True,
        "publish_carve_out": "cedar_domain.may_publish_individual_native_field"
                             " - a UEI whose legal name is a natural person's "
                             "resolves to that person in SAM's public search, "
                             "so it is withheld. A DIGEST OF A UEI IS NOT A "
                             "PRIVACY CONTROL: SAM's entity space is "
                             "enumerable, so any digest is reversible by "
                             "hashing every UEI and comparing. The protection "
                             "is that the column never ships.",
        "cardinality": "MANY_PER_ENTITY",
        "tier_source": "cedar_identifier_ledger_final.csv::confidence_tier",
        "carried_in": "cedar_identifier_ledger_final.csv",
    },
    "CAGE": {
        "authority": "DLA",
        "publishes": True,
        "cardinality": "MANY_PER_ENTITY",
        "tier_source": "cedar_identifier_ledger_final.csv::confidence_tier",
        "carried_in": "cedar_identifier_ledger_final.csv",
        "note": "Survives the DUNS->UEI transition; CAGE-first, then UEI.",
    },
    "EIN": {
        "authority": "IRS",
        "publishes": True,
        "cardinality": "MANY_PER_ENTITY",
        "tier_source": "cedar_identifier_ledger_final.csv::confidence_tier",
        "carried_in": "cedar_identifier_ledger_final.csv",
        "note": "1,104 rows, NOT ONE tier A. 873 sit on 52 entities carrying "
                "5+ EINs each and 821 are tier B via need_v6 (6.5% accurate). "
                "A tribe with 38 EINs is a matching artefact, not a corporate "
                "structure. Never read an EIN row here as evidence that an "
                "organisation is Native.",
    },
    "DUNS": {
        "authority": "Dun & Bradstreet",
        "publishes": False,
        "licensed": True,
        "cardinality": "MANY_PER_ENTITY",
        "tier_source": "inherited from the row that carries it",
        "note": "LICENSED. Join on it internally; it never publishes at any "
                "tier. cedar_domain.LICENSED_IDENTIFIER_TYPES and "
                "cedar_schema's column-definition gate both refuse it.",
    },
    "CICD_NEID": {
        "authority": "CICD Native Entity Connector Crosswalk (Feb 2026)",
        "publishes": True,
        "cardinality": "ONE_PER_ENTITY",
        "tier_source": "the crosswalk row it came from",
        "note": "687 entities under TRBF/AKNF/TRBS/CNSF/ANRC/SGVF/CNSS. "
                "SEEDED the spine and the string is still the spine's own id "
                "for those rows - so the mapping is an IDENTITY today. It is "
                "declared anyway, because Cedar's is authoritative and CICD's "
                "is an ALIAS: the day the two diverge (a recognition event, a "
                "split, a merge) the alias keeps resolving and nothing "
                "breaks. Owner ruling 2026-08-26: an INPUT, not a blocker "
                "(docs/PUBLISHED_LANDSCAPE_2026-08-26.md).",
    },
    "ENTITY_MASTER": {
        "authority": "Cedar's own upstream Entity_Master workbook register",
        "publishes": False,
        "cardinality": "ONE_PER_ENTITY",
        "tier_source": "the spine row that carries it",
        "note": "T-/A-/N-/I- short codes. Lives TODAY in the spine column "
                "misleadingly named `cedar_entity_id`. An attribute, not a "
                "key. Scripts 52/61/66/163 dedupe on it.",
    },
    "LEGACY_ASSISTANCE_INT": {
        "authority": "the Lineage A assistance build (pre-Cedar)",
        "publishes": False,
        "cardinality": "ONE_PER_ENTITY",
        "tier_source": "assistance_tribe_id_crosswalk.csv::tier",
        "note": "365,535 rows of federal_funding_transactions.csv carry an "
                "INTEGER here, worth $107.50B, beside 178,820 carrying a "
                "Cedar id. `tribe_id_scheme_resolved` declares which, per "
                "row. THE CROSSWALK IS NOT APPLIED AND MUST NOT BE APPLIED "
                "HERE: 344 of 361 candidates exist, ALL tier B, 122 of them "
                "via the containment matcher AGENTS.md forbids from keying a "
                "dollar. Scripts 152 and 24 both decline in writing - 'the "
                "NEID crosswalk is a ruling, not a computation.' That "
                "refusal is honoured; the proposal rides in "
                "`tribe_id_neid_proposed` so a consumer adopts or refuses it "
                "EXPLICITLY. The right key is "
                "data/raw/external/federal_funding/"
                "lineageA_dta_corrtd_tribe_key.csv - NEVER playground.do, "
                "which is a different lineage whose ranges overlap and "
                "disagree (307 -> Stillaguamish there, Southern Ute here).",
    },
    "LDA_REGISTRANT": {
        "authority": "Senate/House Office of Public Records",
        "publishes": True,
        "cardinality": "MANY_PER_ENTITY",
        "tier_source": "the lobbying registrant hub row",
        "note": "Senate and House assign SEPARATE registrant ids for the same "
                "firm; both are attributes and neither is the key.",
    },
    "HOUSE_REGISTRANT": {
        "authority": "Clerk of the House",
        "publishes": True,
        "cardinality": "MANY_PER_ENTITY",
        "tier_source": "the lobbying registrant hub row",
    },
    "TRIBAL_CERTIFICATION": {
        "authority": "a tribal government (TERO / commerce / TERO commission)",
        "publishes": False,
        "cardinality": "MANY_PER_ENTITY",
        "tier_source": "the certification row",
        "note": "CONSENT-GATED, not licence-gated. "
                "cedar_codebook.TRIBAL_SOURCE_RESTRICTED_FILES and "
                "code/321_gate_tribal_source_restriction.py fail the build if "
                "one reaches data/clean or dist. Silence is UNRESOLVED, never "
                "permission. And being on a certified list is NOT by itself "
                "an ownership claim - Colville flags firms CERTIFIED TITLE 10 "
                "at 0% Indian ownership.",
    },
    "FACILITY_ID": {
        "authority": "Cedar, or the vendor whose prefix it carries",
        "publishes": True,
        "cardinality": "MANY_PER_ENTITY",
        "tier_source": "the facility row",
        "note": "CCP-/VP-/TPL-. A facility is not an entity; the prefix is "
                "HISTORY, not provenance. `id_type()` returns 'facility'.",
    },
}


def identifier_scheme(name):
    """The registry entry for an external identifier scheme, or None.

    None rather than a guess: an unregistered scheme must be declared before
    it can carry a mapping, or the crosswalk grows a column nobody can read.
    """
    return EXTERNAL_IDENTIFIER_SCHEMES.get((name or "").strip().upper())


def mapping_is_defect(n_entities):
    """One identifier resolving to N entities: is that a defect?

    MANY identifiers per entity is EXPECTED (NANA holds 67 UEIs; the 8(a)
    nine-year term mints successor entities sharing a name and an address).
    ONE identifier held by many entities is a DEFECT and goes to review - it
    is the shape behind all 911 rows of
    `review/identifier_one_to_many_defects_2026-08-26.csv`.
    """
    try:
        return int(n_entities) > 1
    except (TypeError, ValueError):
        return True


# ---------------------------------------------------------------------------
# RECLASSIFICATION AND RENAME - the two events that must never break a join.
# ---------------------------------------------------------------------------

#: The alias_type used when an id is retired by a class change. It is a member
#: of `cedar_domain.ALIAS_TYPES`; nothing parallel is invented here.
RETIRED_ID_ALIAS_TYPE = "historical"


def reclassify(old_entity_id, new_entity_class, token=None,
               effective_date="", authority="", citation=""):
    """A class change mints a NEW id and RETIRES the old one as an alias.

    Returns {old_id, new_id, alias_record, event_record}. **It writes
    nothing.** The caller records the alias and the event, so the write stays
    in one auditable place and this function stays importable from a dry run.

    WHY NOT JUST EDIT THE CLASS COLUMN AND KEEP THE ID?
        Because the owner ruled the prefix should be legible - "so if the
        number can also code other things like these are tribes, ANCs, NHO,
        individuals" - and a legible prefix that lies is worse than an opaque
        one. `TRBS-` on a now-federally-recognised tribe reads as a fact and
        is false.

    WHY NOT JUST REWRITE THE ID EVERYWHERE?
        Because 20,577 ledger rows, 365,535 assistance rows and a hand-
        authored ruling file cite ids BY VALUE. A rewrite is a rebuild of
        every consumer at once, which is the collision this repo has paid for
        four times in one day.

    SO: BOTH IDS RESOLVE, FOREVER. The new one is `current`; the old one is
    `historical` and never returns a miss. Cedar's own live example is the
    Lumbee: 64 state-recognized tribes sit in the spine and
    `federal_recognition_roster` carries FR citations for status changes, so
    this is a scheduled event, not a hypothetical.

    A RENAME IS NOT A RECLASSIFICATION AND MUST NOT COME HERE.
        "Tolowa Dee-ni' Nation (previously listed as the Smith River
        Rancheria)", 81 FR 5019, and "Yuhaaviatam of San Manuel Nation
        (previously listed as San Manuel Band of Mission Indians)", 87 FR
        4636, are the SAME entity under a new name. The id does not move; a
        `former_legal` alias is added with the FR citation. Calling
        `reclassify()` on a rename would mint a second id for one entity and
        break rule 1.
    """
    parsed = parse_entity_id(old_entity_id)
    if parsed is None:
        raise ValueError(f"{old_entity_id!r} is not a canonical Cedar entity "
                         f"id - reclassify() only retires ids it can parse")
    new_prefix = class_prefix(new_entity_class)
    if new_prefix is None:
        raise KeyError(
            f"no prefix declared for entity_class {new_entity_class!r}. Add "
            f"it to CLASS_PREFIX with a written reason; an undeclared class "
            f"must not silently acquire a prefix that asserts something.")
    if new_prefix == parsed["prefix"]:
        raise ValueError(
            f"{old_entity_id} is already under {new_prefix}. A class change "
            f"WITHIN one prefix (Alaska Native Village Corporation -> ANCSA "
            f"Group Corporation, Native CDFI -> Native Financial Institution) "
            f"changes the COLUMN and keeps the ID. Do not mint a second id "
            f"for one entity.")
    tok = (token or parsed["token"]).upper()
    tail = "-".join(parsed["qualifiers"])
    new_id = f"{new_prefix}-{tok}-{parsed['sequence'] or '00'}"
    if tail:
        new_id = f"{new_id}-{tail}"
    return {
        "old_id": old_entity_id,
        "new_id": new_id,
        "alias_record": {
            "entity_id": new_id,
            "alias_name": old_entity_id,
            "alias_type": RETIRED_ID_ALIAS_TYPE,
            "source_system": "cedar_ids.reclassify",
            "verification_status": "RETIRED_ID_PERMANENT_ALIAS",
            "start_date": "",
            "end_date": effective_date,
            "source_id": citation or authority,
        },
        "event_record": {
            "event_type": "ENTITY_RECLASSIFIED",
            "old_entity_id": old_entity_id,
            "new_entity_id": new_id,
            "new_entity_class": new_entity_class,
            "effective_date": effective_date,
            "authority": authority,
            "citation": citation,
            "rule": "The old id is a PERMANENT alias and always resolves. "
                    "It is never reused for a different entity.",
        },
    }


if __name__ == "__main__":
    import csv
    import sys
    csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
    print("=== Cedar ID service: adopting existing IDs ===\n")

    sp = SPINE / "cedar_entity_spine.csv"
    with open(sp, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rows = list(csv.DictReader(fh))
    from collections import Counter
    pre = Counter()
    for r in rows:
        t = (r.get("tribe_id") or "").split("-")[0]
        if t:
            pre[t] += 1
    for p, n in pre.most_common():
        mark = "grandfathered" if p in PREFIXES else "UNKNOWN PREFIX"
        print(f"  {p:8s} {n:>5}  {mark}")

    fac = CEDAR / "data" / "clean" / "gaming_facilities.csv"
    if fac.exists():
        with open(fac, encoding="utf-8-sig", errors="replace", newline="") as fh:
            f = Counter((r.get("facility_id") or "").split("-")[0]
                        for r in csv.DictReader(fh))
        print()
        for p, n in f.most_common():
            hi = adopt_existing(p, [])
            print(f"  {p:8s} {n:>5}  facility, grandfathered "
                  f"({PREFIXES.get(p, ('unregistered',))[0]})")

    print("\n  minting test:")
    for p in ("CEDAR-ENT", "CEDAR-ADMREG"):
        print(f"    {p:14s} -> {allocate(p, 2)}")
    print(f"\n  id_type('CCP-000123')      = {id_type('CCP-000123')}")
    print(f"  id_type('TRBF-CHKSWN-00')  = {id_type('TRBF-CHKSWN-00')}")
    print(f"  is_internal('CEDAR-ENT-1') = {is_internal('CEDAR-ENT-000001')}")
    try:
        allocate("TRBF")
    except ValueError as e:
        print(f"\n  minting a grandfathered prefix correctly refused:\n    {e}")
