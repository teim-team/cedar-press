#!/usr/bin/env python3
"""
Cedar Press - PRIMARY KEYS. The one place a row identity is minted or judged.

WHY THIS FILE EXISTS
--------------------
`ferc_filing_id`'s last segment is `abs(hash(filer_organization)) % 10000`
(`133_build_ferc_advocacy.py:1833`). **Python randomises string hashing per
process** unless `PYTHONHASHSEED` is pinned, so the same FERC document gets a
different id in every build. Measured across the 2026-08-12 and 2026-08-26
files: **4 of 2,534 shared documents kept their id.**

Nothing joined on it, so nothing broke - which is exactly why it survived. A
database keyed on that column corrupts on the next rebuild, silently, and the
corruption looks like new rows rather than like an error.

The related defect is not about hashing at all. `verification_id = INV-{rank:04d}`
in `170_build_individual_native_candidates.py:482` is assigned in descending
obligation order. A concurrent agent rewrote `prime_contracts.csv`, every rank
below the change shifted by one, and **INV-0307 silently acquired another
firm's ownership sentence** (`171_build_individual_native_verification.py:338`).

    THE RULE THAT COVERS BOTH:
    A KEY MAY NEVER DEPEND ON ANYTHING OUTSIDE THE ROW ITSELF.
    Not the process (`hash()`, `uuid4()`, `id()`), not the row's position in a
    file (`enumerate`), not its rank among other rows (`sorted(...)[i]`), and
    not the iteration order of a `set` or a pre-3.7 `dict`.
    NEVER JOIN TWO ARTEFACTS ON A RANK when either derives from a file another
    agent can write.

WHAT A GOOD KEY LOOKS LIKE HERE
-------------------------------
1. **Natural.** Columns the SOURCE assigned, that are unique and non-null.
   `(docket_number, accession_number, filer_organization_as_recorded)` for a
   FERC filing. Preferred always: it survives a rebuild because it never
   depended on the build.
2. **Deterministic surrogate.** Where no natural key exists, a stable digest
   of stated columns - `surrogate_id()` below. Same inputs, same id, forever,
   in any process, on any machine. `hashlib`, never `hash()`.
3. **Privacy surrogate.** Where the natural key is a pointer to a natural
   person, the digest is the ONLY published key and the natural key never
   leaves the building. `cedar_domain` already reasons this through for
   individually Native-owned firms: SAM's public entity search resolves a UEI
   to a name and an address, so for a firm whose legal name IS a person's
   name the UEI publishes that person by one hop. That policy is IMPORTED
   here, not restated.

USAGE

    from cedar_keys import surrogate_id, stable_digest, key_for, KeyError_

    surrogate_id("FERCFIL", row, ("docket_number", "accession_number",
                                  "filer_organization_as_recorded"))
    #  -> 'FERCFIL-3f2a91c0d4e18b76'

The registry of discovered keys is GENERATED - `docs/schema/keys.json`, written
by `284_audit_nondeterministic_keys.py` - because a hand-maintained list of 275
tables is a list that goes stale. This module holds only the digest primitives
and the hand-ruled overrides that no scan can infer.

Claimed 2026-08-26 with script numbers 284-292.
"""

import hashlib
import json
import re
import unicodedata
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
SCHEMA_DIR = CEDAR / "docs" / "schema"
KEYS_JSON = SCHEMA_DIR / "keys.json"

DIGEST_BYTES = 8          # 16 hex chars. 2^64 space; collision-tested on load.
DIGEST_SEP = "\x1f"       # ASCII unit separator: cannot occur in a CSV cell.


class UnstableKey(Exception):
    """Raised when a key would depend on something outside the row."""


# ---------------------------------------------------------------------------
# THE PRIMITIVES
# ---------------------------------------------------------------------------

_WS = re.compile(r"\s+")


def normalise(value) -> str:
    """Canonical text form of one key part.

    Deliberately conservative. Case-folded and whitespace-collapsed, because
    `"Southern Ute Indian Tribe "` and `"SOUTHERN UTE INDIAN TRIBE"` are the
    same filer and the sources disagree about both. NFKC-normalised because
    the FERC and NIGC scrapes carry non-breaking spaces and typographic
    dashes that a byte comparison would split.

    NOT stripped of punctuation: `P-2232` and `P2232` are different dockets
    and collapsing them would merge two real rows into one.
    """
    s = "" if value is None else str(value)
    s = unicodedata.normalize("NFKC", s)
    s = _WS.sub(" ", s).strip()
    return s.casefold()


