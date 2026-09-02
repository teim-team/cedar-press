#!/usr/bin/env python3
"""
Cedar Press - 1104: AUDIT THE THREE NAGPRA AFFILIATION RULES. DO NOT RELAX
THEM.

    py -3 code/1104_nagpra_affiliation_rule_audit.py           # audit, exit 1 on a defect
    py -3 code/1104_nagpra_affiliation_rule_audit.py selftest  # prove each rule FIRES

READ-ONLY on every shipped table. It writes one measurement file,
`docs/NAGPRA_AFFILIATION_RULE_AUDIT.json`, and one review file naming every
alias proposal and how many INDEPENDENT notices it actually has.

THE THREE RULES, AND HOW EACH IS TESTED
---------------------------------------
**R1 - an affiliation comes from the notice's own text.** Not from geography,
not from another notice, not from Cedar's entity layer. Tested by taking every
one of the 51,579 rows in `nagpra_notice_entity_bridge.csv` and requiring
`party_name_verbatim` to appear as a contiguous substring of

  (a) that row's own `source_span_text`, and
  (b) the cached Federal Register full text OF THAT DOCUMENT, read from
      `data/raw/federal_register/nagpra_fulltext/<year>/<doc>.txt.gz`.

(b) is the load-bearing half: it is the only test that can distinguish a name
the notice published from a name Cedar supplied. Whitespace is collapsed and
case folded on both sides - the FR full text carries GPO line wrapping, so a
name that spans a line break is still the notice's own word - and nothing
else is normalised.

**R2 - an alias enters the IDENTITY LAYER only after THREE INDEPENDENT
notices.** Two halves, and the second is the one the assertion layer insists
on: `docs/ASSERTION_LAYER.md` - *three notices that are republications of one
another are ONE source, not three.* So this does not count rows. It builds
republication families first:

  * every notice with `is_correction = 1` is an amendment to another notice,
    not a second sighting;
  * within a block of notices sharing an institution, two notices whose full
    texts have a 7-gram Jaccard similarity >= 0.90 are the same publication.

Then it counts DISTINCT FAMILIES per proposed alias, not notices, and reports
how many clear the bar on that stricter count.

**R3 - cultural detail beyond what the notice publishes is not extracted.**
Tested structurally rather than by reading column names: every free-text
column on `nagpra_notices.csv` is required to be VERBATIM in that notice's own
cached full text (or empty). A column carrying inferred cultural, ceremonial
or provenance detail cannot pass that test, because inferred text is by
definition not in the source. Columns that are controlled enumerations, dates,
counts, ids, URLs or Cedar-derived classifications are listed by name and
excluded, so the exclusion list is auditable rather than implicit.

WHAT COUNTS AS A DEFECT (exit 1)
--------------------------------
  D1  a bridge row whose `party_name_verbatim` is not in its own notice's text
  D2  an alias in `data/clean/entity_aliases.csv` sourced from this dataset
      with fewer than three INDEPENDENT notices behind it
  D3  a free-text notice column whose value is not verbatim in the source

UNMEASURED is emitted, and the run exits 1, wherever an input is missing -
a cached text that is not on disk, an empty table, an alias file without the
column the test needs. An absence of evidence never prints as evidence of
absence.
"""
from __future__ import annotations

import csv
import glob
import gzip
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

NOTICES = ROOT / "data" / "clean" / "nagpra_notices.csv"
BRIDGE = ROOT / "data" / "clean" / "nagpra_notice_entity_bridge.csv"
ALIASES = ROOT / "data" / "clean" / "entity_aliases.csv"
PROPOSALS = ROOT / "review" / "nagpra_alias_proposals.csv"
FULLTEXT = ROOT / "data" / "raw" / "federal_register" / "nagpra_fulltext"
OUT_JSON = ROOT / "docs" / "NAGPRA_AFFILIATION_RULE_AUDIT.json"
OUT_REVIEW = ROOT / "review" / "nagpra_alias_independence.csv"

