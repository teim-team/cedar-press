#!/usr/bin/env python3
r"""
Cedar Press - 61: Add Native Hawaiian Organizations and Intertribal
Organizations to the entity spine.

THE GAP THIS CLOSES
-------------------
The spine held 866 entities and **zero** Native Hawaiian Organizations and
**zero** entities classed as intertribal. Elijah has been ruling NHO parents
since 2026-08-05 (`data/clean/nho_parents.csv`, 21 parents) and those rulings
had nothing to land on: `code/09_import_rulings.py` re-attributes a ruling that
names a different owner, so a named owner absent from the spine sends the whole
link to tier X with the correct answer sitting unusable in its own rationale.

This is the same defect script 52 closed for ANCSA village corporations, and it
follows script 52's shape exactly: a name collision aborts rather than
overwrites, no existing spine row is altered or deleted, and every added row
carries a `cedar_entity_id` back to the register that sourced it.

SOURCES (nothing is invented here; everything is joined)
--------------------------------------------------------
  data/clean/nho_register.csv        218 rows - 33 verified contracting NHOs
                                     + 185 DOI Office of Native Hawaiian
                                     Relations roster rows at tier C
  data/clean/intertribal_orgs.csv     57 verified intertribal organizations
  data/clean/intertribal_memberships.csv  989 membership rows (NOT ownership)

Both registers were built by `code/36_build_nho_intertribal.py` and every row
carries `evidence_url` + `evidence_quote`. This script adds NOTHING that lacks
both.

WHAT THIS REFUSES TO ADD, AND WHY
---------------------------------
1. **`Hoilina Ranch LLC`** - 13 C.F.R. 124.110 requires an NHO to be a
   NON-PROFIT organization. An LLC cannot be one. It is described in the wild as
   "Native Hawaiian organization-OWNED", which names it a subsidiary. Its actual
   NHO parent is unidentified. Review item NHOIT-002.

2. **`Alaka'i Services Group Inc.` (ASGI)** - a SUBSIDIARY of `Alaka'i
   Foundation, Inc.`, which is the NHOA member in all 9 captures 2022-2024. The
   parent is added (N-0018); the subsidiary is not. Review item NHOIT-001.
   DO NOT MERGE `Alaka'i Foundation, Inc.` with `Alaka'ina Foundation` - two
   different organisations whose names differ by two letters.

3. **`Kalaimoku Foundation`** (N-0033, tier C) - the only evidence located is a
   consulting VENDOR'S case study. Neither the Foundation nor kalaimoku.com
   states the relationship. Review item NHOIT-004.

4. **`Ho'opale Foundation`** (N-0032, tier C) - its own site says "a Native
   Hawaiian organization" in lower case, which is a descriptor and not the
   13 C.F.R. 124.110 term of art; the Ho'opale -> Nexus -> Pacific Ridge chain
   is uncorroborated by any retrieved source. Review item NHOIT-003.

5. **The 185 DOI-roster rows** - the DOI ONHR list is an NHPA *consultation*
   notification list, not a contracting registry. Those rows are a discovery
   pool at tier C. Putting them in the spine would make 185 unverified
   organisations roll-up targets.

6. **8(a) certification is never the basis.** 8(a) admits both entity-owned
   firms and firms owned by disadvantaged INDIVIDUALS - HALOA Construction is
   family-owned and 8(a). What carries evidentiary weight is the NHOA membership
   rule, because NHOA membership is gated: "NHOA membership is open to any
   non-profit NHO certified by the SBA pursuant to 13 C.F.R. 124.3." That makes
   a directory listing evidence about the PARENT.

HAWAIIAN ORTHOGRAPHY
--------------------
`norm()` is imported from `code/33_apply_party_rulings.py` rather than copied,
for the reason script 09 gives in its own docstring: there must be ONE
normaliser in the project or the copies drift. That function folds diacritics
through NFKD BEFORE stripping non-alphanumerics, so it handles the okina AND the
kahako together. A normaliser that folded only the okina cost 8 organisations
their EINs (`Hui o Kuapa` vs the IRS record `Hui O Kuapa`), and the same class of
bug hid `Ukpeagvik Inupiat Corporation` from its own spine row.

MEMBERS ARE NOT OWNERS
----------------------
Intertribal organizations have MEMBERS. `parent_native_entity` must stay empty
for every `ITO-` row. The spine schema has no such column at all, so this is
satisfied structurally; the membership relation lives in
`intertribal_memberships.csv` and is joined through the crosswalk this script
writes. `CRITFC` and `NWIFC` have no EIN because they are intertribal
GOVERNMENTAL fishery agencies, not chartered charities - NWIFC files 103
lobbying reports with zero 990 presence. Absence of an EIN is not absence of the
organisation.

Reads  data/clean/nho_register.csv
       data/clean/intertribal_orgs.csv
       data/spine/cedar_entity_spine.csv
Writes data/spine/cedar_entity_spine.csv          (+ .bak_<date>_pre61)
       data/clean/nho_ito_spine_crosswalk.csv     proposed_id -> tribe_id
       data/clean/nho_ownership_changes.csv       Alaka'ina -> BSNC, June 2026
       review/nho_ito_refused_<date>.csv          every refusal, with its reason
       logs/61_add_nho_intertribal.log
"""

