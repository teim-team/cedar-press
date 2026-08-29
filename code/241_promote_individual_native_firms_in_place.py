#!/usr/bin/env python3
r"""
Cedar Press - 241: create the individually Native-owned FIRM entity class and
promote the owner's 45 rulings into the spine IN PLACE.

THE DEFECT
----------
`AGENTS.md` ruled this class into existence on **2026-08-07**:

    Elijah, on Hidden Water Inc: "individual Native American owned - to the
    extent we identify individual native owned businesses might as well add
    them as a category, and if people want to be added gives them a
    centralized source to do so."

**It never reached the spine.** Nineteen days later the class exists in three
documents, a 45-row ruling table and a 335-row verification table, and in
**zero** rows of `data/spine/cedar_entity_spine.csv`.

Measured on this repo before this script ran:

    owner's individual-Native rulings                          45
      ...UEI-keyed                                             40
      ...carrying a retrieved evidence URL                     36
      ...matching a row in cedar_identifier_ledger_final.csv   42   (X 33, C 9)
      ...with a BLANK tribe_id                                 40
    prime_contracts.csv rows reached by those rulings      16,910
      ...every one attributed_flag = 0, tier C, tribe_id blank
      ...obligations                              $2,340,066,582.34
      ...fiscal years                                     FY2000-2022

That is the largest single body of the owner's own hand work going unused, and
it is the SAME failure as the NHOs - 218 registered, 31 in the spine - which
`code/163_promote_nho_universe_in_place.py` fixed the same way this does.

A discard pile is what a ruled category looks like when nobody built it a home.

WHAT THIS SCRIPT DOES NOT DO, AND WHY
--------------------------------------
1. **It does not run `01_build_entity_spine.py`.** That rebuilds from a stale
   upstream and drops every appended entity - the village corporations, NHOs,
   TCUs, CDFIs, BIE schools and UIOs. It is exactly how the NHOs were lost.
   Everything here is written IN PLACE, on the `124_apply_rulings_in_place.py`
   pattern: back up, write `.part`, rename, re-read to verify.
2. **It does not run `09_import_rulings.py`, `41_build_codebooks.py` or
   `88_build_deals_taxonomy.py`.** All three are global rebuilds on the
   do-not-run list.
3. **It seeds from the 45 RULINGS, not from the 305 candidates.**
   A ruling is evidence. A candidate is a question. Seeding from the candidates
   would make the first version of the class large and indefensible instead of
   small and defensible, and a SAM self-certification is not evidence of
   anything but a filing (see below).

   **A RULING IS NOT TIER A BECAUSE ITS METHOD IS "RULED".** That framing is
   wrong and it is expensive. `elijah_ruling` is in
   `cedar_domain.RULED_METHODS` whether the owner said YES or NO, so method
   membership answers *"did a human decide?"* and says nothing about *what*
   they decided. `148_resolve_schedule_i_recipients.py` wrote
   `tier = "A" if method in RULED` and published **317 of the owner's tier-X
   EXCLUSIONS as tier-A attributions** - at the only publishable tier. The
   count was first believed to be 42.

   So the tier here comes from the ruling's **OUTCOME**, through the exhaustive
   `RULING_OUTCOME` map below, and is inherited verbatim wherever the source
   carries a tier column. `tier_source` records which happened, on every row.
   An unrecognised outcome ABORTS. `status` says a ruling was processed;
   `outcome` says what it decided - an agent has already resolved onto a ruling
   whose `status` was `SETTLED` and whose `outcome` was `HOLD_OVER_OWNER`,
   text "HOLD - RETRACTION REQUIRED".

   This script's input is a curated positive-ruling file, so today either
   reading gives the same answer. **That is a property of the INPUT, not of
   this code**, and the individually-Native space is full of negative rulings -
   including the five that read "Not a Native entity - individually
   Native-owned firm". Widen the input to a mixed file and the branch on
   OUTCOME is the only thing that still holds.
4. **It does not touch `prime_contracts.csv`.** Two reasons, and the second is
   the important one. (a) It is the most-rebuilt file in the repo and an
   in-place enricher on it is the documented rebuild/in-place collision, now on
   its fourth instance. (b) `attributed_flag` and the $244.77B attributed total
   are the flagship figure, and writing this class into them would inflate a
   published number by summing two classes that must NEVER be summed. The
   dollars are rolled up in their own class-scoped table by `code/242`.

THE SCHEMA, AND THE FOUR RULES THAT KEEP TRIBAL ATTRIBUTION CORRECT
--------------------------------------------------------------------
Every one of these is imported from `cedar_domain`, never re-typed here.

* **The class is the FIRM, never the person.** A person has no federal
  identifier and their name is not one. The key is a Cedar-minted surrogate,
  `CEDAR-ENT-nnnnnn`, allocated through `cedar_ids.allocate()` under the file
  lock. Deliberately NOT a mnemonic slug: `INDV-GANJEROB-00` built from a
  person's name IS the disclosure, minted into the primary key of every
  downstream join. The prefix is already registered and `cedar_ids.is_internal`
  already answers True for it, so no new prefix decision is pre-empted - RULE
  NEEDED #1 in the class proposal stays open, and the surrogate requirement is
  satisfied either way it is answered.
* `parent_native_entity` is **permanently NULL** and `ultimate_parent_entity_id`
  is the entity's **own** id. `ownership_basis` says the blank is a RULING and
  not unfinished research - the distinction the 56 federally operated BIE
  schools needed.
* **No `bears_ownership()` edge exists in either direction.**
  `cedar_domain.individual_native_refusal_reason()` refuses the class by name,
  and the assertion is executed in `guard_no_ownership_edge()` below, so the
  rule is enforced by code rather than by memory.
* `owner_self_identifies_with` is added to `cedar_domain.NEVER_OWNERSHIP`.
  *"owned by individual Cherokees"* - 38 of the 45 rulings - is an attribute of
  a PERSON. It never keys a `tribe_id`, and `owner_tribal_affiliation_named`
  stays free text forever. Resolving it is what would break it: "Cherokee"
  names three federally recognised tribes and a long tail of unrecognised
  groups.

READ THIS BEFORE YOU READ ANY RULING IN THIS CLASS
---------------------------------------------------
**Five of the owner's rulings read, verbatim: "Not a Native entity -
individually Native-owned firm."** That refuses the TRIBAL LINK. It does not
say the firm is not Native-owned - the second half of the sentence says the
opposite.

It has already been read literally once and the damage is on disk. `09`'s
`NOT_NATIVE_RE` matched the leading clause, and the ledger carries:

    CAGE 9DVK5  SAN JUAN SERVICES LLC
        confidence_tier = X
        tribe_id        = TRBF-SNJUAN-00        <- a tribe that does not own it
        entity_class    = FEDERAL_TRIBE_LOWER48
        tier_rationale  = "Ruled by Elijah 2026-08-12: not a Native entity"

    CAGE 9H8M8  FOUR CORNER PEST CONTROL LLC -> TRBF-TEMOAK-00, same shape

The refusal was recorded as its own opposite, **on the very tribal binding the
ruling was refusing**. Those two rows are REPOINTED here, loudly, and the
repointing is declared up front so that a refusal which fails to fire aborts
the run - a refusal that does not fire reads exactly like a decision that was
applied. Everything else in the ledger belonging to another pass is reported,
never silently corrected.

SELF-CERTIFICATION LIVES IN ITS OWN COLUMN AND IS NEVER A VERDICT
------------------------------------------------------------------
Measured: **`americanIndianOwned = YES` on 2,846 of 8,273 rows of the TRIBAL
SAM extract** - rows that are tribal enterprises - so the flag does not
separate individual from entity ownership. And **$140.00B of the $244.77B
attributed (57.2%) carries no Native set-aside at all**, so absence of a flag
is not evidence against. 22 of the 40 prior-ruled firms carry ZERO native flags
on any contract row; the largest, Frontier Electronic Systems, on 998 rows and
$204,225,019. `sam_self_certification` is therefore a discovery channel with a
documented blind spot, recorded beside the verdict and never folded into it.

Absence is `NO_CLAIM_FOUND`. **There is no `NOT_NATIVE` value in this schema**
and `assert_no_forbidden_absence_value()` refuses to write one.

PRIVACY - A SECOND RESTRICTION, INDEPENDENT OF D&B
---------------------------------------------------
It survives any answer to the licensing question. A sole proprietorship's legal
name is frequently a private person's name; **even in the TRIBAL extract, 8 of
402 UEIs are unambiguous personal names** with street addresses.

    MAY publish      contract facts, class totals, distributions
    MAY NOT publish  legal/DBA/owner name, address, any person<->ancestry
                     pairing, AND THE UEI where the name is a person's -
                     SAM's public search resolves a UEI to that name, so
                     publishing the UEI publishes the name by one hop

Cedar Press's existing written policy is INHERITED, not restated:
`nrc_meeting_participants` records *"Cedar Press names an individual only where
a public professional capacity is established"*; `ferc_ex_parte_parties`
records *"Cedar Press does not publish datasets about private individuals."*
Cells resolving to fewer than 3 firms are suppressed, and the suppression is
reported rather than the row dropped (the CGCC precedent).

**A firm's own website statement is our EVIDENCE, never their PERMISSION to be
named.** `consent_status = OPTED_IN` is the only thing that releases a name.

    py -3 code/241_promote_individual_native_firms_in_place.py --check  # no write
    py -3 code/241_promote_individual_native_firms_in_place.py          # apply

Reads   data/clean/individual_native_prior_rulings.csv          (the 45)
        data/clean/individual_native_ownership_verification.csv  (335)
        data/clean/prime_contracts.csv                           (READ ONLY)
        data/spine/cedar_entity_spine.csv
        data/clean/cedar_identifier_ledger_final.csv
Writes  data/spine/cedar_entity_spine.csv
            + .bak_<date>_pre_241_promote_individual_native_firms_in_place
        data/clean/cedar_identifier_ledger_final.csv             (same tag)
        data/clean/individual_native_firm_register.csv           (new)
        review/individual_native_promotion_refused_<date>.csv
        review/individual_native_ledger_repointed_<date>.csv
        review/individual_native_canonical_name_privacy_<date>.csv
        logs/241_promote_individual_native_firms.log
"""