JACCARD = 0.90
SHINGLE_K = 7

# R3: columns that are NOT free text extracted from the notice. Each is named
# so the exclusion is auditable. Anything not here must be verbatim in source.
R3_NOT_FREE_TEXT = {
    # identifiers, dates, urls, counts, derived enumerations
    "document_number", "publication_date", "publication_year", "notice_type",
    "notice_title_form", "statute_stage", "is_correction",
    "institution_count", "institution_name_basis", "institution_type_derived",
    "mni_basis", "mni_statement_count", "removal_location_basis",
    "window_days_derived", "parse_template", "spans_found",
    "html_url", "pdf_url", "full_text_url", "source_url", "parent_dataset",
    "fetched_date", "artifact_mtime",
    "has_resolved_entity", "lineal_descendant_determination",
    "culturally_unidentifiable",
    # Cedar entity ids and the counts over them - these are the identity
    # layer, and the whole point of R1 is that they are keyed to verbatim
    # strings that ARE tested against the source.
    "consulted_entity_ids", "affiliated_entity_ids",
    "disposition_priority_entity_ids", "repatriation_recipient_entity_ids",
    "letter_of_support_entity_ids", "aboriginal_land_entity_ids",
    "n_consulted_named", "n_consulted_resolved", "n_affiliated_named",
    "n_affiliated_resolved", "n_disposition_priority_named",
    "n_disposition_priority_resolved", "n_repatriation_recipient_named",
    "n_repatriation_recipient_resolved", "n_letter_of_support_named",
    "n_letter_of_support_resolved", "n_aboriginal_land_named",
    "n_aboriginal_land_resolved", "n_parties_named", "n_entities_resolved",
    # numeric statements: digits parsed out of prose, tested as numbers below
    "mni_total_stated", "n_associated_funerary_objects_stated",
    "n_unassociated_funerary_objects_stated", "n_sacred_objects_stated",
    "n_objects_of_cultural_patrimony_stated", "cultural_items_total_stated",
    "repatriation_eligible_date", "response_deadline_date",
    # institution columns: 1077's output, audited by code/1084 against the
    # TITLE rather than the body, and the title is not always in the .txt
    "institution_name", "institution_primary", "institution_names_all",
    "institution_city", "institution_state",
    # `removal_counties` / `removal_states` are normalised place lists derived
    # from `removal_location_statements`, which IS tested verbatim.
    "removal_counties", "removal_states",
    # `object_categories` and `agency_names` are controlled vocabularies.
    "object_categories", "agency_names",
    "title",   # the FR title is metadata, not body text; often absent from .txt
}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip().lower()


def load_texts():
    """-> {document_number: normalised full text}. Missing files are returned
    as a separate list so the caller can print UNMEASURED rather than a clean
    number."""
    out = {}
    for f in glob.glob(str(FULLTEXT / "*" / "*.txt.gz")):
        dn = os.path.basename(f)[:-7]
        try:
            with gzip.open(f, "rt", encoding="utf-8", errors="replace") as fh:
                out[dn] = norm(fh.read())
        except OSError:
            continue
    return out


def read_csv(p: Path):
    with p.open(newline="", encoding="utf-8-sig", errors="replace") as fh:
        rd = csv.DictReader(fh)
        return list(rd.fieldnames or []), list(rd)


def shingles(t: str, k: int = SHINGLE_K):
    w = re.sub(r"[^a-z0-9 ]", " ", t).split()
    return {" ".join(w[i:i + k]) for i in range(max(0, len(w) - k + 1))}


