#!/usr/bin/env python3
"""
Cedar Press - 615: RESOLVE `publishable` ON native_owned_businesses.csv.

    py -3 code/615_set_publishable_native_owned_businesses.py            # report
    py -3 code/615_set_publishable_native_owned_businesses.py --apply
    py -3 code/615_set_publishable_native_owned_businesses.py verify

WHY
---
All 2,393 rows shipped with `publishable = N` and `consent_status = UNRESOLVED`
because nobody had decided the question. The owner decided it on 2026-09-01:

    "It's not like we just are taking a tribe dataset of their vendors and just
     putting it on our website. We're making it all cohesive and harmonized
     into one dataset per category... To the extent where we said we'll
     acknowledge you because you shared this data, we'll do that."

See `docs/PUBLICATION_POLICY.md`. The product is the harmonized dataset - 2,393
rows from 18 certifying authorities under one schema, with `identity_scope`
preserved so `enrolled_member_100pct` and `shareholder_descendant_or_spouse`
stay distinguishable. That is not a redistribution of anyone's page.

TWO INDEPENDENT GATES, AND A ROW MUST CLEAR BOTH
------------------------------------------------
Conflating them is how this would go wrong, so they are computed separately.

1. PERMISSION - a property of the SOURCE.
   `TERMS_STATED_RESTRICTIVE` (346 rows, Navajo NBOA) stays N. Harmonizing
   changes what we publish, not what we were allowed to take, and a harmonized
   derivative of refused data is still refused data. `SILENT` (1,998) and
   `TERMS_STATED_NO_REUSE_RESTRICTION` (49) clear this gate.

2. PRIVACY - and the owner CORRECTED an over-withholding here on 2026-09-01.

   The first version of this script withheld 521 rows because
   `business_name_is_person_name` was 1 or undecidable - "Jane Doe
   Construction" was treated as publishing Jane Doe. That was wrong, and the
   owner said so:

       "If a site is publicly accessible, it is part of the public domain and
        therefore we can incorporate it. So if they have their names or
        whatever, that's fine. It's not PII, it's not Social Security numbers.
        But the firm is named after the owner - it's the name of the firm, and
        of course we're going to include that."

   He is right. **A firm's legal name is the firm's name.** A business listed
   on a tribe's public vendor directory has been published by that tribe as a
   business, and the certifying authority chose to list it. Suppressing the
   business name would make the row useless while protecting nobody - the name
   is already public, on the tribe's own site, precisely so people can hire
   them.

   The distinction that survives is NOT name-shaped-ness. It is: does the
   column describe the FIRM, or a PERSON separate from the firm?

     FIRM      legal name, DBA, city, state, NAICS, certification number,
               licence number, identity_scope  ->  publish
     PERSON    a home address, a personal email or phone, an owner's date of
               birth, an SSN or TIN, anything a person holds apart from the
               business  ->  never, and none of it is in this table anyway

   The clean table was verified before this ran: it carries no
   `owner_name_raw`, email, phone or street-address column at all.
   `owner_name_present` and `n_owners_named` are counts. So there is nothing
   left in it that the privacy gate needs to catch, and the gate is retired.

   `business_name_is_person_name` is KEPT as a column. It is no longer a
   suppression trigger, but it is a real property of the row and a downstream
   consumer may want it.

The clean table was already sanitized before this ran and that was verified:
no `owner_name_raw`, email, phone, or street address column exists in it.
`owner_name_present` and `n_owners_named` are counts; `withheld_fields` names
per row what stayed in staging.

WHAT THIS DOES NOT DO
---------------------
It does not touch `consent_status`. Consent is a statement by the source about
Cedar's use, and no source has made one. `publishable` records OUR decision
under a stated policy; `consent_status` records THEIRS. A project that
overwrote the second with the first would be recording a permission nobody
gave, which is precisely the failure this dataset is most exposed to.

> **AMENDED 2026-09-02 (second owner ruling).** `PERMISSION_OK` below is
> extended from two values to five, and two NON-terms withholdings are made
> explicit so the extension cannot swallow them. Read
> `<!-- BEGIN TERMS-OWNER-RULING-PUBLISH-2026-09-02 -->` in
> `docs/PUBLICATION_POLICY.md` first; the reasoning is recorded at
> `PERMISSION_OK` and `NOT_A_FIRM`.
"""
from __future__ import annotations

import csv
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
T = ROOT / "data" / "clean" / "native_owned_businesses.csv"