def stable_digest(parts, n_bytes=DIGEST_BYTES) -> str:
    """Deterministic hex digest of an ordered sequence of key parts.

    blake2b, not `hash()`. Same answer in every process, every build, every
    machine, forever. That is the entire point and it is the property
    `hash()` does not have.

    The separator is ASCII 0x1F, which cannot appear in a CSV cell, so
    `("ab", "c")` and `("a", "bc")` cannot collide by concatenation - a real
    failure mode when one part is an empty string.
    """
    if isinstance(parts, (str, bytes)):
        raise TypeError(
            "stable_digest takes a SEQUENCE of parts, not a single string - "
            "passing a joined string makes the separator guarantee void")
    material = DIGEST_SEP.join(normalise(p) for p in parts)
    return hashlib.blake2b(material.encode("utf-8"),
                           digest_size=n_bytes).hexdigest()


def surrogate_id(prefix, row, columns, n_bytes=DIGEST_BYTES) -> str:
    """A deterministic surrogate primary key for `row`, built from `columns`.

    `prefix` names the table so two tables' surrogates can never be confused
    for one another in a join - the failure `cedar_ids.id_type` exists to
    prevent, applied to row keys.

    Raises `UnstableKey` if EVERY stated column is blank: a digest of nothing
    is the same digest for every such row, which is a duplicate key wearing a
    hash. Callers must handle the blank-row case explicitly rather than
    receive a plausible-looking id for it.
    """
    vals = [row.get(c, "") for c in columns]
    if not any(normalise(v) for v in vals):
        raise UnstableKey(
            f"{prefix}: every key column is blank ({', '.join(columns)}). "
            f"A digest of nothing collides with every other blank row.")
    return f"{prefix}-{stable_digest(vals, n_bytes)}"


def verify_unique(rows, columns, label=""):
    """Is `columns` actually a key over `rows`? Returns (ok, n, n_distinct,
    n_null_or_blank, examples_of_duplicates).

    Uniqueness is the claim a primary key makes. Asserting one without
    measuring it is how `07j`/`07k`/`07l` shipped as stubs - a declared
    property nobody computed.
    """
    seen, dupes, blanks = {}, [], 0
    n = 0
    for r in rows:
        n += 1
        vals = tuple(normalise(r.get(c, "")) for c in columns)
        if not any(vals):
            blanks += 1
            continue
        if vals in seen:
            if len(dupes) < 5:
                dupes.append(vals)
        else:
            seen[vals] = 1
    return (not dupes and blanks == 0), n, len(seen), blanks, dupes


# ---------------------------------------------------------------------------
# HAND-RULED OVERRIDES
#
# Everything a scan CAN infer lives in the generated docs/schema/keys.json.
# What lands here is what no scan can know: a measured defect, a recorded
# workaround, a privacy judgement.
# ---------------------------------------------------------------------------

#: table -> {column: ruling}. A column named here MUST NOT be a primary key,
#: MUST NOT be a foreign key, and MUST NOT be joined on - in this repo or in
#: any database built from it.
NON_DETERMINISTIC_COLUMNS = {
    "ferc_docket_filings.csv": {
        "ferc_filing_id": {
            "cause": "WAS abs(hash(filer_organization)) % 10000",
            "producer": "133_build_ferc_advocacy.py:1832",
            "why_unstable": "Python randomises string hashing per process "
                            "(PYTHONHASHSEED); the same document got a new "
                            "id in every build",
            "measured": "4 of 2,534 documents shared between the 2026-08-12 "
                        "and 2026-08-26 files kept their id",
            "fixed_on": "2026-08-26",
            "fixed_by": "327_migrate_class7_keys_to_digests.py - the live "
                        "table was migrated in place and 133 now mints "
                        "surrogate_id('FERCFIL', row, key_columns). The "
                        "instability is GONE.",
            "key_columns": ["docket_number", "subdocket", "accession_number",
                            "filer_organization_as_recorded",
                            "document_description_verbatim"],
            "STILL_FORBIDDEN_AS_A_KEY": True,
            "why_still_forbidden":
                "FOR A DIFFERENT REASON THAN BEFORE, and the reason is worth "
                "keeping: the column is now STABLE but NOT UNIQUE. 769 groups "
                "covering 1,758 rows share a key - 989 excess rows - and each "
                "of those rows is identical to its twin on EVERY other column "
                "up to case and whitespace. They are the same eLibrary "
                "document recorded twice, and the process hash had been "
                "masking that duplication behind 855 collisions of its own. "
                "The column is a stable CONTENT identity: load and diff on "
                "it, never make it a foreign-key target, until the duplicate "
                "rows are resolved at source.",
            "join_instead": ["docket_number", "subdocket", "accession_number",
                             "filer_organization_as_recorded",
                             "document_description_verbatim"],
            "severity": "BLOCKING",
        },
    },
}

