#!/usr/bin/env python3
"""1133 - THE OWNER'S v6 ENTERPRISE FILE, AS AN INPUT TO THE NEST BUILDER.

    py -3 code/1133_nest_owner_v6_builder_input.py report    # decisions, no writes
    py -3 code/1133_nest_owner_v6_builder_input.py apply     # stage the builder input
    py -3 code/1133_nest_owner_v6_builder_input.py verify    # exits 1 when the rows
                                                             # are NOT in NEST
    py -3 code/1133_nest_owner_v6_builder_input.py selftest  # proves verify FIRES

Zero network. MINTS ZERO Cedar ids - `1072 build` mints them, from the
append-only `data/spine/cedar_nest_id_register.csv`, which stays the only place
an enterprise id is created. Does not write `nest_enterprises.csv`. Does not
touch `data/spine/cedar_identifier_ledger.csv` (another workstream owns it).

===========================================================================
WHY THIS EXISTS: 1130 MEASURED THE GAP AND DELIBERATELY DID NOT CLOSE IT
===========================================================================
`code/1130_nest_owner_v6_reconcile.py` put the owner's 18,110-row file through
NEST's own clustering and found **4,786 net-new enterprises**. It wrote them to
staging and stopped, because `1072 build` is a FULL REBUILD of
`nest_enterprises.csv` and an in-place append would be reverted by the next run
while printing a larger row count - the FERC rebuild/in-place collision in
`START_HERE.md`, four times over.

The fix is not to append more carefully. It is to make the owner's file an
**INPUT** to `1072`, so the rows are re-derived on every rebuild:

    1133 apply                -> data/staging/nest/owner_v6_edges.jsonl
    1072 load_sources()       -> source 7 reads that file
    1072 assemble             -> hub resolution + the ANCSA guards
    1072 build                -> clustering + id minting
    1102 (enricher) re-run    -> its 8 columns, which a rebuild blanks

1133 owns the DECISIONS (which rows may enter, and on what evidence); 1072 owns
the clustering and the ids. The split is deliberate: every other NEST source is
staged by a sibling script and read by `load_sources()` the same way
(`1070`'s held CSV is source 6a), and putting 4,786 rows of reasoning inside a
shared file that many workstreams edit is how a shared file gets clobbered.

===========================================================================
DECISION 1 - THE 12,085 ROWS WITH NO `tribe_id` ARE NOT "NAMED, NEVER FOLDED"
===========================================================================
The brief for this pass said 12,084 of the owner's rows "were named, never
folded". They were measured instead, and they are four different things:

    8,928  attribution_method = `unmatched`, data_sources =
           `master_entity_registry`, verification_source BLANK
    3,140  data_sources = `sba_dsbs_native_entities`,
           parent_entity_type = `TRIBAL_ENTITY_UNCROSSWALKED_SBA`
       16  AIHEC tribal colleges
        1  a tribal-press row

**The 8,928 are the owner's own UNMATCHED RESIDUE and they are refused.** His
file says so in its own column: `attribution_method = unmatched`. They are FPDS
awardees his resolver could not attribute to any Native entity, and reading the
rows makes it unmistakable - `Merchen & Reed Gravel Inc`, `Goldenlook Of San
Antonio Inc`, `Supplemental Medical Services, Inc.`, `A A M C Inc`, and
**natural persons' names**: `Benward, Ursula`, `William Woolard`. Nothing in the
file asserts that any of them is Native-owned. Publishing them as enterprises of
Indian Country would be fabrication at a scale of 8,928 rows, and it would
publish natural persons.

This is START_HERE §1b in a third vocabulary: **`unmatched` is a NEGATIVE
result.** Inheriting the row while dropping its sign is exactly how 317
`elijah_ruling` tier-X refusals were published as confident attributions.

**The 3,140 SBA rows are real firms with no owner named, and they belong in a
different dataset.** They are self-certified Native-owned businesses in the SBA
certification register - `SALCO LLC`, `HAKU SYSTEMS LLC`, `MAKWA GLOBAL
SERVICES, LLC`, 8(a) certified. That is an evidenced Native firm. It is not a
NEST row, because NEST's grain is (owner hub, enterprise name) and no owner
nation is named on any of them. They are registered for
`native-owned-businesses` / the individually-Native-owned class rather than
forced onto a hub, and the register names each one so the promotion is a join
and not a re-harvest.

Nothing is deleted. All 12,085 are written to
`data/staging/nest/owner_v6_refused.csv` with the measured reason.

===========================================================================
DECISION 2 - THE 160 v3-ONLY ROWS ARE NOT 158 LOST FIRMS. DO NOT RECOVER THEM.
===========================================================================
`1130` measured that 160 rows / 158 normalised names present in v3 are absent
from v6, and staged them as recovery candidates. The obvious next move is to
recover them. **It is wrong, and one measurement settles it:**

    v3-only rows whose UEI IS ALSO IN v6:  160 of 160

Every one of them is the SAME FIRM, under the same federal registration, spelled
differently:

    v3 `GLACIER TECHNOLOGIES LLC`        = v6 `Glacier Technologies Limited
                                               Liability Company`
    v3 `GOLDBELT HAWK L.L.C.`            = v6 `Goldbelt Hawk Llc`
    v3 `BOWHEAD MANUFACTURING COMPANY,   = v6 `Bowhead Manufacturing Company`
        L.L.C.`
    v3 `CADDO INDUSTRIES ENTERPRISE`     = v6 `CADDO INDUSTRIES ENTERPRISES`

and **0 of 160 carry a name string v6 also carries under that UEI**, which is
why a name-keyed comparison reports them as missing.

NEST clusters on the normalised NAME, and `norm()` strips a trailing corporate
form but not `limited liability` in the middle of one - so
`glacier technologies` and `glacier technologies limited liability` are two
keys, and rapidfuzz declines to fuse them because their lengths differ by 18
and the merge rule caps the difference at 6. **Feeding v3 would therefore have
created up to 158 duplicate enterprises**, which is the exact defect the
"merged, not appended" design of `1072` exists to stop and which already cost 25
duplicate rows once.

So the v3 strings are recorded as OBSERVED NAME VARIANTS keyed on UEI -
`data/staging/nest/owner_v3_name_variants.csv` - and not as enterprises. The
loss the recovery list described does not exist; what does exist is 160 extra
renderings of names Cedar already holds, which is worth having and is worth
nothing as rows.

===========================================================================
DECISION 3 - NO `relation_class` IS PROPOSED, AND THAT IS NOT A GAP
===========================================================================
v6 has 31 columns and **not one of them states a relationship**. There is no
"wholly owned", no "subsidiary", no percentage. So `relationship` is emitted
as the literal `unspecified`, which `1072.canon_rel` does not recognise and
therefore classes `("unspecified", "affiliation")` - the weaker of the two
readings, which is the direction that does not fabricate.

**It is emitted as `unspecified` and not as a blank, and that distinction cost
a whole build.** `1072.stage_build` reads `x.get("relationship") or
"subsidiary"`, so a BLANK relationship is coerced to `subsidiary` and published
as `relation_class = ownership`. The first build of this input did exactly
that on **3,189 rows** - 3,189 affiliations silently promoted to ownership
claims, in the dataset whose own docstring says an affiliation recorded as
ownership is the defect it is most exposed to. Invariant **W3** caught it,
which is the only reason this paragraph is a note and not a defect.

**An affiliation recorded as ownership is the defect this dataset is most
exposed to.** These rows say a nation and a firm are connected and name the
source that says so. They do not say the nation owns the firm, and neither will
Cedar until a source does.

===========================================================================
DECISION 4 - A UEI CEDAR ALREADY HOLDS IS A CORROBORATION, NOT A NEW FIRM
===========================================================================
A UEI is one federal registration for one firm. An owner row whose UEI is
already carried by a live NEST row is that firm again under a different name
rendering, and emitting it would create a second enterprise for one company -
the same duplication as decision 2, arriving by a different door.

**But a collision only matters when the row would create a NEW cluster.** Where
NEST already holds `(this hub, this normalised name)` the row MERGES onto the
existing enterprise and raises its observation count, which is a corroboration
and is the whole reason for putting the file through the builder's clustering
instead of appending it. Refusing on the UEI alone discarded 173 of those; the
rule tests the clustering key first.

Measured against the live NEST table, the rows that WOULD create a new
enterprise for a firm Cedar already registers: **21** on the same hub and
**172** on a different one. Both are refused and registered in
`owner_v6_uei_already_held.csv` - the same-hub ones as a name-rendering
duplicate, the cross-hub ones as an ownership DISAGREEMENT that needs an
adjudication and must not be settled by whichever pass ran last.

===========================================================================
DECISION 5 - THE 212 ALASKA VILLAGE-GOVERNMENT HUBS ARE LEFT TO 1072'S GUARD
===========================================================================
`1130` found that 223 net-new clusters are held by NEST under a different hub,
and that the large majority hub an ANCSA corporation's subsidiary on the Native
Village GOVERNMENT - `Alutiiq LLC` and `Afognak Diversified Services` under
`AKNF-AFGNAK-00-KONIAG` rather than under Afognak Native Corporation.
`ANCSA_OWNERSHIP_RULING` rule 2 settles every one and **NEST is right on all of
them**.

This pass adds no new guard for it, because `1072.stage_assemble` already has
one: a hub that resolves to `Federally recognized Alaska Native Village` is
either REPOINTED to the corporation the source itself names, or HELD. The
owner's file names no corporation, so these are HELD - written to
`held_rows.csv` with the reason, not dropped and not attached to a government.

**And they are not new evidence anyway.** Their `data_sources` is
`anc_tribal_subsidiary_lookup` - the same
`data/raw/external/anc_tribal_subsidiary_lookup.csv` that `1072` already reads
as its own source 5, with the repoint machinery applied. They are a restatement
of an input the builder already has.

*(A correction to the record while measuring this: `docs/NEST_BUILD_LOG.md`
states the split as 212 / 20 / 14 = 223, which does not add up - those three
numbers sum to 246. The live
`data/staging/nest_owner_v6/enterprise_reconciliation.csv` says
**196 / 14 / 13 = 223**, which does. The doc's table is from an earlier run;
the file is right.)*

===========================================================================
WHAT IS EMITTED
===========================================================================
An owner row reaches `owner_v6_edges.jsonl` when ALL of these hold:

  1. it carries a `tribe_id` that crosswalks to a live register `cedar_uid`
     (`1130.resolve_parent`, imported - ONE crosswalk, not a second copy);
  2. its `enterprise_name` is non-blank after `tidy`;
  3. its UEI, if it has one, is not already carried by a live NEST row.

Everything else is written to a register with its reason. `1072` then applies
its own refusals on top - restricted publishers, the ANCSA village-government
guard, the hub-names-itself test - and this script does not duplicate any of
them.

Reads   <dissertation>/native_entity_enterprise_dataset_v6_geocoded.csv
        <dissertation>/native_entity_enterprise_dataset_v3.csv  (variants only)
        data/spine/cedar_identity_register.csv
        data/clean/nest_enterprises.csv
        code/1130_nest_owner_v6_reconcile.py   (the parent crosswalk)
        code/1072_tribally_owned_enterprises.py (norm/tidy - ONE normaliser)
Writes  data/staging/nest/owner_v6_edges.jsonl        <- the builder input
        data/staging/nest/owner_v6_refused.csv
        data/staging/nest/owner_v6_uei_already_held.csv
        data/staging/nest/owner_v3_name_variants.csv
        data/staging/nest/owner_v6_conservation.csv
        docs/nest_owner_v6_builder_input.json
"""
from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(10 ** 8)

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
STAGE = ROOT / "data" / "staging" / "nest"
DOCS = ROOT / "docs"
SCRIPT = "code/1133_nest_owner_v6_builder_input.py"
TODAY = dt.date.today().isoformat()

