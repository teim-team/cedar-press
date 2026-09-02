#!/usr/bin/env python3
"""
585_factcheck_nigc_keys.py -- Cedar Press, workstream INT-2 (gaming promotion).

WHY THIS EXISTS
---------------
`code/344_pull_nigc_document_surface.py` staged four NIGC families on
2026-09-01 and keyed the tribe on each row with `resolve_entity`. 320 of 362
enforcement actions, 98 of 102 Indian lands opinions and 67 of 68 management
contract approvals came back keyed. A key is not a fact until something has
checked it, and the resolver's last tier -- CONTAINMENT -- is the tier that
put $592M of Umatilla Electric Cooperative onto the Confederated Tribes of the
Umatilla Reservation and $2.8B onto Chickasaw Children's Village.

232 of the 485 keys on those three files came from that tier. This script
re-derives every key and reports what does not hold. It writes NOTHING to
`data/clean/`; `code/586_promote_nigc_gaming.py` reads its output.

WHAT IT DOES, IN ORDER
----------------------
1. CLEANS THE FILED NAME. NIGC's document titles carry the action code inside
   the subject string -- "Fort Sill Apache Tribe of Oklahoma <tab>NOV-09-35".
   The tab and the code are not part of the party's name, and their presence
   is why that exact string resolved by ALIAS to the correct
   `Fort Sill-Chiricahua-Warm Springs-Apache Tribe` on one row of the file and
   by CONTAINMENT to a DIFFERENT tribe, `Apache Tribe of Oklahoma`, on
   another. Cleaning the source string is not matching; it is reading the
   source.

2. RUNS THE ONE RESOLVER, against a spine with the classes a gaming regulator
   cannot be talking about REMOVED. This is `code/92_build_gaming_capacity_
   official.py`'s REFUSED_CLASSES guard, applied as a pre-filter rather than a
   post-filter so that an entity refused by class stops OUTSCORING the real
   tribe instead of merely being dropped after it wins.

   Measured here: "San Carlos Apache Tribe" was UNKEYED in staging, reported
   as `ambiguous_containment:2:San Carlos Apache College, San Carlos Apache
   Tribe Relending Enterprise`. The spine holds the tribe itself two rows away
   (`TRBF-SNCRLS-00 San Carlos`). The college and the CDFI beat it because
   their canonical names carry MORE of the filed string's tokens. Removing the
   two classes leaves one answer and it is the right one.

   No second matcher is written. AGENTS.md holds `resolve_entity` as the one
   resolver and that rule is not bent here.

3. APPLIES A NAMED RULING per remaining defect, each carrying its own
   evidence, in `RULINGS` below. A ruling quotes the spine's own alias or the
   primary document. It is not a fuzzy rescue.

4. REFUSES what cannot be established, with a written reason. Four 1999
   enforcement actions keyed to the Seneca Nation are refused here, and the
   reason is the strongest single finding in this pass -- see SENECA_1999.

OUTPUT
------
  data/interim/nigc_key_corrections_<date>.csv   machine-readable, for 586
  review/nigc_key_factcheck_<date>.md            the written finding
"""
import csv
import importlib.util
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parents[1]
STAGING = CEDAR / "data" / "staging"
INTERIM = CEDAR / "data" / "interim"
REVIEW = CEDAR / "review"
SPINE = CEDAR / "data" / "spine"
TODAY = date.today().isoformat()

_spec = importlib.util.spec_from_file_location(
    "party_rulings", str(CEDAR / "code" / "33_apply_party_rulings.py"))
_pr = importlib.util.module_from_spec(_spec)
sys.modules["party_rulings"] = _pr
_spec.loader.exec_module(_pr)
resolve_entity = _pr.resolve_entity

# ---------------------------------------------------------------------------
# The classes a NIGC enforcement action, Indian lands opinion or management
# contract approval is NEVER about. Copied deliberately, not imported, from
# `92_build_gaming_capacity_official.py` REFUSED_CLASSES -- 92 is a 1,200-line
# build and importing it to borrow a set would run it. The list is identical
# and the comment there carries the measurement that produced it.
REFUSED_CLASSES = {
    "Tribal College or University", "BIE School", "Urban Indian Organization",
    "Native Community Development Financial Institution",
    "Native Financial Institution",
}

# NIGC writes the action code INSIDE the document title. These are the shapes
# observed across all 532 staged rows, verified by eye against the source
# strings before being written here.
CODE_TAIL = re.compile(
    r"\s*[\t]?\s*("
    r"(NOV/CO|NOV|SA|CFA|CO|TCO|NDO|ASA\d?)[\s\-/]*\d{2}[\s\-]?\d{0,3}"
    r"(/(TCO|CO|NOV)-\d{2}-\d{2})?"
    r"(\s+\w{3}-\d{2}-\d{2})?"
    r"|SA-PTO"
    r"|ASA\d-\d{2}-[A-Z]{3}"
    r")\s*$", re.I)