#: Columns that WERE in NON_DETERMINISTIC_COLUMNS and are now sound. Kept as a
#: record - deleting the entry deletes the reasoning, and the next reader would
#: have no way to tell "never had this defect" from "had it and it was fixed".
REPAIRED_COLUMNS = {
    "earmarks.csv": {
        "earmark_id": {
            "cause": "abs(hash(p.stem)) % 10**6 in the EXPLANATORY-statement "
                     "branch, and a positional counter in the H and S "
                     "branches - three sites, three different broken schemes "
                     "writing one column",
            "producer": "99_build_earmarks_and_schedc.py:1626,1661,1887",
            "why_unstable": "the same PYTHONHASHSEED defect as "
                            "ferc_filing_id, found 2026-08-26 by "
                            "284_audit_nondeterministic_keys.py and NOT "
                            "previously recorded anywhere",
            "fixed_on": "2026-08-26",
            "fixed_by": "327_migrate_class7_keys_to_digests.py - all three "
                        "sites now mint surrogate_id('EMK', row, "
                        "key_columns) and the live table was migrated.",
            "key_columns": ["fiscal_year", "chamber", "requesting_member",
                            "recipient_name", "project_title",
                            "amount_enacted", "source_url", "source_quote"],
            "why_those_columns":
                "the six-column form this file previously recommended leaves "
                "7 collisions over 1,002 rows - one member requesting the "
                "same project twice in one year is real, and both rows are "
                "real. Adding source_url and source_quote makes it unique "
                "with 0 blanks. It is a WIDE key: an identity for the row's "
                "CONTENT, which changes if any of those values is corrected.",
            "severity": "RESOLVED",
        },
    },
}

#: table -> {column: ruling}. Rank- or position-derived. Stable only while
#: the producing input is byte-identical, which on a machine with live agents
#: is not a property anyone can rely on. Lesser than the above - the id does
#: not change every process - but it is still not a key.
RANK_DERIVED_COLUMNS = {
    "individual_native_firm_register.csv": {
        "verification_id": {
            "cause": "INV-{rank:04d}, assigned in descending obligation order",
            "producer": "170_build_individual_native_candidates.py:482",
            "why_unstable": "a concurrent agent rewrote prime_contracts.csv, "
                            "every rank below the change shifted by one, and "
                            "INV-0307 briefly carried another firm's "
                            "ownership sentence",
            "recorded_at": "171_build_individual_native_verification.py:338",
            "join_instead": "SEE PRIVACY_SURROGATE - this table may not be "
                            "keyed on its natural key either",
            "severity": "BLOCKING",
        },
    },
}

#: Tables whose NATURAL key is a pointer to a natural person. The published
#: key is a deterministic surrogate; the natural key stays internal.
#:
#: The reasoning is NOT restated here - it is `cedar_domain`'s, and this is a
#: pointer to it so the two cannot drift:
#:   cedar_domain.INDIVIDUAL_NATIVE_WITHHELD_FIELDS  (awardee_uei, cage_code)
#:   cedar_domain.may_publish_individual_native_field
#:   cedar_domain.INDIVIDUAL_NATIVE_PUBLISHABLE_FIELDS -> 'surrogate_entity_id'
PRIVACY_SURROGATE = {
    "individual_native_firm_register.csv": {
        "natural_key_internal": ["awardee_uei"],
        "published_key": "surrogate_entity_id",
        "prefix": "INF",
        "policy": "cedar_domain.may_publish_individual_native_field",
        "why": "SAM's public entity search resolves a UEI to a legal name and "
               "a street address. For a firm whose legal name IS a person's "
               "name, publishing the UEI publishes the person by one hop. "
               "cedar_domain already withholds awardee_uei and cage_code for "
               "exactly this reason; the primary key must obey the same rule "
               "or it reintroduces what the field policy removed.",
        "salt": None,
        "salt_note": "NO SALT. A salt that is not persisted makes the key "
                     "non-deterministic - the defect this module exists to "
                     "kill. A salt that IS persisted is recoverable by "
                     "anyone holding the file. The protection here is that "
                     "the UEI column never ships, not that the digest is "
                     "secret; say so plainly rather than implying more.",
    },
    "individual_native_firm_contracts.csv": {
        "natural_key_internal": ["awardee_uei", "piid",
                                 "modification_number"],
        "published_key": "surrogate_entity_id",
        "prefix": "INF",
        "policy": "cedar_domain.may_publish_individual_native_field",
        "why": "same one-hop exposure; the contract facts publish, the "
               "identifier that resolves to a person does not",
        "salt": None,
    },
}


