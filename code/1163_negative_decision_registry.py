#!/usr/bin/env python3
"""
1163 - the NEGATIVE-DECISION REGISTRY.  Internal infrastructure, not a product.

    py -3 code/1163_negative_decision_registry.py report    # what already exists
    py -3 code/1163_negative_decision_registry.py seed      # APPEND seed events
    py -3 code/1163_negative_decision_registry.py build     # derive the view
    py -3 code/1163_negative_decision_registry.py check     # the release gate
    py -3 code/1163_negative_decision_registry.py selftest  # WATCH the gate fire
    py -3 code/1163_negative_decision_registry.py verify    # exit 1 on violation

WHAT THIS IS NOT
----------------
It is not a table of `is_native = false`.  The owner ruled that claim out and
the reason is the whole design:

    "I would not create a table that says is_native = false.  That claim is too
     broad and will create its own serious errors."

Ruling that **United Tribes Technical College is not owned by United Auburn**
says nothing about whether UTTC is Native - it is a tribal college.  Ruling that
**Goldbelt Hawk is not owned by Tlingit & Haida** does not make Goldbelt
non-Native - it is an ANCSA corporation and its real owner, Goldbelt,
Incorporated, is already in the spine.  Ruling that a UEI is **out of scope for
the tribally-owned collection** says nothing about the firm's owner's identity;
31 of the 123 seeded exclusions are individually Native-owned firms, which is
precisely why they are out of a *tribal* collection and precisely why the
exclusion is not a statement about them.

Every row here rules out ONE OF FOUR THINGS and never an identity:

    a RELATIONSHIP        owned_by / controlled_by
    an IDENTITY MATCH     same_entity_as  ("this record is not THAT entity")
    a CLASSIFICATION      native_ownership_status, and only ever as
                          INSUFFICIENT_EVIDENCE - never as a finding
    DATASET ELIGIBILITY   eligible_for_collection

ONE SOURCE OF TRUTH, NOT A PARALLEL DATASET
--------------------------------------------
The owner's second instruction:

    "The best implementation is probably not a completely new parallel dataset.
     Your link layer already has proposed, contested, denied, unresolved and
     verified states.  I would strengthen that layer with structured denial
     reasons, temporal scope, evidence, supersession and dataset-eligibility
     predicates, then generate cedar_negative_constraints as a derived view."

MEASURED, before adding anything.  `data/spine/cedar_source_record_links.csv`
holds 585 rows and does carry those five states - `proposed` 570, `contested` 7,
`denied` 5, `unresolved` 2, `verified` 1 - plus `polarity` (affirm 580 / deny 5)
and `supersedes_link_id`.  What it does NOT carry, and what the negative half
needs, is: a closed reason vocabulary (its `status_reason` is free prose), any
temporal scope at all (no `valid_from`, no `valid_to`, no `as_of_date`), an
evidence-strength grade, a dataset-eligibility predicate, a hard/soft
distinction, or a recheck date.  And it covers exactly ONE dataset:
`source_dataset` is `fr_recognized_entities` on all 585 rows.

Everything else Cedar has ruled out is scattered across the shapes each pass
happened to invent - `key_review_disposition` in `np_orgs.csv`, `disposition`
in a 1079 triage review file, `action=UNLINK` in the correction register,
`exclusion_reason` in `cedar_exclusion_rulings.csv`, `agrees_with_shipped=0` in
a temporal as-of file.  Nine shapes, no shared vocabulary, no shared temporal
model, and nothing that can answer "is this pair ruled out?" in one call.

So `cedar_decision_events.csv` is that layer's negative half made explicit and
extended to every dataset, and `cedar_negative_constraints.csv` is a DERIVED
VIEW rebuilt from it on every `build` - never hand-edited, and it says so in its
own first data column.  The nine existing shapes are SEEDS, imported here with
their own file named in `source_table`, not re-authored.  Nothing was invented:
`seed` reads only from disk and `verify` fails if any seeded event's natural key
cannot be re-derived from the file it claims.

THE FIVE RULES THAT MAKE IT SAFE
---------------------------------
1.  HARD vs SOFT, and ONLY HARD AUTO-SUPPRESSES.  The owner's reason is the one
    encoded: *"otherwise the system will fossilize old research gaps and create
    false negatives."*  A name mismatch, a weak geographic conflict, an
    unsuccessful search and "no evidence found" are SOFT - they are the state of
    Cedar's research, not the state of the world.  An authoritative identifier
    conflict, two different legal entities, an adjudicated false match and an
    ownership contradicted on a date are HARD.
      Hardness is not a property of the reason code alone: a NAME_COLLISION a
    machine noticed is soft, and the same NAME_COLLISION after the owner ruled
    on it is hard.  `hardness()` states that in one place and `verify` proves no
    row escapes it.
2.  `INSUFFICIENT_EVIDENCE` triggers review and NEVER becomes a permanent
    negative fact.  It is forced SOFT, forced `review_status=PENDING_REVIEW`,
    and forced `suppresses=N`, whatever the row says.
3.  NO SILENT OVERWRITE.  New evidence appends a superseding event pointing at
    the original through `supersedes_decision_id`; the original is never edited.
    A superseding event only takes effect once `review_status=ADJUDICATED`; a
    `PROPOSED_SUPERSEDE` leaves the original standing and lands in the queue.
    Append-only is enforced, not asked for: `_decision_events_ledger.json` holds
    a row hash per decision_id and `verify` fails on any edit or deletion.
4.  TEMPORAL.  A company not tribally owned in 2018 can be acquired in 2024, so
    every ownership decision is date-bounded and carries a `recheck_after`.
    Permanent identity denials - two definitively different legal organisations
    - do not expire, and `verify` asserts they carry no `valid_to`.  A passed
    `recheck_after` does not un-suppress a hard constraint (evidence does not
    decay into permission); it marks it `ACTIVE_STALE` and queues it.
5.  RELEASE CHECK.  No published row may violate an active hard constraint.
    `check` reads `dist/customer/*.csv` and `selftest` WATCHES IT FAIL against a
    synthetic violating row in a temporary directory, because a gate nobody has
    watched fail is not known to work.  `846_session_audit.py` runs `check`.

HOW A CONSTRAINT NAMES ITS TARGET COLUMN
-----------------------------------------
`dataset_scope` is `<collection>` or `<collection>:<column>`.  The qualified
form exists for one measured reason: `429_apply_asof_ownership_status.py`
deliberately keeps `cedar_uid` on a `CONTRADICTED_AS_OF` row - it is Cedar's
CURRENT attribution and it is correct - and publishes the historical answer in
`owner_as_of_transaction_cedar_uid`.  A gate that read `cedar_uid` there would
fire on a considered design decision.  So those 411 events scope to
`contractors:owner_as_of_transaction_cedar_uid` and the gate reads that column.

WHAT IS DELIBERATELY NOT DONE
------------------------------
No `cedar_uid` is minted, none is reused, no source row is edited, no shelf is
touched.  This collection is NOT one of the twelve
(`cedar_publication.STOREFRONT_SHELVES`) and must never appear on one.  An agent
ruling may not mint tier A - `docs/ENTITY_MATCH_RULES.md` rule 8 - and no seed
here promotes anything: every event only ever WITHDRAWS or QUESTIONS.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

SCRIPT = "code/1163_negative_decision_registry.py"
ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
RAW = ROOT / "data" / "raw"
REVIEW = ROOT / "review"
DIST = ROOT / "dist" / "customer"

EVENTS = SPINE / "cedar_decision_events.csv"
VIEW = SPINE / "cedar_negative_constraints.csv"
LEDGER = SPINE / "_decision_events_ledger.json"
QUEUE = REVIEW / "negative_decision_review_queue.csv"

TODAY = date.today().isoformat()
csv.field_size_limit(10 ** 9)

try:                                    # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------------------------------------------------------------------------
# THE SCHEMA.  The first nineteen columns are the owner's specification, in the
# owner's order, unchanged.  Three are appended and the reason is Cedar's own
# convention: a registry whose rows cannot be traced back to the file they were
# read from cannot be re-derived, and `verify` re-derives every seeded row's
# natural key from `source_table`.  `evidence_id` holds evidence; it is not a
# place to hide provenance.
# ---------------------------------------------------------------------------
COLS = [
    "decision_id", "subject_record_id", "subject_entity_id",
    "candidate_cedar_uid",
    "predicate", "decision", "reason_code", "reason_detail", "dataset_scope",
    "valid_from", "valid_to", "as_of_date", "evidence_id", "evidence_strength",
    "review_status", "reviewer", "decided_at", "supersedes_decision_id",
    "recheck_after",
    # appended, and named as appended
    "source_table", "built_by_script", "built_date",
]

PREDICATES = {
    "same_entity_as": {"DENIED"},
    "owned_by": {"DENIED"},
    "controlled_by": {"DENIED"},
    "eligible_for_collection": {"DENIED"},
    "native_ownership_status": {"INSUFFICIENT_EVIDENCE"},
    "duplicate_of": {"VERIFIED"},
}

REASON_CODES = (
    "NAME_COLLISION", "GEOGRAPHY_CONFLICT", "IDENTIFIER_CONFLICT",
    "DIFFERENT_LEGAL_ENTITY", "WRONG_ENTITY_CLASS",
    "OWNERSHIP_CONTRADICTED_AS_OF", "OWNERSHIP_ENDED",
    "NATIVE_SERVING_NOT_NATIVE_CONTROLLED", "TRIBAL_GOVERNMENT_NOT_ENTERPRISE",
    "NO_QUALIFYING_CONTROL_EVIDENCE", "CERTIFICATION_EXPIRED",
    "OUT_OF_DATASET_SCOPE", "DUPLICATE_SOURCE_RECORD", "INSUFFICIENT_EVIDENCE",
)

# --- rule 1.  Hard vs soft, in ONE place. ----------------------------------
#: Hard by their own nature.  Each is a fact about the WORLD that does not
#: become false because Cedar looked harder: an authoritative registry says two
#: identifiers are different; two legal organisations are two legal
#: organisations; a class that structurally cannot hold the relation cannot
#: hold it; an ownership was contradicted, or ended, on a date; a record is a
#: duplicate of another record; a scope decision is definitional.
HARD_BY_NATURE = frozenset({
    "IDENTIFIER_CONFLICT", "DIFFERENT_LEGAL_ENTITY", "WRONG_ENTITY_CLASS",
    "OWNERSHIP_CONTRADICTED_AS_OF", "OWNERSHIP_ENDED",
    "TRIBAL_GOVERNMENT_NOT_ENTERPRISE", "DUPLICATE_SOURCE_RECORD",
    "OUT_OF_DATASET_SCOPE", "CERTIFICATION_EXPIRED",
})

#: Never hard, however strong the evidence looks.  Each is a fact about
#: CEDAR'S RESEARCH, not about the world.  "We found no qualifying control
#: evidence" and "this is Native-serving, we saw no Native control" are the
#: exact shapes the owner named: fossilize them and the next matcher inherits a
#: 2026 research gap as a 2030 fact.
NEVER_HARD = frozenset({
    "INSUFFICIENT_EVIDENCE", "NO_QUALIFYING_CONTROL_EVIDENCE",
    "NATIVE_SERVING_NOT_NATIVE_CONTROLLED",
})

#: Hard ONLY once a named person adjudicated it.  A machine noticing that two
#: names collide is a question.  The owner ruling on that same collision -
#: "United Tribes Technical College -> United Auburn" - is an answer.  Same
#: reason code, different standing, and the difference is a human.
HARD_IF_ADJUDICATED = frozenset({"NAME_COLLISION", "GEOGRAPHY_CONFLICT"})

EVIDENCE_STRENGTH = (
    "ADJUDICATED_BY_OWNER",     # a named person ruled on this pair
    "AUTHORITATIVE_REGISTRY",   # CAGE, SAM, IRS BMF, the Federal Register list
    "STRUCTURAL_RULE",          # a class cannot hold the relation (ANCSA r.2)
    "SOURCE_SELF_PUBLISHED",    # the publisher's own words about itself
    "ALGORITHMIC",              # a matcher's verdict, unreviewed
    "ABSENCE_OF_EVIDENCE",      # we looked and found nothing
)

REVIEW_STATUS = ("ADJUDICATED", "AUTO", "PENDING_REVIEW", "PROPOSED_SUPERSEDE")

#: A permanent identity denial.  Two definitively different legal
#: organisations do not become the same organisation later, so rule 4's expiry
#: does not apply - unless the original ruling was WRONG, which is a
#: supersession, not an expiry.
PERMANENT = frozenset({"DIFFERENT_LEGAL_ENTITY", "IDENTIFIER_CONFLICT"})

#: Ownership can change.  Every ownership decision gets a recheck horizon.
RECHECK_DAYS = 365
OWNERSHIP_PREDICATES = frozenset({"owned_by", "controlled_by"})


def hardness(ev: dict) -> tuple[str, str]:
    """(HARD|SOFT, why).  The single definition.  Nothing else may decide it."""
    rc = (ev.get("reason_code") or "").strip()
    dec = (ev.get("decision") or "").strip()
    rs = (ev.get("review_status") or "").strip()
    reviewer = (ev.get("reviewer") or "").strip()
    if dec == "INSUFFICIENT_EVIDENCE":
        return "SOFT", ("rule 2 - INSUFFICIENT_EVIDENCE triggers review and "
                        "never becomes a permanent negative fact")
    if rc in NEVER_HARD:
        return "SOFT", (f"{rc} is a statement about Cedar's research, not "
                        f"about the world; hardening it fossilizes a gap")
    if rc in HARD_BY_NATURE:
        return "HARD", f"{rc} is hard by its own nature"
    if rc in HARD_IF_ADJUDICATED:
        if rs == "ADJUDICATED" and reviewer:
            return "HARD", f"{rc} adjudicated by {reviewer}"
        return "SOFT", (f"{rc} is a question until a named person answers it "
                        f"(review_status={rs or 'blank'}, "
                        f"reviewer={reviewer or 'none'})")
    return "SOFT", f"{rc or 'blank'} is not in any hard class - default SOFT"


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def read_csv(p) -> list[dict]:
    p = Path(p)
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p: Path, cols, rows) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, p)


def did(*parts) -> str:
    """A deterministic decision_id from the event's NATURAL key.

    Deterministic so `seed` is idempotent: re-running appends only ids the file
    does not already carry, which is how an append-only table stays
    append-only under a re-run.  It is NOT a content hash - the natural key is
    what the event is ABOUT, so a corrected reason_detail on the same pair is
    an edit the ledger will catch rather than a silent second row.
    """
    h = hashlib.sha1("|".join(str(p) for p in parts).encode("utf-8"))
    return "NDR-" + h.hexdigest()[:12].upper()


def row_hash(r: dict) -> str:
    return hashlib.sha1("|".join((r.get(c) or "") for c in COLS)
                        .encode("utf-8")).hexdigest()[:16]


def ev(**kw) -> dict:
    r = {c: "" for c in COLS}
    r.update(kw)
    r["built_by_script"] = SCRIPT
    r["built_date"] = kw.get("built_date") or TODAY
    if not r["decided_at"]:
        r["decided_at"] = r["as_of_date"] or TODAY
    # rule 2, applied at construction so no seeder can forget it
    if r["decision"] == "INSUFFICIENT_EVIDENCE":
        r["review_status"] = "PENDING_REVIEW"
    # rule 4, applied at construction
    if r["predicate"] in OWNERSHIP_PREDICATES and not r["recheck_after"]:
        base = r["as_of_date"] or TODAY
        try:
            r["recheck_after"] = (date.fromisoformat(base[:10])
                                  + timedelta(days=RECHECK_DAYS)).isoformat()
        except ValueError:
            r["recheck_after"] = (date.fromisoformat(TODAY)
                                  + timedelta(days=RECHECK_DAYS)).isoformat()
    if r["reason_code"] in PERMANENT and r["predicate"] == "same_entity_as":
        r["valid_to"] = ""
        r["recheck_after"] = ""
    return r


def load_events() -> list[dict]:
    """Read the ledger, normalised to the CURRENT schema.

    A column added to `COLS` after some events were written is absent from
    those rows, and every rule below indexes by name. Rebuilding each row from
    `COLS` fills the gap with a blank and NAMES what it filled, rather than
    letting a later `KeyError` - or worse, a silent `.get()` default - decide
    whether an old event is bound by a new rule.
    """
    rows = read_csv(EVENTS)
    if not rows:
        return []
    added = [c for c in COLS if c not in rows[0]]
    if added:
        print(f"    schema note: {len(rows)} event(s) predate the column(s) "
              f"{', '.join(added)} and read blank there")
    return [{c: (r.get(c) or "") for c in COLS} for r in rows]


# ===========================================================================
# STAGE: report - what the existing layer already carries.  No writes.
# ===========================================================================
def stage_report() -> int:
    print("  1163  what the ruling / link layer ALREADY carries, measured\n")

    links = read_csv(SPINE / "cedar_source_record_links.csv")
    print(f"  data/spine/cedar_source_record_links.csv   {len(links)} rows")
    for c in ("source_dataset", "link_status", "polarity", "authority_basis"):
        cc = Counter((r.get(c) or "") for r in links)
        print(f"      {c:18s} " + "  ".join(f"{k or '(blank)'}={v}"
                                            for k, v in cc.most_common(6)))
    have = [c for c in ("valid_from", "valid_to", "as_of_date", "reason_code",
                        "evidence_strength", "dataset_scope", "recheck_after")
            if links and c in links[0]]
    print(f"      columns the negative half needs and it LACKS: "
          f"{', '.join(c for c in ('valid_from','valid_to','as_of_date','reason_code','evidence_strength','dataset_scope','recheck_after') if c not in have)}")
    print(f"      it DOES already carry: supersedes_link_id="
          f"{'yes' if links and 'supersedes_link_id' in links[0] else 'no'}\n")

    for path, key in (
        (SPINE / "cedar_exclusion_rulings.csv", "exclusion_reason"),
        (SPINE / "cedar_rulings.csv", "ruling"),
        (CLEAN / "cedar_correction_register.csv", "action"),
    ):
        rows = read_csv(path)
        cc = Counter((r.get(key) or "") for r in rows)
        print(f"  {path.relative_to(ROOT)}   {len(rows)} rows")
        print(f"      {key}: " + "  ".join(f"{k}={v}"
                                           for k, v in cc.most_common(8)))
    print()
    np = read_csv(CLEAN / "np_orgs.csv")
    cc = Counter((r.get("key_review_disposition") or "") for r in np)
    print(f"  data/clean/np_orgs.csv   {len(np)} rows")
    print("      key_review_disposition: " + "  ".join(
        f"{k or '(blank)'}={v}" for k, v in cc.most_common(8)))
    print(f"      rows carrying a placename_refusal_rung: "
          f"{sum(1 for r in np if (r.get('placename_refusal_rung') or '').strip())}")
    print("\n  Nine shapes, no shared vocabulary, no shared temporal model.")
    print("  That is what cedar_decision_events.csv unifies; it does not "
          "replace any of them.")
    return 0


# ===========================================================================
# STAGE: seed.  Reads ONLY from disk.  Invents nothing.
# ===========================================================================
def _seed_goldbelt_lookup() -> list[dict]:
    """The 23 rows keyed to Tlingit & Haida, and the owner's own ANCSA ruling.

    `anc_tribal_subsidiary_lookup.csv` carries 23 rows whose
    `parent_entity_type` names the ANCSA corporation `ANC_VILLAGE_GOLDBELT`
    while `parent_entity_id` is `AKNF-TLNGHD-00-SEALSK`, Tlingit & Haida, a
    tribal GOVERNMENT.  `docs/ANCSA_OWNERSHIP_RULING.md` rule 2 - "a village
    government never owns an ANC" - and rule 4 - the tie is ancestral
    association, never a corporate edge - forbid it.  Goldbelt, Incorporated is
    the ANCSA urban corporation for Juneau and is already the spine's
    `ANVC-GLDBLT-00`.

    HARD, and not because a name collided: an entity class that structurally
    cannot hold the relation cannot hold it.  The denial is about the EDGE.
    Goldbelt is unambiguously Native and so is Tlingit & Haida.
    """
    src = RAW / "external" / "anc_tribal_subsidiary_lookup.csv"
    out = []
    for r in read_csv(src):
        if "GOLDBELT" not in (r.get("parent_entity_type") or "").upper():
            continue
        pid = (r.get("parent_entity_id") or "").strip()
        if pid != "AKNF-TLNGHD-00-SEALSK":
            continue
        sub = (r.get("subsidiary_name") or "").strip()
        out.append(ev(
            decision_id=did("goldbelt-lookup", sub, pid),
            subject_record_id=sub,
            subject_entity_id="",
            candidate_cedar_uid=pid,
            predicate="owned_by", decision="DENIED",
            reason_code="WRONG_ENTITY_CLASS",
            reason_detail=(
                f"'{sub}' is a Goldbelt, Incorporated operating company. "
                f"Tlingit & Haida ({pid}) is a tribal GOVERNMENT and a village "
                f"or tribal government never owns an ANCSA corporation "
                f"(ANCSA_OWNERSHIP_RULING rules 2 and 4); the real owner is "
                f"the spine's ANVC-GLDBLT-00, Goldbelt, Incorporated. This "
                f"denies the EDGE only - Goldbelt is an ANCSA corporation and "
                f"is Native."),
            dataset_scope="nest",
            as_of_date=(r.get("fetched_date") or "").strip(),
            evidence_id=(r.get("source_url") or "").strip(),
            evidence_strength="STRUCTURAL_RULE",
            review_status="ADJUDICATED", reviewer="Elijah Moreno",
            decided_at="2026-08-26",
            source_table="data/raw/external/anc_tribal_subsidiary_lookup.csv",
        ))
    return out


def _seed_goldbelt_nest() -> list[dict]:
    """The same ruling, at the grain the EXPORT publishes.

    `1157` fixed the lookup path.  Measured on `data/clean/nest_enterprises.csv`
    2026-09-02 the OWNERV6 path still keys Goldbelt-named enterprises to
    Tlingit & Haida's `CE-0006B-0K`, and `dist/customer/nest.csv` ships them.
    An event keyed to `enterprise_id` is what the release gate can actually
    test, so the ruling is recorded at both grains.
    """
    out = []
    for r in read_csv(CLEAN / "nest_enterprises.csv"):
        name = (r.get("enterprise_name") or "").strip()
        hub = (r.get("owner_hub_cedar_uid") or "").strip()
        if not name.upper().startswith("GOLDBELT") or hub != "CE-0006B-0K":
            continue
        eid = (r.get("enterprise_id") or "").strip()
        out.append(ev(
            decision_id=did("goldbelt-nest", eid, hub),
            subject_record_id=eid,
            subject_entity_id=(r.get("enterprise_existing_cedar_uid") or "").strip(),
            candidate_cedar_uid=hub,
            predicate="owned_by", decision="DENIED",
            reason_code="WRONG_ENTITY_CLASS",
            reason_detail=(
                f"'{name}' is a Goldbelt, Incorporated operating company. "
                f"CE-0006B-0K is Tlingit & Haida, a tribal government; "
                f"ANCSA_OWNERSHIP_RULING rules 2 and 4 forbid the edge and "
                f"make the real tie ancestral association. Correct owner: the "
                f"spine's ANVC-GLDBLT-00 / CE-0008Y-WE."),
            dataset_scope="nest",
            as_of_date="2026-08-26",
            evidence_id="docs/ANCSA_OWNERSHIP_RULING.md",
            evidence_strength="STRUCTURAL_RULE",
            review_status="ADJUDICATED", reviewer="Elijah Moreno",
            decided_at="2026-08-26",
            source_table="data/clean/nest_enterprises.csv",
        ))
    return out


def _seed_uttc() -> list[dict]:
    """United Tribes Technical College is not owned by United Auburn.

    The owner's own ten-row NEST review, quoted verbatim in
    `code/1157_nest_relationship_resolution_qa.py`: *"The ten-row review caught
    Goldbelt Hawk -> Tlingit & Haida and United Tribes Technical College ->
    United Auburn."*  The mechanism is the token `united`, which has been in
    `cedar_domain.NAME_TRAPS` since 2026-08-07 with this exact case named in
    its own comment.

    HARD, and only because a person ruled it - a bare NAME_COLLISION is soft.
    UTTC is a tribal college in Bismarck ND chartered by five Dakota nations
    and it already holds its own Cedar entity (`TCU-NTDTRB-00`).  The denial is
    about the OWNER, and says nothing about UTTC being Native.
    """
    out = []
    for r in read_csv(CLEAN / "nest_enterprises.csv"):
        if (r.get("enterprise_name") or "").strip().lower() \
                != "united tribes technical college":
            continue
        hub = (r.get("owner_hub_cedar_uid") or "").strip()
        eid = (r.get("enterprise_id") or "").strip()
        out.append(ev(
            decision_id=did("uttc", eid, hub),
            subject_record_id=eid,
            subject_entity_id=(r.get("enterprise_existing_cedar_uid") or "").strip(),
            candidate_cedar_uid=hub,
            predicate="owned_by", decision="DENIED",
            reason_code="NAME_COLLISION",
            reason_detail=(
                "United Tribes Technical College (Bismarck ND, "
                "TCU-NTDTRB-00) is not owned by United Auburn Indian "
                "Community (CA). The only thing they share is the token "
                "'united', which cedar_domain.NAME_TRAPS has listed since "
                "2026-08-07 naming this exact pair. Owner-ruled in the ten-row "
                "NEST review, quoted in code/1157. Denies the OWNER only; UTTC "
                "is a tribal college and is Native."),
            dataset_scope="nest",
            as_of_date="2026-09-02",
            evidence_id="code/1157_nest_relationship_resolution_qa.py (owner "
                        "quote, ten-row NEST review)",
            evidence_strength="ADJUDICATED_BY_OWNER",
            review_status="ADJUDICATED", reviewer="Elijah Moreno",
            decided_at="2026-09-02",
            source_table="data/clean/nest_enterprises.csv",
        ))
    return out


def _seed_placename() -> list[dict]:
    """`1155`'s place-name refusals.  SOFT, and that is the point.

    A refusal says only "this filer is not THAT nation" - the token that
    matched is the filer's own IRS BMF city, or is qualified as geography
    inside its own name.  `1155`'s own docstring: *"A refusal says ONLY 'this
    is not THAT entity.' It is not a finding that the organisation is not
    Native. Several demoted rows plainly deserve their own spine entity."*

    They stay SOFT here because the reason code is NAME_COLLISION and no person
    adjudicated the individual row - `1155` measured its rungs on a 210-row
    sample, it did not rule 517 organisations one by one.  They do not
    auto-suppress: `cedar_publication` already MASKs the key, which is the
    right treatment, and this registry records WHY without hardening it into a
    permanent negative about an organisation nobody looked at.
    """
    out = []
    for r in read_csv(CLEAN / "np_orgs.csv"):
        rung = (r.get("placename_refusal_rung") or "").strip()
        if not rung:
            continue
        eink = (r.get("EIN") or r.get("ein") or "").strip()
        uid = (r.get("cedar_uid") or "").strip()
        tid = (r.get("tribe_id") or "").strip()
        out.append(ev(
            decision_id=did("placename", eink, uid or tid),
            subject_record_id=eink,
            subject_entity_id="",
            candidate_cedar_uid=uid or tid,
            predicate="same_entity_as", decision="DENIED",
            reason_code="NAME_COLLISION",
            reason_detail=((r.get("placename_refusal_basis") or "")[:600]
                           or f"{rung}: place-name collision"),
            dataset_scope="nonprofits",
            as_of_date=(r.get("placename_refusal_date") or "2026-09-02").strip(),
            evidence_id=f"code/1155_np_placename_precision.py rung {rung}",
            evidence_strength="ALGORITHMIC",
            review_status="PENDING_REVIEW", reviewer="",
            decided_at=(r.get("placename_refusal_date") or "2026-09-02").strip(),
            recheck_after="",
            source_table="data/clean/np_orgs.csv",
        ))
    return out


def _seed_1079() -> list[dict]:
    """The 1079 quarantine WITHDRAWs, including AVCP RHA -> ASRC.

    743 identifier-to-entity attributions withdrawn 2026-09-02, all applied.
    The named case from the funding review is UEI `WSPWNRKSH5N1`, `AVCP
    REGIONAL HOUSING AUTHORITY`, attributed to Arctic Slope Regional
    Corporation by `cluster_v3` on the single shared token `regional`.

    MOSTLY SOFT, and deliberately.  428 + 225 + 69 = 722 of the 743 read "no
    rung of the corroboration ladder reached" - an ABSENCE of evidence, which
    is the exact shape the owner said must not fossilize.  AVCP RHA is a real
    tribal housing authority; the withdrawal says it is not ASRC's, not that it
    is not Native.  The 21 that are hard say something positive instead: the
    awardee is a federal or state AGENCY (WRONG_ENTITY_CLASS), or an
    FPDS-declared parent names a different corporation (IDENTIFIER_CONFLICT).
    """
    src = REVIEW / "1079_quarantine_triage_2026-09-02.csv"
    out = []
    for r in read_csv(src):
        if (r.get("disposition") or "").strip() != "WITHDRAW":
            continue
        basis = (r.get("basis") or "").strip()
        low = basis.lower()
        if low.startswith("awardee") and "agency" in low:
            rc, strength = "WRONG_ENTITY_CLASS", "AUTHORITATIVE_REGISTRY"
        elif "fpds-declared parent" in low:
            rc, strength = "IDENTIFIER_CONFLICT", "AUTHORITATIVE_REGISTRY"
        else:
            rc, strength = "NO_QUALIFYING_CONTROL_EVIDENCE", "ABSENCE_OF_EVIDENCE"
        ident = (r.get("identifier") or "").strip()
        tid = (r.get("tribe_id") or "").strip()
        out.append(ev(
            decision_id=did("1079", (r.get("identifier_type") or ""), ident, tid),
            subject_record_id=ident,
            subject_entity_id="",
            candidate_cedar_uid=tid,
            predicate="owned_by", decision="DENIED",
            reason_code=rc,
            reason_detail=(f"{(r.get('legal_business_name') or r.get('prime_awardee_name') or '').strip()} "
                           f"-> {(r.get('canonical_name') or '').strip()}: "
                           f"{basis}")[:600],
            dataset_scope="contractors",
            as_of_date="2026-09-02",
            evidence_id="review/1079_quarantine_triage_2026-09-02.csv",
            evidence_strength=strength,
            review_status="AUTO", reviewer="",
            decided_at="2026-09-02",
            source_table="review/1079_quarantine_triage_2026-09-02.csv",
        ))
    return out


def _seed_1079_holds() -> list[dict]:
    """The 1079 HOLDs.  `native_ownership_status = INSUFFICIENT_EVIDENCE`.

    758 attributions `1079` could neither keep nor withdraw.  This is the ONE
    predicate that touches Native status, and rule 2 is why it is safe: it can
    only ever say INSUFFICIENT_EVIDENCE, it is forced SOFT at construction, it
    is forced into the review queue, and it can never suppress a published row.
    A HOLD is Cedar saying it does not know - which is a real, publishable,
    honest state (ADR-010) and is not a finding about anyone.
    """
    src = REVIEW / "1079_quarantine_triage_2026-09-02.csv"
    out = []
    for r in read_csv(src):
        if (r.get("disposition") or "").strip() != "HOLD":
            continue
        ident = (r.get("identifier") or "").strip()
        tid = (r.get("tribe_id") or "").strip()
        out.append(ev(
            decision_id=did("1079hold", (r.get("identifier_type") or ""),
                            ident, tid),
            subject_record_id=ident,
            subject_entity_id="",
            candidate_cedar_uid=tid,
            predicate="native_ownership_status",
            decision="INSUFFICIENT_EVIDENCE",
            reason_code="INSUFFICIENT_EVIDENCE",
            reason_detail=((r.get("basis") or "").strip()
                           or "1079 HOLD: neither kept nor withdrawn")[:600],
            dataset_scope="contractors",
            as_of_date="2026-09-02",
            evidence_id="review/1079_quarantine_triage_2026-09-02.csv",
            evidence_strength="ABSENCE_OF_EVIDENCE",
            review_status="PENDING_REVIEW", reviewer="",
            decided_at="2026-09-02", recheck_after="",
            source_table="review/1079_quarantine_triage_2026-09-02.csv",
        ))
    return out


def _seed_corrections() -> list[dict]:
    """`cedar_correction_register.csv` - 178 rows, human-authored reasons.

    Every reason names a DIFFERENT LEGAL ENTITY in its own words: "Bristol Bay
    Area Health Corporation (BBAHC) is a separate tribal health organisation.
    It is NOT Bristol Bay Native Corporation."  "Santa Rosa County, FLORIDA - a
    county government, not the Santa Rosa Rancheria."  92 of them are the
    georgetown-inside-an-email-domain class and 14 are `TRBF-ENTPRS-00`, whose
    canonical name is the common English noun 'Enterprise'.

    HARD and PERMANENT: two different legal organisations do not become one
    later, so rule 4's expiry does not apply and `verify` asserts these carry
    no `valid_to`.  Note again what is NOT claimed: BBAHC and BBEDC are both
    Native organisations.  The denial is the IDENTITY MATCH.
    """
    out = []
    seen = set()
    for r in read_csv(CLEAN / "cedar_correction_register.csv"):
        if (r.get("action") or "").strip() not in ("UNLINK", "REFUTE"):
            continue
        wk = (r.get("withdrawn_key") or "").strip()
        eid = (r.get("entity_id") or "").strip()
        if not wk or not eid:
            continue
        k = (wk.upper(), eid)
        if k in seen:
            continue
        seen.add(k)
        low = (r.get("reason") or "").lower()
        rc = ("NAME_COLLISION" if "matched inside" in low or "matched on" in low
              or "common english noun" in low else "DIFFERENT_LEGAL_ENTITY")
        out.append(ev(
            decision_id=did("corr", wk.upper(), eid),
            subject_record_id=wk,
            subject_entity_id="",
            candidate_cedar_uid=(r.get("cedar_uid") or eid).strip(),
            predicate="same_entity_as", decision="DENIED",
            reason_code=rc,
            reason_detail=((r.get("reason") or "").strip())[:600],
            dataset_scope="ALL",
            as_of_date=(r.get("recorded_date") or "").strip(),
            evidence_id=(r.get("correction_id") or "").strip(),
            evidence_strength="ADJUDICATED_BY_OWNER",
            review_status="ADJUDICATED",
            reviewer=(r.get("recorded_by_script") or "").strip() or "Cedar",
            decided_at=(r.get("recorded_date") or "").strip(),
            source_table="data/clean/cedar_correction_register.csv",
        ))
    return out


def _seed_link_denials() -> list[dict]:
    """The 5 `denied` rows already in the link layer, imported unchanged.

    Their own `status_reason`: *"The Federal Register list of federally
    recognized tribal entities enumerates GOVERNMENTS. An ANCSA corporation, a
    school or a nonprofit cannot appear on it, so a name match onto one is
    wrong however well the string agrees."*  That is WRONG_ENTITY_CLASS stated
    in prose; importing it is the migration, not a re-authoring.
    """
    out = []
    for r in read_csv(SPINE / "cedar_source_record_links.csv"):
        if (r.get("link_status") or "").strip() != "denied":
            continue
        srid = (r.get("source_record_id") or "").strip()
        uid = (r.get("cedar_uid") or "").strip()
        out.append(ev(
            decision_id=did("link", srid, uid),
            subject_record_id=srid,
            subject_entity_id="",
            candidate_cedar_uid=uid,
            predicate="same_entity_as", decision="DENIED",
            reason_code="WRONG_ENTITY_CLASS",
            reason_detail=((r.get("status_reason") or "").strip())[:600],
            dataset_scope="federal-register",
            as_of_date=(r.get("asserted_date") or "").strip(),
            evidence_id=(r.get("link_id") or "").strip(),
            evidence_strength="AUTHORITATIVE_REGISTRY",
            review_status="ADJUDICATED",
            reviewer=(r.get("proposed_by") or "").strip() or "Cedar",
            decided_at=(r.get("asserted_date") or "").strip(),
            source_table="data/spine/cedar_source_record_links.csv",
        ))
    return out


def _seed_exclusions() -> list[dict]:
    """`cedar_exclusion_rulings.csv` - the dataset-eligibility predicate.

    123 UEIs Elijah ruled out of the tribally-owned collection, 76 of them on a
    `cage.dla.mil` registry lookup with the URL on the row.  `03_apply_
    exclusions_and_tier.py` already stamps them tier X and refuses to publish.

    This is the seed that makes the owner's distinction concrete: 31 of the 123
    are `individually_native_owned` and 26 are `nonprofit_not_tribally_owned`.
    Every one is Native.  They are out of a TRIBAL collection because the
    collection is about tribal ownership, and `eligible_for_collection DENIED /
    OUT_OF_DATASET_SCOPE` is the only thing said about them.  A table that read
    `is_native = false` would have swallowed all 57.
    """
    out = []
    for r in read_csv(SPINE / "cedar_exclusion_rulings.csv"):
        ident = (r.get("identifier") or "").strip()
        if not ident:
            continue
        out.append(ev(
            decision_id=did("excl", (r.get("identifier_type") or ""), ident),
            subject_record_id=ident,
            subject_entity_id="",
            candidate_cedar_uid="",
            predicate="eligible_for_collection", decision="DENIED",
            reason_code="OUT_OF_DATASET_SCOPE",
            reason_detail=(
                f"{(r.get('exclusion_reason') or '').strip()}"
                f"{': ' + r['ruling_note'].strip() if (r.get('ruling_note') or '').strip() else ''}"
                f" | This is a SCOPE decision about the tribally-owned "
                f"collection. It is not a statement about the firm's owner's "
                f"identity - `individually_native_owned` firms are Native and "
                f"are excluded precisely because the collection is about "
                f"TRIBAL ownership.")[:600],
            dataset_scope="contractors",
            as_of_date=(r.get("extracted_date") or "").strip(),
            evidence_id=(r.get("evidence_url") or "").strip()
                        or (r.get("evidence_type") or "").strip(),
            evidence_strength=("AUTHORITATIVE_REGISTRY"
                               if "CAGE" in (r.get("evidence_type") or "").upper()
                               else "ADJUDICATED_BY_OWNER"),
            review_status="ADJUDICATED",
            reviewer=(r.get("ruled_by") or "").strip() or "Elijah Moreno",
            decided_at=(r.get("extracted_date") or "").strip(),
            source_table="data/spine/cedar_exclusion_rulings.csv",
        ))
    return out


def _seed_asof() -> list[dict]:
    """411 ownership attributions CONTRADICTED on a date.  Rule 4, in the data.

    `review/temporal_asof_ownership.csv` cells where `asof_status=RESOLVED` and
    `agrees_with_shipped=0`: the temporal layer resolved the firm's parent for
    that fiscal year and it is SOMEONE ELSE.  Each carries `fy_start` and
    `fy_end`, so each event is bounded to exactly the year it is about - which
    is the whole reason the schema is temporal.  A firm not tribally owned in
    2018 can be acquired in 2024 and this table will say both.

    Scoped to `contractors:owner_as_of_transaction_cedar_uid`, NOT to
    `cedar_uid`: `429_apply_asof_ownership_status.py` deliberately keeps
    `cedar_uid` on these rows as Cedar's CURRENT attribution and publishes
    UNKNOWN in the historical column.  A gate reading `cedar_uid` would fire on
    a considered design decision.
    """
    out = []
    for r in read_csv(REVIEW / "temporal_asof_ownership.csv"):
        if (r.get("asof_status") or "").strip() != "RESOLVED":
            continue
        if (r.get("agrees_with_shipped") or "").strip() != "0":
            continue
        uei = (r.get("subject_uei") or "").strip()
        shipped = (r.get("currently_shipped_cedar_uid") or "").strip()
        fy = (r.get("fiscal_year") or "").strip()
        out.append(ev(
            decision_id=did("asof", uei, fy, shipped),
            subject_record_id=uei,
            subject_entity_id="",
            candidate_cedar_uid=shipped,
            predicate="owned_by", decision="DENIED",
            reason_code="OWNERSHIP_CONTRADICTED_AS_OF",
            reason_detail=(
                f"FY{fy}: the temporal layer resolves this UEI's parent to "
                f"{(r.get('resolved_parent_uei') or '').strip()} / "
                f"{(r.get('resolved_owner_cedar_uid') or '').strip()}, which is "
                f"NOT the shipped owner {shipped}. Basis: "
                f"{(r.get('resolution_basis') or '').strip()}, granularity "
                f"{(r.get('granularity') or '').strip()}, "
                f"{(r.get('n_candidate_facts') or '').strip()} candidate "
                f"fact(s). Bounded to this fiscal year ONLY.")[:600],
            dataset_scope="contractors:owner_as_of_transaction_cedar_uid",
            valid_from=(r.get("fy_start") or "").strip(),
            valid_to=(r.get("fy_end") or "").strip(),
            as_of_date=(r.get("built_date") or "").strip(),
            evidence_id="review/temporal_asof_ownership.csv",
            evidence_strength="AUTHORITATIVE_REGISTRY",
            review_status="AUTO", reviewer="",
            decided_at=(r.get("built_date") or "").strip(),
            source_table="review/temporal_asof_ownership.csv",
        ))
    return out


# `duplicate_of VERIFIED` IS IN THE VOCABULARY AND HAS ZERO SEEDS.  Measured,
# and the measurement is the reason.
#
# The obvious seed was `data/clean/subawards.csv`, where 846 rows read
# `duplicate_status = superseded_by_primary_source`.  A `duplicate_of` event
# has to ADDRESS a record, and that file has no row-unique column: all 81 of
# them repeat.  `subaward_source_record_id` comes closest at 89,462 distinct
# values over 89,809 rows - and **346 of the 846 superseded records share their
# source-record id with a row marked `primary`**, which is the file saying
# plainly that the id names the SOURCE RECORD and not the Cedar row.
#
# Seeded on that key the gate reported 366 violations, 346 of them its own bad
# key reading a primary row as its own duplicate.  A registry that cannot
# address the thing it rules on is not a registry, so the seeder was removed
# rather than weakened, and the 846 events it had written were deleted before
# anything consumed them.  When subawards carries a row id, this is a
# five-line seeder.
#
# `controlled_by DENIED` is likewise empty on purpose: nothing on disk rules at
# the grain of control-without-ownership.  The nearest candidates -
# `nonprofit_not_tribally_owned` in the exclusion rulings - are scope
# decisions, and calling them control findings would be the invention this
# whole file exists to avoid.


def _seed_cedar_rulings() -> list[dict]:
    """`cedar_rulings.csv` - eight hand-written owner rulings, four of them
    negative, and the one real SUPERSESSION on disk.

    RUL-0002 / RUL-0003.  `Cherokee General Corporation` (UEI YBZGKKUPSUD4) is
    a wholly owned subsidiary of Doyon Government Group, quoted from Doyon's
    own site.  Two sources had attributed it to Cherokee Nation and to the
    Cherokee of Georgia Tribal Council on the token `cherokee` - which
    `cedar_domain.NAME_TRAPS` has carried since the original list.  HARD:
    a person ruled it.

    RUL-0007.  `DO_NOT_CONFLATE`: Native Hawaiian Legal CORPORATION is a
    different organisation from Native Hawaiian Legal Defense & Education Fund.
    HARD and PERMANENT - and note what it is not.  Both are Native Hawaiian
    organisations.

    RUL-0008.  `ATTRIBUTION_NOT_ESTABLISHED`: the Lawelawe / Ho'omaka
    hypothesis was tested and rejected.  This is exactly rule 2's case - the
    owner did not find that Lawelawe is non-Native, he found that Cedar could
    not establish the parent.  `native_ownership_status INSUFFICIENT_EVIDENCE`,
    SOFT, queued, and it can never suppress anything.

    RUL-0001 supersedes EXCL-0116.  Rule 3, from disk: EXCL-0116 excluded UEI
    YBZGKKUPSUD4 with the reason text `ANC`, and the owner later ruled the firm
    IS attributable, to Doyon.  The original exclusion event is not edited and
    not deleted; a superseding event bounds it with `valid_to` the day before
    the ruling, so the constraint reads EXPIRED and the original reads
    SUPERSEDED.  Both stay on the record, which is what a history is.
    """
    out = []
    for r in read_csv(SPINE / "cedar_rulings.csv"):
        rid = (r.get("ruling_id") or "").strip()
        ruling = (r.get("ruling") or "").strip()
        ident = (r.get("identifier") or "").strip()
        url = (r.get("evidence_url") or "").strip()
        note = (r.get("note") or "").strip()
        quote = (r.get("evidence_quote") or "").strip()
        rdate = (r.get("ruled_date") or "").strip()
        if ruling == "REJECT_ATTRIBUTION":
            out.append(ev(
                decision_id=did("rul", rid),
                subject_record_id=ident,
                subject_entity_id="",
                candidate_cedar_uid=(r.get("parent_entity_id") or "").strip(),
                predicate="owned_by", decision="DENIED",
                reason_code="NAME_COLLISION",
                reason_detail=(
                    f"{(r.get('entity_name') or '').strip()} is not owned by "
                    f"{(r.get('parent_native_entity') or '').strip()}. "
                    f"Evidence: \"{quote}\". {note}")[:600],
                dataset_scope="contractors",
                as_of_date=rdate,
                evidence_id=url, evidence_strength="ADJUDICATED_BY_OWNER",
                review_status="ADJUDICATED",
                reviewer=(r.get("ruled_by") or "").strip(), decided_at=rdate,
                source_table="data/spine/cedar_rulings.csv",
            ))
        elif ruling == "DO_NOT_CONFLATE":
            out.append(ev(
                decision_id=did("rul", rid),
                subject_record_id=ident,
                subject_entity_id="",
                candidate_cedar_uid="NHO-HOOMAKA",
                predicate="same_entity_as", decision="DENIED",
                reason_code="DIFFERENT_LEGAL_ENTITY",
                reason_detail=(f"{(r.get('entity_name') or '').strip()}: "
                               f"{note}")[:600],
                dataset_scope="ALL", as_of_date=rdate,
                evidence_id=url, evidence_strength="ADJUDICATED_BY_OWNER",
                review_status="ADJUDICATED",
                reviewer=(r.get("ruled_by") or "").strip(), decided_at=rdate,
                source_table="data/spine/cedar_rulings.csv",
            ))
        elif ruling == "ATTRIBUTION_NOT_ESTABLISHED":
            out.append(ev(
                decision_id=did("rul", rid),
                subject_record_id=ident,
                subject_entity_id="",
                candidate_cedar_uid="",
                predicate="native_ownership_status",
                decision="INSUFFICIENT_EVIDENCE",
                reason_code="INSUFFICIENT_EVIDENCE",
                reason_detail=(f"{(r.get('entity_name') or '').strip()}: "
                               f"{note} Evidence: \"{quote}\"")[:600],
                dataset_scope="ALL", as_of_date=rdate,
                evidence_id=url, evidence_strength="ABSENCE_OF_EVIDENCE",
                review_status="PENDING_REVIEW",
                reviewer=(r.get("ruled_by") or "").strip(), decided_at=rdate,
                recheck_after="",
                source_table="data/spine/cedar_rulings.csv",
            ))
        elif ruling == "ATTRIBUTE" and (r.get("supersedes") or "").strip():
            prior = (r.get("supersedes") or "").strip()
            excl = {x.get("exclusion_id", "").strip(): x
                    for x in read_csv(SPINE / "cedar_exclusion_rulings.csv")}
            row = excl.get(prior)
            if not row:
                continue
            vfrom = (row.get("extracted_date") or "").strip()
            try:
                vt = (date.fromisoformat(rdate) - timedelta(days=1)).isoformat()
            except ValueError:
                continue
            # EXCL-0116 was recorded and reversed on the SAME day (both
            # 2026-08-05), so `ruling date - 1` would write an empty window -
            # a constraint that can never be true, which is not the same
            # statement as "it was in force for one day".
            if vfrom and vt < vfrom:
                vt = vfrom
            out.append(ev(
                decision_id=did("rul", rid),
                subject_record_id=(row.get("identifier") or "").strip(),
                subject_entity_id="",
                candidate_cedar_uid="",
                predicate="eligible_for_collection", decision="DENIED",
                reason_code="OUT_OF_DATASET_SCOPE",
                reason_detail=(
                    f"SUPERSEDES {prior}. The exclusion stood until {vt}. "
                    f"{rid} ({rdate}) rules the firm IS attributable, to "
                    f"{(r.get('parent_native_entity') or '').strip()} "
                    f"({(r.get('parent_entity_id') or '').strip()}): "
                    f"\"{quote}\". {note} The original exclusion event is not "
                    f"edited and not deleted - it is bounded.")[:600],
                dataset_scope="contractors",
                valid_from=vfrom,
                valid_to=vt,
                as_of_date=rdate, evidence_id=url,
                evidence_strength="ADJUDICATED_BY_OWNER",
                review_status="ADJUDICATED",
                reviewer=(r.get("ruled_by") or "").strip(), decided_at=rdate,
                supersedes_decision_id=did(
                    "excl", (row.get("identifier_type") or "").strip(),
                    (row.get("identifier") or "").strip()),
                source_table="data/spine/cedar_rulings.csv",
            ))
    return out


SEEDERS = (
    ("goldbelt_anc_lookup", _seed_goldbelt_lookup),
    ("goldbelt_nest_published", _seed_goldbelt_nest),
    ("uttc_united_auburn", _seed_uttc),
    ("np_placename_refusals", _seed_placename),
    ("quarantine_1079_withdraw", _seed_1079),
    ("quarantine_1079_hold", _seed_1079_holds),
    ("correction_register", _seed_corrections),
    ("link_layer_denials", _seed_link_denials),
    ("exclusion_rulings", _seed_exclusions),
    # must follow exclusion_rulings: RUL-0001 supersedes EXCL-0116 and I7
    # refuses a dangling supersedes_decision_id
    ("cedar_rulings_hand", _seed_cedar_rulings),
    ("temporal_contradicted_asof", _seed_asof),
)


def stage_seed(apply_: bool = True) -> int:
    existing = load_events()
    have = {r["decision_id"] for r in existing}
    print(f"  1163 seed   {len(existing)} events already on disk\n")
    fresh, dupes_in_batch = [], 0
    batch_ids = set()
    for name, fn in SEEDERS:
        got = fn()
        new = []
        for e in got:
            if e["decision_id"] in have or e["decision_id"] in batch_ids:
                dupes_in_batch += 1
                continue
            batch_ids.add(e["decision_id"])
            new.append(e)
        hard = sum(1 for e in new if hardness(e)[0] == "HARD")
        print(f"    {name:28s} read {len(got):5d}   new {len(new):5d}   "
              f"HARD {hard:5d}   SOFT {len(new) - hard:5d}")
        fresh += new
    print(f"\n    {len(fresh)} new events, {dupes_in_batch} already present "
          f"(seed is idempotent by natural key)")
    if not apply_:
        return 0
    if fresh:
        write_csv(EVENTS, COLS, existing + fresh)
        _ledger_record(existing + fresh)
    print(f"    wrote {EVENTS.relative_to(ROOT)}  "
          f"{len(existing) + len(fresh)} rows")
    return 0


# ---------------------------------------------------------------------------
# rule 3 - append-only, enforced.
# ---------------------------------------------------------------------------
def _ledger_record(rows) -> None:
    LEDGER.write_text(json.dumps(
        {"n": len(rows), "updated": TODAY,
         "hashes": {r["decision_id"]: row_hash(r) for r in rows}},
        indent=0), encoding="utf-8")


def _ledger_check(rows) -> tuple[bool, str]:
    if not LEDGER.exists():
        return True, "no ledger yet (first seed writes it)"
    prev = json.loads(LEDGER.read_text(encoding="utf-8"))
    now = {r["decision_id"]: row_hash(r) for r in rows}
    gone = [k for k in prev["hashes"] if k not in now]
    edited = [k for k, v in prev["hashes"].items()
              if k in now and now[k] != v]
    if gone or edited:
        return False, (f"APPEND-ONLY VIOLATED: {len(gone)} decision(s) deleted, "
                       f"{len(edited)} edited in place. "
                       f"first: {(gone + edited)[:3]}")
    return True, (f"{len(prev['hashes'])} prior decisions all present and "
                  f"byte-identical; {len(now) - len(prev['hashes'])} appended")


# ===========================================================================
# STAGE: build - the DERIVED view.  Never hand-edited.
# ===========================================================================
VIEW_COLS = [
    "THIS_FILE_IS_DERIVED", "constraint_id", "subject_record_id",
    "subject_entity_id", "candidate_cedar_uid", "predicate", "reason_code",
    "strength", "suppresses", "constraint_state", "dataset_scope",
    "valid_from", "valid_to", "recheck_after", "evidence_strength",
    "review_status", "reviewer", "why", "reason_detail", "source_table",
    "built_by_script", "built_date",
]

DERIVED_BANNER = ("DERIVED VIEW - regenerate with `py -3 " + SCRIPT
                  + " build`. Edit cedar_decision_events.csv, never this file.")


def in_window(c: dict, when: str) -> bool:
    """Is `when` inside the period this constraint is ABOUT?

    `valid_from`/`valid_to` bound the FACT, not the decision.  A 2018
    contradicted ownership is a permanently true statement about 2018 and it
    must still suppress a 2018 row published in 2030 - so this is asked of the
    ROW's date, never of the clock.  Whether the DECISION is still in force is
    a different question and supersession answers it.
    """
    vf = (c.get("valid_from") or "").strip()[:10]
    vt = (c.get("valid_to") or "").strip()[:10]
    if not when:
        return not (vf or vt)      # an undated row cannot be placed in a window
    if vf and when < vf:
        return False
    if vt and when > vt:
        return False
    return True


def resolve(events=None, on: str | None = None) -> list[dict]:
    """Events -> constraints.  Supersession, then hardness, then staleness.

    `on` is the clock and it decides exactly two things: whether a
    `recheck_after` has passed, and nothing else.  It does NOT expire a
    constraint: `valid_from`/`valid_to` bound the fact the constraint is about
    and are tested against the published ROW in `release_check`.  An earlier
    draft evaluated the window against today and quietly stood down 403 of 411
    ownership contradictions the moment their fiscal year ended - a gate that
    disarms itself with the calendar.
    """
    on = on or TODAY
    events = events if events is not None else load_events()
    by_id = {e["decision_id"]: e for e in events}
    # rule 3: only an ADJUDICATED superseding event retires its predecessor.
    retired = set()
    for e in events:
        sup = (e.get("supersedes_decision_id") or "").strip()
        if sup and sup in by_id and \
                (e.get("review_status") or "").strip() == "ADJUDICATED":
            retired.add(sup)

    out = []
    for e in events:
        strength, why = hardness(e)
        if e["decision_id"] in retired:
            state, suppresses = "SUPERSEDED", "N"
        elif strength == "SOFT":
            state, suppresses = "REVIEW_ONLY", "N"
        else:
            ra = (e.get("recheck_after") or "").strip()[:10]
            vt = (e.get("valid_to") or "").strip()[:10]
            if ra and on > ra:
                state = "ACTIVE_STALE"
            elif vt and on > vt:
                # still in force, still suppressing - but only for rows dated
                # inside its window.  Named so nobody reads ACTIVE and assumes
                # it covers today's rows.
                state = "ACTIVE_HISTORICAL"
            else:
                state = "ACTIVE"
            suppresses = "Y"
        out.append({
            "THIS_FILE_IS_DERIVED": DERIVED_BANNER,
            "constraint_id": e["decision_id"],
            "subject_record_id": e.get("subject_record_id", ""),
            "subject_entity_id": e.get("subject_entity_id", ""),
            "candidate_cedar_uid": e.get("candidate_cedar_uid", ""),
            "predicate": e.get("predicate", ""),
            "reason_code": e.get("reason_code", ""),
            "strength": strength,
            "suppresses": suppresses,
            "constraint_state": state,
            "dataset_scope": e.get("dataset_scope", ""),
            "valid_from": e.get("valid_from", ""),
            "valid_to": e.get("valid_to", ""),
            "recheck_after": e.get("recheck_after", ""),
            "evidence_strength": e.get("evidence_strength", ""),
            "review_status": e.get("review_status", ""),
            "reviewer": e.get("reviewer", ""),
            "why": why,
            "reason_detail": e.get("reason_detail", ""),
            "source_table": e.get("source_table", ""),
            "built_by_script": SCRIPT,
            "built_date": TODAY,
        })
    return out


def stage_build() -> int:
    events = load_events()
    cons = resolve(events)
    write_csv(VIEW, VIEW_COLS, cons)
    q = [c for c in cons
         if c["constraint_state"] in ("REVIEW_ONLY", "ACTIVE_STALE")
         or c["review_status"] in ("PENDING_REVIEW", "PROPOSED_SUPERSEDE")]
    write_csv(QUEUE, VIEW_COLS, q)
    st = Counter(c["constraint_state"] for c in cons)
    sc = Counter(c["strength"] for c in cons)
    print(f"  1163 build   {len(events)} events -> {len(cons)} constraints\n")
    print("    strength: " + "  ".join(f"{k}={v}" for k, v in sc.most_common()))
    print("    state:    " + "  ".join(f"{k}={v}" for k, v in st.most_common()))
    print(f"    suppressing (HARD + ACTIVE): "
          f"{sum(1 for c in cons if c['suppresses'] == 'Y')}")
    print(f"    review queue: {len(q)} -> {QUEUE.relative_to(ROOT)}")
    print(f"    wrote {VIEW.relative_to(ROOT)}")
    return 0


# ===========================================================================
# STAGE: check - THE RELEASE GATE.
# ===========================================================================
#: Where a published row carries its record id.  Not guessed at runtime: a gate
#: that goes looking for a plausible column will silently test nothing when the
#: column is renamed.  A collection absent from this table is REPORTED as
#: untested rather than passing quietly.
#: `dates` is how a windowed constraint is placed against a published row.  A
#: collection with no date column cannot be tested by a windowed constraint,
#: and that is REPORTED as untested rather than passing quietly - rule 9, an
#: absence of evidence must not print as evidence of absence.
PROBES = {
    "nest": {"ids": ("enterprise_id", "uei", "cage_code"),
             "uids": ("owner_hub_cedar_uid", "owner_hub_handle"),
             "dates": ()},
    "nonprofits": {"ids": ("EIN", "ein"),
                   "uids": ("cedar_uid", "tribe_id"),
                   "dates": ("tax_period",)},
    "contractors": {"ids": ("awardee_uei", "cage_code"),
                    "uids": ("cedar_uid", "tribe_id"),
                    "dates": ("action_date", "fiscal_year")},
    "native-owned-businesses": {"ids": ("federal_uei_linked",
                                        "federal_cage_linked"),
                                "uids": ("cedar_uid", "tribe_id"),
                                "dates": ()},
    "subcontracting": {"ids": ("subaward_source_record_id",),
                       "uids": ("cedar_uid", "sub_cedar_uid",
                                "prime_cedar_uid"),
                       "dates": ("subaward_action_date", "fiscal_year")},
    "funding": {"ids": ("recipient_uei",), "uids": ("cedar_uid", "tribe_id"),
                "dates": ("action_date", "fiscal_year")},
    "lobbying": {"ids": ("client_name",), "uids": ("cedar_uid", "tribe_id"),
                 "dates": ("filing_year",)},
    "deals": {"ids": (), "uids": ("cedar_uid",), "dates": ("announced_date",)},
    "federal-register": {"ids": ("document_number",), "uids": ("cedar_uid",),
                         "dates": ("publication_date",)},
    "legislation": {"ids": (), "uids": ("cedar_uid",), "dates": ()},
    "nagpra": {"ids": (), "uids": ("cedar_uid",), "dates": ()},
    "natural-resources": {"ids": (), "uids": ("cedar_uid",), "dates": ()},
    "gaming": {"ids": (), "uids": ("cedar_uid", "tribe_id"), "dates": ()},
}


def _row_date(row, date_ix) -> str:
    """The published row's own date, ISO, or ''.

    A bare four-digit year is a FISCAL year here, because that is what every
    `fiscal_year` column in this project means.  It is placed at its own
    mid-point (1 April) rather than 1 January: FY2018 runs 2017-10-01 to
    2018-09-30, and a January date would fall outside its own fiscal year's
    window and silently disarm every constraint bounded that way.
    """
    for i in date_ix:
        if i >= len(row):
            continue
        v = (row[i] or "").strip()
        if not v:
            continue
        if len(v) >= 10 and v[4] == "-" and v[7] == "-":
            return v[:10]
        if len(v) == 4 and v.isdigit():
            return f"{v}-04-01"
    return ""

#: Predicates whose violation is "this row keys subject to candidate".
PAIR_PREDICATES = frozenset({"same_entity_as", "owned_by", "controlled_by"})


def _norm(v) -> str:
    return (v or "").strip().upper()


def release_check(dist_dir=None, on: str | None = None) -> tuple[int, str, list]:
    """No published row may violate an ACTIVE HARD constraint.

    Returns (n_violations, one-line detail, rows).  Imported by `846`.
    """
    dist_dir = Path(dist_dir) if dist_dir else DIST
    on = on or TODAY
    cons = [c for c in resolve(on=on) if c["suppresses"] == "Y"]

    pair, scope_ban, dupes = defaultdict(list), defaultdict(list), defaultdict(list)
    for c in cons:
        coll, _, col = c["dataset_scope"].partition(":")
        p = c["predicate"]
        if p in PAIR_PREDICATES:
            pair[(coll, col)].append(c)
        elif p == "eligible_for_collection":
            scope_ban[(coll, col)].append(c)
        elif p == "duplicate_of":
            dupes[(coll, col)].append(c)

    files = sorted(p for p in dist_dir.glob("*.csv") if p.name != "MANIFEST.csv")
    viol, untested, scanned = [], [], 0
    for p in files:
        stem = p.name[:-4]
        probe = PROBES.get(stem)
        if probe is None:
            untested.append(f"{stem} (no probe defined)")
            continue
        # everything this collection is constrained by, plus the ALL scope
        keys = [(stem, ""), ("ALL", "")]
        pairs = [c for k in keys for c in pair.get(k, [])]
        pairs += [c for (coll, col), lst in pair.items() if coll == stem and col
                  for c in lst]
        bans = [c for k in keys for c in scope_ban.get(k, [])]
        dup = [c for (coll, col), lst in dupes.items() if coll == stem
               for c in lst]
        if not (pairs or bans or dup):
            continue

        pair_idx = defaultdict(list)
        for c in pairs:
            _, _, col = c["dataset_scope"].partition(":")
            for s in (c["subject_record_id"], c["subject_entity_id"]):
                if s:
                    pair_idx[(_norm(s), _norm(c["candidate_cedar_uid"]))].append(
                        (c, col))
        ban_idx = {_norm(c["subject_record_id"]): c for c in bans
                   if c["subject_record_id"]}
        dup_idx = {}
        for c in dup:
            _, _, col = c["dataset_scope"].partition(":")
            dup_idx[_norm(c["subject_record_id"])] = (c, col or "duplicate_status")

        windowed_untestable = {c["constraint_id"] for c in pairs + bans + dup
                               if (c["valid_from"] or c["valid_to"])
                               and not probe["dates"]}

        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.reader(fh)
            hdr = next(rd, [])
            ix = {c: i for i, c in enumerate(hdr)}
            id_cols = [ix[c] for c in probe["ids"] if c in ix]
            uid_cols = [ix[c] for c in probe["uids"] if c in ix]
            date_ix = [ix[c] for c in probe["dates"] if c in ix]
            if windowed_untestable:
                untested.append(f"{stem} ({len(windowed_untestable)} windowed "
                                f"constraint(s), no date column)")
            elif [c for c in pairs + bans + dup
                  if (c["valid_from"] or c["valid_to"])] and not date_ix:
                untested.append(f"{stem} (date column named in PROBES is "
                                f"absent from the file)")
            for n, row in enumerate(rd, 2):
                scanned += 1
                subs = {_norm(row[i]) for i in id_cols if i < len(row)}
                subs |= {_norm(row[i]) for i in uid_cols if i < len(row)}
                subs.discard("")
                if not subs:
                    continue
                uids = {_norm(row[i]) for i in uid_cols if i < len(row)}
                uids.discard("")
                when = _row_date(row, date_ix)
                for s in subs:
                    for u in uids:
                        for c, col in pair_idx.get((s, u), ()):
                            # a scoped constraint tests ONE named column
                            if col:
                                j = ix.get(col)
                                if j is None or j >= len(row) \
                                        or _norm(row[j]) != u:
                                    continue
                            if not in_window(c, when):
                                continue
                            viol.append({
                                "file": p.name, "line": n,
                                "constraint_id": c["constraint_id"],
                                "predicate": c["predicate"],
                                "reason_code": c["reason_code"],
                                "subject": s, "candidate_cedar_uid": u,
                                "column": col or "(any uid column)",
                                "why": c["reason_detail"][:200],
                            })
                    c = ban_idx.get(s)
                    if c is not None and uids and in_window(c, when):
                        viol.append({
                            "file": p.name, "line": n,
                            "constraint_id": c["constraint_id"],
                            "predicate": c["predicate"],
                            "reason_code": c["reason_code"],
                            "subject": s,
                            "candidate_cedar_uid": sorted(uids)[0],
                            "column": "(attributed at all)",
                            "why": c["reason_detail"][:200],
                        })
                    hit = dup_idx.get(s)
                    if hit is not None and in_window(hit[0], when):
                        c, col = hit
                        j = ix.get(col)
                        if j is not None and j < len(row) \
                                and _norm(row[j]) == "PRIMARY":
                            viol.append({
                                "file": p.name, "line": n,
                                "constraint_id": c["constraint_id"],
                                "predicate": c["predicate"],
                                "reason_code": c["reason_code"],
                                "subject": s, "candidate_cedar_uid": "",
                                "column": col,
                                "why": c["reason_detail"][:200],
                            })
    per = Counter(v["file"] for v in viol)
    detail = (f"{len(cons)} active HARD constraints vs {scanned:,} published "
              f"rows in {len(files)} files: {len(viol)} violation(s)"
              + (" - " + ", ".join(f"{k} {v}" for k, v in per.most_common(4))
                 if viol else "")
              + (f"; UNTESTED: {', '.join(untested)}" if untested else ""))
    return len(viol), detail, viol


def stage_check(dist_dir=None) -> int:
    n, detail, viol = release_check(dist_dir)
    print(f"  1163 release gate\n\n    {detail}\n")
    for v in viol[:15]:
        print(f"    {v['file']}:{v['line']}  {v['predicate']} "
              f"{v['reason_code']}  {v['subject']} -> "
              f"{v['candidate_cedar_uid']}")
        print(f"        {v['why'][:150]}")
    if len(viol) > 15:
        print(f"    ... and {len(viol) - 15} more")
    if viol:
        out = REVIEW / f"negative_constraint_violations_{TODAY}.csv"
        write_csv(out, list(viol[0].keys()), viol)
        print(f"\n    wrote {out.relative_to(ROOT)}")
    return 1 if n else 0


# ===========================================================================
# STAGE: selftest - WATCH THE GATE FIRE.
# ===========================================================================
def stage_selftest() -> int:
    """Two gates shipped today without one.  This one gets watched.

    Builds a throwaway `dist/` holding one row that violates a real, active,
    hard constraint from the live registry, and asserts the gate FINDS it.
    Then flips the same row's candidate to a uid no constraint names and
    asserts the gate is SILENT - a gate that fires on everything is not a gate.
    Then re-runs both against a SOFT constraint and asserts silence, which is
    rule 1 - only hard negatives auto-suppress.
    """
    cons = resolve()
    hard = [c for c in cons if c["suppresses"] == "Y"
            and c["predicate"] in PAIR_PREDICATES
            and c["subject_record_id"] and c["candidate_cedar_uid"]
            and c["dataset_scope"].split(":")[0] == "nest"]
    soft = [c for c in cons if c["strength"] == "SOFT"
            and c["predicate"] == "same_entity_as"
            and c["subject_record_id"] and c["candidate_cedar_uid"]
            and c["dataset_scope"].split(":")[0] == "nonprofits"]
    if not hard or not soft:
        print(f"  1163 selftest  CANNOT RUN: hard-nest={len(hard)} "
              f"soft-nonprofit={len(soft)}. Run `seed` first.")
        return 1
    h, s = hard[0], soft[0]
    fails = []
    tmp = Path(tempfile.mkdtemp(prefix="ndr_selftest_"))
    try:
        def nest(eid, uid):
            write_csv(tmp / "nest.csv",
                      ["enterprise_id", "enterprise_name",
                       "owner_hub_cedar_uid"],
                      [{"enterprise_id": eid,
                        "enterprise_name": "FIXTURE ROW",
                        "owner_hub_cedar_uid": uid}])

        # A. the gate MUST fire on a real active hard constraint
        nest(h["subject_record_id"], h["candidate_cedar_uid"])
        n, d, v = release_check(tmp)
        print(f"    A  violating row      -> {n} violation(s)   "
              f"[{h['constraint_id']} {h['reason_code']}]")
        if n != 1:
            fails.append(f"A: expected exactly 1 violation, got {n}")

        # B. and MUST be silent on a pair no constraint names
        nest(h["subject_record_id"], "CE-ZZZZZ-ZZ")
        n, d, v = release_check(tmp)
        print(f"    B  innocent row       -> {n} violation(s)")
        if n != 0:
            fails.append(f"B: expected 0, got {n} - the gate fires on "
                         f"everything, which is not a gate")

        # C. rule 1 - a SOFT constraint must NOT suppress
        (tmp / "nest.csv").unlink()
        write_csv(tmp / "nonprofits.csv", ["EIN", "cedar_uid"],
                  [{"EIN": s["subject_record_id"],
                    "cedar_uid": s["candidate_cedar_uid"]}])
        n, d, v = release_check(tmp)
        print(f"    C  SOFT constraint    -> {n} violation(s)   "
              f"[{s['constraint_id']} {s['reason_code']} "
              f"{s['constraint_state']}]")
        if n != 0:
            fails.append(f"C: a SOFT constraint suppressed a published row. "
                         f"Rule 1 broken - this is how research gaps fossilize")

        # D. rule 4 - a windowed constraint is tested against the ROW's date.
        #    The same firm, the same uid, two different transaction dates: the
        #    year the layer contradicted must fire and a later year must not.
        #    This is the acquisition case in miniature - not tribally owned in
        #    2018, acquired in 2024 - and the gate has to tell them apart.
        cand = [c for c in cons if c["strength"] == "HARD"
                and c["valid_from"] and c["valid_to"]
                and c["valid_from"] < c["valid_to"]
                and c["predicate"] in PAIR_PREDICATES
                and c["subject_record_id"] and c["candidate_cedar_uid"]
                and c["dataset_scope"].split(":")[0] == "contractors"]
        # The same firm can be contradicted in SEVERAL fiscal years, and a
        # date outside one window then lands inside the next - the first draft
        # of this test read that as the gate ignoring the window. Take a pair
        # constrained in exactly one year, so "outside" really is outside.
        grp = defaultdict(list)
        for c in cand:
            grp[(c["subject_record_id"], c["candidate_cedar_uid"])].append(c)
        exp = [v[0] for v in grp.values() if len(v) == 1]
        if exp:
            e = exp[0]
            (tmp / "nonprofits.csv").unlink()

            def contractor(action_date):
                write_csv(tmp / "contractors.csv",
                          ["awardee_uei", "cedar_uid", "action_date",
                           "owner_as_of_transaction_cedar_uid"],
                          [{"awardee_uei": e["subject_record_id"],
                            "cedar_uid": e["candidate_cedar_uid"],
                            "action_date": action_date,
                            "owner_as_of_transaction_cedar_uid":
                                e["candidate_cedar_uid"]}])

            contractor(e["valid_from"][:10])
            n_in, _, _ = release_check(tmp)
            contractor((date.fromisoformat(e["valid_to"][:10])
                        + timedelta(days=400)).isoformat())
            n_out, _, _ = release_check(tmp)
            print(f"    D  row inside window  -> {n_in} violation(s); "
                  f"row 400 days after it -> {n_out}   "
                  f"[{e['constraint_id']} {e['valid_from']}..{e['valid_to']}]")
            if n_in != 1 or n_out != 0:
                fails.append(f"D: the window was not tested against the row's "
                             f"own date (inside={n_in}, outside={n_out})")
        else:
            fails.append("D: no date-bounded hard constraint to test with")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    for f in fails:
        print(f"    FAIL  {f}")
    print(f"    {4 - len(fails)}/4 selftest assertions pass")
    return 1 if fails else 0


# ===========================================================================
# STAGE: verify
# ===========================================================================
def stage_verify() -> int:
    events = load_events()
    bad = []

    def chk(cond, msg):
        if not cond:
            bad.append(msg)

    chk(bool(events), "cedar_decision_events.csv is empty - run `seed`")
    ok, why = _ledger_check(events)
    chk(ok, why)
    print(f"  I1  append-only: {why}")

    ids = Counter(e["decision_id"] for e in events)
    dup = [k for k, v in ids.items() if v > 1]
    chk(not dup, f"I2 duplicate decision_id: {dup[:3]}")
    print(f"  I2  {len(ids)} distinct decision_ids, {len(dup)} duplicated")

    v = [e for e in events if e["predicate"] not in PREDICATES
         or e["decision"] not in PREDICATES.get(e["predicate"], ())]
    chk(not v, f"I3 predicate/decision pair outside the vocabulary: "
               f"{[(x['predicate'], x['decision']) for x in v[:3]]}")
    v2 = [e for e in events if e["reason_code"] not in REASON_CODES]
    chk(not v2, f"I3b reason_code outside the vocabulary: "
                f"{[x['reason_code'] for x in v2[:3]]}")
    print(f"  I3  vocabulary: {len(v)} bad predicate/decision, "
          f"{len(v2)} bad reason_code")

    # rule 2
    ie = [e for e in events if e["decision"] == "INSUFFICIENT_EVIDENCE"]
    b = [e for e in ie if hardness(e)[0] != "SOFT"
         or e["review_status"] != "PENDING_REVIEW"]
    chk(not b, f"I4 rule 2 broken on {len(b)} INSUFFICIENT_EVIDENCE events")
    print(f"  I4  rule 2: {len(ie)} INSUFFICIENT_EVIDENCE, all SOFT and "
          f"PENDING_REVIEW ({len(b)} exceptions)")

    # rule 1
    b = [e for e in events if e["reason_code"] in NEVER_HARD
         and hardness(e)[0] == "HARD"]
    chk(not b, f"I5 rule 1 broken: {len(b)} NEVER_HARD reasons resolved HARD")
    print(f"  I5  rule 1: {sum(1 for e in events if hardness(e)[0]=='HARD')} "
          f"HARD / {sum(1 for e in events if hardness(e)[0]=='SOFT')} SOFT; "
          f"{len(b)} NEVER_HARD escapes")

    # rule 4
    b = [e for e in events if e["reason_code"] in PERMANENT
         and e["predicate"] == "same_entity_as" and e["valid_to"].strip()]
    chk(not b, f"I6 rule 4: {len(b)} permanent identity denials carry a "
               f"valid_to")
    b2 = [e for e in events if e["predicate"] in OWNERSHIP_PREDICATES
          and not (e["recheck_after"].strip() or e["valid_to"].strip())]
    chk(not b2, f"I6b rule 4: {len(b2)} ownership decisions never expire and "
                f"carry no recheck_after")
    print(f"  I6  rule 4: {len(b)} permanent denials with an expiry, "
          f"{len(b2)} unbounded ownership decisions")

    # rule 3
    by_id = {e["decision_id"] for e in events}
    b = [e for e in events if e["supersedes_decision_id"].strip()
         and e["supersedes_decision_id"].strip() not in by_id]
    chk(not b, f"I7 dangling supersedes_decision_id on {len(b)} events")
    print(f"  I7  supersession: "
          f"{sum(1 for e in events if e['supersedes_decision_id'].strip())} "
          f"superseding events, {len(b)} dangling")

    # every seeded event must be re-derivable from the file it names
    missing = sorted({e["source_table"] for e in events
                      if e["source_table"] and not (ROOT / e["source_table"]).exists()})
    chk(not missing, f"I8 source_table not on disk: {missing[:3]}")
    print(f"  I8  provenance: "
          f"{len({e['source_table'] for e in events})} source tables, "
          f"{len(missing)} missing from disk")

    # the derived view must actually be derived
    if VIEW.exists():
        live = resolve(events)
        disk = read_csv(VIEW)
        same = (len(live) == len(disk) and
                all(a["constraint_id"] == b_["constraint_id"]
                    and a["suppresses"] == b_["suppresses"]
                    and a["constraint_state"] == b_["constraint_state"]
                    for a, b_ in zip(live, disk)))
        chk(same, "I9 cedar_negative_constraints.csv has DRIFTED from the "
                  "events - it is derived; run `build`")
        print(f"  I9  derived view: {len(disk)} rows, "
              f"{'in sync' if same else 'DRIFTED'}")
    else:
        bad.append("I9 cedar_negative_constraints.csv absent - run `build`")

    # an empty window is a constraint that can never be true
    b = [e for e in events if e["valid_from"].strip() and e["valid_to"].strip()
         and e["valid_to"].strip()[:10] < e["valid_from"].strip()[:10]]
    chk(not b, f"I11 {len(b)} events carry valid_to < valid_from - an empty "
               f"window is a constraint that can never fire")
    print(f"  I11 windows: "
          f"{sum(1 for e in events if e['valid_from'].strip() or e['valid_to'].strip())} "
          f"date-bounded events, {len(b)} inverted")

    # not a product
    try:
        sys.path.insert(0, str(CODE))
        import cedar_publication as cp
        leak = [c for c in cp.built_collections()
                if "negative" in c or "decision_event" in c]
        chk(not leak, f"I10 the registry appears on a shelf: {leak}")
        print(f"  I10 not a product: {len(cp.customer_collections())} "
              f"storefront collections, registry absent from all of them")
    except Exception as e:
        bad.append(f"I10 could not read cedar_publication: {type(e).__name__}")

    print()
    for m in bad:
        print(f"  FAIL  {m}")
    print(f"  {11 - len(bad)}/11 invariants hold")
    return 1 if bad else 0


def main() -> int:
    stage = (sys.argv[1] if len(sys.argv) > 1 else "report").lower()
    fn = {"report": stage_report, "seed": stage_seed, "build": stage_build,
          "check": stage_check, "selftest": stage_selftest,
          "verify": stage_verify}.get(stage)
    if fn is None:
        print(__doc__)
        return 2
    return fn()


if __name__ == "__main__":
    sys.exit(main())