DATE_HEAD = re.compile(r"^\s*\d{4}[.\-]\d{2}[.\-]\d{2}[_\s]*")


def clean_filed(s):
    """The party's name, with NIGC's filing apparatus removed.

    Returns (cleaned, original_if_changed). Reading the source is not
    matching.
    """
    orig = (s or "").replace(" ", " ").strip()
    out = DATE_HEAD.sub("", orig)
    prev = None
    while prev != out:
        prev = out
        out = CODE_TAIL.sub("", out).strip()
    out = out.strip(" \t-–—,")
    return out, ("" if out == orig else orig)


# ---------------------------------------------------------------------------
# NAMED RULINGS. Each is a specific defect with its own evidence. The key is
# the CLEANED filed name, upper-cased and whitespace-collapsed.
#
# `to` of None means REFUSE: the row stays unkeyed and carries `why` as its
# record_scope_basis. A refusal with a written reason is honest; a guess is
# not, and `record_scope = unresolved` is a work-queue entry, not a hole.
SENECA_1999 = (
    "REFUSED. NOV-99-11/26/27/33 belong to NIGC's 1999 sweep of retail "
    "outlets: the same cohort in this file includes Hoag's Smoke Shop, "
    "Iroquois Smoke Shop, Big Indian Smoke Shop, Peace Pipe Tobacco, "
    "Two-Way Thru Smoke Shop, Oil Springs Corner Store, M & M Smoke Shop, "
    "Triple J's, Sandy's, Penalty Box, Native Pride, Ken's Smoke Shop and "
    "more -- ALL of which stayed unkeyed. These four keyed only because "
    "their business names carry the token 'Seneca'. That is the UMATILLA "
    "ELECTRIC COOPERATIVE defect: a business named for the nation whose "
    "territory it sits on is not the nation. The document is an image-only "
    "scan (3 characters of extractable text), so the respondent cannot be "
    "read from it; the respondent is therefore NOT ASSERTED."
)

RULINGS = {
    "CHEROKEE NATION OF OKLAHOMA": (
        "TRBF-CHKNAT-00",
        "Staging keyed this to TRBF-UKEETW-00, the United Keetoowah Band of "
        "Cherokee Indians in Oklahoma -- a DIFFERENT federally recognized "
        "tribe. The spine holds `Cherokee Nation` (TRBF-CHKNAT-00, Federally "
        "recognized tribe, OK). Containment preferred the UKB because the "
        "UKB's canonical name happens to contain BOTH distinctive tokens of "
        "the filed string ('Cherokee', 'Oklahoma') while `Cherokee Nation` "
        "contains only one, so the wrong tribe scored higher."),
    "FORT PECK RESERVATION": (
        "TRBF-ABSXFP-00",
        "Staging keyed this to TCU-FRTPCK-00, Fort Peck Community College. "
        "Spine alias, verbatim: 'Assiniboine and Sioux Tribes of the Fort "
        "Peck Indian Reservation' on TRBF-ABSXFP-00, and other rows of this "
        "same file key correctly to it. A gaming enforcement action is not "
        "issued to a tribal college."),
    "CONFEDERATED SALISH AND KOOTENAI TRIBES": (
        "TRBF-CSKTFR-00",
        "Staging keyed this to TCU-SLSHKT-00, Salish Kootenai College. Spine "
        "alias, verbatim: 'Confederated Salish and Kootenai Tribes of the "
        "Flathead Reservation' on TRBF-CSKTFR-00."),
    "FLANDREAU SANTEE SIOUX TRIBE": (
        "TRBF-FLANDR-00",
        "Staging keyed this to TRBF-SANTSX-00 `Santee Sioux`, which is the "
        "NEBRASKA tribe. Spine alias, verbatim: 'Flandreau Santee Sioux "
        "Tribe of South Dakota' on TRBF-FLANDR-00. Two distinct federally "
        "recognized tribes; the South Dakota one is the filer."),
    "AUTHORIZATION TO RE-OPEN SEMINOLE NATION GAMING FACILITY": (
        "TRBF-SMNLOK-00",
        "Staging keyed this to TRBF-SMNLFL-00 `Seminole` (Florida). The "
        "document on disk settles it. data/raw/external/nigc_documents/pdf/"
        "enforcement-actions__authorization-to-re-open-seminole-nation-"
        "gaming-facility.pdf, first lines: 'March 5, 2004 / Kenneth E. "
        "Chambers, Principal Chief / Seminole Nation of Oklahoma / P.O. Box "
        "1498 / Wewoka, OK 74884 / Re: Reopening of Gaming Facilities by the "
        "Seminole Nation of Oklahoma'. It is the OKLAHOMA nation."),
    "SENECA JUNCTION": (None, SENECA_1999),
    "SENECA HAWK TRUCK STOP": (None, SENECA_1999),
    "SENECA SMOKE SHOP": (None, SENECA_1999),
    "SENECA HAWK PETRO MART": (None, SENECA_1999),
}

