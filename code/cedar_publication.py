#!/usr/bin/env python3
"""
Cedar Press - `cedar_publication`: THE publication rules, in one importable place.

    from cedar_publication import NEVER, GATES, FLAGSHIP, PRODUCT_ID, \
                                  DROP_COLS, CUSTOMER_SHELVES, SPINE
    py -3 code/cedar_publication.py verify   # exit 1 if any consumer diverges

WHY THIS FILE EXISTS
--------------------
Owner, 2026-09-02: *"if we can consolidate files to process stuff to make it
easier, fact check - this should be a well oiled machine, not running in
circles over and over again."*

Three scripts write customer-facing extracts - `770_sample_extracts.py`,
`1135_full_dataset_review_bundle.py`, `1137_customer_dataset_combine.py` - and
until this file they agreed about the publication rules by **reading each
other's source code as text**. Five such scrapers were in the tree:

  1. `770._760_product_id_map()`      PRODUCT_ID out of 760
  2. `760._flagship_map()`            FLAGSHIP + SPINE out of 770
  3. `1135._from_770()`               NEVER, GATES out of 770
  4. `1137._from()`                   NEVER, GATES, FLAGSHIP out of 770,
                                      COLLECTIONS out of 500
  5. the product repo's
     `scripts/import_cedar_manifest.py::_flagship_map()`
                                      FLAGSHIP out of 770 - IN ANOTHER BRANCH

Scraper 4 had already failed silently: its regex could not match the annotated
binding `COLLECTIONS: list[dict] = [`, so `shelves()` returned `{}`, every
collection failed the shelf test, and `1137` printed "0 customer shelves" and
**exited 0**. A confident report of nothing.

THE STATED REASON FOR TEXT-SCRAPING IS FALSE, AND THAT IS MEASURED
-------------------------------------------------------------------
Every one of those five scrapers carries the same justification in a comment,
in some variation of:

    "a module name beginning with a digit is not importable, and 770 does file
     work at import time"

**Both halves are wrong.** The `import` STATEMENT cannot name a digit-leading
module; `importlib.util.spec_from_file_location` imports it without complaint.
And `770_sample_extracts.py` does no file work at import: measured
2026-09-02, importing it takes **0.04 s** and touches no table - every read is
inside `main()`, behind `if __name__ == "__main__"`. So the scraping was never
necessary. `_from_numbered()` below is the two-line function that replaces all
of it.

A regex over source text fails OPEN - it returns `{}` or `None` and the caller
decides what to do with nothing. An import fails CLOSED, with a traceback that
names the missing symbol. That difference is the whole argument.

WHAT IS CANONICAL HERE, AND WHAT IS NOT
----------------------------------------
Canonical (hand-maintained, this file is the only copy):

  `NEVER`             row-level withholding: personal data held APART from a
                      public role
  `GATES`             row-level publication gates
  `FLAGSHIP`          the ONE table a customer opens first, per collection
  `SPINE`             flagship tables that live in `data/spine`, not `clean`
  `PRODUCT_ID`        Cedar id -> the product's id, where they differ
  `DROP_COLS`         proprietary identifiers, dropped as COLUMNS not rows
  `CUSTOMER_SHELVES`  which shelves a paying customer sees
  `YEAR_COLS`         the fiscal-year column names, in preference order

Derived (measured elsewhere, exposed here so there is one accessor):

  `shelves()`         collection id -> shelf, from `500.COLLECTIONS`
  `row_ok(row)`       the row gate, applied identically by all three scripts

`shelves()` is deliberately NOT a literal here. `500_build_architecture_map.py`
owns the collection map and adding a duplicate would be the defect this file
exists to remove; what this file owns is the single ACCESSOR, which imports 500
rather than scraping it, and refuses an empty map.

THE ONE PLACE A SECOND COPY IS STILL REQUIRED, AND HOW IT IS GATED
-------------------------------------------------------------------
Consumer 5 above lives in `scripts/import_cedar_manifest.py` on branch
`claude/real-collections-manifest` - the PRODUCT repo. That branch and `master`
are disjoint trees in one repository and never merge, so a change here cannot
reach it. It does `text.find("FLAGSHIP = {")` against `770_sample_extracts.py`
and `raise SystemExit` when the dict is absent. Deleting 770's literal would
therefore break a live consumer.

So `770_sample_extracts.py` keeps a `FLAGSHIP = {...}` literal, and it is
**generated from this file, not maintained beside it**:

    py -3 code/cedar_publication.py sync     # rewrite 770's compat block
    py -3 code/cedar_publication.py verify   # fail if it has drifted

770 asserts the equality at import time as well, so a hand-edit there raises on
the next run rather than shipping a different flagship to the storefront than
the one the samples were drawn from. Two copies, one of them derived, with a
runtime assert and a gate - which is this project's convention for generated
content, not an exception to it.

THE FAILURE MODE THIS FILE MUST NOT HAVE
-----------------------------------------
Guessing. A missing publication rule is not a missing convenience: `GATES`
is what keeps Navajo's 346 restrictive-terms NBOA rows out of a release, and
`NEVER` is what keeps a home address out of one. Every accessor here raises
rather than returning a default. Crashing is cheap; a quiet `{}` that publishes
everything is not.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"

# ---------------------------------------------------------------------------
# ROW-LEVEL PUBLICATION RULES
# ---------------------------------------------------------------------------
# A row carrying any of these is withheld outright.
#
# This is NOT "a table carrying a natural person is refused", and the
# distinction is load-bearing: `lobbying_registrants.csv` publishes STEPHEN
# GRAHAM of Boston MA and that is correct, because an individual may register
# as a lobbyist and the registration IS the public record the Lobbying
# Disclosure Act creates. A lobbying dataset that hid individual registrants
# would be broken. What is refused is a person's data held APART from their
# public role - home address, personal email or phone, date of birth, SSN or
# TIN.
NEVER = ("owner_name_raw", "email", "phone", "home_address", "personal_email",
         "ssn", "tin", "date_of_birth", "officer_name", "contact_name")

# Columns whose presence means the row is gated. Value -> keep only if match.
# The empty string is in every allow-set on purpose: a blank gate column means
# the gate was never evaluated for that row, not that it failed.
GATES = {"publishable": {"Y", "y", "1", "true", "TRUE", ""},
         "source_terms_status": {"SILENT", "TERMS_STATED_NO_REUSE_RESTRICTION",
                                 ""}}

# ---------------------------------------------------------------------------
# COLUMN-LEVEL PUBLICATION RULES
# ---------------------------------------------------------------------------
# Proprietary identifiers: licensed internal-only, never shipped. These drop as
# COLUMNS, not rows - the row is ours, the identifier is not. `casino_city_id`
# is Casino City Press; the D-U-N-S family is Dun & Bradstreet.
#
# Compared case-INSENSITIVELY by every consumer (`c.lower() in DROP_COLS`), so
# every entry here must be lower case or it can never match.
DROP_COLS = ("casino_city_id", "duns", "duns_number", "dnb_duns",
             "ultimate_duns", "parent_duns")

# Fiscal-year column names, in preference order. Used to split an oversized
# table by a column a buyer would have asked for rather than by byte offset.
YEAR_COLS = ("fiscal_year", "fy", "action_date_fiscal_year", "award_fiscal_year",
             "year", "report_year", "filing_year")

# ---------------------------------------------------------------------------
# THE STOREFRONT
# ---------------------------------------------------------------------------
# Shelves a paying customer sees. `grove` goes to Cedar Grove, `infrastructure`
# is the hub, `withdrawn` is the owner's newsletters ruling of 2026-09-02.
CUSTOMER_SHELVES = ("standard", "pro")

# THE PRODUCT'S ID IS NOT ALWAYS CEDAR'S ID, and there is exactly one case.
# `deals` and `contractors` match exactly, which is what made the assumption
# look safe. But the product catalog, launch collection, article wiring,
# profile construction and API tests all call the owned-business collection
# `owned`. Emitting `native-owned-businesses` would leave a READY dataset
# unable to replace the demonstration record it is meant to replace, silently.
PRODUCT_ID = {
    "native-owned-businesses": "owned",
}

# Flagship tables that live in `data/spine/`, not `data/clean/`.
SPINE = {"cedar_identity_register.csv"}

# ---------------------------------------------------------------------------
# THE FLAGSHIP CHOICE - curated, per collection, and stated rather than derived
# ---------------------------------------------------------------------------
# THE TABLE A CUSTOMER WANTS IS NOT THE BIGGEST TABLE. Picking by row count
# chooses `individual_native_exclusion_pairs.csv` for native-owned-businesses -
# an EXCLUSION list, the rows we decided are NOT Native - and a BIE sub-table
# for funding. Both are real and neither is the product.
#
# The per-entry reasoning that used to sit in 770 is preserved here, because
# this is now the only hand-maintained copy.
FLAGSHIP = {
    "contractors":              "prime_contracts.csv",
    "subcontracting":           "subawards.csv",
    "funding":                  "federal_funding_transactions.csv",
    "gaming":                   "gaming_facilities.csv",
    "natural-resources":        "resource_revenue.csv",
    "native-owned-businesses":  "native_owned_businesses.csv",
    "nonprofits":               "np_orgs.csv",
    "deals":                    "deals_classified.csv",
    # 2026-09-02: was `lobbying_registrants.csv`, 653 rows - a REFERENCE LIST
    # of who is registered, not the record of what they did. A buyer of
    # "Lobbying" is asking which filings name their tribe and what was lobbied
    # on, and that is `native_entity_lobbying_disclosures.csv`, 27,825 x 44,
    # "one row per LDA filing attributed to a Native entity".
    "lobbying":                 "native_entity_lobbying_disclosures.csv",
    # 2026-09-02: was `bill_votes.csv`, 423 rows. The collection is
    # "Congressional Votes and Proposed Legislation" and the unit a buyer works
    # in is the BILL - `native_bills.csv`, 3,069 x 29. `member_positions.csv`
    # has 136,119 rows and is the deeper table, but its grain is (roll-call
    # vote, member of Congress), which is an analyst's join target, not the
    # headline row. Picking by size would have chosen it.
    "legislation":              "native_bills.csv",
    "federal-register":         "consultation_events.csv",
    # 2026-09-02: was `fr_nagpra_title_index.csv`, a 10-column list of document
    # numbers and headline strings. The descriptor promises notices "with the
    # institutions and affiliated tribes named in each" and the title index
    # carries neither - both are parsed out and on disk in `nagpra_notices.csv`
    # (6,792 x 67), with `nagpra_notice_entity_bridge.csv` holding 51,579
    # notice->party links of which 48,111 resolve to a Cedar entity. The
    # buyer's first question - "which notices name my tribe?" - had 48,111
    # answers on disk and a sample that could not ask it.
    "nagpra":                   "nagpra_notices.csv",
    # The corpus, not the coverage table: `tribal_newsletter_coverage.csv` is
    # one row per entity PROBED (1,555) and answers "did we look?"; the corpus
    # is one row per channel or absence and answers "what is published?".
    "newsletters":              "tribal_newsletter_corpus.csv",
    "_entity_layer":            "cedar_identity_register.csv",
    # Enterprises, not relations: the relation table is one row per ASSERTION
    # and a buyer's first question is which firms a nation owns, not how many
    # sources said so.
    "nest":                     "nest_enterprises.csv",
}


# ---------------------------------------------------------------------------
# ACCESSORS
# ---------------------------------------------------------------------------
def product_id(did: str) -> str:
    """Cedar's collection id -> the id the product ships it under."""
    return PRODUCT_ID.get(did, did)