import csv
import importlib.util
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
RULINGS = CLEAN / "individual_native_prior_rulings.csv"
VERIFICATION = CLEAN / "individual_native_ownership_verification.csv"
PRIME = CLEAN / "prime_contracts.csv"
REGISTER = CLEAN / "individual_native_firm_register.csv"
EXCLUSION_PAIRS = CLEAN / "individual_native_exclusion_pairs.csv"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

# Standing rule 1 of the concurrency block: a backup tag names the SCRIPT, not
# the number. Four agents each wrote a `code/163_*.py` and each backed up as
# `.bak_2026-08-26_pre163`; restoring by glob then reverted seven files
# belonging to two other agents.
BACKUP_TAG = "pre_241_promote_individual_native_firms_in_place"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

LOG_LINES = []


def log(msg=""):
    print(msg)
    LOG_LINES.append(msg)


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, CEDAR / "code" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# One vocabulary, one ID service, one resolver - imported, never re-typed
# (standing rule 8). `09_import_rulings.py` is unsafe to RUN and safe to
# IMPORT; it is not imported here because this pass reads a normalised ruling
# table rather than a raw inbox.
D = load_module("cedar_domain", "cedar_domain.py")
IDS = load_module("cedar_ids", "cedar_ids.py")
M33 = load_module("m33", "33_apply_party_rulings.py")
norm = M33.norm

CLASS = D.INDIVIDUAL_NATIVE_CLASS
SURROGATE_PREFIX = "CEDAR-ENT"

# ---------------------------------------------------------------------------
# DECLARED REPOINTS. Both are the "Not a Native entity - individually
# Native-owned firm" mis-transcription: `09`'s NOT_NATIVE_RE matched the
# leading clause and wrote tier X onto a TRIBAL binding the ruling was
# refusing. Declared here rather than discovered in a loop so that a repoint
# which fails to fire ABORTS the run.
#
# FAIL CLOSED: a declared correction that matches nothing is a correction that
# did not happen, and it looks identical to one that did. This is the same
# guard `163` needed after the okina/apostrophe near-miss.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# TIER COMES FROM THE RULING'S **OUTCOME**, NEVER FROM ITS METHOD.
#
# This map exists because of a 317-row defect in
# `148_resolve_schedule_i_recipients.py`, which wrote
#
#     tier = "A" if method in RULED_METHODS else ...
#
# and thereby published **317 of the owner's tier-X EXCLUSIONS as tier-A
# attributions** - at the only publishable tier. The count was first believed
# to be 42. `elijah_ruling` is in `RULED_METHODS` whether the owner said YES or
# NO, so method membership answers "did a human decide?" and says NOTHING about
# WHAT they decided. `status` says a ruling was processed; `outcome` says what
# it decided. An agent has already resolved onto a ruling whose `status` was
# `SETTLED` and whose `outcome` was `HOLD_OVER_OWNER`, text
# "HOLD - RETRACTION REQUIRED".
#
# This script's input happens to be a curated POSITIVE-ruling file, so branching
# on the method would be safe today. That is a property of the INPUT, not of
# this code, and the individually-Native space is full of negative rulings -
# including the five that read "Not a Native entity - individually Native-owned
# firm". Widen the input to a mixed file and the identical bug appears. So the
# branch is on the outcome, the map is exhaustive, and an unrecognised outcome
# ABORTS rather than defaulting.
#
#   ruling_class -> (outcome, tier, promote?)
# ---------------------------------------------------------------------------
RULING_OUTCOME = {
    "INDIVIDUAL_NATIVE": (
        "AFFIRM_INDIVIDUAL_NATIVE_OWNERSHIP", "A", True,
        "The owner affirmed that a private Native individual or family owns "
        "this firm. A positive ruling: promote."),
    "INDIVIDUAL_NATIVE_NOT_TRIBAL": (
        "REFUSE_TRIBAL_LINK_AFFIRM_INDIVIDUAL_NATIVE_OWNERSHIP", "A", True,
        "'Not a Native entity - individually Native-owned firm'. The FIRST "
        "clause refuses the TRIBAL LINK; the SECOND affirms Native ownership. "
        "Two decisions in one sentence, and reading only the first inverts the "
        "owner's meaning. Promote the firm AND record the tribal exclusion."),
}
#: Outcomes that are NOT decisions and must never be promoted, whatever the
#: method says. Present so that widening the input fails loudly instead of
#: silently publishing a hold or a retraction.
NON_DECISION_OUTCOMES = {
    "HOLD", "HOLD_OVER_OWNER", "RETRACTION_REQUIRED", "MULTI", "UNRESOLVED",
    "NEEDS_VERIFICATION", "DROP", "NOT_NATIVE_ENTITY", "SUPERSEDED",
}
#: Text that means a human declined to decide. Scanned on every ruling before
#: anything is promoted, because a non-decision arriving as free text is how
#: "HOLD - RETRACTION REQUIRED" reached a resolver under a SETTLED status.
NON_DECISION_TEXT = ("hold", "retraction", "needs verification", "unresolved",
                     "pending", "do not use", "withdraw")