# Rows whose subject string names MORE THAN ONE tribe. ADR-010 scope
# `multi_entity`: the entity is not unresolved, there are two of them, and the
# source itself names both. No research is added -- the string is the evidence.
MULTI = {
    "MIAMI TRIBE/MODOC TRIBE": (
        ["TRBF-MIAMIT-00", "TRBF-MODOCN-00"],
        "The filed string names two federally recognized tribes. Staging "
        "keyed it to Modoc Nation alone, silently dropping Miami. ADR-010 "
        "scope `multi_entity`."),
}

# lint-ok: class1 - reading STAGING is the whole job. This script exists to
# check keys BEFORE they are promoted; `code/586` builds the promoted tables
# FROM the output of this check. Reading the promoted table instead would make
# the check circular - it would verify the keys against themselves - and would
# also mean the first promotion had already shipped unchecked keys, which is
# the failure this script was written to prevent.
FILES = ["nigc_enforcement_actions_staged.csv",
         "nigc_indian_lands_opinions_staged.csv",
         "nigc_management_contract_approvals_staged.csv"]


def norm_key(s):
    return re.sub(r"\s+", " ", s).strip().upper()


def main():
    spine = list(csv.DictReader(
        open(SPINE / "cedar_entity_spine.csv", encoding="utf-8-sig")))
    reg = list(csv.DictReader(
        open(SPINE / "cedar_identity_register.csv", encoding="utf-8-sig")))
    by_tid = {r["tribe_id"]: r for r in spine}
    cls_of = {r["tribe_id"]: r.get("entity_class", "") for r in spine}
    reg_eid = {r["cedar_entity_id"] for r in reg}
    uid_of = {r["tribe_id"]: (r.get("cedar_uid") or "") for r in spine}
    gaming_spine = [r for r in spine
                    if r.get("entity_class", "") not in REFUSED_CLASSES]
    print(f"585: spine {len(spine):,} entities, {len(gaming_spine):,} after "
          f"removing {len(REFUSED_CLASSES)} classes a gaming regulator "
          f"cannot be naming")

    out, tally = [], Counter()
    per_file = defaultdict(Counter)
    for fname in FILES:
        rows = list(csv.DictReader(
            open(STAGING / fname, encoding="utf-8-sig")))
        for i, r in enumerate(rows):
            filed = r.get("source_name_verbatim", "") or ""
            cleaned, removed = clean_filed(filed)
            k = norm_key(cleaned)
            was_id = (r.get("tribe_entity_id") or "").strip()

            if k in MULTI:
                ids, why = MULTI[k]
                new_id, meth, scope = "", "ruling:multi_entity", "multi_entity"
                basis, extra = why, "|".join(ids)
            elif k in RULINGS:
                tid, why = RULINGS[k]
                if tid is None:
                    new_id, meth, scope = "", "ruling:refused", "unresolved"
                else:
                    new_id, meth, scope = tid, "ruling:corrected", "entity"
                basis, extra = why, ""
            else:
                tid, _tname, how = resolve_entity(cleaned, gaming_spine)
                new_id = tid or ""
                meth = (("resolver:" + (how or "no_spine_match")) if tid
                        else ("resolver_unresolved:" +
                              (how or "no_spine_match")))
                scope = "entity" if tid else "unresolved"
                basis, extra = "", ""
                if tid and cls_of.get(tid) in REFUSED_CLASSES:
                    raise SystemExit(f"class pre-filter leaked: {tid}")

            reachable = ""
            if new_id:
                if new_id not in by_tid:
                    reachable = "NOT_IN_SPINE"
                elif by_tid[new_id]["cedar_entity_id"] not in reg_eid:
                    reachable = "NOT_IN_IDENTITY_REGISTER"
                else:
                    reachable = "ok"

            changed = (new_id != was_id)
            verdict = ("MULTI_ENTITY" if scope == "multi_entity" else
                       "UNCHANGED" if not changed else
                       "CORRECTED" if (was_id and new_id) else
                       "WITHDRAWN" if (was_id and not new_id) else
                       "RECOVERED")
            tally[verdict] += 1
            per_file[fname][verdict] += 1
            out.append({
                "staged_file": fname,
                "row_index": i,
                "source_name_verbatim": filed,
                "cleaned_name": cleaned,
                "filing_apparatus_removed": removed,
                "staged_tribe_entity_id": was_id,
                "staged_tribe_canonical_name": r.get("tribe_canonical_name", ""),
                "staged_tribe_match_method": (r.get("tribe_match_method") or ""),
                "checked_tribe_entity_id": new_id,
                "checked_tribe_canonical_name":
                    by_tid.get(new_id, {}).get("canonical_name", ""),
                "checked_cedar_uid": uid_of.get(new_id, ""),
                "checked_tribe_match_method": meth,
                "record_scope": scope,
                "record_scope_basis": basis,
                "additional_entity_ids": extra,
                "register_reachable": reachable,
                "verdict": verdict,
                "checked_by": "code/585_factcheck_nigc_keys.py",
                "checked_date": TODAY,
            })

    INTERIM.mkdir(parents=True, exist_ok=True)
    dest = INTERIM / f"nigc_key_corrections_{TODAY}.csv"
    with open(dest, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"  wrote {dest.relative_to(CEDAR)}  ({len(out):,} rows)")
    for v, n in tally.most_common():
        print(f"    {v:<10} {n:>5}")
    for f, c in per_file.items():
        print(f"    {f}: " + ", ".join(f"{k}={v}" for k, v in c.most_common()))

    changes = [r for r in out if r["verdict"] != "UNCHANGED"]
    unres = [r for r in out if r["record_scope"] == "unresolved"]
    L = [f"# NIGC staged keys - fact check, {TODAY}", "",
         "*`code/585_factcheck_nigc_keys.py`, workstream INT-2. Read before "
         "`code/586_promote_nigc_gaming.py`.*", "",
         f"**{len(out):,} rows checked across three staged files. "
         f"{len(changes)} keys did not survive re-derivation.**", "",
         "| verdict | rows | meaning |", "|---|---:|---|",
         f"| UNCHANGED | {tally['UNCHANGED']} | staging's key re-derived "
         "identically |",
         f"| CORRECTED | {tally['CORRECTED']} | staging keyed a real entity "
         "and it was the WRONG one |",
         f"| WITHDRAWN | {tally['WITHDRAWN']} | staging keyed an entity that "
         "cannot be established; now `unresolved` |",
         f"| RECOVERED | {tally['RECOVERED']} | staging left it unkeyed and "
         "the spine holds the answer |",
         f"| MULTI_ENTITY | {tally['MULTI_ENTITY']} | the source names more "
         "than one tribe; staging kept only one |", "",
         "## Every change, with its evidence", "",
         "| staged name | staged key | checked key | verdict | why |",
         "|---|---|---|---|---|"]
    seen = set()
    for r in changes:
        sig = (r["cleaned_name"], r["staged_tribe_entity_id"],
               r["checked_tribe_entity_id"])
        if sig in seen:
            continue
        seen.add(sig)
        why = (r["record_scope_basis"] or
               ("resolver re-run on the cleaned name: " +
                r["checked_tribe_match_method"]))
        L.append("| `{}` | {} | {} | {} | {} |".format(
            r["cleaned_name"][:60],
            (r["staged_tribe_canonical_name"] or "-"),
            (r["checked_tribe_canonical_name"] or
             (r["additional_entity_ids"] or "- (refused)")),
            r["verdict"], why.replace("|", "/").replace("\n", " ")))
    L += ["", f"## Still unresolved: {len(unres)} rows", "",
          "`record_scope = unresolved` is the work queue, and it is honest. "
          "The distinct names:", ""]
    for (nm, meth), n in Counter(
            (r["cleaned_name"], r["checked_tribe_match_method"])
            for r in unres).most_common():
        L.append(f"- `{nm}` x{n} - {meth}")
    L += ["", "## Register reachability", "",
          "Every checked key was tested against "
          "`data/spine/cedar_identity_register.csv`, not merely against the "
          "spine. Result: " + ", ".join(
              f"`{k}` {v}" for k, v in Counter(
                  r["register_reachable"] for r in out
                  if r["register_reachable"]).most_common()) + "."]
    REVIEW.mkdir(parents=True, exist_ok=True)
    (REVIEW / f"nigc_key_factcheck_{TODAY}.md").write_text(
        "\n".join(L) + "\n", encoding="utf-8")
    print(f"  wrote review/nigc_key_factcheck_{TODAY}.md")


if __name__ == "__main__":
    main()