OWNER_DIR = Path(os.path.expanduser("~")) / "Desktop" / "dissertation" / \
    "data" / "tribal_federal_spending" / "clean"
V6 = OWNER_DIR / "native_entity_enterprise_dataset_v6_geocoded.csv"
V3 = OWNER_DIR / "native_entity_enterprise_dataset_v3.csv"

OUT_EDGES = STAGE / "owner_v6_edges.jsonl"
OUT_REFUSED = STAGE / "owner_v6_refused.csv"
OUT_UEIHELD = STAGE / "owner_v6_uei_already_held.csv"
OUT_VARIANTS = STAGE / "owner_v3_name_variants.csv"
OUT_CONSV = STAGE / "owner_v6_conservation.csv"
OUT_JSON = DOCS / "nest_owner_v6_builder_input.json"

SOURCE_ID = "OWNERV6"
OWNER_DOC = ("native_entity_enterprise_dataset_v6_geocoded.csv "
             "(the owner's research dataset, on this machine at "
             "~/Desktop/dissertation/data/tribal_federal_spending/clean/)")

# The floor `verify` holds. Set BELOW a measured green run so a real
# regression fails and ordinary drift does not.
FLOOR_EDGES = 5000
FLOOR_NEST_ROWS = 2800


def rd(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


def wcsv(path, rows, first=()):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    seen, cols = set(), []
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                cols.append(k)
    lead = [c for c in first if c in seen]
    cols = lead + [c for c in cols if c not in set(lead)]
    tmp = str(path) + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols or ["note"])
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    os.replace(tmp, path)


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def load_1072():
    """`norm` and `tidy` come from the builder itself. Two normalisers that
    drift are two clusterings, and this file would be measuring the drift."""
    return _load(CODE / "1072_tribally_owned_enterprises.py", "nest1072")