DECLARED_REPOINTS = {
    ("CAGE", "9DVK5"): (
        "TRBF-SNJUAN-00",
        "SAN JUAN SERVICES LLC. Ruled 'Not a Native entity - individually "
        "Native-owned firm'. `09`'s NOT_NATIVE_RE matched the leading clause "
        "and wrote tier X while LEAVING the tribal binding in place, so the "
        "ledger recorded the refusal as its own opposite: a firm bound to San "
        "Juan Southern Paiute Tribe of Arizona at entity_class "
        "FEDERAL_TRIBE_LOWER48. Note the spine short-name collision behind it "
        "- the spine's canonical 'San Juan' IS the Arizona Paiute tribe "
        "(AGENTS.md 2026-08-07). The tribal binding is REMOVED and the firm is "
        "bound to its own entity in the individually Native-owned class, which "
        "has no ownership edge to any tribe."),
    ("CAGE", "9H8M8"): (
        "TRBF-TEMOAK-00",
        "FOUR CORNER PEST CONTROL LLC. Identical defect against Te-Moak Tribe "
        "of Western Shoshone. Same correction, same reasoning."),
}


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_atomic(path, rows, fields, backup=True):
    """Back up, write `.part`, rename. An interruption must not look like a
    completion (START_HERE, standing rules)."""
    path = Path(path)
    if backup and path.exists():
        bak = Path(f"{path}.bak_{TODAY}_{BACKUP_TAG}")
        if not bak.exists():
            shutil.copy2(path, bak)
            log(f"  backed up -> {bak.name}")
    part = Path(str(path) + ".part")
    part.parent.mkdir(parents=True, exist_ok=True)
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({f: r.get(f, "") for f in fields})
    part.replace(path)
    log(f"  wrote {path.relative_to(CEDAR)}  ({len(rows):,} rows, "
        f"{len(fields)} columns)")


# ---------------------------------------------------------------------------
# GUARDS. Each one is executed, not asserted in prose.
# ---------------------------------------------------------------------------
def guard_no_ownership_edge():
    """The class must have no dollar-bearing edge in EITHER direction."""
    checks = [
        D.bears_ownership("owner_self_identifies_with"),
        D.bears_ownership("owned_by", CLASS, "Federally recognized tribe"),
        D.bears_ownership("owned_by", "Federally recognized tribe", CLASS),
        D.bears_ownership("wholly_owned_by", CLASS,
                          "Alaska Native Regional Corporation"),
        D.bears_ownership("subsidiary_of", "Native Hawaiian Organization", CLASS),
    ]
    if any(checks):
        raise SystemExit(
            "ABORT: cedar_domain.bears_ownership() permits an edge on the "
            f"individually Native-owned class ({checks}). The class must never "
            "roll up to a tribe, an ANC or an NHO. Fix cedar_domain before "
            "any row is written.")
    # And a control: the normal tribal case must still work, or the guard is
    # passing because everything is refused.
    if not D.bears_ownership("owned_by", "Federally recognized tribe",
                             "Federally recognized tribe"):
        raise SystemExit(
            "ABORT: bears_ownership() now refuses an ordinary tribal ownership "
            "edge. The refusal above proves nothing if it refuses everything.")
    log("  guard: bears_ownership() refuses every edge on the class, and "
        "still permits an ordinary tribal edge")


def assert_no_forbidden_absence_value(rows, where):
    """There is no NOT_NATIVE in this schema and there never will be one."""
    bad = []
    for r in rows:
        for k, v in r.items():
            if not D.absence_value_ok(v):
                bad.append((where, k, v))
    if bad:
        raise SystemExit(
            f"ABORT: a forbidden absence value was about to be written: "
            f"{bad[:5]}. Absence is NO_CLAIM_FOUND. Cedar Press is in no "
            f"position to adjudicate anyone's Native identity, and "
            f"'nobody said' is not 'the answer is no'.")


# ---------------------------------------------------------------------------
def firm_key(r):
    """The identity of a ruling. UEI first, then CAGE, then the name.

    NEVER a row number, an index or a rank. `verification_id` is positional and
    a concurrent rewrite of `prime_contracts.csv` shifted every id below an
    insertion point on 2026-08-26, putting Frontier Electronic Systems'
    ownership sentence on Cherokee Construction's row. Nothing errored.
    """
    return ((r.get("identifier_type") or "").strip().upper(),
            (r.get("identifier") or "").strip().upper())


def affiliation_from_note(note):
    """Free text, forever. Returned exactly as the owner wrote it.

    Resolving this string is the containment defect with a respectable label:
    the Cherokee Nation does not own these firms, and "Cherokee" does not
    resolve to one tribe in any case.
    """
    n = (note or "").strip()
    return n if n else ""


