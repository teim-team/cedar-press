#!/usr/bin/env python3
r"""
Cedar Press - 163: promote the verified NHO universe into the spine IN PLACE,
and carry the 8(a)-firm identifiers into the ledger through the ledger's own
path.

THE PROBLEM
-----------
Elijah, 2026-08-26: "there should be way more NHOs, I identified several."

He is right, and the work already exists. `data/clean/nho_register.csv` holds
**218** organisations; the spine holds **31**. The 185 rows that never landed
are the DOI Office of Native Hawaiian Relations NHO Notification List, parsed by
`code/05_parse_doi_nho_list.py` and registered by `code/36_build_nho_intertribal.py`,
and `code/61_add_nho_intertribal_to_spine.py` deliberately declined to add them:

    "The 185 DOI-roster rows - the DOI ONHR list is an NHPA *consultation*
     notification list, not a contracting registry. Those rows are a discovery
     pool at tier C. Putting them in the spine would make 185 unverified
     organisations roll-up targets."

WHY THAT DECISION IS REVERSED HERE, AND WHAT IS KEPT FROM IT
------------------------------------------------------------
61 was answering the wrong question. It asked "is this a CONTRACTING NHO under
13 C.F.R. 124.3?" - and for a roster row the answer is no. But the spine's
question is "does this Native entity exist, and what is it?", and for that the
DOI list is a first-party federal source. Verified against the PDF itself
(`data/raw/external/doi_nho_complete_list_2025-04.pdf`, 111 pages), every
directory entry carries a formal **"Originally Registered:"** date with the
Office of Native Hawaiian Relations - 12/19/2007 for the Office of Hawaiian
Affairs, 6/28/2022 for Native Hawaiian Community Development Corporation. That
is a registration with the federal office that administers the relationship,
not a name pattern and not a self-description.

61's actual fear - that the rows become roll-up targets - was a fear about
GRADE TRAVEL, not about the entities. It was correct at the time because the
spine had nowhere to put a grade: every row looked equally solid once it was a
row. This script fixes that instead of withholding the entities:

  * four columns are added to the spine - `evidence_tier`, `evidence_grade`,
    `verification_route`, `evidence_url` - and every NHO row carries them,
    including the 31 already there, whose grades are backfilled from the same
    register that produced them.
  * a DOI-roster row lands at `evidence_tier = C` and
    `evidence_grade = doi_roster_only`, INHERITED verbatim from
    `nho_register.csv`. This script assigns no tier to anything.
  * no DOI-roster row carries an identifier, so nothing can roll up through it.
    `n_uei_tierA`, `n_uei_tierB`, `n_cage`, `n_ein` are all written `0`.

**A SAM socio-economic flag is self-certification** (START_HERE), and 8(a) is
not evidence of NHO status either - `code/19_rebuild_nho_layer.py` proved that
on HALOA CONSTRUCTION LLC, 8(a)-certified and family-owned. Neither route is
used here to CREATE an NHO. Both appear only as an inherited grade on a row
whose NHO status was established elsewhere.

WHAT IS REFUSED, AND WHY
------------------------
1. **The 444 rows of `hawaii_nho_candidates.csv`** - a geographic net of Hawaii
   SAM registrants including "Backflow Testing Hawaii LLC". A Hawaiian-language
   token in a company name is not evidence of anything. None is promoted.
2. **`Office of Hawaiian Affairs - continued`** - a PAGE-CONTINUATION HEADER,
   not an organisation. Confirmed by reading PDF page 94: the line is followed
   by "Additional Contacts:" and nothing else. It is a defect in the roster,
   reported to review rather than silently dropped.
3. **Two natural persons on the DOI list** - `Keoni Kealoha Alvarez` (registered
   2008, summary begins "I am a des...") and `Brian Kaniela Nae'ole Naauao`.
   They are genuinely listed, and they are people. The spine has no class for an
   individual and inventing one here would be inventing a schema to hold a
   privacy decision nobody has made. Routed to review.
4. **`Ma'a 'Ohana c/o Lani Ma'a Lapilio`** - the organisation is `Ma'a 'Ohana`;
   the rest of the string is a private individual's name used as a postal
   care-of. Promoting the string verbatim publishes a person as an entity name.
   Routed to review for a human to approve the canonical form.
5. **Every decision already recorded in `nho_ito_spine_crosswalk.csv` and
   `review/nho_ito_refused_2026-08-06.csv`** stands untouched. N-0032
   (Ho'opale Foundation) and N-0033 (Kalaimoku Foundation) stay refused; the
   31 ADDED rows and 2 ALREADY_IN_SPINE rows are not re-litigated.

THE LEDGER, AND THE CONFLATION CHECK THAT COMES FIRST
------------------------------------------------------
`nho_verified_entities.csv` holds 36 8(a) firms. They are SUBSIDIARIES, not
NHOs, so none becomes a spine row. Their UEI and CAGE go to the ledger keyed to
the PARENT the ruling names, at the tier the source row already carries
(A, `elijah_ruling` - script 19: "Elijah ruled the parent. Ruling is the
verification.").

**The ledger has an invariant nothing in it states: measured 2026-08-26, of
20,473 distinct (type, identifier) keys, 86 carry more than one row and ZERO
carry two DISTINCT non-blank `tribe_id`.** One identifier means one entity. So
a write that binds an identifier already bound elsewhere is refused, not
appended - appending would break the invariant quietly and look like coverage.

Four disposition rules, applied per identifier:

  absent from the ledger              -> APPEND a new row
  present, tribe_id blank             -> UPDATE IN PLACE (the 124 pattern)
  present, a DIFFERENT tribe_id       -> REFUSE, report as a conflation
  present with a tier-X row           -> REFUSE. A negative ruling is permanent.

The third rule fires. Three Hawaii NHO firms' CAGE codes are already sitting on
lower-48 tribes via `need_v6`, the method `cedar_domain.METHOD_ACCURACY` records
at **6.5% accurate**:

    CAGE 9YWT7  CORNERSTONE BESTICA FEDERAL SERVICE (Ho'omaka, HI)
                -> CNSS-TURTLM-TR  Trenton Indian Service Area (ND)   tier B
    CAGE 8WD37  ISLAND EMPIRE TECHNOLOGY SYSTEMS (HI)
                -> TRBF-PRAIRI-00  Prairie Island (MN)                tier B
    CAGE 6SUD3  HOILINA RANCH LLC (Keaau, HI)
                -> TRBF-CHCKNR-00  Chicken Ranch (CA)                 tier B

They are tier B and never publish, so the defect is contained. It is REPORTED,
not corrected - same treatment `61` gave NHO-MANUKAI-00, and for the same
reason: fixing another pass's row is that pass's job, and a silent repoint is
how one entity becomes two.

WRITE DISCIPLINE
----------------
`01_build_entity_spine.py` rebuilds from a stale upstream and drops every
appended entity; `09_import_rulings.py` does the same to the ledger. Neither is
run, neither is imported for anything but grammar. Both files are backed up,
written `.part`, then renamed, exactly as `124_apply_rulings_in_place.py` does.
The resolver and the normaliser are imported from `33_apply_party_rulings.py` -
one resolver, project-wide, and only `exact`/`core`/`alias` matches are
accepted. `containment` is refused outright; it is the defect that put $13.4B
on other people's schools.

    py -3 code/163_promote_nho_universe_in_place.py --check   # write nothing
    py -3 code/163_promote_nho_universe_in_place.py           # apply

OBSERVED 2026-08-26, WORTH THE NEXT AGENT'S TIME
-------------------------------------------------
This script is idempotent - a second run promotes 0 and skips 181 as "prior
decision on file". It was run twice, and BETWEEN the two runs two of its
outputs reverted to their pre-run contents: `nho_ito_spine_crosswalk.csv` was
read back at 88 rows after being written at 269, and
`data/clean/codebook/05_entities.csv` came back at the post-run 82 rows after
being restored by hand to 80. Four other agents were live on this machine at
the time (`121_pull_subawards_api.py`, `167_link_nonprofit_family_via_ein_hub.py`,
and the 170/171 individual-Native pair). The effect on the crosswalk was
cosmetic but misleading: on the re-run the 179 rows resolved through the
"already in spine" branch - which was TRUE by then, because run one had put
them there - and were re-labelled `ALREADY_IN_SPINE` with a note saying they
were not minted here. They were. Corrected by hand and verified.

**The lesson: idempotence is not enough on a shared machine. Verify the file
you wrote by RE-READING it, in the same command, before believing the run
log.** Every count in this docstring and in the run report was confirmed that
way. Note also that script numbers 163 and 164 already existed
(`163_load_sam_contract_awards.py`, `164_link_facility_hub_sources.py`) when
these were written - the numeric prefix has not implied a unique step since
2026-08-07.

Reads   data/clean/nho_register.csv
        data/clean/nho_doi_notification_roster.csv
        data/clean/nho_verified_entities.csv
        data/clean/nho_ito_spine_crosswalk.csv
        data/raw/external/hawaii_nho_candidates.csv
        data/spine/cedar_entity_spine.csv
        data/clean/cedar_identifier_ledger_final.csv
        review/nho_ito_refused_2026-08-06.csv
Writes  data/spine/cedar_entity_spine.csv           (+ .bak_<date>_pre163)
        data/clean/cedar_identifier_ledger_final.csv(+ .bak_<date>_pre163)
        data/clean/nho_ito_spine_crosswalk.csv       (append only)
        data/clean/codebook/05_entities.csv          (FRAGMENT only, never master)
        review/nho_promotion_refused_<date>.csv
        review/nho_ledger_id_conflations_<date>.csv
        logs/163_promote_nho_universe.log
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
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
LEDGER = CLEAN / "cedar_identifier_ledger_final.csv"
CROSSWALK = CLEAN / "nho_ito_spine_crosswalk.csv"
FRAGMENT = CLEAN / "codebook" / "05_entities.csv"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

CLASS_NHO = "Native Hawaiian Organization"
DOI_PDF_URL = ("https://www.doi.gov/sites/default/files/documents/2025-04/"
               "nhol-complete-list-final-web.pdf")

# One normaliser and one resolver, imported not copied (standing rule 8).
_spec = importlib.util.spec_from_file_location(
    "m33", CEDAR / "code" / "33_apply_party_rulings.py")
_M33 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_M33)
norm, core, resolve_entity = _M33.norm, _M33.core, _M33.resolve_entity

_spec_d = importlib.util.spec_from_file_location(
    "cedar_domain", CEDAR / "code" / "cedar_domain.py")
_DOMAIN = importlib.util.module_from_spec(_spec_d)
_spec_d.loader.exec_module(_DOMAIN)
RULED_METHODS = _DOMAIN.RULED_METHODS
METHOD_ACCURACY = _DOMAIN.METHOD_ACCURACY

# Only these say the resolver found the entity by identity. `containment` is
# the defect that booked $13.4B onto schools and is never accepted here.
ACCEPTED_RESOLUTIONS = {"exact", "core", "alias"}

STOP = {"the", "inc", "incorporated", "corporation", "corp", "company", "llc",
        "ltd", "limited", "native", "of", "and", "association", "foundation",
        "national", "american", "indian", "tribal", "tribes", "inter",
        "intertribal", "council"}

# ---------------------------------------------------------------------------
# REFUSALS specific to this pass, keyed on the register's `proposed_id`.
#
# Keyed on the ID and NOT on the name, because `norm()` folds the Hawaiian okina
# (U+2018) but leaves an ASCII apostrophe as a space - so `Nae'ole` and
# `Nae‘ole` normalise differently and a name-keyed refusal silently fails
# open. That is the same class of bug as the `\b`-vs-underscore matcher that
# dropped all 48 Indian Affairs FOIA logs while printing a zero.
#
# Each refusal was confirmed against the source PDF, not guessed.
# ---------------------------------------------------------------------------
REFUSE_DOI = {
    "N-0170": (
        "PARSE ARTEFACT, not an organisation. This is the running header on "
        "directory page 87 (PDF page 94) where the Office of Hawaiian Affairs "
        "entry spills over; the line is followed by 'Additional Contacts:' and "
        "nothing else. The organisation itself is already promoted from the "
        "'Office of Hawaiian Affairs' row. Reported so the roster defect in "
        "code/05_parse_doi_nho_list.py is visible rather than silently dropped."),
    "N-0112": (
        "A NATURAL PERSON. Genuinely listed on the DOI roster (directory p.52, "
        "Originally Registered 2008, summary begins 'I am a des...'), and a "
        "person is not an organisation. The spine has no entity_class for an "
        "individual Native person and this script will not invent one to hold "
        "a privacy decision nobody has made. Needs a ruling on both the class "
        "and on naming a private individual in a shipping dataset."),
    "N-0048": (
        "A NATURAL PERSON on the DOI roster (directory p.14). Same reasoning as "
        "Keoni Kealoha Alvarez: no entity_class exists for an individual, and "
        "creating a spine row for a named private individual is a privacy "
        "decision, not a data-completeness one."),
    "N-0145": (
        "The ORGANISATION is 'Ma'a 'Ohana'. The rest of the roster string is a "
        "private individual's name used as a postal care-of (PDF page 69: "
        "'Contact: Lani Ma'a Lapilio ... c/o Aukahi, P.O. Box 6087'). Promoting "
        "the string verbatim would publish a person's name as an entity name. "
        "A human must approve the canonical form before this is added."),
}

# ---------------------------------------------------------------------------
# Grade vocabulary. Every value is INHERITED from nho_register.csv - this map
# only records what each inherited value means and what it does NOT prove.
# ---------------------------------------------------------------------------
GRADE_MEANING = {
    "doi_roster_only":
        "Registered with the DOI Office of Native Hawaiian Relations and "
        "listed on its NHO Notification List (each directory entry carries an "
        "'Originally Registered' date). Establishes NHO status for NHPA "
        "consultation under 54 U.S.C. 300309. Does NOT establish 13 C.F.R. "
        "124.3 NHO status for SBA 8(a) contracting.",
    "sba_8a_entity_owned":
        "Named as the NHO parent of an SBA 8(a) entity-owned firm, "
        "corroborated by the gated NHOA member directory. 8(a) alone is NOT "
        "the basis - 8(a) admits individually owned firms too.",
    "self_stated":
        "The organisation's own words, quoted verbatim with its URL.",
    "elijah_ruling":
        "Human ruling by the project owner. Permanent; only a new ruling "
        "reverses it.",
}


def log_open():
    return []


LOG_LINES = []


def log(msg=""):
    print(msg)
    LOG_LINES.append(msg)


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


def write_atomic(path, rows, fields, backup_tag):
    """Back up, write `.part`, rename. An interruption must not look like a
    completion (START_HERE, standing rules)."""
    # REGENERATE GUARD (ADR-017, 2026-09-02): derive the header, do not declare it.
    fields = _carry_live_columns(path, fields)
    path = Path(path)
    if path.exists():
        bak = Path(str(path) + f".bak_{TODAY}_{backup_tag}")
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


def write_review(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = Path(str(path) + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    part.replace(path)
    log(f"  wrote {path.relative_to(CEDAR)}  ({len(rows):,} rows)")


def token(name, taken):
    """Deterministic 6-character id token in the spine's existing style.
    Same shape as scripts 52/61/75 so the mints stay compatible."""
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


# ===========================================================================
def main():
    check = "--check" in sys.argv
    log("=== Cedar Press 163: promote the NHO universe IN PLACE ===")
    log(f"    mode: {'--check (writes nothing)' if check else 'APPLY'}\n")

    spine = load(SPINE)
    ledger = load(LEDGER)
    register = load(CLEAN / "nho_register.csv")
    roster = load(CLEAN / "nho_doi_notification_roster.csv")
    verified = load(CLEAN / "nho_verified_entities.csv")
    crosswalk = load(CROSSWALK)
    candidates = load(CEDAR / "data/raw/external/hawaii_nho_candidates.csv")
    prior_refused = load(REVIEW / "nho_ito_refused_2026-08-06.csv")
    prior_conflations = load(REVIEW / "nho_ledger_id_conflations_2026-08-06.csv")

    spine_fields = list(spine[0].keys())
    ledger_fields = list(ledger[0].keys())

    log("[0] RECONCILIATION of the five NHO files")
    log(f"  nho_register.csv                : {len(register):>5}")
    log(f"  nho_doi_notification_roster.csv : {len(roster):>5}")
    log(f"  hawaii_nho_candidates.csv       : {len(candidates):>5}  "
        f"(geographic net - NOT evidence)")
    log(f"  nho_verified_entities.csv       : {len(verified):>5}  "
        f"(8(a) FIRMS, i.e. subsidiaries)")
    log(f"  nho_ito_spine_crosswalk.csv     : {len(crosswalk):>5}")
    log(f"  spine, all entities             : {len(spine):>5}")

    spine_nho_before = [r for r in spine if r["entity_class"] == CLASS_NHO]
    log(f"  spine, entity_class = NHO       : {len(spine_nho_before):>5}")

    contracting = [r for r in register if r["nho_class"] == "contracting_nho"]
    doi_rows = [r for r in register if r["nho_class"] != "contracting_nho"]
    log(f"\n  register splits into {len(contracting)} contracting_nho + "
        f"{len(doi_rows)} doi_notification_list")

    # The roster's 190 minus the 5 that are ALSO contracting NHOs = the 185
    # register rows. Verified rather than assumed.
    reg_doi_norms = {norm(r["organization_name"]) for r in doi_rows}
    dedup = [r for r in roster if norm(r["organization_name"]) not in reg_doi_norms]
    log(f"  roster rows already carried as contracting NHOs: {len(dedup)}")
    for r in dedup:
        log(f"      {r['nho_id']}  {r['organization_name']}")
    log("  -> the DOI roster CORROBORATES those five independently of NHOA. "
        "Recorded as a fact; no tier is changed by it.")

    # Roster completeness: the ToC parse covers every directory page.
    pages = {int(r["doi_list_page"]) for r in roster if r["doi_list_page"].isdigit()}
    gaps = sorted(set(range(1, max(pages) + 1)) - pages)
    log(f"  DOI directory pages covered by the parse: 1..{max(pages)}, "
        f"gaps: {gaps if gaps else 'none'}")

    prior_ids = {r["proposed_id"] for r in crosswalk}
    prior_refused_ids = {r["proposed_id"] for r in prior_refused}
    log(f"\n  existing crosswalk decisions honoured : {len(prior_ids)} "
        f"({Counter(r['status'] for r in crosswalk)})")
    log(f"  existing refusals honoured            : "
        f"{sorted(prior_refused_ids)}")

    # ---- lookups on the existing spine ------------------------------------
    have_norm, have_core = {}, {}
    for r in spine:
        have_norm.setdefault(norm(r["canonical_name"]), r)
        c = core(r["canonical_name"])
        if c:
            have_core.setdefault(c, r)
        for a in (r.get("aliases") or "").split("|"):
            if a.strip():
                have_norm.setdefault(norm(a), r)
    have_ids = {r["tribe_id"] for r in spine}
    have_ceid = {r.get("cedar_entity_id", "") for r in spine
                 if r.get("cedar_entity_id")}
    taken = {r["tribe_id"].split("-")[1] for r in spine if "-" in r["tribe_id"]}

    # =======================================================================
    # PART A - the spine
    # =======================================================================
    log("\n[A] Promoting DOI-registered NHOs into the spine")

    NEW_COLS = ["evidence_tier", "evidence_grade", "verification_route",
                "evidence_url"]
    for c in NEW_COLS:
        if c not in spine_fields:
            spine_fields.append(c)
    log(f"  spine columns {len(spine_fields) - len(NEW_COLS)} -> "
        f"{len(spine_fields)}: added {NEW_COLS}")
    log("  A tier is INHERITED. Every value in those four columns is copied "
        "verbatim")
    log("  from nho_register.csv; this script computes none of them.")

    added, refused, new_crosswalk = [], [], []
    skipped = Counter()

    for r in doi_rows:
        name = r["organization_name"].strip()
        n = norm(name)
        pid = r["proposed_id"]

        if pid in prior_ids or pid in prior_refused_ids:
            skipped["prior decision on file - untouched"] += 1
            continue

        if pid in REFUSE_DOI:
            refused.append({
                "proposed_id": pid, "organization_name": name,
                "entity_class_proposed": CLASS_NHO,
                "source": "nho_register.csv (DOI ONHR notification list)",
                "reason": REFUSE_DOI[pid],
                "evidence_url": r["evidence_url"], "refused_date": TODAY,
                "refused_by": "code/163_promote_nho_universe_in_place.py",
            })
            skipped["refused on evidence"] += 1
            continue

        # Prime directive gate, same as 61: a retrieved URL and a verbatim
        # quote, or it does not enter.
        if not (r["evidence_url"] or "").strip():
            refused.append({
                "proposed_id": pid, "organization_name": name,
                "entity_class_proposed": CLASS_NHO,
                "source": "nho_register.csv",
                "reason": "No retrieved evidence_url. Prime directive: zero "
                          "fabrication.",
                "evidence_url": "", "refused_date": TODAY,
                "refused_by": "code/163_promote_nho_universe_in_place.py",
            })
            skipped["no evidence url"] += 1
            continue
        if not (r["evidence_quote"] or "").strip():
            refused.append({
                "proposed_id": pid, "organization_name": name,
                "entity_class_proposed": CLASS_NHO,
                "source": "nho_register.csv",
                "reason": "No verbatim evidence_quote. An NHO class claim "
                          "requires the source's own words.",
                "evidence_url": r["evidence_url"], "refused_date": TODAY,
                "refused_by": "code/163_promote_nho_universe_in_place.py",
            })
            skipped["no evidence quote"] += 1
            continue

        c = core(name)
        hit = have_norm.get(n) or (have_core.get(c) if c else None)
        if hit:
            new_crosswalk.append({
                "proposed_id": pid, "organization_name": name,
                "layer": CLASS_NHO, "tribe_id": hit["tribe_id"],
                "spine_canonical_name": hit["canonical_name"],
                "spine_entity_class": hit["entity_class"],
                "status": "ALREADY_IN_SPINE",
                "note": "Matched an existing spine entity; not re-minted. The "
                        "existing row is authoritative. DOI-roster presence is "
                        "recorded here as independent corroboration only.",
            })
            skipped["already in spine"] += 1
            continue
        if pid in have_ceid:
            skipped["already in spine by cedar_entity_id"] += 1
            continue

        tok = token(name, taken)
        taken.add(tok)
        tid = f"NHO-{tok}-00"
        if tid in have_ids:
            raise SystemExit(f"ABORT: {tid} already exists. Refusing to "
                             f"overwrite an existing spine entity.")

        aliases = [a.strip() for a in re.split(r"[;|]", r["aliases"] or "")
                   if a.strip()]
        if name not in aliases:
            aliases.insert(0, name)

        row = {f: "" for f in spine_fields}
        row.update({
            "tribe_id": tid,
            "canonical_name": name,
            "entity_class": CLASS_NHO,
            "state": (r.get("state") or "HI").strip() or "HI",
            "city": (r.get("city") or "").strip(),
            "cedar_entity_id": pid,
            "aliases": "|".join(aliases),
            "ultimate_parent_entity_id": tid,
            "ultimate_parent_entity_name": name,
            # No identifiers. A DOI-roster row can never carry a dollar.
            "n_uei_tierA": "0", "n_uei_tierB": "0", "n_cage": "0",
            "n_ein": "1" if (r.get("ein") or "").strip() else "0",
            # Grade travels with the row. Inherited, never assigned.
            "evidence_tier": r["confidence_tier"],
            "evidence_grade": r["nho_status_basis"],
            "verification_route": r["verification_route"],
            "evidence_url": r["evidence_url"],
            "entity_source_url": r["evidence_url"],
            "entity_source_quote": r["evidence_quote"],
            "reconciliation_status": "nho_doi_registered_not_contracting_verified",
            "reconciliation_note": GRADE_MEANING.get(
                r["nho_status_basis"], r["nho_status_basis"]),
            "built_by_script": "code/163_promote_nho_universe_in_place.py",
        })
        added.append(row)
        have_ids.add(tid)
        have_norm[n] = row
        if c:
            have_core.setdefault(c, row)
        new_crosswalk.append({
            "proposed_id": pid, "organization_name": name,
            "layer": CLASS_NHO, "tribe_id": tid,
            "spine_canonical_name": name, "spine_entity_class": CLASS_NHO,
            "status": "ADDED",
            "note": f"tier {r['confidence_tier']}; basis: "
                    f"{r['nho_status_basis']}; route: {r['verification_route']}; "
                    f"evidence: {r['evidence_url']}",
        })

    log(f"  promoted : {len(added)}")
    for k, v in skipped.most_common():
        log(f"  skipped  : {v:>3}  ({k})")
    log(f"  refused  : {len(refused)}")
    for x in refused:
        log(f"      {x['proposed_id']}  {x['organization_name']}")

    # FAIL CLOSED. A refusal that matches nothing is a refusal that did not
    # happen, and it looks identical to one that did. This is the check that
    # would have caught the okina/apostrophe mismatch on the first run.
    fired = {x["proposed_id"] for x in refused}
    missed = set(REFUSE_DOI) - fired
    if missed:
        raise SystemExit(
            f"ABORT: {len(missed)} declared refusals matched no register row: "
            f"{sorted(missed)}. A refusal that does not fire is worse than no "
            f"refusal - it reads as a decision that was applied.")

    # ---- SHORT-NAME COLLISION RISK ----------------------------------------
    # AGENTS.md, 2026-08-07: 161 spine entities carry a 1-2 word canonical name
    # and "each is a collision waiting for the right input string". Adding rows
    # adds collisions, so the ones this pass creates are counted and named
    # rather than discovered later as a resolver bug that is not one.
    short_risk = []
    for row in added:
        toks = [t for t in norm(row["canonical_name"]).split() if t not in STOP]
        if len(toks) <= 2:
            short_risk.append({
                "tribe_id": row["tribe_id"],
                "canonical_name": row["canonical_name"],
                "entity_class": CLASS_NHO,
                "distinctive_tokens": " ".join(toks),
                "n_tokens": len(toks),
                "risk": "Short canonical name added to the spine. resolve_entity's "
                        "containment path can match this from an unrelated record "
                        "string. It carries no identifiers and no ownership edge, "
                        "so it cannot receive a dollar today - but it can receive "
                        "a NAME match.",
                "flagged_date": TODAY,
            })
    log(f"\n  short-name collision risk added by this pass: {len(short_risk)} "
        f"of {len(added)}")
    for s in short_risk[:12]:
        log(f"      {s['tribe_id']:18s} {s['canonical_name']}")
    if len(short_risk) > 12:
        log(f"      ... {len(short_risk) - 12} more, full list in review/")

    # ---- backfill the grade onto the 31 rows already in the spine ---------
    reg_by_pid = {r["proposed_id"]: r for r in register}
    reg_by_norm = {norm(r["organization_name"]): r for r in register}
    backfilled = 0
    for row in spine:
        if row["entity_class"] != CLASS_NHO:
            continue
        src = reg_by_pid.get(row.get("cedar_entity_id", "")) \
            or reg_by_norm.get(norm(row["canonical_name"]))
        if not src:
            continue
        # Only ever FILL an empty column. Nothing existing is overwritten.
        wrote = False
        for col, val in (("evidence_tier", src["confidence_tier"]),
                         ("evidence_grade", src["nho_status_basis"]),
                         ("verification_route", src["verification_route"]),
                         ("evidence_url", src["evidence_url"]),
                         ("entity_source_url", src["evidence_url"]),
                         ("entity_source_quote", src["evidence_quote"])):
            if not (row.get(col) or "").strip() and (val or "").strip():
                row[col] = val
                wrote = True
        if wrote:
            backfilled += 1
    log(f"\n  grade backfilled onto pre-existing NHO spine rows: {backfilled} "
        f"of {len(spine_nho_before)}")
    log("  (empty columns FILLED only; no existing spine value is overwritten)")

    # ---- corroboration: which spine NHOs the DOI list independently lists --
    roster_norms = {norm(r["organization_name"]) for r in roster}
    corrob = [r for r in spine_nho_before
              if norm(r["canonical_name"]) in roster_norms
              or core(r["canonical_name"]) in
              {core(x["organization_name"]) for x in roster}]
    log(f"  of the {len(spine_nho_before)} NHOs already in the spine, "
        f"{len(corrob)} are independently on the DOI list:")
    for r in corrob:
        log(f"      {r['tribe_id']}  {r['canonical_name']}")
    log("  Recorded as corroboration. NO tier is raised on it - a second "
        "source is")
    log("  a fact about the evidence, and promotion is a ruling.")

    # =======================================================================
    # PART B - the ledger
    # =======================================================================
    log("\n[B] Carrying 8(a)-firm identifiers into the ledger")
    log(f"  nho_verified_entities.csv tiers: "
        f"{dict(Counter(r['confidence_tier'] for r in verified))}")
    log("  These are FIRMS (subsidiaries). None becomes a spine row; their")
    log("  identifiers key to the PARENT the ruling names.")

    # Re-read the spine view INCLUDING the rows just added, so a parent added
    # in this same run resolves.
    spine_now = spine + added

    # Index the ledger by (type, identifier).
    lidx = {}
    for r in ledger:
        lidx.setdefault((r["identifier_type"], (r["identifier"] or "").upper()),
                        []).append(r)

    lstats = Counter()
    ledger_new, conflations, unresolved_parents = [], [], []
    updated_rows = 0

    for f in verified:
        tier = (f["confidence_tier"] or "").strip()
        parent = (f["parent_native_entity"] or "").strip()
        firm = (f["firm_name"] or "").strip()

        if tier == "X":
            lstats["source row is tier X (ruled NOT NHO-owned) - skipped"] += 1
            continue
        if tier != "A" or not parent:
            unresolved_parents.append({
                "firm_name": firm, "uei": f["uei"], "cage_code": f["cage_code"],
                "city": f.get("city", ""), "source_tier": tier,
                "reason": "No ruled parent on the source row. 8(a) alone is "
                          "not evidence of NHO ownership (code/19).",
            })
            lstats["source row not tier A - no ledger write"] += 1
            continue

        tid, cname, how = resolve_entity(parent, spine_now)
        if not tid or how not in ACCEPTED_RESOLUTIONS:
            unresolved_parents.append({
                "firm_name": firm, "uei": f["uei"], "cage_code": f["cage_code"],
                "city": f.get("city", ""), "source_tier": tier,
                "reason": f"Ruled parent '{parent}' does not resolve to a spine "
                          f"entity by identity (resolver said '{how}'). This is "
                          f"a SPINE GAP, reported rather than forced - the "
                          f"parent is one of the organisations "
                          f"review/nho_ito_refused_2026-08-06.csv and review "
                          f"items NHOIT-001..004 already hold open.",
            })
            lstats["ruled parent not in spine - REFUSED, reported"] += 1
            continue

        spine_row = next((r for r in spine_now if r["tribe_id"] == tid), None)
        ecls = spine_row["entity_class"] if spine_row else ""

        for idtype, value in (("UEI", (f["uei"] or "").strip().upper()),
                              ("CAGE", (f["cage_code"] or "").strip().upper())):
            if not value:
                lstats[f"{idtype} absent on source row"] += 1
                continue
            existing = lidx.get((idtype, value), [])

            # RULE: a negative ruling is permanent and never resurfaces.
            if any(r.get("confidence_tier") == "X" for r in existing):
                conflations.append({
                    "identifier_type": idtype, "identifier": value,
                    "firm_name": firm, "proposed_tribe_id": tid,
                    "proposed_canonical_name": cname,
                    "existing_tribe_id": "|".join(
                        sorted({r["tribe_id"] for r in existing})),
                    "existing_tier": "X",
                    "existing_method": "|".join(
                        sorted({r["attribution_method"] for r in existing})),
                    "problem": "The ledger already carries a tier-X row on this "
                               "identifier. X is a negative ruling and never "
                               "resurfaces (cedar_domain.Tier.X).",
                    "recommended_action": "A new ruling is the only thing that "
                                          "reverses an X. Not written.",
                    "flagged_date": TODAY,
                })
                lstats[f"{idtype} REFUSED - tier X on file"] += 1
                continue

            bound = {r["tribe_id"] for r in existing if (r["tribe_id"] or "").strip()}
            if bound and bound != {tid}:
                conflations.append({
                    "identifier_type": idtype, "identifier": value,
                    "firm_name": firm, "proposed_tribe_id": tid,
                    "proposed_canonical_name": cname,
                    "existing_tribe_id": "|".join(sorted(bound)),
                    "existing_tier": "|".join(sorted(
                        {r["confidence_tier"] for r in existing})),
                    "existing_method": "|".join(sorted(
                        {r["attribution_method"] for r in existing})),
                    "problem": "ID CONFLATION. This identifier is already bound "
                               "to a DIFFERENT entity. Measured 2026-08-26, "
                               "zero of the ledger's 20,473 identifier keys "
                               "carry two distinct non-blank tribe_id values; "
                               "appending here would break that invariant "
                               "silently.",
                    "recommended_action": "Read the existing row's "
                                          "attribution_method first. Where it "
                                          "is need_v6 (6.5% accurate, "
                                          "cedar_domain.METHOD_ACCURACY) the "
                                          "existing binding is the suspect one, "
                                          "but correcting another pass's row is "
                                          "that pass's job. Nothing written.",
                    "flagged_date": TODAY,
                })
                lstats[f"{idtype} REFUSED - already bound elsewhere"] += 1
                continue

            if bound == {tid}:
                lstats[f"{idtype} already correct - idempotent skip"] += 1
                continue

            rationale = (f"{f['verification_basis']} Firm: {firm}. "
                         f"Parent resolved to {cname} ({tid}) by '{how}'. "
                         f"Written by code/163 on {TODAY}.")

            if existing:
                # UPDATE IN PLACE - the 124 pattern. No row added, no row
                # removed; only the binding columns change.
                for r in existing:
                    r["tribe_id"] = tid
                    r["canonical_name"] = cname
                    r["entity_class"] = ecls
                    r["attribution_method"] = "elijah_ruling"
                    r["confidence_tier"] = "A"
                    r["is_authority"] = "YES"
                    r["tier_rationale"] = rationale
                    if not (r.get("legal_business_name") or "").strip():
                        r["legal_business_name"] = firm
                    r["evidence_source_file"] = f["source_file"]
                    updated_rows += 1
                lstats[f"{idtype} UPDATED IN PLACE (was unbound)"] += 1
            else:
                row = {k: "" for k in ledger_fields}
                row.update({
                    "identifier_type": idtype,
                    "identifier": value,
                    "tribe_id": tid,
                    "canonical_name": cname,
                    "legal_business_name": firm,
                    "entity_class": ecls,
                    "attribution_method": "elijah_ruling",
                    "confidence_tier": "A",
                    "tier_rationale": rationale,
                    "is_authority": "YES",
                    "verified_date": f.get("rebuilt_date", TODAY),
                    "state": (f.get("state") or "").strip(),
                    "source_file": "nho_verified_entities.csv",
                    "evidence_source_file": f["source_file"],
                    "evidence_url_integrity":
                        "No URL. The evidence is the owner's ruling on the "
                        "firm's UEI, recorded in review/rulings_inbox_*.csv and "
                        "applied by code/19_rebuild_nho_layer.py; there is no "
                        "retrievable page that states the ownership.",
                })
                ledger_new.append(row)
                lidx.setdefault((idtype, value), []).append(row)
                lstats[f"{idtype} APPENDED"] += 1

    for k, v in lstats.most_common():
        log(f"  {k:52s} {v:>4}")
    log(f"\n  ledger rows to append : {len(ledger_new)}")
    log(f"  ledger rows updated in place : {updated_rows}")
    log(f"  conflations refused   : {len(conflations)}")
    for c in conflations:
        log(f"      {c['identifier_type']} {c['identifier']}  {c['firm_name'][:34]:36s}"
            f" proposed {c['proposed_tribe_id']:18s} vs existing "
            f"{c['existing_tribe_id'] or '(tier X)'} [{c['existing_method']}]")

    # ---- WIDER CONFLATION AUDIT -------------------------------------------
    # The two refusals above are only the conflations this pass tried to write
    # over. The same defect exists on identifiers this pass never touches, and
    # it is invisible unless somebody looks. Every Hawaii SAM registrant whose
    # identifier is bound in the ledger to an entity OUTSIDE Hawaii is a
    # candidate conflation - the geographic mismatch is the signal, not proof.
    log("\n[B2] Wider conflation audit over hawaii_nho_candidates.csv")
    hi_ids = {}
    for r in candidates:
        for idtype, v in (("UEI", (r.get("uei") or "").strip().upper()),
                          ("CAGE", (r.get("cage_code") or "").strip().upper())):
            if v:
                hi_ids[(idtype, v)] = r
    spine_state = {r["tribe_id"]: (r.get("state") or "").strip().upper()
                   for r in spine_now}
    spine_name = {r["tribe_id"]: r["canonical_name"] for r in spine_now}
    wider = []
    for key, hrow in hi_ids.items():
        for lr in lidx.get(key, []):
            tid = (lr.get("tribe_id") or "").strip()
            if not tid:
                continue
            st = spine_state.get(tid, "")
            method = (lr.get("attribution_method") or "").strip()
            # A RULED row is a human decision, not a conflation. Bristol Bay
            # and Ahtna really do own Hawaii-registered subsidiaries. Only
            # algorithmic bindings are suspects.
            if method in RULED_METHODS:
                continue
            if st and st != "HI":
                wider.append({
                    "identifier_type": key[0], "identifier": key[1],
                    "firm_name": (hrow.get("name_clean") or "").strip(),
                    "proposed_tribe_id": "",
                    "proposed_canonical_name": "",
                    "existing_tribe_id": tid,
                    "existing_tier": lr.get("confidence_tier", ""),
                    "existing_method": lr.get("attribution_method", ""),
                    "problem":
                        f"A Hawaii SAM registrant ({hrow.get('City','')}, HI) is "
                        f"bound in the ledger to {spine_name.get(tid, tid)} in "
                        f"{st}. Geographic mismatch, not proof - but every one "
                        f"of these arrived by an algorithmic method, and "
                        f"need_v6 is 6.5% accurate.",
                    "recommended_action":
                        "Check the firm's ownership before this row leaves its "
                        "current tier. Nothing was written or repointed by "
                        "code/163.",
                    "flagged_date": TODAY,
                })
    log(f"  Hawaii-registrant identifiers bound to a non-HI entity: {len(wider)}")
    for w in sorted(wider, key=lambda x: x["existing_tier"])[:20]:
        log(f"      {w['identifier_type']} {w['identifier']}  "
            f"{w['firm_name'][:32]:34s} -> {w['existing_tribe_id']:18s} "
            f"tier {w['existing_tier']} [{w['existing_method']}]")
    conflations.extend(wider)

    # Prior conflation flags stay on the register, restated so they do not age
    # out of view.
    for c in prior_conflations:
        conflations.append({
            "identifier_type": "SPINE_ID", "identifier": c["tribe_id"],
            "firm_name": "", "proposed_tribe_id": "", "proposed_canonical_name": "",
            "existing_tribe_id": c["tribe_id"], "existing_tier": "C",
            "existing_method": "need_v6",
            "problem": c["problem"],
            "recommended_action": c["recommended_action"],
            "flagged_date": c["flagged_date"] + " (restated by 163 " + TODAY + ")",
        })

    # ---- guard the ledger invariant BEFORE writing -------------------------
    log("\n[C] Ledger invariant check (one identifier, one entity)")
    check_idx = {}
    for r in ledger + ledger_new:
        check_idx.setdefault(
            (r["identifier_type"], (r["identifier"] or "").upper()),
            set()).add((r["tribe_id"] or "").strip())
    broken = {k: v for k, v in check_idx.items()
              if len({x for x in v if x}) > 1}
    log(f"  identifier keys bound to >1 entity after this pass: {len(broken)}")
    if broken:
        for k, v in list(broken.items())[:10]:
            log(f"      {k} -> {sorted(v)}")
        log("\n  *** INVARIANT WOULD BREAK - refusing to write the ledger. ***")
        return

    tierA_ruled_before = sum(
        1 for r in ledger if r.get("confidence_tier") == "A"
        and (r.get("attribution_method") or "").strip()
        in {"hand", "bgov_manual", "elijah_ruling_redirect", "elijah_ruling",
            "ruling", "web_verified"})
    tierA_ruled_after = sum(
        1 for r in (ledger + ledger_new) if r.get("confidence_tier") == "A"
        and (r.get("attribution_method") or "").strip()
        in {"hand", "bgov_manual", "elijah_ruling_redirect", "elijah_ruling",
            "ruling", "web_verified"})
    log(f"  tier_A_ruled : {tierA_ruled_before:,} -> {tierA_ruled_after:,} "
        f"({tierA_ruled_after - tierA_ruled_before:+,})")
    if tierA_ruled_after < tierA_ruled_before:
        log("\n  *** tier_A_ruled FELL - refusing to write. ***")
        return

    # =======================================================================
    # SUMMARY / WRITE
    # =======================================================================
    log("\n[D] Result")
    grade_dist = Counter()
    for r in spine + added:
        if r.get("entity_class") == CLASS_NHO:
            grade_dist[(r.get("evidence_tier", "") or "?",
                        r.get("evidence_grade", "") or "?")] += 1
    log(f"  spine NHOs : {len(spine_nho_before)} -> "
        f"{len(spine_nho_before) + len(added)}")
    log("  evidence grade distribution (tier, grade):")
    for (t, g), n in sorted(grade_dist.items()):
        log(f"      tier {t}  {g:34s} {n:>4}")

    if check:
        log("\n  --check: nothing written.")
        LOGS.mkdir(parents=True, exist_ok=True)
        (LOGS / "163_promote_nho_universe.check.log").write_text(
            "\n".join(LOG_LINES), encoding="utf-8")
        return

    log("\n[E] Writing (backup, .part, rename)")
    write_atomic(SPINE, spine + added, spine_fields, "pre163")
    write_atomic(LEDGER, ledger + ledger_new, ledger_fields, "pre163")
    write_atomic(CROSSWALK, crosswalk + new_crosswalk,
                 ["proposed_id", "organization_name", "layer", "tribe_id",
                  "spine_canonical_name", "spine_entity_class", "status",
                  "note"], "pre163")

    write_review(REVIEW / f"nho_promotion_refused_{TODAY}.csv", refused,
                 ["proposed_id", "organization_name", "entity_class_proposed",
                  "source", "reason", "evidence_url", "refused_date",
                  "refused_by"])
    write_review(REVIEW / f"nho_ledger_id_conflations_{TODAY}.csv", conflations,
                 ["identifier_type", "identifier", "firm_name",
                  "proposed_tribe_id", "proposed_canonical_name",
                  "existing_tribe_id", "existing_tier", "existing_method",
                  "problem", "recommended_action", "flagged_date"])
    if short_risk:
        write_review(REVIEW / f"nho_short_name_collision_risk_{TODAY}.csv",
                     short_risk,
                     ["tribe_id", "canonical_name", "entity_class",
                      "distinctive_tokens", "n_tokens", "risk", "flagged_date"])
    if unresolved_parents:
        write_review(REVIEW / f"nho_firm_parent_spine_gap_{TODAY}.csv",
                     unresolved_parents,
                     ["firm_name", "uei", "cage_code", "city", "source_tier",
                      "reason"])

    # ---- codebook FRAGMENT only. Never codebook_master.csv. ---------------
    log("\n[F] Codebook fragment (05_entities only; master untouched)")
    # The 05_entities fragment pools SIX source files (script 41, DATASETS map):
    # the spine, intertribal_orgs, nho_register, entity_hierarchy,
    # entity_aliases, entity_relationships. Its `n_rows` is the POOLED row count
    # - 10,772 was exactly the pooled total before this pass - but its
    # `pct_filled` is measured against the file that OWNS each variable, not
    # against the pool. Measured 2026-08-26: applying a pooled denominator to
    # every variable moves 76 of 80 (tribe_id 100.0 -> 22.3). So only the
    # variables this pass is responsible for are written, exactly as script 156
    # does for the deals fragment. Refreshing the other 80 is script 41's job.
    #
    # `evidence_url` and `verification_route` ALREADY exist in this fragment -
    # they are nho_register.csv columns, 100% filled there, and the spine's new
    # columns of the same name carry the same fact. Their rows are left
    # byte-identical rather than re-pointed at a second owning file.
    POOLED_FILES = [SPINE, CLEAN / "intertribal_orgs.csv",
                    CLEAN / "nho_register.csv", CLEAN / "entity_hierarchy.csv",
                    CLEAN / "entity_aliases.csv",
                    CLEAN / "entity_relationships.csv"]
    frag = load(FRAGMENT)
    if frag:
        frag_fields = list(frag[0].keys())
        have_var = {r["variable"] for r in frag}
        n_spine = len(spine) + len(added)
        pooled = sum(len(load(p)) for p in POOLED_FILES)
        log(f"  pooled n_rows across the fragment's 6 source files: {pooled:,}")
        for col in NEW_COLS:
            if col in have_var:
                log(f"  {col:20s} already documented (nho_register.csv column, "
                    f"same fact) - row left byte-identical")
                continue
            filled = sum(1 for r in spine + added if (r.get(col) or "").strip())
            desc = {
                "evidence_tier":
                    "Confidence tier of the evidence for this entity's CLASS, "
                    "inherited verbatim from the register that sourced the row "
                    "(nho_register.csv). Never assigned by a consuming script. "
                    "Distinct from a ledger identifier tier.",
                "evidence_grade":
                    "What kind of evidence establishes the entity's class. One "
                    "of: `doi_roster_only` (registered on the DOI Office of "
                    "Native Hawaiian Relations NHO Notification List - NHPA "
                    "consultation status under 54 U.S.C. 300309, NOT 13 C.F.R. "
                    "124.3 contracting status), `sba_8a_entity_owned`, "
                    "`self_stated`, `elijah_ruling`.",
                "verification_route":
                    "The chain of sources that established the class claim, "
                    "verbatim from the register - e.g. "
                    "`doi_onhr_notification_list`, `NHOA_member_directory + "
                    "NHOA_board_seat + elijah_ruling`.",
                "evidence_url":
                    "Retrieved URL supporting the class claim. Same value as "
                    "entity_source_url, written from one variable so the pair "
                    "cannot drift.",
            }[col]
            frag.append({
                "dataset": "05_entities", "variable": col, "type": "text",
                "units": "category" if col != "evidence_url" else "URL",
                # pct_filled is measured against the OWNING file (the spine),
                # which is how every other row in this fragment is measured.
                "pct_filled": f"{100.0 * filled / n_spine:.1f}",
                "n_rows": str(pooled), "published": "1",
                "access_tier": "public", "description": desc,
                "generated": TODAY,
            })
            log(f"  {col:20s} documented: {filled:,}/{n_spine:,} spine rows "
                f"({100.0 * filled / n_spine:.1f}%)")
        write_atomic(FRAGMENT, frag, frag_fields, "pre163")
    else:
        log("  fragment missing - skipped")

    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "163_promote_nho_universe.log").write_text(
        "\n".join(LOG_LINES), encoding="utf-8")
    log("\n  now run:  py -3 code/62_no_regression_check.py")


if __name__ == "__main__":
    main()