def load_1130():
    """`resolve_parent` is the ONE parent crosswalk. Re-implementing it here
    would be a second detector for one class, which is why `248` is a retired
    stub pointing at `293`."""
    return _load(CODE / "1130_nest_owner_v6_reconcile.py", "nest1130")


# ---------------------------------------------------------------------------
# EVIDENCE FAMILY -> the evidence_class vocabulary 1072 publishes
# ---------------------------------------------------------------------------
# `1130.family_of` classifies the owner's `verification_source` into the 1118
# families. Those are families, not evidence classes, so they are mapped once,
# here, into the vocabulary `nest_enterprises.evidence_class` already carries -
# and where no existing class is truthful, a new one is declared rather than
# an existing one stretched to cover it.
#
# EVID_RANK in 1072 scores the four pre-existing classes and defaults unknown
# ones to 0. That is the correct outcome and is deliberate: a resolver output
# must not win the canonical-display-name contest against an audited filing.
FAMILY_TO_EVIDENCE_CLASS = {
    "entity_self_published": (
        "parent_self_published_company_list",
        "the verification_source is the PARENT's own website, which is the "
        "same evidence class 1072 already publishes for a parent's company "
        "list"),
    "federal_registry": (
        "federal_certification_registry",
        "SBA DSBS or the IRS EO Business Master File - a federal register "
        "entry, an observer independent of the owner's own research"),
    "human_ruling": (
        "owner_research_dataset_hand_ruling",
        "the owner ruled this row by hand (`attribution_method = hand`, "
        "`user_final_tribes.dta`). A person decided it; no third party "
        "published it"),
    "cedar_inference": (
        "owner_research_dataset_resolver_output",
        "the owner's own cluster_v3 resolver produced this attribution. It is "
        "an inference, not an observation, and it is labelled as one so a "
        "consumer can exclude it"),
    "compiled_directory": (
        "compiled_third_party_directory",
        "a compiled corpus or encyclopaedia; per-statement provenance is not "
        "recorded"),
    "unattributed": (
        "owner_research_dataset_unattributed",
        "the row carries no verification_source. The only thing behind it is "
        "that the owner's dataset holds the row"),
}


# ---------------------------------------------------------------------------
# APPLIED CORRECTIONS - a refutation Cedar already made may not be re-imported
# ---------------------------------------------------------------------------
# `data/clean/cedar_correction_register.csv` (written by
# `code/354_correction_register.py`) records 178 APPLIED corrections as
# (entity, withdrawn_key) pairs: a name that was linked to an entity and has
# been UNLINKED, with the reason. `62_no_regression_check.py` scans every
# sibling table for a row that still keys one of them.
#
# THIS CHECK EXISTS BECAUSE THIS PASS TRIPPED IT. The owner's v6 file is an
# earlier vintage than the corrections, and its first ingest put
# `BRISTOL BAY AREA HEALTH CORPORATION` back under Bristol Bay Native
# Corporation (`ANRC-BRBYCO-00` / `CE-0007A-ZA`) as a NEST enterprise. That is
# finding **FA-01**, settled 2026-08-26 and again on 2026-08-29: BBAHC is a
# separate tribal health organisation, `SGVF-BRSTLB-00`; 742 rows were
# unlinked, the ledgers marked tier X, and the refutation harvested by `510`
# as deny assertion #332. `62` caught the re-import on the first run after
# the ingest.
#
# **An old file is a time machine.** Any pass that imports a dataset built
# before a correction will re-assert what the correction withdrew, and it will
# look like coverage. The register is the guard, and it is read here rather
# than a second list being written.
def load_corrections(m72):
    """-> {(entity_key, normalised withdrawn name)} for every applied UNLINK."""
    out = {}
    for r in rd(CLEAN / "cedar_correction_register.csv"):
        key = m72.norm(r.get("withdrawn_key") or "")
        if not key:
            continue
        for ent in ((r.get("entity_id") or "").strip(),
                    (r.get("cedar_uid") or "").strip()):
            if ent:
                out[(ent, key)] = r
    return out


def norm_uei(s):
    s = re.sub(r"[^A-Za-z0-9]", "", s or "").upper()
    return s if len(s) == 12 else ""