def row_ok(r: dict) -> tuple[bool, str]:
    """(publishable, reason). The row gate, applied identically everywhere.

    Returns the REASON, not just a boolean, because every consumer counts
    withholdings per cause in its manifest - a reviewer seeing "342 rows held"
    with no cause cannot tell a licensing gate from a personal-data gate.
    """
    for col, allowed in GATES.items():
        if col in r and (r.get(col) or "").strip() not in allowed:
            return False, col
    for col in NEVER:
        if col in r and (r.get(col) or "").strip():
            return False, "personal:" + col
    return True, ""


def publishable_columns(header) -> list:
    """Header minus the proprietary identifiers. Case-insensitive, as every
    consumer already compared them."""
    return [c for c in header if c.lower() not in DROP_COLS]


def _from_numbered(stem: str):
    """Import a `code/<digits>_<name>.py` module.

    The `import` statement cannot name it; `importlib` can. This is what
    replaces five regex scrapers, and it is the whole of the replacement.
    """
    path = CODE / stem
    if not path.exists():
        raise SystemExit(f"cedar_publication: {path} is absent - refusing to "
                         f"guess what it declares")
    spec = importlib.util.spec_from_file_location(
        "cedarnum_" + re.sub(r"\W", "_", stem), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_SHELVES: dict = {}


def shelves() -> dict:
    """collection id -> shelf, from `500_build_architecture_map.COLLECTIONS`.

    500 owns the collection map; restating it here would be the duplication
    this module exists to remove. What lives here is the single accessor.

    Refuses to return an empty map. `1137`'s regex version could not match the
    annotated binding `COLLECTIONS: list[dict] = [`, returned `{}`, and the
    build reported "0 customer shelves" and exited 0. An import cannot fail
    that way - it raises on the missing name - and this raises anyway if the
    map is somehow empty, because guessing the shelf assignment would ship the
    wrong storefront.
    """
    global _SHELVES
    if _SHELVES:
        return dict(_SHELVES)
    cols = getattr(_from_numbered("500_build_architecture_map.py"),
                   "COLLECTIONS", None)
    if not cols:
        raise SystemExit("cedar_publication: 500 declares no COLLECTIONS - "
                         "the shelf assignment decides which datasets a "
                         "customer sees, and guessing it would ship the wrong "
                         "storefront")
    _SHELVES = {c["id"]: c.get("shelf") for c in cols}
    return dict(_SHELVES)


def customer_collections() -> list:
    """The collections a paying customer sees, sorted. Twelve, today."""
    sh = shelves()
    return sorted(c for c, s in sh.items() if s in CUSTOMER_SHELVES)


# ---------------------------------------------------------------------------
# THE 770 COMPATIBILITY BLOCK - generated, gated, never hand-edited
# ---------------------------------------------------------------------------
COMPAT_FILE = CODE / "770_sample_extracts.py"
COMPAT_BEGIN = "# <<< BEGIN GENERATED FLAGSHIP COMPAT (cedar_publication.py sync)"
COMPAT_END = "# >>> END GENERATED FLAGSHIP COMPAT"


def _compat_block() -> str:
    """The literal the product repo's importer scrapes, rendered from FLAGSHIP.

    Shape matters, not prettiness. Three consumers parse this text and each
    wants something slightly different, so the block satisfies all three:

      * `FLAGSHIP = {` on one line          - `str.find` in 760 and in the
                                              product repo's importer
      * `"key": "value",` one pair per line - the `re.findall` in both
      * a bare `}` at column 0              - `text.find("\\n}")` bounds the body

    Keys are emitted in FLAGSHIP's declaration order so `sync` is idempotent.
    """
    lines = [COMPAT_BEGIN,
             "# Generated from `FLAGSHIP` in `code/cedar_publication.py`. DO NOT EDIT:",
             "# run `py -3 code/cedar_publication.py sync`. It exists because the",
             "# product repo's `scripts/import_cedar_manifest.py` reads this dict out of",
             "# THIS FILE by text, from a branch that never merges with master, so the",
             "# literal cannot be deleted. `verify` fails if it drifts from the module.",
             "FLAGSHIP = {"]
    for k, v in FLAGSHIP.items():
        lines.append(f'    "{k}": "{v}",')
    lines.append("}")
    lines.append(COMPAT_END)
    return "\n".join(lines)


def _compat_current() -> str | None:
    if not COMPAT_FILE.exists():
        return None
    txt = COMPAT_FILE.read_text(encoding="utf-8")
    i = txt.find(COMPAT_BEGIN)
    j = txt.find(COMPAT_END, i)
    if i < 0 or j < 0:
        return None
    return txt[i:j + len(COMPAT_END)]


def sync() -> int:
    cur = _compat_current()
    want = _compat_block()
    if cur is None:
        print(f"  FAIL {COMPAT_FILE.name} carries no compat markers; add them "
              f"once by hand, then `sync` maintains the block.")
        return 1
    if cur == want:
        print("  compat block already current; nothing written.")
        return 0
    COMPAT_FILE.write_text(
        COMPAT_FILE.read_text(encoding="utf-8").replace(cur, want),
        encoding="utf-8")
    print(f"  rewrote the FLAGSHIP compat block in {COMPAT_FILE.name}")
    return 0


# ---------------------------------------------------------------------------
# VERIFY - fail if any consumer has diverged
# ---------------------------------------------------------------------------
CONSUMERS = ("770_sample_extracts.py",
             "1135_full_dataset_review_bundle.py",
             "1137_customer_dataset_combine.py")

# Names every consumer must resolve to the value here, if it defines them at
# all. A consumer that does not define one is fine; a consumer that defines a
# DIFFERENT one is the failure this gate exists for.
SHARED = ("NEVER", "GATES", "FLAGSHIP", "PRODUCT_ID", "DROP_COLS",
          "CUSTOMER_SHELVES", "SPINE", "YEAR_COLS")


def verify() -> int:
    bad = []
    here = globals()

    # 1. Every consumer that names a shared constant must hold THIS value.
    for stem in CONSUMERS:
        try:
            mod = _from_numbered(stem)
        except SystemExit as e:
            bad.append(f"{stem}: will not import - {e}")
            continue
        except Exception as e:
            bad.append(f"{stem}: import raised {type(e).__name__}: {e}")
            continue
        for name in SHARED:
            if not hasattr(mod, name):
                continue
            got, want = getattr(mod, name), here[name]
            if got != want:
                bad.append(f"{stem}.{name} DIVERGED from cedar_publication."
                           f"{name}\n         theirs: {got!r}\n         ours:   {want!r}")

    # 2. No consumer may still be scraping another script's source for a rule.
    #    A live scraper is how the rules drifted in the first place, and it
    #    fails open - `{}` or `None` - which is why it must be gone, not merely
    #    unused.
    scrape = re.compile(r"read_text\([^)]*\)[\s\S]{0,400}?"
                        r"(?:FLAGSHIP|NEVER|GATES|PRODUCT_ID|COLLECTIONS)")
    for stem in CONSUMERS + ("760_collection_descriptors.py",):
        p = CODE / stem
        if not p.exists():
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        for m in scrape.finditer(txt):
            line = txt[:m.start()].count("\n") + 1
            bad.append(f"{stem}:{line} still reads a publication rule out of "
                       f"another script by text; import cedar_publication instead")

    # 3. The generated compat block must match the module.
    cur = _compat_current()
    if cur is None:
        bad.append(f"{COMPAT_FILE.name}: FLAGSHIP compat markers are missing - "
                   f"the product repo's importer scrapes that literal and will "
                   f"SystemExit without it")
    elif cur != _compat_block():
        bad.append(f"{COMPAT_FILE.name}: the generated FLAGSHIP compat block has "
                   f"DRIFTED from cedar_publication.FLAGSHIP - run "
                   f"`py -3 code/cedar_publication.py sync`")

    # 4. The compat block must still satisfy the two scrapers we cannot change:
    #    760's, and the product repo's. Both are `str.find` + `re.findall`, and
    #    both `raise SystemExit` on an empty parse. Run their exact expressions.
    if cur is not None:
        txt = COMPAT_FILE.read_text(encoding="utf-8")
        i = txt.find("FLAGSHIP = {")
        if i < 0:
            bad.append("770: `FLAGSHIP = {` not findable - the product repo's "
                       "import_cedar_manifest.py raises SystemExit on this")
        else:
            # the product repo's parse
            body = txt[i + len("FLAGSHIP = {"):txt.find("\n}", i)]
            prod = dict(re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', body))
            if prod != FLAGSHIP:
                bad.append(f"770: the product repo's scrape yields {len(prod)} "
                           f"entries, FLAGSHIP has {len(FLAGSHIP)} - the "
                           f"storefront would ship a different flagship than "
                           f"the samples were drawn from")
            # 760's parse
            body760 = txt[i:txt.find("\n}", i)]
            c760 = dict(re.findall(r'"([a-z0-9_\-]+)":\s*"([a-z0-9_]+\.csv)"',
                                   body760))
            if c760 != FLAGSHIP:
                bad.append(f"770: 760's scrape yields {len(c760)} entries, "
                           f"FLAGSHIP has {len(FLAGSHIP)}")

    # 5. The shelf map must resolve, and to the twelve the owner ruled.
    try:
        cust = customer_collections()
    except SystemExit as e:
        bad.append(f"shelves(): {e}")
        cust = []
    if cust and len(cust) != 12:
        bad.append(f"{len(cust)} customer collections on shelves "
                   f"{CUSTOMER_SHELVES}, expected 12: {cust}")

    # 6. Every collection on a customer shelf must name a flagship, or 1137
    #    ships an empty dataset that looks finished.
    for c in cust:
        if c not in FLAGSHIP:
            bad.append(f"{c}: on a customer shelf and FLAGSHIP names no table")

    # 7. DROP_COLS is compared case-insensitively by every consumer, so an
    #    upper-case entry could never match and would silently ship.
    for c in DROP_COLS:
        if c != c.lower():
            bad.append(f"DROP_COLS entry {c!r} is not lower case; every "
                       f"consumer compares `col.lower() in DROP_COLS`, so it "
                       f"can never match")

    for b in bad:
        print("  FAIL " + b)
    print(f"  cedar_publication verify   {'FAIL' if bad else 'PASS'}   "
          f"{len(bad)} problem(s); {len(CONSUMERS)} consumers, "
          f"{len(SHARED)} shared constants, {len(cust)} customer collections")
    return 1 if bad else 0


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "show"
    if mode == "verify":
        return verify()
    if mode == "sync":
        return sync()
    print("  cedar_publication - the publication rules, in one place")
    print(f"    NEVER            : {len(NEVER)} columns")
    print(f"    GATES            : {', '.join(sorted(GATES))}")
    print(f"    DROP_COLS        : {len(DROP_COLS)} proprietary identifiers")
    print(f"    FLAGSHIP         : {len(FLAGSHIP)} collections")
    print(f"    PRODUCT_ID       : {PRODUCT_ID}")
    print(f"    CUSTOMER_SHELVES : {CUSTOMER_SHELVES}")
    try:
        print(f"    customer datasets: {len(customer_collections())} "
              f"({', '.join(customer_collections())})")
    except SystemExit as e:
        print(f"    customer datasets: UNRESOLVED - {e}")
    print("\n  `verify` gates divergence; `sync` regenerates 770's compat block.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