import csv
import importlib.util
import re
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(CEDAR / "code"))
from cedar_keys import surrogate_id                            # noqa: E402

# --------------------------------------------------------------------------
# THE PRIMARY KEY OF nho_ownership_changes.csv, AND WHAT IT IS MADE OF
#
# `event_id` was `f"OWN-NHO-2026-{i:03d}"` where `i` was the position in a
# `|`-split of one subsidiary string. Re-order that string upstream and every
# ownership event changes id - on a table whose whole purpose is to date an
# ownership change so contract attribution can be time-aware.
#
# It is now a deterministic blake2b digest of what the source states: the
# MONTH it took effect, the ACQUIRER, the FIRM ACQUIRED, and the DIRECTION.
# `effective_date` is deliberately BLANK on all nine rows - the source says
# "June 2026" and gives no day, and this project does not invent one - so the
# MONTH is the dated part of the key and `effective_date` is not in it.
# Measured 2026-08-26: unique over all 9 rows, 0 blank.
# --------------------------------------------------------------------------
NHO_OWNERSHIP_EVENT_KEY_COLUMNS = ["effective_month", "acquirer_entity",
                                   "target_entity", "direction"]
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

# ---------------------------------------------------------------------------
# ONE normaliser, imported not copied (see docstring).
# ---------------------------------------------------------------------------
_spec = importlib.util.spec_from_file_location(
    "m33", CEDAR / "code" / "33_apply_party_rulings.py")
_M33 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_M33)
norm = _M33.norm
core = _M33.core

LOG_LINES = []


def log(msg=""):
    print(msg)
    LOG_LINES.append(msg)


# ---------------------------------------------------------------------------
# Refusals. Keyed on the normalised name so orthography cannot dodge the rule.
# ---------------------------------------------------------------------------
REFUSE = {
    norm("Hoilina Ranch LLC"): (
        "13 C.F.R. 124.110 requires an NHO to be a NON-PROFIT organization; an "
        "LLC cannot be one. Described in the wild as 'Native Hawaiian "
        "organization-owned', which names it a SUBSIDIARY, not the NHO. Its "
        "actual NHO parent is unidentified. Review item NHOIT-002."),
    norm("ALAKA`I SERVICES GROUP INC."): (
        "SUBSIDIARY of Alaka`i Foundation, Inc., which is the NHOA member in "
        "all 9 captures 2022-05-28..2024-04-14 and is added here as N-0018. "
        "ASGI's own site states no NHO status. Review item NHOIT-001."),
    norm("Alaka'i Services Group Inc."): (
        "SUBSIDIARY of Alaka`i Foundation, Inc. - see above. Review NHOIT-001."),
    norm("Kalaimoku Foundation"): (
        "Tier C. The only evidence located is a consulting VENDOR'S case study; "
        "neither the Foundation nor kalaimoku.com states the relationship, and "
        "kalaimoku.com describes itself only as 'Native Hawaiian-Owned' and "
        "'8(a) Certified since 2011'. 8(a) is not evidence of NHO status. "
        "Review item NHOIT-004."),
    norm("Ho'opale Foundation"): (
        "Tier C. Its own site says 'a Native Hawaiian organization' in LOWER "
        "CASE - a descriptor, not the 13 C.F.R. 124.110 term of art. The "
        "Ho'opale -> Nexus Consulting Group -> Pacific Ridge chain is "
        "uncorroborated by any retrieved source. Review item NHOIT-003."),
}