# ---------------------------------------------------------------------------
def build_context():
    m72 = load_1072()
    m30 = load_1130()
    reg, by_handle, by_stem, _names = m30.load_register()
    reg_by_uid = {r["cedar_uid"]: r for r in reg}
    # NEVER LET AN INSTRUMENT SCAN ITS OWN OUTPUT (AGENT_FIELD_GUIDE rule 10,
    # five instruments in this repo have now done it). The UEI-collision and
    # already-clustered tests below ask "does NEST ALREADY hold this firm" -
    # and after the first ingest NEST holds THIS SCRIPT'S OWN ROWS, so the
    # answer would depend on whether 1072 had been run yet. Rows whose
    # source_id is this pass are excluded, which makes `apply` idempotent and
    # its output independent of build order.
    nest_all = rd(CLEAN / "nest_enterprises.csv")
    nest = [r for r in nest_all if SOURCE_ID not in (r.get("source_id") or "")]
    uei_owner = {}          # UEI -> (enterprise_id, hub uid, name, column)
    nest_keys = set()       # (hub uid, normalised name) - the clustering key
    for r in nest:
        for c in ("uei", "uei_candidate"):
            u = norm_uei(r.get(c))
            if u:
                uei_owner.setdefault(u, (r["enterprise_id"],
                                         r["owner_hub_cedar_uid"],
                                         r["enterprise_name"], c))
        nest_keys.add((r["owner_hub_cedar_uid"],
                       r.get("enterprise_name_normalized") or ""))
    corrections = load_corrections(m72)
    return (m72, m30, reg, by_handle, by_stem, reg_by_uid, nest, uei_owner,
            nest_keys, corrections)