def publishable_key_for(table, discovered=None):
    """The key a DATABASE should use for `table`, with the reason.

    Returns a dict: {kind, columns, prefix, note}. `kind` is one of
    'natural', 'deterministic_surrogate', 'privacy_surrogate', 'BLOCKED'.

    Order of precedence is deliberate: a privacy ruling outranks a natural
    key, and a non-determinism ruling outranks everything - a table whose
    only candidate key is unstable is BLOCKED, not "good enough for now".
    """
    t = Path(str(table)).name
    if t in PRIVACY_SURROGATE:
        p = PRIVACY_SURROGATE[t]
        return {"kind": "privacy_surrogate",
                "columns": p["natural_key_internal"],
                "published_as": p["published_key"],
                "prefix": p["prefix"],
                "note": p["why"]}
    disc = (discovered or load_discovered()).get(t)
    if disc and disc.get("natural_key"):
        return {"kind": "natural", "columns": disc["natural_key"],
                "published_as": None, "prefix": None,
                "note": disc.get("evidence", "")}
    if disc and disc.get("surrogate_from"):
        return {"kind": "deterministic_surrogate",
                "columns": disc["surrogate_from"],
                "published_as": disc.get("surrogate_column",
                                         "cedar_row_key"),
                "prefix": disc.get("prefix"),
                "note": disc.get("evidence", "")}
    return {"kind": "BLOCKED", "columns": [], "published_as": None,
            "prefix": None,
            "note": "no unique, non-null column combination was found; "
                    "this table cannot be ingested until one is declared"}


_DISCOVERED = None


def load_discovered(path=None):
    """The generated key registry. Empty dict if 284 has not run."""
    global _DISCOVERED
    if _DISCOVERED is None or path:
        p = Path(path or KEYS_JSON)
        if p.exists():
            _DISCOVERED = json.loads(p.read_text(encoding="utf-8")).get(
                "tables", {})
        else:
            _DISCOVERED = {}
    return _DISCOVERED


def is_forbidden_join_column(table, column):
    """True if joining on this column is a known corruption path."""
    t, c = Path(str(table)).name, (column or "").strip()
    for reg in (NON_DETERMINISTIC_COLUMNS, RANK_DERIVED_COLUMNS):
        if c in reg.get(t, {}):
            return True, reg[t][c]
    return False, None


if __name__ == "__main__":
    print("=== cedar_keys self-test ===\n")
    row = {"docket_number": "P-2232", "accession_number": "20190401-5123",
           "filer_organization_as_recorded": "  Southern Ute Indian Tribe "}
    cols = ["docket_number", "accession_number",
            "filer_organization_as_recorded"]
    a = surrogate_id("FERCFIL", row, cols)
    row2 = dict(row, filer_organization_as_recorded="SOUTHERN UTE INDIAN TRIBE")
    b = surrogate_id("FERCFIL", row2, cols)
    print(f"  surrogate_id           -> {a}")
    print(f"  case/space variant     -> {b}")
    print(f"  stable under normalise -> {a == b}")
    print(f"  separator guarantee    -> "
          f"{stable_digest(['ab', 'c']) != stable_digest(['a', 'bc'])}")
    try:
        surrogate_id("X", {"a": "", "b": "  "}, ["a", "b"])
    except UnstableKey as e:
        print(f"  all-blank row refused  -> {str(e)[:60]}...")
    try:
        stable_digest("already joined")
    except TypeError as e:
        print(f"  joined string refused  -> {str(e)[:60]}...")
    bad, why = is_forbidden_join_column("ferc_docket_filings.csv",
                                        "ferc_filing_id")
    print(f"\n  ferc_filing_id forbidden -> {bad} ({why['severity']})")
    print(f"  join instead on          -> {why['join_instead']}")
    print(f"\n  discovered registry: {len(load_discovered())} tables "
          f"({'run 284 first' if not load_discovered() else 'loaded'})")