CLASS_NHO = "Native Hawaiian Organization"
CLASS_ITO = "Intertribal Organization"

# ---------------------------------------------------------------------------
# THE LEDGER ALREADY USES THE `NHO-` PREFIX.
#
# `cedar_identifier_ledger_tiered.csv` carries 20 links on two `NHO-` ids that
# no spine row ever backed - orphan identifiers with an empty canonical_name.
# Minting a SECOND id for an organisation the ledger can already name is
# exactly how one entity becomes two, so where a pre-existing id demonstrably
# belongs to a register organisation the spine ADOPTS it rather than minting.
#
# Note the token conventions differ: the ledger's ids are 7-8 characters
# (NHO-MANUKAI-00, NHO-NAKUPUNA-00) and this script mints 6, so no minted id
# can silently land on one of them.
# ---------------------------------------------------------------------------
ADOPT_EXISTING_ID = {
    norm("Nakupuna Foundation"): (
        "NHO-NAKUPUNA-00",
        "The ledger already carries NHO-NAKUPUNA-00 on 'Nakupuna Solutions, "
        "Llc'. nakupuna.com: 'The Nakupuna Companies are majority owned by the "
        "Nakupuna Foundation, a Native Hawaiian Organization...' and Nakupuna "
        "Solutions is one of the eight named companies. Adopting the id makes "
        "that link join instead of orphaning."),
}

# NOT adoptable, and the reason is the finding. Reported, never merged.
CONFLATED_LEDGER_IDS = [{
    "tribe_id": "NHO-MANUKAI-00",
    "n_links": "19",
    "problem":
        "One id carrying at least 17 UNRELATED organisations. 16 of the 19 "
        "links come from need_v6_geocoded.csv - the method quarantined at 9 "
        "rulings against and 0 for - and the names under it include Ailani "
        "Hawaiian Defense/Federal/Solutions/Technology, Hungry Hawaiian LLC, "
        "Hawaiian Steam Inc, Native Hawaiian Legal Corporation, Native "
        "Hawaiian Education Association and COUNCIL FOR NATIVE HAWAIIAN "
        "ADVANCEMENT (which is I-012 in the intertribal register, a wholly "
        "different organisation).",
    "why_not_fixed_here":
        "'Manu Kai, LLC' and 'Polu Kai Services LLC' are not in nho_register.csv "
        "at all, so no evidence in this build names their NHO parent. Adopting "
        "this id for any register organisation would inherit the conflation. "
        "All 19 links are tier C and therefore unpublishable, so the defect is "
        "contained; it is NOT corrected.",
    "recommended_action":
        "Split by organisation before any of these leave tier C. Council for "
        "Native Hawaiian Advancement should be re-pointed at the new ITO row.",
    "flagged_date": TODAY,
}]

STOP = {"the", "inc", "incorporated", "corporation", "corp", "company", "llc",
        "ltd", "limited", "native", "of", "and", "association", "foundation",
        "national", "american", "indian", "tribal", "tribes", "inter",
        "intertribal", "council"}