def classify(rows, m72, m30, by_handle, by_stem, reg, reg_by_uid, uei_owner,
             nest_keys, corrections):
    """-> (edges, refused, uei_held, counts). No writes."""
    edges, refused, uei_held = [], [], []
    counts = Counter()

    # THE PARENT CROSSWALK IS PER tribe_id, NOT PER ROW. 29 rows carry a
    # tribe_id and a BLANK canonical_name, and resolving per row made
    # `resolve_parent` fall to its name route with nothing to match on -
    # 83 rows refused as UNRESOLVED_NO_DISTINCTIVE_TOKENS for a parent the
    # same file names on another row. The name is a property of the PARENT.
    best_name = {}
    for r in rows:
        t = (r.get("tribe_id") or "").strip()
        c = (r.get("canonical_name") or "").strip()
        if t and c and len(c) > len(best_name.get(t, "")):
            best_name[t] = c
    xwalk = {}                       # tribe_id -> (uid, method, note)

    for r in rows:
        tid = (r.get("tribe_id") or "").strip()
        name = m72.tidy(r.get("enterprise_name") or "")
        canon = (r.get("canonical_name") or "").strip()
        am = (r.get("attribution_method") or "").strip()
        ds = (r.get("data_sources") or "").strip()

        def refuse(reason, detail):
            counts[reason] += 1
            refused.append({
                "refusal": reason, "refusal_basis": detail,
                "enterprise_name": r.get("enterprise_name", ""),
                "tribe_id": tid, "canonical_name": canon,
                "enterprise_uei": r.get("enterprise_uei", ""),
                "enterprise_cage_code": r.get("enterprise_cage_code", ""),
                "data_sources": ds, "attribution_method": am,
                "verification_source": r.get("verification_source", ""),
                "parent_entity_type": r.get("parent_entity_type", ""),
                "hq_state": r.get("hq_state", ""),
                "total_master_prime_dol_M": r.get("total_master_prime_dol_M", ""),
                "built_by": SCRIPT, "built_date": TODAY})

        if not name:
            refuse("BLANK_ENTERPRISE_NAME",
                   "the row names no enterprise, so there is nothing to hub")
            continue

        if not tid:
            # DECISION 1. Four different things, and only one of them is a
            # Cedar deficiency.
            if am == "unmatched":
                refuse("OWNER_FILE_SAYS_UNMATCHED",
                       "the owner's own `attribution_method` on this row is "
                       "`unmatched`: his resolver could NOT attribute this "
                       "federal awardee to any Native entity, and the row "
                       "carries no verification_source. A negative result may "
                       "not be published as a positive one (START_HERE 1b). "
                       "This block also contains natural persons' names.")
            elif ds == "sba_dsbs_native_entities":
                refuse("SBA_CERTIFIED_BUT_NO_OWNER_NAMED",
                       "a real, evidenced Native-owned firm in the SBA "
                       "certification register, with NO owner nation named on "
                       "the row. NEST's grain is (owner hub, enterprise "
                       "name), so it cannot hold this row. It belongs to "
                       "`native-owned-businesses` / the individually "
                       "Native-owned class, and this register is the join "
                       "that promotes it without a re-harvest.")
            else:
                refuse("NO_TRIBE_ID_ON_THE_ROW",
                       "the row names an enterprise but no owner, so it "
                       "cannot be hubbed. Source: %s" % (ds or "(none)"))
            continue

        if tid not in xwalk:
            xwalk[tid] = m30.resolve_parent(tid, best_name.get(tid, canon),
                                            by_handle, by_stem, reg)
        uid, method, note = xwalk[tid]
        if not uid:
            refuse("PARENT_UNRESOLVED_" + method,
                   "the owner's tribe_id %s does not crosswalk to a live "
                   "register entity, and an unresolved parent is an honest "
                   "outcome that is never forced (ADR-010). %s" % (tid, note))
            continue

        # AN APPLIED CORRECTION IS A REFUTATION, AND IT OUTRANKS THIS FILE.
        nk = m72.norm(name)
        corr = (corrections.get((tid, nk)) or corrections.get((uid, nk)))
        if corr:
            refuse("APPLIED_CORRECTION_" + (corr.get("finding_id") or "UNKNOWN"),
                   "Cedar has ALREADY WITHDRAWN this link. %s unlinked "
                   "%r from %s in %s on %s (%s rows). The owner's file is an "
                   "earlier vintage than the correction and re-asserts it. "
                   "Reason on the register: %s"
                   % (corr.get("recorded_by_script"),
                      corr.get("withdrawn_key"), corr.get("entity_id"),
                      corr.get("table"), corr.get("recorded_date"),
                      corr.get("rows_affected"), (corr.get("reason") or "")[:160]))
            continue

        u = norm_uei(r.get("enterprise_uei"))
        # A UEI collision only matters when this row would create a NEW
        # cluster. Where NEST already holds (this hub, this normalised name)
        # the row MERGES onto the existing enterprise and raises its
        # observation count - that is a corroboration and it is the point of
        # putting the file through the builder's clustering rather than
        # appending it. Refusing those would have discarded 173 of them.
        creates_new = (uid, m72.norm(name)) not in nest_keys
        if u and u in uei_owner and creates_new:
            eid, hub, ename, col = uei_owner[u]
            same = (hub == uid)
            uei_held.append({
                "collision": ("SAME_HUB_CORROBORATION" if same
                              else "CROSS_HUB_OWNERSHIP_DISAGREEMENT"),
                "enterprise_uei": u,
                "owner_enterprise_name": name,
                "owner_tribe_id": tid, "owner_hub_cedar_uid": uid,
                "owner_hub_name": (reg_by_uid.get(uid) or {}).get(
                    "canonical_name", ""),
                "nest_enterprise_id": eid, "nest_enterprise_name": ename,
                "nest_owner_hub_cedar_uid": hub,
                "nest_owner_hub_name": (reg_by_uid.get(hub) or {}).get(
                    "canonical_name", ""),
                "nest_uei_column": col,
                "collision_basis": (
                    "a UEI is ONE federal registration for ONE firm. NEST "
                    "already carries it, so emitting this row would create a "
                    "second enterprise for one company - the duplication the "
                    "merged-not-appended design of 1072 exists to stop. "
                    + ("Same hub: this is a corroboration of a row NEST "
                       "already holds, under a different name rendering."
                       if same else
                       "DIFFERENT HUB: the owner's file and NEST disagree "
                       "about who owns this firm. That needs an adjudication "
                       "and must not be settled by whichever pass ran last.")),
                "built_by": SCRIPT, "built_date": TODAY})
            refuse("UEI_ALREADY_HELD_BY_NEST_" + ("SAME_HUB" if same
                                                  else "OTHER_HUB"),
                   "UEI %s is already on NEST row %s (%s)" % (u, eid, ename))
            continue

        fam, _why = m30.family_of(r.get("verification_source") or "")
        ecls, ebasis = FAMILY_TO_EVIDENCE_CLASS.get(
            fam, ("owner_research_dataset_unattributed",
                  "family %r has no declared evidence class" % fam))
        vs = (r.get("verification_source") or "").strip()
        url = vs if vs.lower().startswith("http") else ""
        doc = OWNER_DOC if not url else (OWNER_DOC + " :: " + vs)
        rclass = (reg_by_uid.get(uid) or {}).get("entity_class", "")
        hint = ("ANC" if "Alaska Native" in rclass and "Corporation" in rclass
                else "NHO" if rclass == "Native Hawaiian Organization"
                else "TRIBE")
        # A VERBATIM rendering of the row, not a sentence about it.
        quote = ("owner v6 row: tribe_id=%s canonical_name=%s "
                 "enterprise_name=%s enterprise_uei=%s cage=%s ein=%s "
                 "is_federal_contractor=%s is_8a_certified=%s "
                 "is_nonprofit=%s verification_source=%s verified_date=%s "
                 "attribution_method=%s data_sources=%s"
                 % (tid, canon, r.get("enterprise_name", ""),
                    r.get("enterprise_uei", ""),
                    r.get("enterprise_cage_code", ""),
                    r.get("enterprise_ein", ""),
                    r.get("is_federal_contractor", ""),
                    r.get("is_8a_certified", ""), r.get("is_nonprofit", ""),
                    vs, r.get("verified_date", ""), am, ds))[:900]
        reviewed = "reviewed" if am in ("hand", "web_verified") \
            else "auto_ruled_not_human_reviewed"
        edges.append(m72._edge(
            parent_name=canon or tid,
            parent_cedar_uid=uid,
            parent_handle=tid,
            hub_cedar_uid=uid,
            hub_hint_name=canon,
            owner_class_hint=hint,
            child_name_raw=name,
            # DECISION 3. v6 states no relationship word, so none is
            # invented. The literal `unspecified` is emitted rather than a
            # BLANK: `1072.stage_build` reads `x.get("relationship") or
            # "subsidiary"`, so a blank is COERCED to `subsidiary` and
            # published as `relation_class = ownership`. It was, on 3,189
            # rows, on the first build of this input - caught by W3.
            # `canon_rel("unspecified")` finds no entry in `REL_CANON` and
            # returns `("unspecified", "affiliation")`, which is what the
            # evidence supports.
            relationship="unspecified",
            ownership_percent="",
            sector=(r.get("industry_sector") or
                    r.get("supersector_master_prime") or ""),
            child_cage=(r.get("enterprise_cage_code") or "").strip(),
            child_uei=u,
            child_city=(r.get("hq_city") or "").strip(),
            child_state=(r.get("hq_state") or "").strip(),
            evidence_class=ecls,
            source_id=SOURCE_ID,
            source_url=url,
            source_document=doc,
            source_fy="",
            source_edition_date=(r.get("verified_date") or "").strip(),
            quote=quote,
            depth_hint=1,
            identity_scope="owner_research_dataset_named_enterprise",
            retrieved_date=(r.get("verified_date") or TODAY).strip() or TODAY,
            source_terms_status="SILENT",
            source_review_status=reviewed,
        ))
        counts["EMITTED_" + ecls] += 1
        counts["_emitted"] += 1
        counts["_xwalk_" + method] += 1
    return edges, refused, uei_held, counts, xwalk