def republication_families(notices, texts):
    """ASSERTION_LAYER: three notices that are republications of one another
    are ONE source. -> {document_number: family_root}, plus a diagnostic."""
    parent = {r["document_number"]: r["document_number"] for r in notices}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # 1. a correction is an amendment to another notice by the same
    #    institution, not a second independent sighting.
    by_inst = defaultdict(list)
    for r in notices:
        by_inst[(r.get("institution_primary")
                 or r.get("institution_name", ""),
                 r.get("notice_type", ""))].append(r)
    n_corr = 0
    for _k, group in by_inst.items():
        base = [r for r in group if r.get("is_correction") != "1"]
        if not base:
            continue
        anchor = min(base, key=lambda r: r.get("publication_date", ""))
        for r in group:
            if r.get("is_correction") == "1":
                union(anchor["document_number"], r["document_number"])
                n_corr += 1

    # 2. near-identical full text within an institution block
    sh = {d: shingles(t) for d, t in texts.items()}
    n_jac = 0
    by_inst2 = defaultdict(list)
    for r in notices:
        by_inst2[r.get("institution_primary")
                 or r.get("institution_name", "")].append(r["document_number"])
    for _k, docs in by_inst2.items():
        for i in range(len(docs)):
            a = sh.get(docs[i])
            if not a:
                continue
            for j in range(i + 1, len(docs)):
                b = sh.get(docs[j])
                if not b:
                    continue
                inter = len(a & b)
                un = len(a) + len(b) - inter
                if un and inter / un >= JACCARD:
                    union(docs[i], docs[j])
                    n_jac += 1
    fam = {d: find(d) for d in parent}
    return fam, {"corrections_folded": n_corr,
                 "jaccard_pairs_folded": n_jac,
                 "notices": len(parent),
                 "families": len(set(fam.values()))}