# ---------------------------------------------------------------------------
# GATE 1 - PERMISSION. An ALLOW-LIST, and it stays one.
# ---------------------------------------------------------------------------
# EXTENDED 2026-09-02 by the owner's second ruling of that day, recorded at
# `<!-- BEGIN TERMS-OWNER-RULING-PUBLISH-2026-09-02 -->` in
# docs/PUBLICATION_POLICY.md:
#
#     "Publish all harvested rows. If a tribe puts its business directory on
#      its own public website, Cedar may republish the listing."
#
# The first ruling of 2026-09-02 released HARVESTING a Native entity's own
# public pages regardless of a terms statement; it left publication unstated,
# and 1,827 lawfully harvested rows sat `publishable = N` in the gap. The
# second ruling closes it. Every row this list now admits was harvested from
# the certifying authority's OWN public page - the distinction the ruling is
# scoped to, and the reason it does not reach a third party's database.
#
# ADDED, each with the count it released on the day and why it is a terms
# decision about the entity's own publication:
#
#   TERMS_STATED_RESTRICTIVE      1,090  Chickasaw 602, Navajo 346, NANA/Akima
#                                        50, Colville 44, Southern Ute 18,
#                                        Forest County Potawatomi 16, CTUIR 14.
#                                        The publisher stated a reuse
#                                        restriction on its own directory. Now
#                                        a RECORDED OBSERVATION, not a gate -
#                                        the first ruling's own words.
#   NO_TERMS_PAGE_SERVED            175  Wampanoag Aquinnah 101, Bad River 39,
#                                        Little Traverse Bay 35. The host
#                                        served no terms page at all, so there
#                                        is no statement to honour. Withholding
#                                        on the ABSENCE of a restriction was
#                                        always the over-compliance defect
#                                        `docs/TERMS_SCOPE` names: it invents a
#                                        prohibition the publisher never made.
#   TERMS_STATED_COPYRIGHT_ONLY      17  Chehalis 10, Delaware Tribe 4,
#                                        California Valley Miwok 3. A bare
#                                        copyright notice asserts authorship of
#                                        the PAGE. It is not a reuse
#                                        restriction on the listing, and Cedar
#                                        republishes the facts of the listing,
#                                        not the page.
#
# DELIBERATELY NOT ADDED:
#
#   NOT_CHECKED                      19  Nineteen shard rows whose host terms
#                                        were never read. This is not a terms
#                                        decision - it is the ABSENCE of one.
#                                        The ruling moved a gate; it did not
#                                        authorise publishing what nobody
#                                        looked at. Check the host, write the
#                                        real status, and the row releases
#                                        itself through the value it earns.
#
# STILL AN ALLOW-LIST ON PURPOSE. A `source_terms_status` value that does not
# appear here withholds. A future harvester inventing a sixth value publishes
# nothing until somebody decides what it means, which is the failure mode this
# file is supposed to have.
#
# AND WHAT THE RULING DOES NOT REACH, so nobody extends this list by analogy:
# technical access controls; a natural person's data held apart from a public
# role (`cedar_publication.NEVER` drops those as COLUMNS); a third party's
# terms (EMMA/MSRB, which has no rows in data/clean and must not acquire any
# through this list); and the proprietary identifiers Casino City and D-U-N-S.
PERMISSION_OK = {
    "SILENT",
    "TERMS_STATED_NO_REUSE_RESTRICTION",
    # released 2026-09-02 by TERMS-OWNER-RULING-PUBLISH-2026-09-02
    "TERMS_STATED_RESTRICTIVE",
    "NO_TERMS_PAGE_SERVED",
    "TERMS_STATED_COPYRIGHT_ONLY",
}

# ---------------------------------------------------------------------------
# GATE 0 - THE ROW IS NOT A FIRM. Nothing to do with permission.
# ---------------------------------------------------------------------------
# THIS GATE EXISTS BECAUSE THE PERMISSION GATE WAS DOING ITS WORK BY ACCIDENT.
# Six rows in this table are parse artefacts, and until 2026-09-02 three of
# them were held only by a sentence typed into `publishable_basis` and three by
# a permission value that the ruling above has now removed. Widening
# PERMISSION_OK without this block would have published a PDF column heading as
# a Native-owned business.
#
# Keyed by `business_source_id`, which is `source_id:source_business_key` and
# survives a rebuild. Verified individually against the raw snapshot on disk:
#
#   TBD-R02  Colville, ContractorListJune26.pdf. The table's own header row and
#            one shifted cell. `Certified Title 10 Yes/No` carries
#            city="Located near Reservation?" and state="LO" - it IS the header
#            line. `Yes` carries city="No", state="NO". `PDF Link` is the link
#            column's label. The other 41 Colville rows are correctly aligned
#            (checked column by column) and every one of them publishes.
#   TBD-059  Doyon / Na-Dena' tourism page. List punctuation and marketing copy
#            filed as firm names; `846_session_audit._artefact` already fails
#            if any of them goes publishable=Y.
#
# FLAGGED, NOT DELETED. The rows stay as the evidence of the parse defect, per
# AGENTS.md, and `publishable_basis` gets the machine-greppable prefix
# `NOT_A_FIRM:` so the reason is legible to a consumer and to
# `846_session_audit._artefact`, which fails if any of the six goes
# publishable=Y.
#
# NOT written into `publish_hold`, deliberately. That column is `1100`'s and
# means exactly one thing - the unreviewed heading/anchor scrape. `1100`'s own
# selftest picks the FIRST publish_hold=Y row to inject its I4 violation into,
# so a row held here for an unrelated reason would make that selftest go
# SILENT: a guard for someone else's rule, disarmed by borrowing their column.
NOT_A_FIRM = {
    "TBD-R02:4bf5f3e26e": "the PDF table's own header row - business_name_raw "
                          "is the 'Certified Title 10 Yes/No' column heading, "
                          "city is 'Located near Reservation?'",
    "TBD-R02:a6105c0a61": "a shifted header/data cell - business_name_raw is "
                          "'Yes', city is 'No', state_province is 'NO'",
    "TBD-R02:74f595db8c": "'PDF Link' is the link column's label, not a "
                          "contractor",
    "TBD-059:3":  "list punctuation captured as a firm name",
    "TBD-059:7":  "marketing copy captured as a firm name",
    "TBD-059:8":  "an award headline captured as a firm name",
}