def read_csv(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    log(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def token(name, taken):
    """Deterministic 6-character id token, in the style the spine already uses
    (ANRC-AHTNAI-00, ANVC-ALAKAN-00). Collisions get a numeric suffix rather
    than a silent merge. Copied in shape from code/52_add_village_corporations.py
    so the two mint compatible ids."""
    words = [w for w in norm(name).split() if w not in STOP]
    if not words:
        words = norm(name).split() or ["entity"]
    base = "".join(words)
    cons = re.sub(r"[aeiou]", "", base)
    cand = (cons if len(cons) >= 6 else base)[:6].upper().ljust(6, "X")
    if cand not in taken:
        return cand
    for i in range(1, 100):
        alt = (cand[:5] + str(i))[:6]
        if alt not in taken:
            return alt
    raise SystemExit(f"cannot mint a unique token for {name}")


def main():
    log("=== Cedar Press 61: add NHOs + intertribal organizations ===\n")

    spine = read_csv(SPINE)
    fields = list(spine[0].keys())
    log(f"spine entities before : {len(spine):,}")
    log(f"spine columns         : {fields}")

    # `parent_native_entity` is not in the spine schema. That is not an
    # omission to fix here: intertribal organizations must NOT carry one, and
    # the NHO subsidiary relation lives in nho_register.subsidiaries. Recorded
    # so the absence is deliberate rather than rediscovered.
    if "parent_native_entity" in fields:
        log("  NOTE: spine carries parent_native_entity; ITO rows leave it EMPTY.")
    else:
        log("  NOTE: spine has no parent_native_entity column - the "
            "'members, not owners' rule is satisfied structurally.")

    nho_all = read_csv(CLEAN / "nho_register.csv")
    nho = [r for r in nho_all if r["nho_class"] == "contracting_nho"]
    doi_only = [r for r in nho_all if r["nho_class"] != "contracting_nho"]
    ito = read_csv(CLEAN / "intertribal_orgs.csv")
    log(f"\nnho_register.csv      : {len(nho_all)} rows "
        f"({len(nho)} contracting NHO, {len(doi_only)} DOI-roster tier C)")
    log(f"intertribal_orgs.csv  : {len(ito)} rows")

    # ---- lookups on the existing spine ------------------------------------
    have_norm, have_core = {}, {}
    for r in spine:
        have_norm.setdefault(norm(r["canonical_name"]), r)
        have_core.setdefault(core(r["canonical_name"]), r)
        for a in (r.get("aliases") or "").split("|"):
            if a.strip():
                have_norm.setdefault(norm(a), r)
    have_ids = {r["tribe_id"] for r in spine}
    have_ceid = {r.get("cedar_entity_id", "") for r in spine if r.get("cedar_entity_id")}
    taken = {r["tribe_id"].split("-")[1] for r in spine if "-" in r["tribe_id"]}

    added, refused, crosswalk = [], [], []
    skipped = Counter()

    def consider(rec, kind):
        """rec: dict with name, aliases, proposed_id, state, url, quote, tier."""
        name = rec["name"].strip()
        n = norm(name)

        if n in REFUSE:
            refused.append({
                "entity_class": kind, "proposed_id": rec["proposed_id"],
                "organization_name": name, "reason": REFUSE[n],
                "evidence_url": rec["url"], "refused_date": TODAY,
            })
            skipped["refused on evidence"] += 1
            return

        # PRIME DIRECTIVE gate. Both layers need a retrieved URL. NHOs
        # additionally need a verbatim quote, because for an NHO the CLASS
        # CLAIM is the contested fact and only the organisation's own words
        # (or the gated NHOA membership rule) establish it. For an intertribal
        # organization the contested fact is existence and membership, which
        # the register carries as EIN / LDA-filing counts / roster counts
        # against a retrieved URL.
        if not rec["url"].strip():
            refused.append({
                "entity_class": kind, "proposed_id": rec["proposed_id"],
                "organization_name": name,
                "reason": "No retrieved evidence_url. "
                          "Prime directive: zero fabrication.",
                "evidence_url": "", "refused_date": TODAY,
            })
            skipped["no evidence url"] += 1
            return
        if kind == CLASS_NHO and not rec["quote"].strip():
            refused.append({
                "entity_class": kind, "proposed_id": rec["proposed_id"],
                "organization_name": name,
                "reason": "No verbatim evidence_quote. An NHO class claim "
                          "requires the organisation's own words or the gated "
                          "NHOA membership rule.",
                "evidence_url": rec["url"], "refused_date": TODAY,
            })
            skipped["no evidence quote"] += 1
            return

        # ---- collision guards. Never overwrite; never duplicate. ----------
        # Guard the empty core: a name made entirely of structural words would
        # otherwise collide with every other such name.
        c = core(name)
        hit = have_norm.get(n) or (have_core.get(c) if c else None)
        if hit:
            # This is not a failure. It means the organisation is ALREADY a
            # spine entity under another class - the Alaska self-governance
            # consortia are intertribal organisations that the NEID backbone
            # already carries as SGVF. Record the mapping so the membership
            # file still joins, and do not mint a second identity for it.
            crosswalk.append({
                "proposed_id": rec["proposed_id"],
                "organization_name": name,
                "layer": kind,
                "tribe_id": hit["tribe_id"],
                "spine_canonical_name": hit["canonical_name"],
                "spine_entity_class": hit["entity_class"],
                "status": "ALREADY_IN_SPINE",
                "note": "Matched an existing spine entity; not re-minted. The "
                        "existing row is authoritative.",
            })
            skipped["already in spine"] += 1
            return

        if rec["proposed_id"] and rec["proposed_id"] in have_ceid:
            skipped["already in spine by cedar_entity_id"] += 1
            return

        prefix = "NHO" if kind == CLASS_NHO else "ITO"
        adopt = ADOPT_EXISTING_ID.get(n)
        if adopt:
            tid, why = adopt
            log(f"  ADOPTING pre-existing ledger id {tid} for {name}")
            log(f"    {why}")
        else:
            tok = token(name, taken)
            taken.add(tok)
            tid = f"{prefix}-{tok}-00"
        if tid in have_ids:
            raise SystemExit(f"ABORT: {tid} already exists. Refusing to "
                             f"overwrite an existing spine entity.")

        aliases = [a.strip() for a in re.split(r"[;|]", rec["aliases"] or "")
                   if a.strip()]
        if name not in aliases:
            aliases.insert(0, name)

        row = {f: "" for f in fields}
        row.update({
            "tribe_id": tid,
            "canonical_name": name,
            "entity_class": kind,
            "state": rec["state"],
            "cedar_entity_id": rec["proposed_id"],
            "aliases": "|".join(aliases),
        })
        for k in ("n_uei_tierA", "n_uei_tierB", "n_cage", "n_ein"):
            if k in row:
                row[k] = "0"
        if "n_ein" in row and rec.get("ein", "").strip():
            row["n_ein"] = "1"

        added.append(row)
        have_ids.add(tid)
        have_norm[n] = row
        if c:
            have_core.setdefault(c, row)
        crosswalk.append({
            "proposed_id": rec["proposed_id"],
            "organization_name": name,
            "layer": kind,
            "tribe_id": tid,
            "spine_canonical_name": name,
            "spine_entity_class": kind,
            "status": "ADDED",
            "note": f"tier {rec['tier']}; basis: {rec['basis']}; "
                    f"evidence: {rec['url']}",
        })

    # ---- PART A: NHOs -----------------------------------------------------
    log("\n[A] Native Hawaiian Organizations")
    for r in nho:
        consider({
            "name": r["organization_name"], "aliases": r["aliases"],
            "proposed_id": r["proposed_id"], "state": r.get("state", "HI") or "HI",
            "url": r["evidence_url"], "quote": r["evidence_quote"],
            "tier": r["confidence_tier"], "basis": r["nho_status_basis"],
            "ein": r.get("ein", ""),
        }, CLASS_NHO)
    n_nho = len(added)
    log(f"  added : {n_nho}")

    # The 185 DOI-roster rows are NOT added. Say so, with the count, so the
    # decision is visible rather than looking like an oversight.
    log(f"  NOT added: {len(doi_only)} DOI Office of Native Hawaiian Relations "
        f"roster rows.")
    log("            The ONHR list is an NHPA CONSULTATION notification list, "
        "not a")
    log("            contracting registry. They stay a tier-C discovery pool.")

    # ---- PART B: intertribal organizations --------------------------------
    log("\n[B] Intertribal organizations")
    for r in ito:
        consider({
            "name": r["organization_name"], "aliases": r["aliases"],
            "proposed_id": r["proposed_id"], "state": "",
            "url": r["evidence_url"],
            "quote": r.get("notes", ""),
            "tier": "A", "basis": f"{r['org_scope']} intertribal organization",
            "ein": r.get("ein", ""),
        }, CLASS_ITO)
    n_ito = len(added) - n_nho
    log(f"  added : {n_ito}")

    for k, v in skipped.most_common():
        log(f"  skipped : {v}  ({k})")

    # ---- write ------------------------------------------------------------
    log("\n[C] Writing")
    if added:
        bak = SPINE.with_suffix(f".csv.bak_{TODAY}_pre61")
        shutil.copy2(SPINE, bak)
        log(f"  backed up spine -> {bak.name}")
        with open(SPINE, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(spine + added)
        log(f"  wrote {SPINE.relative_to(CEDAR)}  "
            f"({len(spine)} -> {len(spine)+len(added)} entities)")

    write_csv(CLEAN / "nho_ito_spine_crosswalk.csv", crosswalk,
              ["proposed_id", "organization_name", "layer", "tribe_id",
               "spine_canonical_name", "spine_entity_class", "status", "note"])
    write_csv(REVIEW / f"nho_ito_refused_{TODAY}.csv", refused,
              ["entity_class", "proposed_id", "organization_name", "reason",
               "evidence_url", "refused_date"])
    write_csv(REVIEW / f"nho_ledger_id_conflations_{TODAY}.csv",
              CONFLATED_LEDGER_IDS,
              ["tribe_id", "n_links", "problem", "why_not_fixed_here",
               "recommended_action", "flagged_date"])
    for c in CONFLATED_LEDGER_IDS:
        log(f"  WARNING: {c['tribe_id']} conflates unrelated organisations "
            f"({c['n_links']} links, all tier C). Flagged, not fixed.")

    # ---- OWNERSHIP CHANGE: Alaka'ina -> BSNC, June 2026 -------------------
    #
    # "Certified in 2004 as a Native Hawaiian Organization (NHO), the Alaka'ina
    #  Foundation entered federal contracting in 2005 and established nine (9)
    #  for profit firms that were wholly acquired in June 2026 by BSNC."
    #                                            -- http://beringalakaina.com/
    #
    # The FOUNDATION remains an NHO. Its nine firms became ANC-owned. Recording
    # the DATE is the whole point - picking one owner silently is what makes
    # contract attribution wrong on both sides of the event.
    log("\n[D] Ownership change: Alaka'ina Foundation -> Bering Straits (June 2026)")
    alakaina = next((r for r in nho_all
                     if r["proposed_id"] == "N-0007"), None)
    ev_rows = []
    if alakaina:
        subs = [s.strip() for s in alakaina["subsidiaries"].split("|") if s.strip()]
        for sub in subs:
            ev = {
                "event_id": "",        # set below, from THIS row's own facts
                "effective_date": "",
                "effective_month": "2026-06",
                "event_year": "2026",
                "acquirer_entity": "Bering Straits Native Corporation",
                "acquirer_tribe_id": "ANRC-BERSTR-00",
                "acquirer_class": "Alaska Native Regional Corporation",
                "target_entity": sub,
                "seller_entity": "Alaka'ina Foundation",
                "seller_class": "Native Hawaiian Organization",
                "direction": "acquisition",
                "ownership_change_type":
                    "NHO-owned -> ANC-owned. The nine for-profit firms changed "
                    "hands; the Alaka'ina Foundation itself remains an NHO.",
                "date_basis":
                    "MONTH ONLY - the source states 'June 2026' with no day. "
                    "No day is invented. Not usable for day-level attribution.",
                "date_usable_for_attribution": "0",
                "source_url": "http://beringalakaina.com/",
                "source_quote": alakaina["evidence_quote"],
                "retrieved_date": alakaina["retrieved_date"],
                "confidence": "A",
                "note": "Attribution of these firms' obligations must switch "
                        "from Alaka'ina Foundation to Bering Straits Native "
                        "Corporation at 2026-06. FPDS does NOT update "
                        "retroactively, so pre-event awards stay NHO-attributed.",
            }
            ev["event_id"] = surrogate_id("OWN-NHO", ev,
                                          NHO_OWNERSHIP_EVENT_KEY_COLUMNS)
            ev_rows.append(ev)
    write_csv(CLEAN / "nho_ownership_changes.csv", ev_rows,
              ["event_id", "effective_date", "effective_month", "event_year",
               "acquirer_entity", "acquirer_tribe_id", "acquirer_class",
               "target_entity", "seller_entity", "seller_class", "direction",
               "ownership_change_type", "date_basis",
               "date_usable_for_attribution", "source_url", "source_quote",
               "retrieved_date", "confidence", "note"])
    log("  NOTE: written to its own file, NOT merged into "
        "data/clean/ownership_events.csv,")
    log("        which is a derived output of code/31_build_dataset5_linked.py "
        "and must be")
    log("        rebuilt rather than hand-edited.")

    # ---- prove the named owners now resolve -------------------------------
    log("\n[E] Owners Elijah named that were absent from the spine:")
    spine2 = read_csv(SPINE)
    for probe in ["Ho'omaka Foundation", "NA 'OIWI KANE",
                  "NATIVE HAWAIIAN ORGANIZATION CHARITY",
                  "ISLAND EMPIRE COMMUNITY DEVELOPMENT", "THE MAKUA GROUP",
                  "ALAKA`I SERVICES GROUP INC.", "Hoilina Ranch LLC"]:
        tid, canon, how = _M33.resolve_entity(probe, spine2)
        log(f"  {probe:38s} -> {tid or 'STILL ABSENT':22s} ({how})")

    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "61_add_nho_intertribal.log").write_text(
        "\n".join(LOG_LINES), encoding="utf-8")


if __name__ == "__main__":
    main()
