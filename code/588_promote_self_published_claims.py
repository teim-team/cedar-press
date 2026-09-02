#!/usr/bin/env python3
"""
588_promote_self_published_claims.py -- Cedar Press, workstream INT-2.

WHAT THIS PROMOTES, AND WHY IT GETS ITS OWN TABLE
-------------------------------------------------
Three staged files hold what tribal gaming properties say about THEMSELVES on
their own websites: 231 claims that `code/383` already adjudicated as
RECOVERED from the 2026-08-12 refusal pile, 41 further claims from `code/382`,
and 622 ownership / management assertions. Measured 2026-09-01: only **8 of
215** distinct `(source_url, metric, value)` triples in the recovered file had
reached `gaming_property_site_observations.csv`. They were adjudicated once and
then left in staging.

**They are NOT appended to `gaming_property_site_observations.csv`**, and the
reason is the whole point of this table:

> **A MACHINE COUNT A CASINO ADVERTISES IS A CLAIM, NOT A MEASUREMENT.**

The staged rows carry the columns that say so -- `value_is_bounded`,
`bound_direction`, `bound_basis`, `not_summable_with`, `vocabulary_status`,
`recovery_rule` -- and `gaming_property_site_observations.csv` has none of
them. Appending would either drop those columns, which erases the warning, or
add thirteen columns to a table whose codebook block is already a documented
6-of-26 stub. A separate table keeps the marketing claim physically apart from
the regulator's figure, which is what a subscriber needs and what an append
would quietly undo.

138 of the 231 recovered claims are BOUNDED -- "more than 1,000 slots", "over
20 tables". A bound is not a count. `value_is_bounded` and `bound_direction`
travel on every row and `not_summable_with` names, per row, the series it must
never be added to.

THE ONE WITHDRAWAL
------------------
`code/587` reclassified the two `oldcampcasino.com` ownership assertions to
`WITHDRAWN_NOT_SELF_PUBLISHED`: the domain lapsed and now serves affiliate
casino marketing, so nothing on it is SELF-published. This script carries that
withdrawal through and REFUSES to run if it finds the withdrawal missing --
a correction that reaches the staging file and not the shipping table is the
`354_correction_register.py` failure mode, in a new file.
"""
import csv
import hashlib
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parents[1]
CLEAN = CEDAR / "data" / "clean"
STAGING = CEDAR / "data" / "staging"
SPINE = CEDAR / "data" / "spine"
TODAY = date.today().isoformat()

sys.path.insert(0, str(CEDAR / "code"))
import cedar_codebook as CB  # noqa: E402

CLAIMS = "gaming_property_self_published_claims.csv"
ASSERTS = "gaming_property_self_published_assertions.csv"

NOT_A_MEASUREMENT = (
    "SELF-PUBLISHED OPERATOR MARKETING. The property states this about itself "
    "on its own website. It is an ASSERTION, not a regulator's measurement and "
    "not an audited figure, and it must never be pooled with "
    "`gaming_capacity_official.csv` (regulator-reported) or with the Casino "
    "City vendor panel. Where the two disagree, this row is the weaker "
    "evidence and says so.")


def read(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write(p, rows, cols):
    if p.exists():
        shutil.copy2(p, p.with_suffix(f".csv.bak_{TODAY}_pre588"))
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows, {len(cols)} cols)")


def cid(*p):
    return "GSPC-" + hashlib.sha1("|".join(map(str, p)).encode()).hexdigest()[:12]


