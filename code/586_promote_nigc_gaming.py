#!/usr/bin/env python3
"""
586_promote_nigc_gaming.py -- Cedar Press, workstream INT-2 (gaming promotion).

WHAT THIS PROMOTES
------------------
Five NIGC families that `code/344_pull_nigc_document_surface.py` fetched into
`data/staging/` on 2026-09-01 and that no customer can reach. NIGC publishes
72 document categories / 4,071 documents; Cedar held FIVE of the 72 before
that pull.

  data/clean/nigc_enforcement_actions.csv            362   1995-2026
  data/clean/nigc_indian_lands_opinions.csv          102   1997-2026
  data/clean/nigc_game_classification_opinions.csv   122   1992-2024
  data/clean/nigc_management_contract_approvals.csv   68   55 tribes
  data/clean/nigc_document_surface.csv             7,930   73 categories
  data/clean/nigc_action_parties.csv                 ---   the party bridge

THE KEYS ARE NOT TAKEN ON TRUST. `code/585_factcheck_nigc_keys.py` re-derives
every one of them and this script REFUSES TO RUN without its output. 20 of the
532 staged keys did not survive that check: four enforcement actions were
keyed to the wrong federally recognized tribe (Cherokee Nation -> United
Keetoowah Band), four to a tribal college, one to Florida instead of Oklahoma,
three to the wrong Santee Sioux, and four 1999 retail smoke-shop NOVs were
keyed to the Seneca Nation purely because their business names carry the word.

WHAT THIS DOES NOT DO, AND WHY
------------------------------
**It does not merge the document surface into `nigc_ordinances` or
`nigc_declination_letters`.** Those are INSTRUMENT tables -- one row per
ordinance, one per declination letter. The surface is an INDEX-MEMBERSHIP
table -- one row per (category, document) pair on nigc.gov, and a document
sits in several categories. Summing the two double-counts. The surface's value
is precisely that it is a different grain: it MEASURES the instrument tables'
coverage, and it says NIGC's index now carries 1,162 ordinance documents
against Cedar's 1,155 instrument rows, and 329 declination documents against
Cedar's 327. Those two deltas are the refresh signal and they are the reason
this table ships rather than being folded away.

**It does not join to `gaming_facilities.csv`.** Nothing here is at facility
grain. The stated grain of that file is 787 rows / 786 facilities with
`VP-0109` the single named non-facility exclusion, and a table that does not
join to it cannot violate it.

GRAIN
-----
Declared per table in `TABLES` below, and NOT declared in
`code/512_build_dataset_contracts.py` -- GRAIN-WS3 owns gaming's grain
declarations and 512 is not touched here.
"""
import csv
import hashlib
import importlib.util
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parents[1]
STAGING = CEDAR / "data" / "staging"
CLEAN = CEDAR / "data" / "clean"
INTERIM = CEDAR / "data" / "interim"
SPINE = CEDAR / "data" / "spine"
TODAY = date.today().isoformat()

sys.path.insert(0, str(CEDAR / "code"))
import cedar_codebook as CB  # noqa: E402

SOURCE_AUTHORITY = "National Indian Gaming Commission (NIGC)"
IC_BASIS = ("NIGC is the federal regulator created by the Indian Gaming "
            "Regulatory Act, 25 U.S.C. 2701 et seq.; every document it "
            "publishes concerns Indian gaming by statute.")


def read(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write(p, rows, cols):
    """Write, backing up anything already there. Never rewrites in place."""
    if p.exists():
        shutil.copy2(p, p.with_suffix(f".csv.bak_{TODAY}_pre586"))
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows, "
          f"{len(cols)} cols)")


def rid(prefix, *parts):
    h = hashlib.sha1("|".join(str(x) for x in parts).encode("utf-8"))
    return f"{prefix}-{h.hexdigest()[:12].upper()}"