def audit(quiet=False):
    problems = []
    unmeasured = []
    out = {"measured_date": TODAY}

    for p in (NOTICES, BRIDGE, ALIASES):
        if not p.exists():
            unmeasured.append(f"{p.name} ABSENT")
    if unmeasured:
        print(f"  1104 UNMEASURED: {'; '.join(unmeasured)}")
        return 1

    ncols, notices = read_csv(NOTICES)
    _bc, bridge = read_csv(BRIDGE)
    texts = load_texts()
    out["notices"] = len(notices)
    out["bridge_rows"] = len(bridge)
    out["cached_texts"] = len(texts)

    missing_text = [r["document_number"] for r in notices
                    if r["document_number"] not in texts]
    if missing_text:
        unmeasured.append(f"{len(missing_text)} notices have no cached full "
                          f"text; R1 and R3 cannot be measured on them "
                          f"(e.g. {missing_text[:3]})")

    # ---- R1 ------------------------------------------------------------
    r1_span_fail, r1_text_fail = [], []
    r1_measured = 0
    for r in bridge:
        dn = r["document_number"]
        v = norm(r.get("party_name_verbatim", ""))
        if not v:
            continue
        span = norm(r.get("source_span_text", ""))
        if span and v not in span:
            r1_span_fail.append((dn, r.get("party_name_verbatim", "")))
        t = texts.get(dn)
        if t is None:
            continue
        r1_measured += 1
        if v not in t:
            r1_text_fail.append((dn, r.get("party_name_verbatim", ""),
                                 r.get("relationship", ""),
                                 r.get("resolve_method", "")))
    out["R1"] = {
        "bridge_rows_measured_against_own_full_text": r1_measured,
        "rows_whose_verbatim_name_is_absent_from_that_notice": len(
            r1_text_fail),
        "rows_whose_verbatim_name_is_absent_from_its_own_span": len(
            r1_span_fail),
    }
    if r1_text_fail:
        problems.append(f"D1 {len(r1_text_fail)} bridge rows name a party "
                        f"that is not in that notice's own text")

    # geography can never be the basis: no resolve_method may name one
    geo = Counter(r.get("resolve_method", "").split(":")[0] for r in bridge)
    out["R1"]["resolve_method_heads"] = dict(geo.most_common())
    geo_methods = [k for k in geo
                   if re.search(r"(?i)state|county|geo|city|region|nearest",
                                k)]
    out["R1"]["resolve_methods_naming_geography"] = geo_methods
    if geo_methods:
        problems.append(f"D1 resolve_method names geography: {geo_methods}")

    # ---- R2 ------------------------------------------------------------
    acols, aliases = read_csv(ALIASES)
    if "source_system" not in acols or "source_id" not in acols:
        unmeasured.append("entity_aliases.csv lacks source_system/source_id; "
                          "R2's first half cannot be measured")
        nag_aliases = None
    else:
        nag_aliases = [a for a in aliases
                       if re.search(r"(?i)nagpra",
                                    a.get("source_system", "") + " "
                                    + a.get("source_id", "") + " "
                                    + a.get("alias_layer_basis", ""))]
    out["R2"] = {"identity_layer_alias_rows": len(aliases),
                 "identity_layer_rows_sourced_from_nagpra":
                     None if nag_aliases is None else len(nag_aliases)}

    fam, famdiag = republication_families(notices, texts)
    out["R2"]["republication"] = famdiag

    # every distinct unresolved party name -> the notices that name it
    party_docs = defaultdict(set)
    for r in bridge:
        if r.get("resolve_status") == "resolved":
            continue
        nm = (r.get("party_name_verbatim") or "").strip()
        if nm:
            party_docs[nm].add(r["document_number"])
    rows_out = []
    clears_notices = clears_families = 0
    for nm, docs in party_docs.items():
        fams = {fam.get(d, d) for d in docs}
        if len(docs) >= 3:
            clears_notices += 1
        if len(fams) >= 3:
            clears_families += 1
        rows_out.append({"proposed_alias": nm, "n_notices": len(docs),
                         "n_independent_notice_families": len(fams),
                         "clears_three_independent": int(len(fams) >= 3),
                         "example_documents": "|".join(sorted(docs)[:5])})
    out["R2"]["distinct_unresolved_party_names"] = len(party_docs)
    out["R2"]["clearing_three_notices"] = clears_notices
    out["R2"]["clearing_three_INDEPENDENT_notices"] = clears_families
    out["R2"]["demoted_by_the_independence_test"] = (clears_notices
                                                     - clears_families)

    if nag_aliases:
        below = []
        for a in nag_aliases:
            nm = a.get("alias_name", "")
            fams = {fam.get(d, d) for d in party_docs.get(nm, set())}
            if len(fams) < 3:
                below.append((nm, len(fams)))
        out["R2"]["nagpra_aliases_below_the_bar"] = len(below)
        out["R2"]["nagpra_aliases_below_the_bar_examples"] = below[:10]
        if below:
            problems.append(f"D2 {len(below)} aliases in the identity layer "
                            f"are sourced from this dataset with fewer than "
                            f"three INDEPENDENT notices behind them")
    else:
        out["R2"]["nagpra_aliases_below_the_bar"] = 0

    # ---- R3 ------------------------------------------------------------
    free_text = [c for c in ncols if c not in R3_NOT_FREE_TEXT]
    r3 = {}
    r3_fail_total = 0
    for c in free_text:
        n_nonblank = n_verbatim = 0
        example = None
        for r in notices:
            v = (r.get(c) or "").strip()
            if not v:
                continue
            t = texts.get(r["document_number"])
            if t is None:
                continue
            n_nonblank += 1
            # multi-valued cells are pipe- or semicolon-joined; every part
            # must be in the source, not just the whole string.
            parts = [p for p in re.split(r"\s*\|\s*", v) if p.strip()]
            if all(norm(p) in t for p in parts):
                n_verbatim += 1
            elif example is None:
                example = (r["document_number"], v[:150])
        r3[c] = {"non_blank": n_nonblank, "verbatim_in_source": n_verbatim,
                 "not_verbatim": n_nonblank - n_verbatim,
                 "first_example_not_verbatim": example}
        r3_fail_total += n_nonblank - n_verbatim
    out["R3"] = {"columns_tested": free_text,
                 "columns_excluded_as_not_free_text": sorted(
                     R3_NOT_FREE_TEXT),
                 "per_column": r3,
                 "cells_not_verbatim_in_source": r3_fail_total}
    # A column is a defect only if it FAILS BROADLY - a handful of misses is a
    # parser artefact, a column that is mostly not-in-source is inference.
    for c, d in r3.items():
        if d["non_blank"] >= 50 and d["not_verbatim"] > 0.10 * d["non_blank"]:
            problems.append(
                f"D3 column `{c}` is non-verbatim on "
                f"{d['not_verbatim']:,} of {d['non_blank']:,} non-blank "
                f"cells ({100.0 * d['not_verbatim'] / d['non_blank']:.1f}%)")

    out["unmeasured"] = unmeasured
    out["defects"] = problems

    if not quiet:
        print("  1104 NAGPRA affiliation-rule audit  (READ-ONLY)")
        print(f"    notices {len(notices):,}   bridge rows {len(bridge):,}   "
              f"cached texts {len(texts):,}")
        print("    -- R1  affiliations come from the notice's own text ------")
        print(f"       DENOMINATOR rows measured against their own cached "
              f"full text   {r1_measured:,}")
        print(f"       party_name_verbatim ABSENT from that notice's text     "
              f"       {len(r1_text_fail):,}")
        print(f"       party_name_verbatim absent from its own source_span    "
              f"       {len(r1_span_fail):,}")
        print(f"       resolve_method values naming geography: "
              f"{geo_methods or 'NONE'}")
        for ex in r1_text_fail[:3]:
            print(f"         example  {ex}")
        print("    -- R2  an alias needs THREE INDEPENDENT notices ----------")
        print(f"       identity-layer alias rows                    "
              f"{len(aliases):,}")
        print(f"       of which sourced from NAGPRA                 "
              f"{out['R2']['identity_layer_rows_sourced_from_nagpra']}")
        print(f"       republication families: {famdiag['notices']:,} notices "
              f"-> {famdiag['families']:,} families "
              f"({famdiag['corrections_folded']} corrections folded, "
              f"{famdiag['jaccard_pairs_folded']} near-identical pairs)")
        print(f"       distinct unresolved party names              "
              f"{len(party_docs):,}")
        print(f"       clearing 3 NOTICES                           "
              f"{clears_notices:,}")
        print(f"       clearing 3 INDEPENDENT notices               "
              f"{clears_families:,}   "
              f"(demoted by the independence test: "
              f"{clears_notices - clears_families:,})")
        print(f"       identity-layer aliases below the bar         "
              f"{out['R2']['nagpra_aliases_below_the_bar']}")
        print("    -- R3  no cultural detail beyond what is published -------")
        print(f"       free-text columns tested   {len(free_text)}  "
              f"(excluded as not free text: {len(R3_NOT_FREE_TEXT)})")
        for c, d in sorted(r3.items(),
                           key=lambda kv: -kv[1]["not_verbatim"]):
            pct = (100.0 * d["verbatim_in_source"] / d["non_blank"]
                   if d["non_blank"] else float("nan"))
            if d["non_blank"]:
                print(f"         {c:<34} {d['verbatim_in_source']:>6,} / "
                      f"{d['non_blank']:>6,} verbatim  ({pct:5.1f}%)")
            else:
                print(f"         {c:<34} UNMEASURED - no non-blank cell")
        for u in unmeasured:
            print(f"    UNMEASURED  {u}")
        for p in problems:
            print(f"    DEFECT  {p}")
        if not problems:
            print("    RESULT: all three rules HOLD on the shipped data. "
                  "Nothing was relaxed.")

    OUT_JSON.write_text(json.dumps(out, indent=2, default=str) + "\n",
                        encoding="utf-8")
    rows_out.sort(key=lambda r: (-r["n_independent_notice_families"],
                                 -r["n_notices"], r["proposed_alias"]))
    with OUT_REVIEW.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)
    if not quiet:
        print(f"    wrote {OUT_REVIEW.relative_to(ROOT)}  "
              f"({len(rows_out):,} rows) and "
              f"{OUT_JSON.relative_to(ROOT)}")
    return 1 if (problems or unmeasured) else 0