def v3_variants(m72):
    """DECISION 2. The v3-only names, keyed on UEI to the v6 row that holds
    the same registration. Recorded, never emitted as enterprises."""
    v6 = rd(V6)
    v3 = rd(V3)
    if not v6 or not v3:
        return [], {}
    by_uei = defaultdict(list)
    n6 = set()
    for r in v6:
        u = norm_uei(r.get("enterprise_uei"))
        if u:
            by_uei[u].append(r)
        n6.add(m72.norm(r.get("enterprise_name") or ""))
    out, stat = [], Counter()
    for r in v3:
        nm = m72.tidy(r.get("enterprise_name") or "")
        if not nm:
            stat["v3_blank_name"] += 1
            continue
        if m72.norm(nm) in n6:
            stat["v3_name_also_in_v6"] += 1
            continue
        u = norm_uei(r.get("enterprise_uei"))
        peers = by_uei.get(u, [])
        stat["v3_only_name_uei_present_in_v6" if peers
             else "v3_only_name_uei_absent_from_v6"] += 1
        out.append({
            "verdict": ("SAME_REGISTRATION_DIFFERENT_RENDERING" if peers
                        else "V3_ONLY_AND_NO_UEI_MATCH_IN_V6"),
            "enterprise_uei": u,
            "v3_enterprise_name": nm,
            "v3_name_normalized": m72.norm(nm),
            "v6_enterprise_name_same_uei": " | ".join(
                (x.get("enterprise_name") or "") for x in peers[:3]),
            "v6_name_normalized": " | ".join(
                m72.norm(x.get("enterprise_name") or "") for x in peers[:3]),
            "v3_tribe_id": (r.get("tribe_id") or "").strip(),
            "v3_data_sources": r.get("data_sources", ""),
            "verdict_basis": (
                "the same UEI is one federal registration for one firm, so "
                "this is v6's row under a different name string, not a firm "
                "v6 lost. Recovering it as an enterprise would create a "
                "duplicate, because NEST clusters on the normalised NAME and "
                "these two normalise apart. Recorded as an observed name "
                "variant." if peers else
                "no v6 row carries this UEI. This one IS a candidate, and it "
                "is the only shape of v3 loss that is real."),
            "built_by": SCRIPT, "built_date": TODAY})
    return out, stat


# ---------------------------------------------------------------------------
def run(write):
    if not V6.exists():
        print("The owner's v6 file is not on this machine:\n  %s" % V6)
        return 2
    ctx = build_context()
    (m72, m30, reg, by_handle, by_stem, reg_by_uid, nest, uei_owner,
     nest_keys, corrections) = ctx
    rows = rd(V6)
    print("=== 1133 %s ===" % ("apply" if write else "report"))
    print("  owner v6            %6d rows" % len(rows))
    print("  live NEST           %6d enterprises, %d not from this pass, "
          "%d distinct UEIs held"
          % (len(rd(CLEAN / "nest_enterprises.csv")), len(nest),
             len(uei_owner)))

    edges, refused, uei_held, counts, xwalk = classify(
        rows, m72, m30, by_handle, by_stem, reg, reg_by_uid, uei_owner,
        nest_keys, corrections)

    print("  EMITTED as builder input   %6d edges on %d hubs"
          % (len(edges), len({e["hub_cedar_uid"] for e in edges})))
    for k, v in sorted(counts.items()):
        if k.startswith("EMITTED_"):
            print("      %-46s %5d" % (k[8:], v))
    print("  REFUSED                    %6d rows" % len(refused))
    for k, v in sorted(Counter(r["refusal"] for r in refused).items(),
                       key=lambda x: -x[1]):
        print("      %-46s %5d" % (k, v))
    print("  UEI collisions             %6d  %s"
          % (len(uei_held),
             dict(Counter(x["collision"] for x in uei_held))))
    print("  parent crosswalk methods:  %s"
          % {k[7:]: v for k, v in counts.items() if k.startswith("_xwalk_")})

    variants, vstat = v3_variants(m72)
    print("  v3 name variants           %6d  %s" % (len(variants), dict(vstat)))

    consv = [
        {"source_table": "owner v6 (%s)" % V6.name, "rows_in": len(rows),
         "rows_accounted": len(edges) + len(refused),
         "unaccounted": len(rows) - len(edges) - len(refused),
         "dispositions": json.dumps(
             {"EMITTED": len(edges),
              **{k: v for k, v in
                 Counter(r["refusal"] for r in refused).items()}}),
         "built_by": SCRIPT, "built_date": TODAY},
        {"source_table": "owner v3 (%s)" % V3.name, "rows_in": len(rd(V3)),
         "rows_accounted": sum(vstat.values()),
         "unaccounted": len(rd(V3)) - sum(vstat.values()),
         "dispositions": json.dumps(dict(vstat)),
         "built_by": SCRIPT, "built_date": TODAY},
    ]
    for c in consv:
        print("  conservation  %-48s in=%d accounted=%d unaccounted=%d"
              % (c["source_table"][:48], c["rows_in"], c["rows_accounted"],
                 c["unaccounted"]))
        if c["unaccounted"]:
            print("      ! UNACCOUNTED ROWS - this must be 0")

    if not write:
        print("\n  report only. Nothing written. `apply` stages the input.")
        return 0

    STAGE.mkdir(parents=True, exist_ok=True)
    tmp = str(OUT_EDGES) + ".part"
    with open(tmp, "w", encoding="utf-8") as fh:
        for e in edges:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(tmp, OUT_EDGES)
    wcsv(OUT_REFUSED, refused, first=("refusal", "enterprise_name", "tribe_id"))
    wcsv(OUT_UEIHELD, uei_held, first=("collision", "enterprise_uei"))
    wcsv(OUT_VARIANTS, variants, first=("verdict", "enterprise_uei"))
    wcsv(OUT_CONSV, consv, first=("source_table",))
    OUT_JSON.write_text(json.dumps({
        "built_by": SCRIPT, "built_date": TODAY,
        "owner_v6_rows": len(rows),
        "edges_emitted": len(edges),
        "hubs": len({e["hub_cedar_uid"] for e in edges}),
        "evidence_class": {k[8:]: v for k, v in counts.items()
                           if k.startswith("EMITTED_")},
        "refused": dict(Counter(r["refusal"] for r in refused)),
        "uei_collisions": dict(Counter(x["collision"] for x in uei_held)),
        "parent_crosswalk": {k[7:]: v for k, v in counts.items()
                             if k.startswith("_xwalk_")},
        "v3": dict(vstat),
        "conservation_unaccounted": sum(c["unaccounted"] for c in consv),
    }, indent=1), encoding="utf-8")
    print("\n  -> %s" % OUT_EDGES)
    print("  -> %s" % OUT_REFUSED)
    print("  -> %s" % OUT_UEIHELD)
    print("  -> %s" % OUT_VARIANTS)
    print("  -> %s" % OUT_CONSV)
    print("\n  NEXT, IN THIS ORDER - the rows are not in NEST until it is run:")
    print("    py -3 code/1072_tribally_owned_enterprises.py assemble")
    print("    py -3 code/1072_tribally_owned_enterprises.py build")
    print("    py -3 code/1102_nest_corroboration_adjudication.py   "
          "# enricher, runs LAST")
    print("    py -3 code/1133_nest_owner_v6_builder_input.py verify")
    return 0