# ---------------------------------------------------------------------------
def main():
    corr_path = INTERIM / f"nigc_key_corrections_{TODAY}.csv"
    if not corr_path.exists():
        # A promotion that has not been fact-checked is the thing this
        # workstream exists to stop. This is a hard stop, not a warning.
        sys.exit(f"REFUSING: {corr_path.relative_to(CEDAR)} is absent. Run "
                 f"`py -3 code/585_factcheck_nigc_keys.py` first -- a key "
                 f"that nothing has checked is not a key.")
    corr = read(corr_path)
    by_row = {(r["staged_file"], int(r["row_index"])): r for r in corr}
    print(f"586: fact check loaded, {len(corr):,} checked keys "
          f"({sum(1 for r in corr if r['verdict'] != 'UNCHANGED')} changed)")

    spine = {r["tribe_id"]: r for r in read(SPINE / "cedar_entity_spine.csv")}

    def key_cols(fname, i):
        """The checked identity block for one staged row."""
        c = by_row[(fname, i)]
        tid = c["checked_tribe_entity_id"]
        return {
            "tribe_entity_id": tid,
            "tribe_canonical_name": c["checked_tribe_canonical_name"],
            "cedar_uid": c["checked_cedar_uid"],
            "tribe_name_as_published": c["source_name_verbatim"],
            "tribe_match_method": c["checked_tribe_match_method"],
            "tribe_key_verified_by": "code/585_factcheck_nigc_keys.py",
            "tribe_key_verdict": c["verdict"],
            "record_scope": c["record_scope"],
            "record_scope_basis": (
                c["record_scope_basis"] or
                ("resolved to one Native entity by the project resolver "
                 "(" + c["checked_tribe_match_method"] + "), re-derived and "
                 "checked against data/spine/cedar_identity_register.csv"
                 if tid else
                 "no spine entity could be established for the subject name "
                 "as NIGC publishes it (" +
                 c["checked_tribe_match_method"] + "); recorded unresolved "
                 "rather than guessed")),
            "additional_entity_ids": c["additional_entity_ids"],
            "inclusion_basis": IC_BASIS,
        }

    ID_COLS = ["tribe_entity_id", "tribe_canonical_name", "cedar_uid",
               "tribe_name_as_published", "tribe_match_method",
               "tribe_key_verified_by", "tribe_key_verdict",
               "record_scope", "record_scope_basis", "additional_entity_ids",
               "inclusion_basis"]

    outputs = {}
    bridge = []

    # ---------------------------------------------------- 1 + 4. documents
    # Enforcement actions and management-contract approvals are the same
    # SHAPE -- a published NIGC document about a named party -- and are built
    # by one loop so the two can never drift apart. They are separate TABLES
    # because they are separate regulatory acts: an enforcement action is a
    # sanction and an approval is a permission, and a user summing them would
    # be summing two opposite things.
    for staged, out_name, prefix, role, what in (
        ("nigc_enforcement_actions_staged.csv", "nigc_enforcement_actions.csv",
         "NIGCEA", "respondent",
         "a NIGC enforcement action: notice of violation, settlement "
         "agreement, civil fine assessment, closure order, temporary closure "
         "order or notice of decision and order"),
        ("nigc_management_contract_approvals_staged.csv",
         "nigc_management_contract_approvals.csv", "NIGCMC", "tribal_party",
         "a management contract approved by the NIGC Chair under 25 U.S.C. "
         "2711"),
    ):
        src = read(STAGING / staged)
        rows = []
        for i, r in enumerate(src):
            k = key_cols(staged, i)
            aid = rid(prefix, r["document_url"], r.get("action_code", ""))
            local = (r.get("local_path") or "").strip()
            txt = ""
            if local and (CEDAR / local).exists():
                txt = "Y"
            rows.append(dict(
                k,
                action_id=aid,
                action_code=r.get("action_code", ""),
                action_type=r.get("action_type", ""),
                action_code_year=r.get("action_code_year", ""),
                action_code_year_basis=r.get("action_code_year_basis", ""),
                document_date=r.get("document_date", ""),
                document_date_basis=r.get("document_date_basis", ""),
                index_post_date=r.get("wp_post_date", ""),
                index_post_date_basis=r.get("wp_post_date_basis", ""),
                document_title_verbatim=r.get("source_name_verbatim", ""),
                nigc_category=r.get("wpdm_category", ""),
                document_url=r.get("document_url", ""),
                resolved_document_url=r.get("resolved_url", ""),
                local_document_path=local,
                document_bytes=r.get("bytes", ""),
                document_md5=r.get("md5", ""),
                document_http_status=r.get("http_status", ""),
                document_retrieved="Y" if txt else "N",
                source_authority=SOURCE_AUTHORITY,
                source_host=r.get("source_host", ""),
                derivation_basis=(
                    "one row per published document on NIGC's "
                    f"`{r.get('wpdm_category','')}` index; {what}. No field "
                    "is inferred: every value is read from the index listing "
                    "or from the document filename, and the basis columns "
                    "say which."),
                fetched_date=r.get("fetched_date", ""),
                retrieved_by=r.get("retrieved_by", ""),
                built_by="code/586_promote_nigc_gaming.py",
                built_date=TODAY,
            ))
            ids = ([k["tribe_entity_id"]] if k["tribe_entity_id"]
                   else [x for x in k["additional_entity_ids"].split("|") if x])
            for tid in ids:
                bridge.append({
                    "record_id": aid,
                    "record_table": out_name,
                    "role": role,
                    "tribe_entity_id": tid,
                    "tribe_canonical_name":
                        spine.get(tid, {}).get("canonical_name", ""),
                    "cedar_uid": spine.get(tid, {}).get("cedar_uid", ""),
                    "party_name_verbatim": r.get("source_name_verbatim", ""),
                    "resolve_method": k["tribe_match_method"],
                    "resolve_status": ("resolved" if k["tribe_entity_id"]
                                       else "resolved_multi_entity"),
                    "record_scope": k["record_scope"],
                    "built_by": "code/586_promote_nigc_gaming.py",
                    "built_date": TODAY,
                })
        cols = (["action_id", "action_code", "action_type",
                 "action_code_year", "action_code_year_basis",
                 "document_date", "document_date_basis",
                 "index_post_date", "index_post_date_basis"]
                + ID_COLS
                + ["document_title_verbatim", "nigc_category", "document_url",
                   "resolved_document_url", "local_document_path",
                   "document_bytes", "document_md5", "document_http_status",
                   "document_retrieved", "source_authority", "source_host",
                   "derivation_basis", "fetched_date", "retrieved_by",
                   "built_by", "built_date"])
        outputs[out_name] = (rows, cols)

    # ------------------------------------------------ 2. Indian lands opinions
    staged = "nigc_indian_lands_opinions_staged.csv"
    src = read(STAGING / staged)
    rows = []
    for i, r in enumerate(src):
        k = key_cols(staged, i)
        oid = rid("NIGCIL", r.get("source_row", ""), r.get("opinion_date", ""),
                  r.get("parcel", ""), r.get("source_name_verbatim", ""))
        rows.append(dict(
            k,
            opinion_id=oid,
            source_index_row=r.get("source_row", ""),
            parcel=r.get("parcel", ""),
            legal_theory=r.get("legal_theory", ""),
            theory_accepted=r.get("theory_accepted", ""),
            theory_accepted_meaning=(
                "Yes = the NIGC Office of General Counsel ACCEPTED the stated "
                "legal theory for the parcel; No = it did not. This is the "
                "outcome of the opinion, not the status of any gaming "
                "operation, and an accepted theory is not by itself a "
                "licence."),
            opinion_date=r.get("opinion_date", ""),
            opinion_date_basis=r.get("opinion_date_basis", ""),
            document_url=r.get("document_url", ""),
            source_index_url=r.get("source_index_url", ""),
            source_authority=SOURCE_AUTHORITY,
            source_host=r.get("source_host", ""),
            derivation_basis=(
                "one row per published Indian lands opinion, transcribed from "
                "the NIGC Office of General Counsel index table (TablePress "
                "id 10) cell for cell. Tribe, parcel, legal theory, outcome "
                "and date are the source's own columns; nothing is derived."),
            fetched_date=r.get("fetched_date", ""),
            retrieved_by=r.get("retrieved_by", ""),
            built_by="code/586_promote_nigc_gaming.py",
            built_date=TODAY,
        ))
    outputs["nigc_indian_lands_opinions.csv"] = (rows, (
        ["opinion_id", "source_index_row"] + ID_COLS +
        ["parcel", "legal_theory", "theory_accepted",
         "theory_accepted_meaning", "opinion_date", "opinion_date_basis",
         "document_url", "source_index_url", "source_authority",
         "source_host", "derivation_basis", "fetched_date", "retrieved_by",
         "built_by", "built_date"]))

    # -------------------------------------- 3. game classification opinions
    src = read(STAGING / "nigc_game_classification_opinions_staged.csv")
    rows = []
    for r in src:
        oid = rid("NIGCGC", r.get("source_row", ""), r.get("game_title", ""),
                  r.get("opinion_date", ""))
        rows.append({
            "opinion_id": oid,
            "source_index_row": r.get("source_row", ""),
            "game_title": r.get("game_title", ""),
            "game_class": r.get("class_ii_iii", ""),
            "game_class_meaning": (
                "II / III / Both, verbatim from the index. Class II and "
                "Class III are the IGRA categories at 25 U.S.C. 2703(7)-(8) "
                "and they carry entirely different regulatory consequences: "
                "Class III requires a tribal-state compact, Class II does "
                "not. A blank means the index left the cell blank."),
            "bingo": r.get("bingo", ""),
            "card_games": r.get("card_games", ""),
            "card_games_state": r.get("card_games_state", ""),
            "pull_tabs": r.get("pull_tabs", ""),
            "internet_gaming": r.get("internet_gaming", ""),
            "other": r.get("other", ""),
            "opinion_date": r.get("opinion_date", ""),
            "opinion_date_basis": r.get("opinion_date_basis", ""),
            "document_url": r.get("document_url", ""),
            "source_index_url": r.get("source_index_url", ""),
            "source_authority": SOURCE_AUTHORITY,
            "source_host": r.get("source_host", ""),
            # ADR-010. A game classification opinion is about a GAME. It names
            # no tribe and the index carries no tribe column, so `unresolved`
            # would be a lie -- there is no entity to find.
            "record_scope": "indian_country",
            "record_scope_basis": (
                "the opinion classifies a GAME under IGRA. It names no "
                "Native entity and the source index carries no party column; "
                "the classification applies wherever the game is offered in "
                "Indian country. ADR-010 scope `indian_country`, which is an "
                "answer and not a gap."),
            "inclusion_basis": IC_BASIS,
            "derivation_basis": (
                "one row per published game classification opinion, "
                "transcribed from the NIGC Office of General Counsel index "
                "table (TablePress id 9). The five feature flags are the "
                "index's own checkbox columns read as Y/N."),
            "fetched_date": r.get("fetched_date", ""),
            "retrieved_by": r.get("retrieved_by", ""),
            "built_by": "code/586_promote_nigc_gaming.py",
            "built_date": TODAY,
        })
    outputs["nigc_game_classification_opinions.csv"] = (
        rows, list(rows[0].keys()))

    # -------------------------------------------------- 5. document surface
    src = read(STAGING / "nigc_document_surface_staged.csv")
    rows = []
    for r in src:
        held = (r.get("cedar_holds_this_family") or "").strip()
        rows.append({
            "membership_id": rid("NIGCDS", r.get("wpdm_category", ""),
                                 r.get("document_slug", "")),
            "nigc_category": r.get("wpdm_category", ""),
            "document_slug": r.get("document_slug", ""),
            "document_title": r.get("document_title", ""),
            "document_url": r.get("document_url", ""),
            "index_post_date": r.get("wp_post_date", ""),
            "listing_page": r.get("listing_page", ""),
            "listing_page_number": r.get("listing_page_number", ""),
            "cedar_holds_this_family": "Y" if held else "N",
            "cedar_local_corpus": held,
            "source_authority": SOURCE_AUTHORITY,
            "source_host": r.get("source_host", ""),
            "record_scope": "indian_country",
            "record_scope_basis": (
                "an index-membership record for a document published by the "
                "federal regulator of Indian gaming. Most categories name no "
                "party, so ADR-010 scope is `indian_country`."),
            "inclusion_basis": IC_BASIS,
            "derivation_basis": (
                "one row per (NIGC document category, document) MEMBERSHIP -- "
                "NOT one row per document. A document that appears in three "
                "categories has three rows and each membership is a separate "
                "published fact. 7,930 memberships over 4,071 distinct "
                "documents in 73 categories. **Never sum this table against "
                "`nigc_ordinances.csv` or `nigc_declination_letters.csv`**: "
                "those are instrument tables at one-row-per-instrument and "
                "this is the index that measures them."),
            "fetched_date": r.get("fetched_date", ""),
            "retrieved_by": r.get("retrieved_by", ""),
            "built_by": "code/586_promote_nigc_gaming.py",
            "built_date": TODAY,
        })
    outputs["nigc_document_surface.csv"] = (rows, list(rows[0].keys()))

    # ------------------------------------------------------- the party bridge
    outputs["nigc_action_parties.csv"] = (bridge, list(bridge[0].keys()))

    # ------------------------------------------------------------ integrity
    print("\n  GRAIN AND DE-DUPE CHECKS (a promotion that double-counts is "
          "worse than no promotion)")
    grain_keys = {
        "nigc_enforcement_actions.csv": ("action_id",),
        "nigc_management_contract_approvals.csv": ("action_id",),
        "nigc_indian_lands_opinions.csv": ("opinion_id",),
        "nigc_game_classification_opinions.csv": ("opinion_id",),
        "nigc_document_surface.csv": ("nigc_category", "document_slug"),
        "nigc_action_parties.csv": ("record_id", "tribe_entity_id", "role"),
    }
    fail = []
    for name, (rows_, _cols) in outputs.items():
        kc = grain_keys[name]
        seen = Counter(tuple(r[c] for c in kc) for r in rows_)
        dupes = [k for k, v in seen.items() if v > 1]
        status = "OK" if not dupes else f"**{len(dupes)} DUPLICATE KEYS**"
        print(f"    {name:<44} {len(rows_):>6,} rows, key {'+'.join(kc)}: "
              f"{status}")
        if dupes:
            fail.append((name, dupes[:5]))
    if fail:
        sys.exit(f"REFUSING to write: duplicate grain keys {fail}")

    # overlap against what clean already holds, stated rather than assumed
    ords_ = read(CLEAN / "gaming_ordinances.csv")
    decl = read(CLEAN / "nigc_declination_letters.csv")
    surf = outputs["nigc_document_surface.csv"][0]
    cats = Counter(r["nigc_category"] for r in surf)
    n_ord_idx = cats.get("gaming-ordinances", 0)
    n_dec_idx = cats.get("declination-letters", 0)
    assert n_ord_idx and n_dec_idx, (
        "the two categories this delta is measured on must both be present; "
        "if NIGC renames a slug this assertion is how we find out")
    print(f"\n  COVERAGE DELTA the surface measures (NOT a double count -- "
          f"different grain):")
    print(f"    ordinances:  NIGC index {n_ord_idx:,} documents vs "
          f"gaming_ordinances.csv {len(ords_):,} instrument rows "
          f"-> {n_ord_idx - len(ords_):+,}")
    print(f"    declinations: NIGC index {n_dec_idx:,} documents vs "
          f"nigc_declination_letters.csv {len(decl):,} instrument rows "
          f"-> {n_dec_idx - len(decl):+,}")

    # physical-line vs csv-record, because 27 counts the former
    print("\n  LINE-COUNT EXPOSURE (`27_build_dataset_manifests.py` counts "
          "PHYSICAL LINES; any newline inside a text field inflates it)")
    for name, (rows_, cols) in outputs.items():
        nl = sum(1 for r in rows_ for c in cols
                 if "\n" in str(r.get(c, "") or ""))
        print(f"    {name:<44} cells containing a newline: {nl}")

    # ---------------------------------------------------------------- write
    print()
    for name, (rows_, cols) in outputs.items():
        write(CLEAN / name, rows_, cols)

    # ------------------------------------------------------------- codebook
    print("\n  codebook fragments (cedar_codebook.write_fragment; the master "
          "is never touched directly)")
    for ds, name in CODEBOOK.items():
        rows_, cols = outputs[name]
        blocks = build_codebook(ds, name, rows_, cols)
        n = CB.write_fragment(ds, blocks)
        print(f"    {ds:<44} {n} variables")

    scopes = Counter()
    for name, (rows_, _c) in outputs.items():
        for r in rows_:
            scopes[(name, r.get("record_scope", ""))] += 1
    print("\n  ADR-010 record_scope, by table")
    for (name, s), n in sorted(scopes.items()):
        print(f"    {name:<44} {s:<16} {n:>6,}")
    print("\n586 done. Next: cedar_codebook build, then 87 -> 25 -> 27.")