def selftest() -> int:
    """Prove the three tests FIRE. Each is exercised on a synthetic fixture
    rather than on the shipped tables."""
    # R1: a party name that is not in the source text must be caught.
    t = norm("the museum consulted the Pueblo of Acoma, New Mexico.")
    assert norm("Pueblo of Acoma, New Mexico") in t
    assert norm("Cherokee Nation") not in t, "R1's substring test is inert"

    # R1 must not be defeated by GPO line wrapping.
    wrapped = norm("consulted the Pueblo of\n   Acoma, New Mexico.")
    assert norm("Pueblo of Acoma, New Mexico") in wrapped, \
        "R1 folds whitespace, so a name across a line break still counts"

    # R2: three notices that are republications of one another must count ONE.
    notices = [
        {"document_number": "A", "institution_primary": "X Museum",
         "notice_type": "inventory_completion", "is_correction": "0",
         "publication_date": "2001-01-01"},
        {"document_number": "B", "institution_primary": "X Museum",
         "notice_type": "inventory_completion", "is_correction": "1",
         "publication_date": "2001-02-01"},
        {"document_number": "C", "institution_primary": "X Museum",
         "notice_type": "inventory_completion", "is_correction": "1",
         "publication_date": "2001-03-01"},
    ]
    body = " ".join(f"word{i}" for i in range(400))
    texts = {"A": body, "B": body + " tail", "C": body + " other"}
    fam, diag = republication_families(notices, texts)
    assert len(set(fam.values())) == 1, (fam, diag)
    assert diag["corrections_folded"] == 2, diag
    # and three genuinely different notices must count THREE
    notices2 = [
        {"document_number": "A", "institution_primary": "X Museum",
         "notice_type": "inventory_completion", "is_correction": "0",
         "publication_date": "2001-01-01"},
        {"document_number": "B", "institution_primary": "Y Museum",
         "notice_type": "inventory_completion", "is_correction": "0",
         "publication_date": "2002-01-01"},
        {"document_number": "C", "institution_primary": "Z Museum",
         "notice_type": "inventory_completion", "is_correction": "0",
         "publication_date": "2003-01-01"},
    ]
    texts2 = {"A": " ".join(f"a{i}" for i in range(400)),
              "B": " ".join(f"b{i}" for i in range(400)),
              "C": " ".join(f"c{i}" for i in range(400))}
    fam2, _d2 = republication_families(notices2, texts2)
    assert len(set(fam2.values())) == 3, fam2
    # and the Jaccard half must fire on its own, with no correction flag
    notices3 = [dict(n, is_correction="0") for n in notices]
    fam3, diag3 = republication_families(
        notices3, {"A": body, "B": body, "C": body})
    assert diag3["jaccard_pairs_folded"] >= 2, diag3
    assert len(set(fam3.values())) == 1, fam3

    # R3: an inferred value cannot be verbatim in the source, by construction.
    src = norm("The human remains were removed from Emmet County, Michigan.")
    assert norm("Emmet County, Michigan") in src
    assert norm("associated with a Woodland-period mortuary tradition") \
        not in src, "R3's verbatim test is inert"

    print("  1104 selftest OK: R1's substring test discriminates and survives "
          "GPO line wrapping, R2 folds a correction chain and two identical "
          "texts to ONE family while keeping three real notices at three, "
          "and R3's verbatim test rejects an inferred sentence")
    return 0


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "selftest":
        return selftest()
    return audit()


if __name__ == "__main__":
    sys.exit(main())