# ---------------------------------------------------------------------------
# verify -- FAILS when the rows are not in NEST
# ---------------------------------------------------------------------------
def _verify():
    fail, note = [], []

    if not OUT_EDGES.exists():
        fail.append("W1 the builder input %s does not exist" % OUT_EDGES.name)
        return False, fail, note
    n_edges = sum(1 for _ in open(OUT_EDGES, encoding="utf-8"))
    if n_edges < FLOOR_EDGES:
        fail.append("W1 builder input holds %d edges, floor %d"
                    % (n_edges, FLOOR_EDGES))
    note.append("W1 builder input %d edges" % n_edges)

    # W2 - THE ONE THAT MATTERS. A staged file is not a delivered row.
    # A conservation check would pass on a no-op (AGENT_FIELD_GUIDE rule 5),
    # so this asserts the INTENDED delta on the table the consumer reads.
    nest = rd(CLEAN / "nest_enterprises.csv")
    if not nest:
        fail.append("W2 nest_enterprises.csv is absent or empty")
        return False, fail, note
    mine = [r for r in nest if SOURCE_ID in (r.get("source_id") or "")]
    if len(mine) < FLOOR_NEST_ROWS:
        fail.append("W2 only %d NEST rows carry source_id %s (floor %d). "
                    "The input is staged but 1072 has NOT ingested it - run "
                    "`1072 assemble` then `1072 build`."
                    % (len(mine), SOURCE_ID, FLOOR_NEST_ROWS))
    else:
        note.append("W2 %d of %d NEST rows carry source_id %s"
                    % (len(mine), len(nest), SOURCE_ID))

    # W3 - no relation_class invented on these rows.
    #
    #      The test allows ONE lawful exception and names it, because the
    #      alternative is a check that fires on a correct row. Where the
    #      cluster carries a SECOND source that DID state a relationship
    #      word, `relationship_as_recorded` shows it beside `unspecified`
    #      ("subsidiary | unspecified") and the ownership claim belongs to
    #      that source, not to the owner's file. `C P Leasing, Inc` under
    #      Tlingit & Haida is the live instance: 2 distinct sources, one of
    #      them goldbelt.com's own directory. What may never happen is an
    #      ownership claim whose ONLY recorded relationship is `unspecified`.
    bad = []
    for r in mine:
        if r.get("relation_class") != "ownership":
            continue
        rec = {x.strip() for x in
               (r.get("relationship_as_recorded") or "").split("|")} - {""}
        if rec <= {"unspecified"}:
            bad.append(r)
    if bad:
        fail.append("W3 %d owner-v6 rows were published as `ownership` with "
                    "NO source stating a relationship word (e.g. %s)"
                    % (len(bad), bad[0].get("enterprise_name")))
    else:
        n_ok = sum(1 for r in mine if r.get("relation_class") == "ownership")
        note.append("W3 0 owner-v6 rows claim ownership on their own "
                    "evidence (%d claim it on a second source that stated a "
                    "relationship)" % n_ok)

    # W4 - every emitted edge has a source, so 1072's I3 cannot fail on us
    nosrc = 0
    with open(OUT_EDGES, encoding="utf-8") as fh:
        for line in fh:
            e = json.loads(line)
            if not (e.get("source_url") or e.get("source_document")):
                nosrc += 1
    if nosrc:
        fail.append("W4 %d staged edges carry no source" % nosrc)
    else:
        note.append("W4 every staged edge names a source")

    # W5 - the refused registers exist and account for the file
    for p in (OUT_REFUSED, OUT_UEIHELD, OUT_VARIANTS, OUT_CONSV):
        if not p.exists():
            fail.append("W5 register %s is missing - a refusal that is not "
                        "written down is a deletion" % p.name)
    consv = rd(OUT_CONSV)
    un = sum(int(c.get("unaccounted") or 0) for c in consv)
    if not consv:
        fail.append("W5 no conservation table - UNMEASURED")
    elif un:
        fail.append("W5 %d owner rows unaccounted for" % un)
    else:
        note.append("W5 conservation balances, 0 unaccounted")

    # W6 - the 8,928 `unmatched` rows must be absent from NEST
    # W6 tests a NAME, and a name is not unique. 11 names refused as
    # `unmatched` on one row of the owner's file are ALSO carried by a
    # properly hubbed row of the same file, so a bare name test reported them
    # as leaks when the row that reached NEST was the legitimate one. The
    # banned set is therefore the refused names MINUS every name this pass
    # emitted - which is what "a name that could only have come from the
    # refused block" actually means.
    ref = rd(OUT_REFUSED)
    emitted_names = set()
    with open(OUT_EDGES, encoding="utf-8") as fh:
        for line in fh:
            emitted_names.add(
                (json.loads(line).get("child_name_raw") or "").strip().lower())
    banned = {(r["enterprise_name"] or "").strip().lower()
              for r in ref
              if r["refusal"] == "OWNER_FILE_SAYS_UNMATCHED"} - emitted_names
    if not banned:
        fail.append("W6 UNMEASURED - no OWNER_FILE_SAYS_UNMATCHED rows in the "
                    "refusal register, so this check proves nothing")
    else:
        leak = [r for r in mine
                if (r.get("enterprise_name") or "").strip().lower() in banned]
        if leak:
            fail.append("W6 %d rows the owner's own file marks `unmatched` "
                        "reached NEST (e.g. %s)"
                        % (len(leak), leak[0].get("enterprise_name")))
        else:
            note.append("W6 0 of %d `unmatched` names reached NEST"
                        % len(banned))

    # W7 - no APPLIED CORRECTION was re-imported. `62` scans every sibling
    #      table for this; the point of checking it here is that a red 62 is
    #      found after the rebuild, and this is found before it.
    m72 = load_1072()
    corr = load_corrections(m72)
    if not corr:
        fail.append("W7 UNMEASURED - cedar_correction_register.csv is empty "
                    "or absent, so this check proves nothing")
    else:
        back = []
        for r in mine:
            nk = m72.norm(r.get("enterprise_name") or "")
            for ent in ((r.get("owner_hub_handle") or "").strip(),
                        (r.get("owner_hub_cedar_uid") or "").strip()):
                if ent and (ent, nk) in corr:
                    back.append(r)
                    break
        if back:
            fail.append("W7 %d owner-v6 rows re-import a WITHDRAWN link "
                        "(e.g. %s under %s)"
                        % (len(back), back[0].get("enterprise_name"),
                           back[0].get("owner_hub_name")))
        else:
            note.append("W7 0 of %d applied corrections re-imported"
                        % len(corr))

    return (not fail), fail, note