# ---------------------------------------------------------------------------
CODEBOOK = {
    "07zi_nigc_enforcement_actions": "nigc_enforcement_actions.csv",
    "07zj_nigc_indian_lands_opinions": "nigc_indian_lands_opinions.csv",
    "07zk_nigc_game_classification_opinions":
        "nigc_game_classification_opinions.csv",
    "07zl_nigc_management_contract_approvals":
        "nigc_management_contract_approvals.csv",
    "07zm_nigc_document_surface": "nigc_document_surface.csv",
    "07zn_nigc_action_parties": "nigc_action_parties.csv",
}

# Every variable gets a written definition. `87` reports `[undefined]` for a
# block that ships columns with no description, and
# `nigc_declination_letters.csv` is already on that list with 45 of 60
# undefined. Registering a block makes a table shippable; it does not make it
# documented, and shipping an undocumented column to a subscriber is the
# defect the runbook names.
DESC = {
    "action_id": "Cedar Press key for one NIGC action document. SHA1 of the "
                 "document URL and the action code, so it is stable across "
                 "rebuilds and never renumbers.",
    "action_code": "NIGC's own action code, verbatim (NOV-24-01, SA-09-31, "
                   "CFA-05-05). Blank where the index title carries none.",
    "action_type": "NOV notice of violation | SA settlement agreement | CFA "
                   "civil fine assessment | CO closure order | TCO temporary "
                   "closure order | NDO notice of decision and order. Parsed "
                   "from the action code, blank where there is none.",
    "action_code_year": "The two-digit year inside the action code. This is "
                        "the year NIGC assigned the code, which is not "
                        "necessarily the document date.",
    "action_code_year_basis": "How action_code_year was obtained, or why it "
                              "is blank.",
    "document_date": "Date on the document itself where the index states "
                     "one. Blank is common and is not an error.",
    "document_date_basis": "How document_date was obtained, or why blank.",
    "index_post_date": "Date NIGC's own content system posted the listing. "
                       "This is a PUBLISHING date, not the date of the "
                       "regulatory act, and the two differ by decades on the "
                       "older documents -- a 1999 notice of violation carries "
                       "an index post date of 2024. Never read it as the "
                       "event date.",
    "index_post_date_basis": "How index_post_date was obtained.",
    "tribe_entity_id": "Cedar entity spine handle for the tribe. Blank where "
                       "record_scope is `unresolved`, `indian_country` or "
                       "`multi_entity` -- read record_scope before reading a "
                       "blank as missing data.",
    "tribe_canonical_name": "The spine's canonical name for tribe_entity_id.",
    "cedar_uid": "The permanent Cedar identifier for the entity. This, not "
                 "the handle, is the documented join key.",
    "tribe_name_as_published": "The subject string exactly as NIGC publishes "
                               "it, including any action code NIGC folded "
                               "into the title. Never edited.",
    "tribe_match_method": "How the key was reached. `ruling:corrected` and "
                          "`ruling:refused` mark rows where an automatic "
                          "match was overturned by a named ruling with "
                          "quoted evidence; see record_scope_basis.",
    "tribe_key_verified_by": "The script that re-derived and checked this "
                             "key. A key nothing has checked does not ship.",
    "tribe_key_verdict": "UNCHANGED | CORRECTED | WITHDRAWN | RECOVERED | "
                         "MULTI_ENTITY, against the staged key that "
                         "code/344 produced.",
    "record_scope": "ADR-010. `entity` one Native entity | `multi_entity` "
                    "several, named in nigc_action_parties.csv | "
                    "`indian_country` generally applicable, no entity and "
                    "that is correct | `unresolved` an entity exists and was "
                    "not found. Only `unresolved` is a defect.",
    "record_scope_basis": "Why this row carries that scope, in words. For a "
                          "corrected or refused key this field holds the "
                          "evidence for the correction.",
    "additional_entity_ids": "Pipe-separated further entity handles where "
                             "the source names more than one party. The "
                             "authoritative representation is "
                             "nigc_action_parties.csv.",
    "inclusion_basis": "ADR-013. Why this record is in Cedar at all.",
    "document_title_verbatim": "The index listing's title, unedited.",
    "nigc_category": "NIGC's own document category slug. The full published "
                     "surface is 73 categories; see nigc_document_surface.",
    "document_url": "The URL NIGC's index links to.",
    "resolved_document_url": "Where that URL resolved after redirects.",
    "local_document_path": "Path to the retrieved PDF inside this repository, "
                           "relative to the repository root.",
    "document_bytes": "Size of the retrieved PDF in bytes.",
    "document_md5": "MD5 of the retrieved PDF. Integrity evidence: it lets a "
                    "subscriber verify the file was not altered.",
    "document_http_status": "HTTP status returned when the PDF was fetched.",
    "document_retrieved": "Y where the PDF is on disk in this repository. A "
                          "retrieved PDF is not necessarily a READABLE one -- "
                          "several are image-only scans with no text layer.",
    "source_authority": "The publishing authority. Always NIGC here.",
    "source_host": "Host the document was read from.",
    "derivation_basis": "What one row of this table IS, and what it is not. "
                        "Read before joining or summing.",
    "fetched_date": "Date Cedar read the source.",
    "retrieved_by": "The script that read the source.",
    "built_by": "The script that built this table.",
    "built_date": "Date this table was built.",
    # opinions
    "opinion_id": "Cedar Press key for one published NIGC legal opinion.",
    "source_index_row": "Row number in NIGC's own index table. Kept so any "
                        "row can be traced back to its position in the "
                        "source.",
    "parcel": "The land NIGC's opinion concerns, verbatim from the index.",
    "legal_theory": "The legal theory under which the parcel was argued to "
                    "be Indian lands eligible for gaming -- Restored Lands, "
                    "Within Reservation Boundaries, Settlement of a Land "
                    "Claim, Last Recognized Reservation and others. Verbatim "
                    "from the index.",
    "theory_accepted": "Yes / No, verbatim from the index.",
    "theory_accepted_meaning": "What Yes and No mean, and what they do not.",
    "opinion_date": "Date of the opinion, verbatim from the index.",
    "opinion_date_basis": "How opinion_date was obtained.",
    "source_index_url": "The NIGC index page this row was transcribed from.",
    "game_title": "The game the opinion classifies, verbatim.",
    "game_class": "II | III | Both, verbatim from the index.",
    "game_class_meaning": "What the class means under IGRA and why it "
                          "matters.",
    "bingo": "Y/N. The index's bingo checkbox for this game.",
    "card_games": "Y/N. The index's card-games checkbox.",
    "card_games_state": "State qualifier the index gives on the card-games "
                        "column, where it gives one.",
    "pull_tabs": "Y/N. The index's pull-tabs checkbox.",
    "internet_gaming": "Y/N. The index's internet-gaming checkbox.",
    "other": "Y/N. The index's `other` checkbox.",
    # surface
    "membership_id": "Cedar Press key for one (category, document) "
                     "membership.",
    "document_slug": "NIGC's own slug for the document. A document in "
                     "several categories carries the SAME slug on each row -- "
                     "this is the de-duplication key, and 7,930 memberships "
                     "resolve to 4,071 distinct documents.",
    "document_title": "Title as the listing shows it.",
    "listing_page": "The category listing page this row was read from.",
    "listing_page_number": "Pagination page number within that listing.",
    "cedar_holds_this_family": "Y where Cedar already holds a local corpus "
                               "for this document's category. This column is "
                               "the coverage instrument: it is how the "
                               "5-of-72 finding was measured.",
    "cedar_local_corpus": "Where that local corpus lives, and which script "
                          "built it.",
    # bridge
    "record_id": "The action_id in record_table this party belongs to.",
    "record_table": "Which table record_id keys into.",
    "role": "`respondent` for an enforcement action, `tribal_party` for a "
            "management contract approval. A role-less bridge loses the "
            "thing that makes it useful.",
    "party_name_verbatim": "The party string as NIGC published it.",
    "resolve_method": "How this party was resolved to the spine.",
    "resolve_status": "resolved | resolved_multi_entity.",
}