def main():
    check = "--check" in sys.argv
    log("=== Cedar Press 241: individually Native-owned FIRM class, IN PLACE ===")
    log(f"    mode: {'--check (writes nothing)' if check else 'APPLY'}")
    log(f"    class: {CLASS!r}")
    log("")

    log("[0] Guards before anything is read")
    guard_no_ownership_edge()
    if CLASS in {"Federally recognized tribe", "Native Hawaiian Organization"}:
        raise SystemExit("ABORT: class name collides with an existing class.")

    rulings = load(RULINGS)
    verification = load(VERIFICATION)
    spine = load(SPINE)
    ledger = load(LEDGER)
    if not (rulings and spine and ledger):
        raise SystemExit("ABORT: a required input is empty or missing.")

    spine_fields = list(spine[0].keys())
    ledger_fields = list(ledger[0].keys())

    log("\n[1] Inputs")
    log(f"  rulings (the 45)            : {len(rulings):>6}")
    log(f"  verification candidates     : {len(verification):>6}")
    log(f"  spine entities              : {len(spine):>6}")
    log(f"  ledger rows                 : {len(ledger):>6}")
    log(f"  spine rows in this class    : "
        f"{sum(1 for r in spine if r.get('entity_class') == CLASS):>6}  "
        f"<- the defect")
    rc = Counter(r["ruling_class"] for r in rulings)
    log(f"  ruling_class                : {dict(rc)}")
    log(f"    INDIVIDUAL_NATIVE_NOT_TRIBAL is the 'Not a Native entity - "
        f"individually")
    log(f"    Native-owned firm' wording. It refuses the TRIBAL LINK, not "
        f"Native ownership.")
    # ---- OUTCOME GATE. Branch on what the ruling DECIDED. ----------------
    # NOT on whether its method is in RULED_METHODS: `elijah_ruling` is a
    # RULED method whether the owner said YES or NO, and reading membership as
    # a verdict published 317 tier-X exclusions as tier-A attributions in
    # 148_resolve_schedule_i_recipients.py.
    for r in rulings:
        rc = (r.get("ruling_class") or "").strip().upper()
        if rc in NON_DECISION_OUTCOMES:
            raise SystemExit(
                f"ABORT: ruling on {r['identifier']} carries outcome {rc!r}, "
                f"which is a NON-DECISION. A hold, a retraction or an "
                f"unresolved item must never be promoted, however 'ruled' its "
                f"method looks.")
        if rc not in RULING_OUTCOME:
            raise SystemExit(
                f"ABORT: ruling on {r['identifier']} has ruling_class {rc!r}, "
                f"which is not in RULING_OUTCOME. An unrecognised outcome "
                f"ABORTS rather than defaulting - defaulting is how a negative "
                f"ruling becomes a positive one.")
        blob = f"{r.get('ruling_text','')} {r.get('ruling_note','')}".lower()
        for bad in NON_DECISION_TEXT:
            if bad in blob:
                raise SystemExit(
                    f"ABORT: ruling on {r['identifier']} contains "
                    f"non-decision text {bad!r}: {blob[:160]!r}. `status` says "
                    f"a ruling was processed; `outcome` says what it decided.")
        # Cross-check the domain predicate against the outcome map. Two
        # independent readings of the same ruling that disagree is a finding.
        if not D.is_tribal_link_refusal_not_native_refusal(
                r["ruling_class"], r["ruling_text"]):
            raise SystemExit(
                f"ABORT: cedar_domain and RULING_OUTCOME disagree about "
                f"{r['identifier']}.")
    log("  outcome gate: every ruling is a POSITIVE decision, read from its")
    log("  OUTCOME and not from its method. Outcomes present: "
        + str(dict(Counter(RULING_OUTCOME[r['ruling_class'].upper()][0]
                           for r in rulings))))

    # ---- TIER IS INHERITED, NOT COMPUTED --------------------------------
    tier_col = next((c for c in ("confidence_tier", "evidence_tier", "tier")
                     if c in rulings[0]), None)
    if tier_col:
        log(f"  tier INHERITED verbatim from the source column {tier_col!r}")
    else:
        log("  the ruling table carries NO tier column, so the tier is taken "
            "from the")
        log("  ruling's OUTCOME via RULING_OUTCOME - never from its method - "
            "and every")
        log("  row records `tier_source` so the next reader can see which "
            "happened.")

    # ---- verification table, keyed on IDENTITY not position ---------------
    ver_by_uei = {(r["awardee_uei"] or "").upper(): r
                  for r in verification if (r["awardee_uei"] or "").strip()}
    ver_by_cage = {(r["cage_code_modal"] or "").upper(): r
                   for r in verification if (r["cage_code_modal"] or "").strip()}

    # ---- ledger index ------------------------------------------------------
    lidx = {}
    for r in ledger:
        lidx.setdefault(
            ((r["identifier_type"] or "").strip().upper(),
             (r["identifier"] or "").strip().upper()), []).append(r)

    # ---- prime contracts, READ ONLY ---------------------------------------
    log("\n[2] Measuring the discard pile (prime_contracts.csv, READ ONLY)")
    want_uei = {r["identifier"].upper() for r in rulings
                if r["identifier_type"] == "UEI"}
    want_cage = {r["identifier"].upper() for r in rulings
                 if r["identifier_type"] == "CAGE"}
    rows_by_id, usd_by_id, fy_by_id = Counter(), Counter(), {}
    tier_seen, attr_seen = Counter(), Counter()
    with open(PRIME, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            u = (row.get("awardee_uei") or "").strip().upper()
            c = (row.get("cage_code") or "").strip().upper()
            key = u if u in want_uei else (c if c and c in want_cage else None)
            if not key:
                continue
            rows_by_id[key] += 1
            try:
                usd_by_id[key] += float(row.get("total_obligations") or 0)
            except ValueError:
                pass
            fy = (row.get("fiscal_year") or "").strip()
            if fy:
                y = int(float(fy))
                lo, hi = fy_by_id.get(key, (y, y))
                fy_by_id[key] = (min(lo, y), max(hi, y))
            tier_seen[(row.get("confidence_tier") or "",
                       (row.get("tribe_id") or "") or "(blank)")] += 1
            attr_seen[row.get("attributed_flag") or ""] += 1
    log(f"  prime rows reached by the 45 rulings : {sum(rows_by_id.values()):,}")
    log(f"  obligations on them                  : "
        f"${sum(usd_by_id.values()):,.2f}")
    log(f"  distinct identifiers with contracts  : {len(rows_by_id)}")
    log(f"  their attributed_flag                : {dict(attr_seen)}")
    log(f"  their (tier, tribe_id)               : {tier_seen.most_common(4)}")
    log("  -> a discard pile: ruled by hand, and attributed to nobody.")
    log("  prime_contracts.csv is NOT written by this script. See the docstring:")
    log("  the tribal total must not absorb a class that was never in it.")

    # =======================================================================
    # PART A - mint the entities
    # =======================================================================
    log("\n[3] Minting entities  (surrogate key, never a name-derived slug)")

    have_ids = {r["tribe_id"] for r in spine}
    have_norm = {}
    for r in spine:
        have_norm.setdefault(norm(r.get("canonical_name") or ""), r)

    added, register_rows, refused, name_privacy, repointed = [], [], [], [], []
    fired_repoints = set()
    stats = Counter()

    # One lock-held allocation for the whole run rather than one per row: the
    # registry lock is contended on this machine and a partial mint is worse
    # than a slow one.
    # ---- IDEMPOTENCE: reuse a surrogate this pass already minted ---------
    # A second run must not mint a second entity for the same firm. The
    # register is this class's crosswalk - the role `nho_ito_spine_crosswalk`
    # plays for the NHOs - so prior ids are read back from it and reused. The
    # spine row alone cannot answer this: it carries no identifier.
    prior_register = load(REGISTER)
    prior_sid = {(r["identifier_type"], r["identifier"].upper()):
                 r["surrogate_entity_id"] for r in prior_register}
    if prior_sid:
        log(f"  prior register on file: {len(prior_sid)} firms already "
            f"promoted; their surrogate ids are REUSED, not re-minted")

    need = len(rulings)
    if check:
        # --check must not consume the shared counter. A dry run that burns 45
        # ids out of a registry other agents mint from is a side effect, and a
        # dry run with a side effect is not a dry run.
        surrogates = [f"{SURROGATE_PREFIX}-CHECK{i:04d}" for i in range(need)]
        log(f"  --check: {need} PLACEHOLDER ids, registry counter untouched")
    else:
        surrogates = IDS.allocate(SURROGATE_PREFIX, need,
                                  note=f"individually Native-owned firms, "
                                       f"code/241 {TODAY}")
    log(f"  allocated {need} {SURROGATE_PREFIX} ids "
        f"({surrogates[0]} .. {surrogates[-1]})")
    log(f"  cedar_ids.is_internal('{surrogates[0]}') = "
        f"{IDS.is_internal(surrogates[0])}  <- never presented as an official "
        f"identifier")

    for i, r in enumerate(rulings):
        idtype, ident = firm_key(r)
        # Tier: inherited verbatim where the source carries one; otherwise
        # taken from the ruling's OUTCOME. Never from the method.
        outcome, outcome_tier, promote, outcome_why = \
            RULING_OUTCOME[r["ruling_class"].strip().upper()]
        if tier_col and (r.get(tier_col) or "").strip():
            row_tier = r[tier_col].strip()
            tier_source = f"INHERITED verbatim from source column {tier_col!r}"
        else:
            row_tier = outcome_tier
            tier_source = (f"OUTCOME {outcome!r} via RULING_OUTCOME "
                           f"(the ruling table carries no tier column). NOT "
                           f"derived from attribution_method: method "
                           f"membership says a human decided, never what they "
                           f"decided.")
        if not promote:
            stats["outcome is not a promotion - skipped"] += 1
            continue
        ver = (ver_by_uei.get(ident) if idtype == "UEI"
               else ver_by_cage.get(ident) if idtype == "CAGE" else None)
        led_rows = lidx.get((idtype, ident), [])

        # ---- the firm's name, in order of how much we trust the source ----
        name = ""
        for cand in ((ver or {}).get("awardee_name_modal"),
                     next((x.get("legal_business_name") for x in led_rows
                           if (x.get("legal_business_name") or "").strip()), ""),
                     r.get("entity_name"),
                     ident if idtype == "NAME" else ""):
            if (cand or "").strip():
                name = cand.strip()
                break
        if not name:
            refused.append({
                "identifier_type": idtype, "identifier": ident,
                "reason": "No name on the ruling, the ledger or the "
                          "verification table. An entity with no name is not "
                          "an entity. Prime directive: zero fabrication.",
                "ruling_source_file": r.get("source_file", ""),
                "refused_date": TODAY,
                "refused_by": "code/241_promote_individual_native_firms_in_place.py",
            })
            stats["refused: no name"] += 1
            continue

        # ---- privacy classification -------------------------------------
        # Resolve the surrogate FIRST so a re-run reports the id the firm
        # actually holds rather than the placeholder this run would have
        # minted.
        sid_for_row = prior_sid.get((idtype, ident)) or surrogates[i]
        priv = (ver or {}).get("privacy_class", "") or "UNKNOWN"
        pub_name = (ver or {}).get("publishable_entity_name", "") or "N"
        # Deliberately over-inclusive, because the two errors do not cost the
        # same: an unnecessary withholding costs a column, a wrong disclosure
        # costs a person.
        if priv in {"POSSIBLE_PERSONAL_NAME", "NO_CORPORATE_FORM", "UNKNOWN"}:
            name_is_person = "UNKNOWN"
        else:
            name_is_person = "0"
        if priv == "POSSIBLE_PERSONAL_NAME":
            pub_name = "N"
        publish_name = "1" if (pub_name == "Y" and name_is_person == "0") else "0"

        if publish_name == "0":
            # The ENTITY is still minted - withholding the entity would drop
            # the owner's ruling, which is the defect this script exists to
            # fix. Only the NAME is withheld, and the canonical-form question
            # goes to a human. Cf. `163`'s N-0145 refusal, where the string
            # itself contained a private person's name used as a postal
            # care-of; here the string is a firm name a heuristic cannot clear.
            name_privacy.append({
                "surrogate_entity_id": sid_for_row,
                "identifier_type": idtype, "identifier": ident,
                "privacy_class": priv,
                "firm_legal_name_is_person": name_is_person,
                "question": "Is this legal name a private individual's name? "
                            "The entity IS minted; only publication of the "
                            "name is withheld pending this answer. Answer "
                            "PERSON / FIRM. A FIRM answer sets "
                            "firm_legal_name_is_person = 0 and releases the "
                            "name and the UEI; a PERSON answer keeps both "
                            "withheld permanently absent consent.",
                "YOUR_RULING": "", "YOUR_NOTE": "",
                "flagged_date": TODAY,
            })

        # ---- the entity row (EXISTING spine columns only) -----------------
        # No new spine columns. The spine is a hot shared file, 20 extra
        # columns blank on 1,489 rows is a collision surface, and the gate
        # watches `files_with_columns_lost_vs_backup`. Everything specific to
        # this class lives in individual_native_firm_register.csv, keyed on
        # the surrogate - the same relationship nho_register.csv has to the
        # spine.
        reused = prior_sid.get((idtype, ident))
        tid = reused or surrogates[i]
        already_in_spine = tid in have_ids
        if already_in_spine and not reused:
            raise SystemExit(f"ABORT: {tid} already exists in the spine. "
                             f"Refusing to overwrite an existing entity.")

        dup = have_norm.get(norm(name))
        if dup and dup.get("entity_class") == CLASS and not reused:
            # Already promoted under a different key. Adopt the existing
            # entity rather than minting a twin - two spine rows for one firm
            # is the Sequoyah/CDFI collision in a new place.
            tid = dup["tribe_id"]
            already_in_spine = True
            stats["adopted an entity already in the class"] += 1
        if dup and dup.get("entity_class") != CLASS:
            # A name collision with a TRIBE is exactly the containment defect
            # arriving from the other direction. Report it; do not merge.
            refused.append({
                "identifier_type": idtype, "identifier": ident,
                "reason": f"Firm name {name!r} normalises onto existing spine "
                          f"entity {dup['tribe_id']} ({dup['canonical_name']}, "
                          f"{dup['entity_class']}). Minting would create a "
                          f"resolver collision between a firm and a Native "
                          f"government. NOT merged and NOT minted - a name "
                          f"match is never evidence of identity.",
                "ruling_source_file": r.get("source_file", ""),
                "refused_date": TODAY,
                "refused_by": "code/241_promote_individual_native_firms_in_place.py",
            })
            stats["refused: name collides with an existing spine entity"] += 1
            continue

        row = {f: "" for f in spine_fields}
        row.update({
            "tribe_id": tid,
            "canonical_name": name,
            "entity_class": CLASS,
            "state": (ver or {}).get("recipient_state_modal", ""),
            "aliases": name,
            # THE THREE FIELDS THAT KEEP TRIBAL ATTRIBUTION CORRECT
            "parent_entity_id": "",
            "parent_entity_name": "",
            "parent_native_entity": "",          # permanently NULL
            "ultimate_parent_entity_id": tid,    # self-parented
            "ultimate_parent_entity_name": name,
            "ownership_basis": D.INDIVIDUAL_NATIVE_OWNERSHIP_BASIS,
            "hierarchy_basis": "SELF_PARENTED_BY_RULING",
            # TIER COMES FROM THE RULING'S OUTCOME, NOT FROM ITS METHOD.
            # `elijah_ruling` is in RULED_METHODS whether the owner said YES or
            # NO; reading that membership as a verdict published 317 tier-X
            # exclusions as tier-A attributions in
            # 148_resolve_schedule_i_recipients.py. `row_tier` is inherited
            # from the source column where one exists and otherwise comes from
            # RULING_OUTCOME, and `tier_source` says which on every row.
            "evidence_tier": row_tier,
            "evidence_grade": "elijah_ruling",
            "verification_route": f"{r.get('evidence_type','')} "
                                  f"<- {r.get('source_file','')}".strip(),
            "evidence_url": r.get("evidence_url", ""),
            "entity_source_url": r.get("evidence_url", ""),
            "entity_source_quote": r.get("ruling_note", ""),
            "n_uei_tierA": "1" if idtype == "UEI" else "0",
            "n_uei_tierB": "0",
            "n_cage": "1" if idtype == "CAGE" else "0",
            "n_ein": "0",
            "reconciliation_status": "individually_native_owned_firm_ruled",
            "reconciliation_note":
                "Individually Native-owned FIRM. NOT a tribe, an ANC or an "
                "NHO. parent_native_entity is permanently NULL by ruling, not "
                "by omission; the entity is self-parented and has no "
                "ownership edge in either direction, so it can never roll up "
                "into a tribal total and no published tribal, ANC or NHO "
                "figure changes. Owner ruling "
                f"{r.get('ruled_date','')} ({r.get('ruling_text','')}). "
                "The tribal affiliation of the OWNER is a fact about a person "
                "and is held as free text in "
                "individual_native_firm_register.csv; it never keys a "
                "tribe_id.",
            "built_by_script": "code/241_promote_individual_native_firms_in_place.py",
        })
        if already_in_spine:
            stats["already in the spine - not re-minted (idempotent)"] += 1
        else:
            added.append(row)
            have_ids.add(tid)
            have_norm.setdefault(norm(name), row)
            stats["minted"] += 1

        # ---- the register row (everything class-specific) -----------------
        fy_lo, fy_hi = fy_by_id.get(ident, ("", ""))
        ruled_year = int((r.get("ruled_date") or "0000")[:4] or 0)
        gap = (ruled_year - int(fy_hi)) if (fy_hi and ruled_year) else ""
        register_rows.append({
            "surrogate_entity_id": tid,
            "entity_class": CLASS,
            # -- identity, withheld per the privacy block ------------------
            "canonical_name": name,
            "identifier_type": idtype,
            "identifier": ident,
            "state": (ver or {}).get("recipient_state_modal", ""),
            # -- the ruling ------------------------------------------------
            "ruling_class": r.get("ruling_class", ""),
            "ruling_text": r.get("ruling_text", ""),
            "ruling_note": r.get("ruling_note", ""),
            "ruled_by": r.get("ruled_by", ""),
            "ruled_date": r.get("ruled_date", ""),
            "ruling_source_file": r.get("source_file", ""),
            "ruling_source_line": r.get("source_line", ""),
            "refuses_tribal_link_not_native_ownership":
                "1" if r.get("ruling_class") == "INDIVIDUAL_NATIVE_NOT_TRIBAL"
                else "0",
            # -- evidence, inherited verbatim ------------------------------
            "native_ownership_evidence_type": r.get("evidence_type", ""),
            "native_ownership_evidence_quote": r.get("ruling_note", ""),
            "native_ownership_evidence_url": r.get("evidence_url", ""),
            "native_ownership_evidence_date": r.get("ruled_date", ""),
            "native_ownership_evidence_n_legs":
                "1" if (r.get("evidence_url") or "").strip() else "0",
            "ruling_outcome": outcome,
            "ruling_outcome_meaning": outcome_why,
            "evidence_tier": row_tier,
            "tier_source": tier_source,
            "evidence_grade": "elijah_ruling",
            "web_pass_evidence_tier": (ver or {}).get("evidence_tier", "NOT_CHECKED"),
            "web_pass_tier_basis": (ver or {}).get("tier_basis", ""),
            "web_pass_independence": (ver or {}).get("evidence_independence", ""),
            # -- the OWNER's affiliation. Free text FOREVER. ---------------
            "owner_tribal_affiliation_named":
                affiliation_from_note(r.get("ruling_note", "")),
            "owner_tribal_affiliation_source": r.get("source_file", ""),
            "owner_tribal_affiliation_basis":
                "SELF_STATED" if (r.get("evidence_url") or "").strip()
                else "OWNER_NARRATIVE_NOTE",
            "owner_tribal_affiliation_resolved_to_tribe_id":
                "",   # permanently blank. See the guard below.
            "owner_self_identifies_with_is_never_an_ownership_edge": "1",
            # -- self-certification, in its OWN column, never a verdict ----
            "sam_self_certification": (ver or {}).get("sam_self_certification",
                                                      "NOT_CHECKED"),
            "sam_flags_asserted": (ver or {}).get("sam_flags_asserted", ""),
            "sam_self_certification_note": D.SELF_CERTIFICATION_IS_NOT_A_VERDICT,
            # -- temporal --------------------------------------------------
            "ownership_asserted_as_of": r.get("ruled_date", ""),
            "contract_fy_min": fy_lo, "contract_fy_max": fy_hi,
            "temporal_gap_years": gap,
            "temporal_caveat": (ver or {}).get(
                "temporal_caveat",
                "Contract activity predates the ruling. Ownership established "
                "at ruling date does not testify about ownership at award "
                "date."),
            # -- contract facts (measured here, prime_contracts NOT written)
            "n_contract_rows": rows_by_id.get(ident, 0),
            "total_obligations_usd": f"{usd_by_id.get(ident, 0.0):.2f}",
            # -- privacy ---------------------------------------------------
            "privacy_class": priv,
            "firm_legal_name_is_person": name_is_person,
            "consent_status": "NOT_ASKED",
            "consent_date": "", "consent_source": "",
            "publish_name": publish_name,
            "publish_surrogate_id_only": "0" if publish_name == "1" else "1",
            "publish_federal_identifier":
                "1" if D.may_publish_individual_native_field(
                    "awardee_uei", name_is_person, "NOT_ASKED") else "0",
            "publish_contract_facts": "Y",
            "dnb_open_data_attaches": (ver or {}).get(
                "dnb_open_data_attaches",
                "NO - sourced from BGOV/USAspending, not a SAM entity extract. "
                "The privacy restriction is INDEPENDENT of this answer and "
                "survives it."),
            "publication_policy_inherited_from":
                "nrc_meeting_participants ('Cedar Press names an individual "
                "only where a public professional capacity is established'); "
                "ferc_ex_parte_parties ('Cedar Press does not publish datasets "
                "about private individuals.')",
            "built_date": TODAY,
            "built_by": "code/241_promote_individual_native_firms_in_place.py",
        })

    log(f"  minted   : {len(added)}")
    log(f"  refused  : {len(refused)}")
    for x in refused:
        log(f"      {x['identifier_type']} {x['identifier']}  "
            f"{x['reason'][:90]}")
    log(f"  name withheld pending a human ruling : {len(name_privacy)}")
    for x in name_privacy:
        log(f"      {x['surrogate_entity_id']}  {x['identifier']}  "
            f"({x['privacy_class']})")

    # ---- EXCLUSIONS, SCOPED TO A (IDENTIFIER, ENTITY) PAIR ----------------
    # A tier-X row is an exclusion, and the SCOPE of an exclusion matters. Read
    # as a blanket block on the identifier it suppresses a CORRECT attribution
    # somewhere else; read as a pair it refuses exactly what the owner refused.
    #
    # And it must block the NAME paths too. Refusing only the identifier route
    # hands the same match straight back through `resolve_entity`, which is
    # name-based - so every excluded entity's normalised and `core()` forms are
    # written out beside the identifier, along with the firm's own name forms.
    # A resolver that consults only the identifier column of this file has done
    # half the job.
    exclusion_pairs = []
    for rr in register_rows:
        if rr["ruling_class"] != "INDIVIDUAL_NATIVE_NOT_TRIBAL":
            continue
        declared = DECLARED_REPOINTS.get(
            (rr["identifier_type"], rr["identifier"]))
        excluded_id = declared[0] if declared else ""
        excluded_row = next((s for s in spine
                             if s["tribe_id"] == excluded_id), None)
        excluded_name = (excluded_row or {}).get("canonical_name", "")
        exclusion_pairs.append({
            "identifier_type": rr["identifier_type"],
            "identifier": rr["identifier"],
            "firm_surrogate_entity_id": rr["surrogate_entity_id"],
            "firm_name_norm": norm(rr["canonical_name"]),
            "firm_name_core": M33.core(rr["canonical_name"]),
            "excluded_entity_id": excluded_id,
            "excluded_entity_name": excluded_name,
            "excluded_entity_name_norm": norm(excluded_name),
            "excluded_entity_name_core": (M33.core(excluded_name)
                                          if excluded_name else ""),
            "exclusion_scope":
                "PAIR" if excluded_id else "ALL_TRIBAL_ANC_NHO_ENTITIES",
            "blocks_identifier_path": "1",
            "blocks_name_path": "1",
            "ruling_outcome": rr["ruling_outcome"],
            "reason":
                "Owner ruling: 'Not a Native entity - individually "
                "Native-owned firm'. The first clause refuses the TRIBAL LINK "
                "named here; the second AFFIRMS Native ownership by a private "
                "individual. This row refuses ONLY the pair - it is not a "
                "blanket block on the identifier, which would suppress a "
                "correct attribution elsewhere - and it blocks the NAME route "
                "as well as the identifier route, because resolve_entity "
                "matches on names and refusing one path hands the match to the "
                "other.",
            "does_not_mean":
                "This is NOT a finding that the firm is not Native-owned. "
                "There is no NOT_NATIVE value in this schema. The firm is in "
                "the spine as an individually Native-owned business at "
                f"{rr['surrogate_entity_id']}.",
            "ruled_date": rr["ruled_date"],
            "flagged_date": TODAY,
        })
    log(f"  exclusion pairs recorded (identifier AND name paths blocked): "
        f"{len(exclusion_pairs)}")
    for e in exclusion_pairs:
        log(f"      {e['identifier_type']} {e['identifier']:12s} "
            f"scope={e['exclusion_scope']:28s} "
            f"excluded={e['excluded_entity_id'] or '(any tribal/ANC/NHO)'}")

    # ---- COLLISION SURFACE ADDED BY THIS PASS -----------------------------
    # AGENTS.md, 2026-08-07: 161 spine entities carry a short canonical name
    # and "each is a collision waiting for the right input string". This pass
    # adds 45 firms of which THIRTY-ONE are Cherokee-named, so it enlarges the
    # single worst trap token in `cedar_domain.NAME_TRAPS` by an order of
    # magnitude. Counted and named here rather than rediscovered later as a
    # "resolve_entity defect" that is not one - two independent builds have
    # already reported that non-bug.
    #
    # Why it is safe to add them anyway: containment "may be used only to
    # resolve an owner already named in evidence - never to detect a match, and
    # never to key a dollar" (AGENTS.md), and every one of these rows is
    # self-parented with no ownership edge, so a name match against one cannot
    # move a dollar onto a tribe. It CAN still move a NAME.
    STOP = {"the", "inc", "incorporated", "corporation", "corp", "company",
            "llc", "ltd", "limited", "of", "and", "services", "service",
            "group", "enterprises", "construction", "systems", "solutions"}
    collision_risk = []
    for row in added:
        toks = [t for t in norm(row["canonical_name"]).split() if t not in STOP]
        traps = sorted(set(toks) & set(D.NAME_TRAPS))
        if len(toks) <= 2 or traps:
            collision_risk.append({
                "tribe_id": row["tribe_id"],
                "canonical_name": row["canonical_name"],
                "entity_class": CLASS,
                "distinctive_tokens": " ".join(toks),
                "n_tokens": len(toks),
                "name_trap_tokens": "|".join(traps),
                "risk": "A firm name added to the spine. resolve_entity's "
                        "containment path can match it from an unrelated "
                        "record string. It is self-parented with NO ownership "
                        "edge, so it cannot receive a dollar - but it can "
                        "receive a NAME match, and for a firm whose legal name "
                        "may be a person's that is a privacy event, not just a "
                        "data-quality one.",
                "flagged_date": TODAY,
            })
    trap_counts = Counter(t for c in collision_risk
                          for t in c["name_trap_tokens"].split("|") if t)
    log(f"  collision surface added: {len(collision_risk)} of {len(added)} "
        f"rows carry a NAME_TRAPS token or a <=2-token name")
    log(f"    trap tokens: {dict(trap_counts)}")

    # GUARD: no register row may resolve an owner affiliation to a tribe.
    spine_ids = {r["tribe_id"] for r in spine} | {r["tribe_id"] for r in added}
    for rr in register_rows:
        v = (rr["owner_tribal_affiliation_resolved_to_tribe_id"] or "").strip()
        if v:
            raise SystemExit(
                f"ABORT: {rr['surrogate_entity_id']} resolved an owner's "
                f"self-stated affiliation to {v!r}. "
                f"`owner_self_identifies_with` is a fact about a PERSON and "
                f"must never key a tribe_id. "
                f"{D.individual_native_refusal_reason('owner_self_identifies_with')}")
        if (rr["owner_tribal_affiliation_named"] or "").strip() in spine_ids:
            raise SystemExit("ABORT: an affiliation string is a spine id.")
    log("  guard: 0 owner affiliations resolved to a tribe_id (must be 0)")
    assert_no_forbidden_absence_value(register_rows, "register")
    assert_no_forbidden_absence_value(added, "spine")
    log("  guard: 0 forbidden absence values (NOT_NATIVE et al.) - must be 0")

    # =======================================================================
    # PART B - the ledger, IN PLACE
    # =======================================================================
    log("\n[4] Binding identifiers in the ledger (IN PLACE, the 124 pattern)")
    log("  disposition rules, per identifier:")
    log("    absent                       -> APPEND")
    log("    present, tribe_id blank      -> UPDATE IN PLACE")
    log("    present, bound to a TRIBE and declared a mis-transcription")
    log("                                 -> REPOINT, reported loudly")
    log("    present, bound elsewhere     -> REFUSE, reported")

    reg_by_key = {(r["identifier_type"], r["identifier"]): r
                  for r in register_rows}
    ledger_new = []
    updated = 0
    lstats = Counter()

    for rr in register_rows:
        idtype, ident = rr["identifier_type"], rr["identifier"]
        tid, cname = rr["surrogate_entity_id"], rr["canonical_name"]
        if idtype == "NAME":
            # A name is not an identifier. The entity exists; nothing is bound,
            # so nothing can roll up through it and nothing can be mis-joined.
            lstats["NAME-keyed ruling - entity minted, NO ledger binding"] += 1
            continue

        existing = lidx.get((idtype, ident), [])
        rationale = (
            f"Ruled by {rr['ruled_by']} {rr['ruled_date']}: "
            f"INDIVIDUALLY NATIVE-OWNED FIRM. This is NOT a tribal, ANC or NHO "
            f"attribution and carries no ownership edge to any of them - the "
            f"entity is self-parented. Ruling text: "
            f"{rr['ruling_text']!r}. Applied by code/241 on {TODAY}.")

        bound = {(x.get("tribe_id") or "").strip() for x in existing}
        bound.discard("")

        if not existing:
            row = {k: "" for k in ledger_fields}
            row.update({
                "identifier_type": idtype, "identifier": ident,
                "tribe_id": tid, "canonical_name": cname,
                "legal_business_name": cname, "entity_class": CLASS,
                "attribution_method": "elijah_ruling",
                "confidence_tier": "A", "is_authority": "YES",
                "tier_rationale": rationale,
                "verified_date": rr["ruled_date"],
                "state": rr["state"],
                "source_file": "individual_native_prior_rulings.csv",
                "evidence_source_file": rr["ruling_source_file"],
                "evidence_url": rr["native_ownership_evidence_url"],
                "evidence_url_integrity":
                    "" if rr["native_ownership_evidence_url"] else
                    "No URL. The evidence is the owner's ruling on this "
                    "identifier, recorded in "
                    f"{rr['ruling_source_file']}; there is no retrievable page "
                    "that states the ownership.",
            })
            ledger_new.append(row)
            lidx.setdefault((idtype, ident), []).append(row)
            lstats[f"{idtype} APPENDED"] += 1
            continue

        declared = DECLARED_REPOINTS.get((idtype, ident))

        if bound and bound != {tid}:
            if declared and bound == {declared[0]}:
                for x in existing:
                    repointed.append({
                        "identifier_type": idtype, "identifier": ident,
                        "firm_name": cname,
                        "was_tribe_id": x.get("tribe_id", ""),
                        "was_canonical_name": x.get("canonical_name", ""),
                        "was_entity_class": x.get("entity_class", ""),
                        "was_tier": x.get("confidence_tier", ""),
                        "was_method": x.get("attribution_method", ""),
                        "was_tier_rationale": x.get("tier_rationale", ""),
                        "now_tribe_id": tid, "now_entity_class": CLASS,
                        "why": declared[1],
                        "flagged_date": TODAY,
                    })
                    x["tribe_id"] = tid
                    x["canonical_name"] = cname
                    x["entity_class"] = CLASS
                    x["attribution_method"] = "elijah_ruling"
                    x["confidence_tier"] = "A"
                    x["is_authority"] = "YES"
                    x["tier_rationale"] = (
                        rationale + " REPOINTED: this row previously bound the "
                        f"firm to {declared[0]} at tier X with the rationale "
                        f"'not a Native entity', which is the leading clause of "
                        f"the ruling read without its second half. The tribal "
                        f"binding the ruling was REFUSING had been left in "
                        f"place. See review/"
                        f"individual_native_ledger_repointed_{TODAY}.csv.")
                    updated += 1
                fired_repoints.add((idtype, ident))
                lstats[f"{idtype} REPOINTED off a wrong tribal binding"] += 1
            else:
                refused.append({
                    "identifier_type": idtype, "identifier": ident,
                    "reason": f"ID CONFLATION. Already bound to "
                              f"{sorted(bound)} by "
                              f"{sorted({x.get('attribution_method','') for x in existing})}. "
                              f"Correcting another pass's row is that pass's "
                              f"job; a silent repoint is how one entity "
                              f"becomes two. Nothing written.",
                    "ruling_source_file": rr["ruling_source_file"],
                    "refused_date": TODAY,
                    "refused_by": "code/241_promote_individual_native_firms_in_place.py",
                })
                lstats[f"{idtype} REFUSED - bound elsewhere"] += 1
            continue

        if bound == {tid}:
            # A DECLARED repoint that is already on disk has FIRED. Without
            # this the fail-closed guard aborts every re-run, which trains the
            # next agent to delete the guard - and a guard that cannot survive
            # idempotence is a guard that will not be there when it matters.
            if declared:
                fired_repoints.add((idtype, ident))
                lstats[f"{idtype} declared repoint ALREADY APPLIED"] += 1
            else:
                lstats[f"{idtype} already correct - idempotent skip"] += 1
            continue

        # tribe_id blank: UPDATE IN PLACE. This is where the 33 tier-X and 9
        # tier-C rows move.
        #
        # THE TIER-X ROWS ARE NOT BEING REVERSED. Their X says "excluded from
        # the TRIBAL universe" - `exclusion_reason = individually_native_owned`
        # from hci_analysis.do, which is the SAME ruling being applied here.
        # The exclusion is preserved verbatim in exclusion_id /
        # exclusion_evidence and the firm remains outside every tribal roll-up,
        # because its new entity has no ownership edge to one. What changes is
        # that the row now names the entity that DOES own the dollars instead
        # of naming nobody.
        for x in existing:
            was_tier = x.get("confidence_tier", "")
            x["tribe_id"] = tid
            x["canonical_name"] = cname
            x["entity_class"] = CLASS
            x["attribution_method"] = "elijah_ruling"
            x["confidence_tier"] = "A"
            x["is_authority"] = "YES"
            x["tier_rationale"] = rationale + (
                f" Previous state: tier {was_tier}"
                + (f", exclusion {x.get('exclusion_id')} "
                   f"(individually_native_owned)" if x.get("exclusion_id")
                   else "")
                + ". The tribal EXCLUSION stands and is preserved in "
                  "exclusion_id/exclusion_evidence: this firm is still outside "
                  "every tribal, ANC and NHO total. The row now names the "
                  "entity that holds the dollars instead of naming nobody.")
            if not (x.get("legal_business_name") or "").strip():
                x["legal_business_name"] = cname
            updated += 1
            lstats[f"{idtype} UPDATED IN PLACE (was tier {was_tier}, unbound)"] += 1

    for k, v in lstats.most_common():
        log(f"  {k:58s} {v:>4}")
    log(f"\n  ledger rows appended        : {len(ledger_new)}")
    log(f"  ledger rows updated in place: {updated}")

    # FAIL CLOSED on the declared repoints.
    missed = set(DECLARED_REPOINTS) - fired_repoints
    if missed:
        raise SystemExit(
            f"ABORT: {len(missed)} DECLARED repoints matched nothing: "
            f"{sorted(missed)}. A correction that does not fire is worse than "
            f"no correction - it reads as a decision that was applied. Either "
            f"another pass already fixed those rows (check them, then remove "
            f"them from DECLARED_REPOINTS with a note) or the key is wrong.")
    log(f"  guard: all {len(DECLARED_REPOINTS)} declared repoints fired "
        f"(fail-closed)")

    # =======================================================================
    # PART C - invariants before any write
    # =======================================================================
    log("\n[5] Invariants")
    combined = ledger + ledger_new
    idx2 = {}
    for r in combined:
        idx2.setdefault(((r["identifier_type"] or "").upper(),
                         (r["identifier"] or "").upper()), set()).add(
            (r.get("tribe_id") or "").strip())
    broken = {k: v for k, v in idx2.items() if len({x for x in v if x}) > 1}
    log(f"  identifier keys bound to >1 entity : {len(broken)}  (must be 0)")
    if broken:
        for k, v in list(broken.items())[:10]:
            log(f"      {k} -> {sorted(v)}")
        log("\n  *** INVARIANT WOULD BREAK - refusing to write. ***")
        return

    RULED = D.RULED_METHODS
    def n_ruled(rows):
        return sum(1 for r in rows if r.get("confidence_tier") == "A"
                   and (r.get("attribution_method") or "").strip() in RULED)
    before = n_ruled(load(LEDGER))
    after = n_ruled(combined)
    log(f"  tier_A_ruled : {before:,} -> {after:,} ({after - before:+,})")
    if after < before:
        log("\n  *** tier_A_ruled FELL - refusing to write. ***")
        return

    tierA_no_entity = sum(1 for r in combined
                          if r.get("confidence_tier") == "A"
                          and not (r.get("tribe_id") or "").strip())
    log(f"  tierA_without_entity : {tierA_no_entity}  (gate requires 0)")
    if tierA_no_entity:
        log("\n  *** would leave a tier-A row attributed to nobody. Refusing. ***")
        return

    x_naming_owner = sum(
        1 for r in combined if r.get("confidence_tier") == "X"
        and "owner is " in (r.get("tier_rationale") or "").lower()
        and "not in the spine" not in (r.get("tier_rationale") or "").lower())
    log(f"  X_rows_naming_an_owner : {x_naming_owner}  (gate requires 0)")
    if x_naming_owner:
        return

    dupe = len(spine) + len(added) - len({r["tribe_id"] for r in spine + added})
    log(f"  spine_duplicate_ids : {dupe}  (gate requires 0)")
    if dupe:
        return

    # =======================================================================
    log("\n[6] Result")
    log(f"  spine : {len(spine):,} -> {len(spine) + len(added):,} entities "
        f"({len(added):+} in class {CLASS!r})")
    moved_rows = sum(int(r["n_contract_rows"]) for r in register_rows)
    moved_usd = sum(float(r["total_obligations_usd"]) for r in register_rows)
    log(f"  prime rows now carrying an entity in this class : {moved_rows:,}")
    log(f"  obligations off the discard pile                : ${moved_usd:,.2f}")
    log(f"  ...and NOT added to any tribal, ANC or NHO total. They never were "
        f"in one.")
    log(f"  register rows : {len(register_rows)}")
    log(f"  publish_name = 1 : "
        f"{sum(1 for r in register_rows if r['publish_name'] == '1')} of "
        f"{len(register_rows)}")
    log(f"  publish_federal_identifier = 1 : "
        f"{sum(1 for r in register_rows if r['publish_federal_identifier'] == '1')}")
    log(f"  evidence with a retrieved URL : "
        f"{sum(1 for r in register_rows if r['native_ownership_evidence_url'])}")

    if check:
        log("\n  --check: nothing written.")
        LOGS.mkdir(parents=True, exist_ok=True)
        (LOGS / "241_promote_individual_native_firms.check.log").write_text(
            "\n".join(LOG_LINES), encoding="utf-8")
        return

    # =======================================================================
    log("\n[7] Writing (backup, .part, rename)")
    # Re-read immediately before writing so a concurrent agent's appends are
    # not clobbered. AGENTS.md: "Re-read the spine immediately before writing
    # so a concurrent agent cannot be clobbered."
    spine_now = load(SPINE)
    if len(spine_now) != len(spine):
        log(f"  *** spine changed under us: {len(spine)} -> {len(spine_now)}. "
            f"Re-basing the append onto the current file. ***")
        cur = {r["tribe_id"] for r in spine_now}
        clash = [r for r in added if r["tribe_id"] in cur]
        if clash:
            log("  *** id clash after re-read - refusing to write. ***")
            return
        spine_fields = list(spine_now[0].keys())
    write_atomic(SPINE, spine_now + added, spine_fields)

    ledger_now = load(LEDGER)
    if len(ledger_now) != len(ledger):
        log(f"  *** ledger changed under us: {len(ledger)} -> "
            f"{len(ledger_now)}. Refusing to write a stale ledger. Re-run. ***")
        return
    write_atomic(LEDGER, combined, ledger_fields)

    reg_fields = list(register_rows[0].keys())
    write_atomic(REGISTER, register_rows, reg_fields)
    if exclusion_pairs:
        write_atomic(EXCLUSION_PAIRS, exclusion_pairs,
                     list(exclusion_pairs[0].keys()))

    REVIEW.mkdir(parents=True, exist_ok=True)
    if refused:
        write_atomic(REVIEW / f"individual_native_promotion_refused_{TODAY}.csv",
                     refused, list(refused[0].keys()), backup=False)
    if repointed:
        write_atomic(REVIEW / f"individual_native_ledger_repointed_{TODAY}.csv",
                     repointed, list(repointed[0].keys()), backup=False)
    if name_privacy:
        write_atomic(
            REVIEW / f"individual_native_canonical_name_privacy_{TODAY}.csv",
            name_privacy, list(name_privacy[0].keys()), backup=False)
    if collision_risk:
        write_atomic(
            REVIEW / f"individual_native_name_collision_risk_{TODAY}.csv",
            collision_risk, list(collision_risk[0].keys()), backup=False)

    # ---- VERIFY BY RE-READING. Idempotence is not enough on this machine. --
    log("\n[8] Verify by RE-READING (standing rule 4)")
    sp = load(SPINE)
    lg = load(LEDGER)
    rg = load(REGISTER)
    n_cls = sum(1 for r in sp if r.get("entity_class") == CLASS)
    log(f"  spine on disk    : {len(sp):,} rows, {n_cls} in class")
    log(f"  ledger on disk   : {len(lg):,} rows")
    log(f"  register on disk : {len(rg):,} rows")
    bad = [r for r in sp if r.get("entity_class") == CLASS
           and ((r.get("parent_native_entity") or "").strip()
                or r.get("ultimate_parent_entity_id") != r.get("tribe_id"))]
    if bad:
        log(f"  *** {len(bad)} class rows are NOT self-parented or carry a "
            f"parent_native_entity. This must be 0. ***")
    else:
        log("  every class row: parent_native_entity NULL, self-parented  OK")
    # Compare against the REGISTER, not against this run's `added`: on an
    # idempotent re-run `added` is 0 and the 45 rows are already there.
    if n_cls != len(register_rows):
        log(f"  *** expected {len(register_rows)} class rows, found {n_cls}. "
            f"Another agent may have written between the write and the "
            f"re-read. ***")
    else:
        log(f"  spine class count matches the register: {n_cls}  OK")

    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "241_promote_individual_native_firms.log").write_text(
        "\n".join(LOG_LINES), encoding="utf-8")
    log("\n  now run:  py -3 code/242_build_individual_native_firm_contracts.py")
    log("  then   :  py -3 code/62_no_regression_check.py")


if __name__ == "__main__":
    main()