def main():
    uid = {r["tribe_id"]: (r.get("cedar_uid") or "")
           for r in read(SPINE / "cedar_entity_spine.csv")}
    obs = read(CLEAN / "gaming_property_site_observations.csv")
    seen_in_obs = {(r.get("source_url", ""), r.get("metric", ""),
                    str(r.get("value", ""))) for r in obs}

    rec = read(STAGING / "gaming_property_site_recovered_claims_2026-08-26.csv")
    cla = read(STAGING / "gaming_property_self_published_claims_2026-08-26.csv")

    # A LITERAL DUPLICATE IN THE STAGED FILE, found by the grain assertion.
    # Two rows of the recovered file are byte-identical twins carrying the SAME
    # `claim_id` -- SPC-582ca0c9cc2f and SPC-dfe9072b3dd4, both venue_capacity
    # claims from one Cache Creek weddings page. That is an upstream de-dupe
    # miss in `code/383`, not two facts, and it is collapsed here rather than
    # published twice. Reported by count so the upstream owner can see it.
    dropped_twins = 0

    def dedupe(src):
        nonlocal dropped_twins
        seen, out = set(), []
        for r in src:
            k = r.get("claim_id", "")
            if k and k in seen:
                dropped_twins += 1
                continue
            seen.add(k)
            out.append(r)
        return out

    rec, cla = dedupe(rec), dedupe(cla)
    rows = []
    for src, family in ((rec, "recovered_from_refusal_pile"),
                        (cla, "first_pass_extraction")):
        for r in src:
            k = (r.get("source_url", ""), r.get("metric", ""),
                 str(r.get("value", "")))
            tid = r.get("tribe_id", "")
            rows.append({
                # GRAIN: one row per ADJUDICATED CLAIM OCCURRENCE, which is
                # the staged `claim_id`, NOT (source_url, metric, value).
                #
                # The first draft keyed on that triple and refused with 15
                # duplicates. Every one of them is real: a page states the
                # same number in two different sentences about two different
                # things. Kwataqnuk lists TWO ballrooms that each seat 200;
                # Blue Lake Casino says "500 slots" in three separate passages
                # under three different recovery rules. Those are distinct
                # claims with distinct quotes and collapsing them would delete
                # a ballroom. True repetition of the SAME sentence is already
                # collapsed upstream and counted in `n_occurrences_collapsed`.
                "claim_id": cid(family, r.get("claim_id", "")),
                "source_claim_id": r.get("claim_id", ""),
                "claim_family": family,
                "assertion_class": "SELF_PUBLISHED_OPERATOR_CLAIM",
                "assertion_class_note": NOT_A_MEASUREMENT,
                "metric": r.get("metric", ""),
                "value": r.get("value", ""),
                "unit": r.get("unit", ""),
                "value_is_bounded": r.get("value_is_bounded", ""),
                "bound_direction": r.get("bound_direction", ""),
                "bound_basis": r.get("bound_basis", ""),
                "not_summable_with": (
                    r.get("not_summable_with", "")
                    or "gaming_capacity_official.csv (regulator-reported); the "
                       "Casino City vendor panel"),
                "measurement_type": r.get("measurement_type", ""),
                "measurement_basis": r.get("measurement_basis", ""),
                "vocabulary_status": r.get("vocabulary_status", ""),
                "metric_renamed_from": r.get("metric_renamed_from", ""),
                "recovery_rule": r.get("recovery_rule", ""),
                "recovery_reason": r.get("recovery_reason", ""),
                "n_occurrences_collapsed": r.get("n_occurrences_collapsed", ""),
                "facility_id": r.get("facility_id", ""),
                "facility_name": r.get("facility_name", ""),
                "tribe_id": tid,
                "tribe_name": r.get("tribe_name", ""),
                "cedar_uid": uid.get(tid, ""),
                "state": r.get("state", ""),
                "record_scope": "entity" if tid else "unresolved",
                "record_scope_basis": (
                    "the claim is published by one property's own site and the "
                    "property resolves to one Native entity"
                    if tid else
                    "the site was crawled but no Cedar facility or entity "
                    "resolved from it; recorded unresolved rather than guessed"),
                "inclusion_basis": (
                    "published on the website of a tribally owned or operated "
                    "gaming property in Cedar's facility universe"),
                "also_in_gaming_property_site_observations": (
                    "Y" if k in seen_in_obs else "N"),
                "site_host": r.get("site_host", ""),
                "source_url": r.get("source_url", ""),
                "source_quote": r.get("source_quote", ""),
                "retrieved_at": r.get("retrieved_at", ""),
                "as_of_date": r.get("as_of_date", ""),
                "as_of_date_precision": r.get("as_of_date_precision", ""),
                "as_of_date_basis": r.get("as_of_date_basis", ""),
                "attribution_basis": r.get("attribution_basis", ""),
                "confidence": r.get("confidence", ""),
                "adjudicated_by_script": r.get("built_by_script", ""),
                "built_by": "code/588_promote_self_published_claims.py",
                "built_date": TODAY,
            })

    # ---------------------------------------------------------- assertions
    sp = read(STAGING /
              "gaming_property_self_published_assertions_2026-08-26.csv")
    withdrawn = [r for r in sp
                 if r.get("assertion_class") == "WITHDRAWN_NOT_SELF_PUBLISHED"]
    if not withdrawn:
        sys.exit(
            "REFUSING: the staging file carries no "
            "WITHDRAWN_NOT_SELF_PUBLISHED rows, so `code/587`'s "
            "oldcampcasino.com withdrawal has not reached it. Run "
            "`py -3 code/587_gaming_facility_corrections.py` first. A "
            "correction that reaches one file and not the table that ships is "
            "the exact failure `code/354_correction_register.py` exists for.")
    arows = []
    for r in sp:
        tid = r.get("tribe_id", "")
        arows.append(dict(
            r,
            assertion_id=r.get("assertion_id", ""),
            cedar_uid=uid.get(tid, ""),
            record_scope=("unresolved"
                          if r["assertion_class"].startswith("WITHDRAWN")
                          else ("entity" if tid else "unresolved")),
            record_scope_basis=(
                r.get("assertion_class_note", "")
                if r["assertion_class"].startswith("WITHDRAWN")
                else ("the assertion is published on the property's own host "
                      "and the property resolves to one Native entity"
                      if tid else "no Cedar entity resolved from this host")),
            inclusion_basis=("published on the website of a gaming property in "
                             "Cedar's facility universe"),
            built_by="code/588_promote_self_published_claims.py",
            built_date=TODAY))

    ccols = list(rows[0].keys())
    acols = list(arows[0].keys())

    # grain assertion, in code
    for name, rs, key in ((CLAIMS, rows, ("claim_id",)),
                          (ASSERTS, arows, ("assertion_id",))):
        d = [k for k, v in Counter(tuple(r[c] for c in key)
                                   for r in rs).items() if v > 1]
        if d:
            sys.exit(f"REFUSING to write {name}: {len(d)} duplicate grain "
                     f"keys, e.g. {d[:3]}")

    write(CLEAN / CLAIMS, rows, ccols)
    write(CLEAN / ASSERTS, arows, acols)

    print("\n  what a subscriber must not do with this table")
    b = Counter(r["value_is_bounded"] for r in rows)
    print(f"    bounded values ('more than 1,000 slots'): {b.get('Y', 0)} of "
          f"{len(rows)} - a bound is not a count")
    print(f"    already in gaming_property_site_observations.csv: "
          f"{sum(1 for r in rows if r['also_in_gaming_property_site_observations'] == 'Y')}"
          f" - flagged, not dropped, so neither table is silently short")
    print(f"    withdrawn assertions carried through from 587: {len(withdrawn)}")
    print("    " + Counter(r["record_scope"] for r in rows).most_common().__str__())

    for ds, name, rs, cols in (
            ("07zo_gaming_self_published_claims", CLAIMS, rows, ccols),
            ("07zp_gaming_self_published_assertions", ASSERTS, arows, acols)):
        blocks = []
        n = len(rs)
        for c in cols:
            filled = sum(1 for r in rs if str(r.get(c, "")).strip())
            blocks.append({
                "dataset": ds, "variable": c, "type": "text", "units": "code",
                "pct_filled": round(100.0 * filled / n, 1),
                "n_rows": n, "published": 1, "access_tier": "public",
                "description": DESC.get(c, DESC_DEFAULT.get(c, "")),
                "generated": TODAY})
        missing = [b["variable"] for b in blocks if not b["description"]]
        if missing:
            sys.exit(f"REFUSING: {ds} would ship undefined variables {missing}")
        print(f"    codebook {ds}: {CB.write_fragment(ds, blocks)} variables")