def build_codebook(ds, fname, rows, cols):
    n = len(rows)
    out = []
    for c in cols:
        filled = sum(1 for r in rows if str(r.get(c, "")).strip())
        vals = {str(r.get(c, "")) for r in rows}
        typ = "text"
        if c.endswith("_date") or c in ("document_date", "opinion_date",
                                        "index_post_date"):
            typ = "date"
        elif c in ("document_bytes", "document_http_status",
                   "listing_page_number", "action_code_year",
                   "source_index_row"):
            typ = "integer"
        elif vals <= {"Y", "N", ""}:
            typ = "flag"
        out.append({
            "dataset": ds,
            "variable": c,
            "type": typ,
            "units": ("date" if typ == "date" else
                      "bytes" if c == "document_bytes" else
                      "count" if typ == "integer" else
                      "Y/N" if typ == "flag" else "code"),
            "pct_filled": round(100.0 * filled / n, 1) if n else 0.0,
            "n_rows": n,
            "published": 1,
            "access_tier": "public",
            "description": DESC.get(c, ""),
            "generated": TODAY,
        })
    missing = [r["variable"] for r in out if not r["description"]]
    if missing:
        sys.exit(f"REFUSING: {ds} would ship undefined variables {missing}. "
                 f"Write the definition; do not tier it away.")
    return out


if __name__ == "__main__":
    main()