def decide(r: dict) -> tuple:
    """(publishable, reason).

    THREE gates, evaluated in this order, and the order is the point. The
    permission gate was widened on 2026-09-02 to release 1,282 rows; run first
    it would have released six parse artefacts and 523 rows an accuracy hold
    already refused, because both of those were sitting behind a permission
    value rather than behind a reason of their own.

      0  NOT A FIRM   an artefact of a parser. Never a permission question.
      1  PUBLISH HOLD `1100`'s hold on the `1070` heading/anchor scrape -
                      'HTML heading/anchor scrape - not a table'. 523 rows,
                      three certifying authorities, and a sample of them reads
                      'ARA Director', 'Panda Express', 'Jersey Mike's Subs',
                      'Connecticut Suns (WNBA)': page furniture and tenant
                      brands at tribal properties, not Native-owned firms.
                      Their `source_terms_status` is NO_TERMS_PAGE_SERVED,
                      which gate 2 now admits - so without this gate the
                      widening would have published all 523. The hold is an
                      ACCURACY refusal and the ruling does not reach it.
      2  PERMISSION   the allow-list above.

    The privacy gate was retired 2026-09-01 - see the module docstring. A
    firm's legal name is the firm's name, and no person-scoped column exists in
    this table to withhold.
    """
    bsid = (r.get("business_source_id") or "").strip()
    if bsid in NOT_A_FIRM:
        return "N", ("NOT_A_FIRM: " + NOT_A_FIRM[bsid]
                     + ". Row retained as evidence of the parse defect.")
    if (r.get("publish_hold") or "").strip() == "Y":
        return "N", ("PUBLISH_HOLD: an accuracy hold, not a terms decision - "
                     "see publish_hold_basis. Not released by "
                     "TERMS-OWNER-RULING-PUBLISH-2026-09-02.")
    terms = (r.get("source_terms_status") or "").strip()
    if terms not in PERMISSION_OK:
        return "N", f"PERMISSION:{terms or 'UNKNOWN'}"
    return "Y", "harmonized_publication_per_PUBLICATION_POLICY"


def main() -> int:
    apply = "--apply" in sys.argv
    verify = "verify" in sys.argv

    with T.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        cols = list(rd.fieldnames or [])
        rows = list(rd)

    tally = Counter()
    for r in rows:
        p, why = decide(r)
        tally[(p, why.split(":")[0])] += 1
        r["_p"], r["_why"] = p, why

    y = sum(n for (p, _), n in tally.items() if p == "Y")
    print(f"  615 publishable  {len(rows):,} rows -> "
          f"{y:,} publishable, {len(rows) - y:,} withheld")
    for (p, cls), n in sorted(tally.items(), key=lambda kv: -kv[1]):
        print(f"    {p}  {cls:<12} {n:,}")

    # by source, so the acknowledgments section can be written from this
    bysrc = Counter()
    for r in rows:
        if r["_p"] == "Y":
            bysrc[r.get("certifying_authority_name") or r.get("source_id")] += 1
    print(f"    publishable authorities: {len(bysrc)}")

    if verify:
        bad = [r for r in rows
               if (r.get("publishable") or "") != r["_p"]]
        return 1 if bad else 0
    if not apply:
        print("    (report only - pass --apply)")
        return 0

    shutil.copy2(T, T.with_name(T.name + f".bak_{TODAY}_pre615"))
    if "publishable_basis" not in cols:
        cols.append("publishable_basis")
    for r in rows:
        r["publishable"] = r["_p"]
        r["publishable_basis"] = r["_why"]
        r.pop("_p", None)
        r.pop("_why", None)
    with T.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"    APPLIED. consent_status untouched - it records the SOURCE's "
          f"statement, not ours.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