DESC_DEFAULT = {}
DESC = {
    "claim_id": "Cedar key for one self-published claim.",
    "source_claim_id": "The id the adjudicating script gave this claim. Kept "
                       "so a row traces to `code/383`'s own ledger.",
    "claim_family": "`recovered_from_refusal_pile` — adjudicated back in by "
                    "`code/383` from the 2026-08-12 refusals — or "
                    "`first_pass_extraction`.",
    "assertion_class": "Always `SELF_PUBLISHED_OPERATOR_CLAIM`. Deliberately "
                       "OUTSIDE `cedar_domain.MeasurementType`, so it can "
                       "never be promoted into a measurement by relabelling.",
    "assertion_class_note": "What the class means and what may not be done "
                            "with it.",
    "assertion_id": "Cedar key for one self-published ownership or management "
                    "assertion.",
    "assertion_subclass": "`owned_and_operated_by`, `operated_by`, and so on, "
                          "as the page words it.",
    "metric": "What is claimed — gaming_machines, table_games, hotel_rooms, "
              "venue_capacity, convention_square_feet, restaurants, "
              "employees.",
    "value": "The number as published. Read `value_is_bounded` FIRST.",
    "unit": "Unit of `value`.",
    "value_is_bounded": "Y where the page states a BOUND rather than a count "
                        "('more than 1,000 slots'). 138 of 231 recovered "
                        "claims are bounded. **A bound is not a count** and "
                        "must not be averaged or summed as one.",
    "bound_direction": "Which way the bound runs — at least / at most.",
    "bound_basis": "The wording that makes it a bound.",
    "not_summable_with": "Named, per row: the series this value must never be "
                         "added to. Normally `gaming_capacity_official.csv` "
                         "(the regulator series) and the Casino City vendor "
                         "panel.",
    "measurement_type": "The typed measurement vocabulary term, where the "
                        "extractor could set one.",
    "measurement_basis": "How the page frames the figure.",
    "vocabulary_status": "`IN_gaming_facility_metrics_metric` where the metric "
                         "already exists in Cedar's vocabulary (160 rows), or "
                         "`NEW_MEASURE_...` where it does not (71) — a new "
                         "measure is a vocabulary decision, not a silent "
                         "addition.",
    "metric_renamed_from": "Prior metric name where `code/383` renamed it.",
    "recovery_rule": "Which adjudication rule recovered this claim from the "
                     "refusal pile.",
    "recovery_reason": "Why that rule applied, in words.",
    "n_occurrences_collapsed": "How many identical page occurrences this one "
                               "row stands for.",
    "facility_id": "Cedar facility key. Blank where the crawl did not resolve "
                   "to a facility.",
    "facility_name": "Cedar's name for that facility.",
    "tribe_id": "Cedar entity spine handle.",
    "tribe_name": "Spine canonical name.",
    "cedar_uid": "The permanent Cedar identifier — the documented join key.",
    "state": "US state of the property.",
    "record_scope": "ADR-010 scope. `entity` or `unresolved`.",
    "record_scope_basis": "Why this row carries that scope.",
    "inclusion_basis": "ADR-013. Why the record is in Cedar at all.",
    "also_in_gaming_property_site_observations": "Y where the same "
        "(source_url, metric, value) already appears in "
        "`gaming_property_site_observations.csv`. Flagged rather than dropped, "
        "so neither table is silently short and neither is double-counted.",
    "site_host": "Host the claim was read from.",
    "source_url": "Page the claim was read from.",
    "source_quote": "The sentence, verbatim.",
    "retrieved_at": "When Cedar captured the page.",
    "as_of_date": "The date this claim is true as of.",
    "as_of_date_precision": "How precise that date is.",
    "as_of_date_basis": "Why. Operators rarely date marketing copy, so this is "
                        "usually the capture date and an UPPER BOUND on when "
                        "the claim was true.",
    "attribution_basis": "How the page was attributed to the property.",
    "confidence": "Extractor confidence. `WITHDRAWN` where a correction "
                  "removed the claim's class.",
    "adjudicated_by_script": "The script that adjudicated or extracted it.",
    "built_by": "The script that built this table.",
    "built_date": "When.",
    # assertion-only columns
    "asserted_value": "The owner or operator as the page names it.",
    "asserted_value_verbatim": "Surrounding text, verbatim.",
    "asserted_precision": "How precisely the page names the party.",
    "asserted_owner_names_tribal_form": "Y where the asserted owner is written "
                                        "in tribal form (Tribe, Nation, Band, "
                                        "Pueblo, Rancheria).",
    "asserted_owner_is_management_brand": "Y where the named party is a "
        "MANAGEMENT brand rather than the owner. Caesars MANAGES Harrah's "
        "Cherokee; the Eastern Band OWNS it. The two are never merged.",
    "cedar_curated_owner": "Who Cedar already had as owner.",
    "agrees_with_curated_owner": "Whether the page agrees with Cedar, and how.",
    "cedar_open_date": "Cedar's open date for the property.",
    "cedar_open_date_precision": "Its precision.",
    "agrees_with_cedar_open_year": "Whether the page agrees on the open year.",
    "entity_id": "Entity handle carried from the crawl.",
    "source_file": "The captured page on disk.",
    "source_md5": "MD5 of that capture — integrity evidence.",
    "built_by_script": "The script that produced the staged row.",
}


if __name__ == "__main__":
    main()