def cmd_verify():
    ok, fail, note = _verify()
    print("=== 1133 VERIFY ===")
    for n in note:
        print("  ok   %s" % n)
    for f in fail:
        print("  FAIL %s" % f)
    print("  %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def cmd_selftest():
    ok, fail, _ = _verify()
    if not ok:
        print("selftest refuses to run on a RED baseline: %s" % fail)
        return 2
    results = []
    baks = {}
    try:
        # W1: the builder input is gone
        baks[OUT_EDGES] = OUT_EDGES.with_suffix(".jsonl.selftest_bak")
        shutil.move(str(OUT_EDGES), str(baks[OUT_EDGES]))
        o, f, _ = _verify()
        results.append(("W1 input missing", not o,
                        any(x.startswith("W1") for x in f)))
        shutil.move(str(baks[OUT_EDGES]), str(OUT_EDGES))
        baks.pop(OUT_EDGES)

        # W1: the input is truncated below the floor
        full = OUT_EDGES.read_text(encoding="utf-8")
        OUT_EDGES.write_text("\n".join(full.splitlines()[:5]) + "\n",
                             encoding="utf-8")
        o, f, _ = _verify()
        results.append(("W1 input below floor", not o,
                        any(x.startswith("W1") for x in f)))
        OUT_EDGES.write_text(full, encoding="utf-8")

        # W2: NEST has not ingested it. Simulated on a COPY of the table.
        p = CLEAN / "nest_enterprises.csv"
        baks[p] = p.with_suffix(".csv.selftest_bak")
        shutil.copy2(p, baks[p])
        rows = rd(p)
        for r in rows:
            r["source_id"] = (r.get("source_id") or "").replace(SOURCE_ID, "")
        wcsv(p, rows, first=list(rows[0].keys()))
        o, f, _ = _verify()
        results.append(("W2 NEST has not ingested", not o,
                        any(x.startswith("W2") for x in f)))
        shutil.copy2(baks[p], p)
        baks[p].unlink(missing_ok=True)
        baks.pop(p)

        # W3: an owner-v6 row published as ownership
        shutil.copy2(p, p.with_suffix(".csv.selftest_bak"))
        baks[p] = p.with_suffix(".csv.selftest_bak")
        rows = rd(p)
        hit = next((r for r in rows
                    if SOURCE_ID in (r.get("source_id") or "")), None)
        if hit is None:
            results.append(("W3 ownership invented", False, False))
        else:
            hit["relation_class"] = "ownership"
            # BOTH halves, or the fixture does not reproduce the defect: W3
            # allows ownership where a SECOND source stated a relationship
            # word, so the injected row must record only `unspecified`.
            hit["relationship_as_recorded"] = "unspecified"
            wcsv(p, rows, first=list(rows[0].keys()))
            o, f, _ = _verify()
            results.append(("W3 ownership invented", not o,
                            any(x.startswith("W3") for x in f)))
        shutil.copy2(baks[p], p)
        baks[p].unlink(missing_ok=True)
        baks.pop(p)

        # W7: a WITHDRAWN link back in NEST (the FA-01 shape)
        m72 = load_1072()
        corr = load_corrections(m72)
        rows2 = rd(p)
        hit2 = next((r for r in rows2
                     if SOURCE_ID in (r.get("source_id") or "")), None)
        if hit2 is None or not corr:
            results.append(("W7 withdrawn link re-imported", False, False))
        else:
            shutil.copy2(p, p.with_suffix(".csv.selftest_bak"))
            baks[p] = p.with_suffix(".csv.selftest_bak")
            ent, key = next(iter(corr))
            src = corr[(ent, key)]
            hit2["owner_hub_cedar_uid"] = src.get("cedar_uid") or ent
            hit2["owner_hub_handle"] = src.get("entity_id") or ent
            hit2["enterprise_name"] = src.get("withdrawn_key")
            wcsv(p, rows2, first=list(rows2[0].keys()))
            o, f, _ = _verify()
            results.append(("W7 withdrawn link re-imported", not o,
                            any(x.startswith("W7") for x in f)))
            shutil.copy2(baks[p], p)
            baks[p].unlink(missing_ok=True)
            baks.pop(p)

        # W5: conservation gone
        baks[OUT_CONSV] = OUT_CONSV.with_suffix(".csv.selftest_bak")
        shutil.move(str(OUT_CONSV), str(baks[OUT_CONSV]))
        o, f, _ = _verify()
        results.append(("W5 register missing", not o,
                        any(x.startswith("W5") for x in f)))
        shutil.move(str(baks[OUT_CONSV]), str(OUT_CONSV))
        baks.pop(OUT_CONSV)
    finally:
        for live, bak in baks.items():
            if Path(bak).exists():
                shutil.move(str(bak), str(live))

    okr, fr, _ = _verify()
    print("=== 1133 SELFTEST ===")
    bad = 0
    for name, fired, named in results:
        print("  %-28s fired=%s named_invariant=%s" % (name, fired, named))
        if not (fired and named):
            bad += 1
    print("  restored baseline green: %s %s" % (okr, "" if okr else fr))
    if not okr:
        bad += 1
    print("  %s" % ("PASS" if bad == 0 else "FAIL (%d)" % bad))
    return 0 if bad == 0 else 1


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "report":
        return run(write=False)
    if cmd == "apply":
        return run(write=True)
    if cmd == "verify":
        return cmd_verify()
    if cmd == "selftest":
        return cmd_selftest()
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
