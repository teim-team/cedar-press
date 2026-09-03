#!/usr/bin/env python3
"""1154 - measure the two defects named in the 2026-09-02 QA reviews.

    A. NAGPRA institution parsing in dist/customer/nagpra.csv
    B. Federal Register / consultation_events.csv grain (fan-out per document)

MEASURE FIRST. This script is read-only; it writes one JSON report and one
CSV of offending rows so every number below can be re-derived and every claim
checked against a real row (field guide rule 3: print the denominator, the
sample cap, and one worked example row).

    py -3 code/1154_nagpra_fr_grain_audit.py report

There is no sampling anywhere in this script - every count is a full census of
the named file, and the denominator is printed next to each count.
"""
from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(10 ** 9)

ROOT = Path(__file__).resolve().parents[1]
# MEASURE THE SOURCE OF TRUTH, THEN CHECK THE EXPORT AGAINST IT. The QA review
# named `dist/customer/nagpra.csv`, but that file is a republish of
# `data/clean/nagpra_notices.csv` and republishing is not this lane's to do, so
# a defect fixed at the parser shows in the clean table first and the export
# lags. Both are read; `customer_export_stale_rows` says whether they agree.
NAGPRA = ROOT / "data" / "clean" / "nagpra_notices.csv"
NAGPRA_DIST = ROOT / "dist" / "customer" / "nagpra.csv"
EVENTS = ROOT / "data" / "clean" / "consultation_events.csv"
FR_CUST = ROOT / "dist" / "customer" / "federal-register.csv"
OUT_JSON = ROOT / "docs" / "NAGPRA_FR_GRAIN_AUDIT_1154.json"
REVIEW = ROOT / "review"

STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC", "PR", "VI", "GU", "AS", "MP",
}

# THREE CLASSES A FIRST DRAFT OF THIS SCRIPT REPORTED, AND WHY THEY ARE GONE.
# The draft printed 526 defective `institution_name` values (7.74%). Reading
# all 37 distinct values behind the biggest of its classes killed the class:
#
#   no_institutional_word_present   108 rows, 37 distinct, ALL REAL
#       Arkansas Archeological Survey (28), Ohio History Connection (22),
#       History Colorado (12), Michigan State Police (6), Folsom History (3),
#       Plimoth Plantation Inc., Dallas Water Utilities, Fremont County
#       Coroner, Cheekwood Estate and Gardens, Tyndall Air Force Base ...
#       The class was measuring THIS SCRIPT'S OWN KEYWORD LIST, not the data.
#       (`Archeological` is not `archaeolog`, and `Survey` was not in it.)
#   reads_as_a_sentence_not_a_name  6 rows, 5 of them
#       "Human Remains Repository, Department of Anthropology, University of
#       Wyoming" - a real repository, caught by a `^human remains` tell.
#   parent_agency_only              1 row, "National Park Service", which
#       genuinely is the controlling agency named by that notice's own title.
#
# That is the repo's signature defect committed by the instrument sent to find
# it, and rule 3 of the field guide - print one worked example row - is what
# caught it. What remains below is contract-based, not vocabulary-based: a
# defect is a cell that CONTRADICTS Cedar's own declared meaning for the
# column, and every one is checkable against the notice's own title.

# `institution_name` is contracted to be the institution string for the notice;
# `institution_names_all` is the pipe-joined split. A `;` inside
# `institution_name` therefore means the parser found more than one holder, and
# it is a defect only when the notice's own title does NOT contain that
# semicolon - i.e. the parser inserted it.
MULTI_SEP = re.compile(r"\s*;\s*")

# Fragments that mean the parser handed back a sentence, not a name. Anchored
# on lead-ins that cannot begin an organisation's name.
SENTENCE_TELLS = re.compile(
    r"^(?:for\s+|in\s+the\s+|the\s+following|this\s+notice|notice\s+is\s+hereby|"
    r"pursuant\s+to|after\s+consultation|determinations?\s+|"
    r"representatives\s+of|disposition\s+of|cultural\s+items\s+within|"
    r"\d+\s)",
    re.I,
)

# Federal Register document-status words shipped as the name of a holder.
EDITORIAL_TAG = re.compile(
    r"^(?:correction|corrections|corrected|republication|republished|"
    r"amendment|amended|erratum|errata|reprint)\.?$", re.I)


def read_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------
# A. NAGPRA institution parsing
# --------------------------------------------------------------------------
def classify_institution(name: str, title: str) -> str:
    """A defect label, or 'ok'. Every label is checkable against `title`."""
    s = (name or "").strip()
    t = re.sub(r"\s+", " ", (title or ""))
    if not s:
        return "empty"
    if SENTENCE_TELLS.search(s):
        return "reads_as_a_sentence_not_a_name"
    if EDITORIAL_TAG.match(s):
        return "federal_register_status_word_shipped_as_an_institution"
    parts = [p for p in MULTI_SEP.split(s) if p.strip()]
    if len(parts) > 1:
        # NOT A DEFECT, AND THIS SCRIPT SAID IT WAS. `institution_name` is
        # `"; ".join(parts)` by construction in 1077, so a jointly-issued
        # notice whose title separated its holders with `, and ` or `and in
        # the possession of` still ships with a `;`. That is Cedar's declared
        # normalisation, not an inserted separator, and calling 290 rows
        # defective for obeying it was this script measuring a convention it
        # had not read. Whether the SPLIT is right is a different question and
        # `institution_split_flag` plus 1084's bridge answer it.
        return ("ok_multi_holder_normalised_to_semicolon" if ";" not in t
                else "ok_multi_holder_semicolon_in_the_title")
    if s.count("(") != s.count(")"):
        return "unbalanced_parenthesis_a_delimiter_fell_inside_one"
    if re.search(r"(?i)\bin the (?:possession|control|collections|custody) of\b", s):
        return "possession_locution_retained_real_holder_is_downstream"
    return "ok"


def audit_nagpra() -> dict:
    rows = read_rows(NAGPRA)
    n = len(rows)
    labels = Counter()
    offenders: list[dict] = []
    state_bad = Counter()
    state_bad_rows: list[dict] = []
    count_mismatch = 0
    count_mismatch_rows: list[dict] = []
    city_bad = 0

    for r in rows:
        lab = classify_institution(r.get("institution_name", ""),
                                   r.get("title", ""))
        labels[lab] += 1
        if not lab.startswith("ok"):
            offenders.append({
                "document_number": r.get("document_number", ""),
                "defect": lab,
                "institution_name": (r.get("institution_name") or "")[:300],
                "institution_names_all": (r.get("institution_names_all") or "")[:300],
                "institution_city": r.get("institution_city", ""),
                "institution_state": r.get("institution_state", ""),
                "institution_name_basis": r.get("institution_name_basis", ""),
                "title": (r.get("title") or "")[:200],
            })

        st = (r.get("institution_state") or "").strip()
        if st and st not in STATES:
            state_bad[st] += 1
            if len(state_bad_rows) < 400:
                state_bad_rows.append({
                    "document_number": r.get("document_number", ""),
                    "institution_state": st,
                    "institution_city": r.get("institution_city", ""),
                    "institution_name": (r.get("institution_name") or "")[:200],
                })

        city = (r.get("institution_city") or "").strip()
        if city and (len(city) > 60 or re.search(r"\d", city)):
            city_bad += 1

        # institution_count must agree with institution_names_all
        try:
            declared = int((r.get("institution_count") or "0") or 0)
        except ValueError:
            declared = -1
        all_names = [p for p in re.split(r"\s*\|\s*|\s*;\s*",
                                         (r.get("institution_names_all") or "")) if p.strip()]
        actual = len(all_names)
        if declared != actual:
            count_mismatch += 1
            if len(count_mismatch_rows) < 200:
                count_mismatch_rows.append({
                    "document_number": r.get("document_number", ""),
                    "institution_count": r.get("institution_count", ""),
                    "n_names_in_institution_names_all": actual,
                    "institution_names_all": (r.get("institution_names_all") or "")[:300],
                })

    REVIEW.mkdir(exist_ok=True)
    with open(REVIEW / "nagpra_institution_defects_1154.csv", "w",
              encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "document_number", "defect", "institution_name",
            "institution_names_all", "institution_city", "institution_state",
            "institution_name_basis", "title"])
        w.writeheader()
        w.writerows(offenders)

    basis = Counter((r.get("institution_name_basis") or "(blank)") for r in rows)
    flags = Counter((r.get("institution_split_flag") or "(none)") for r in rows)

    # Is the shipped customer export the same universe as the clean table?
    stale = "not_measured"
    if NAGPRA_DIST.exists():
        dist = {d["document_number"]: d for d in read_rows(NAGPRA_DIST)}
        cmp_cols = ["institution_name", "institution_primary",
                    "institution_names_all", "institution_count",
                    "institution_city", "institution_state"]
        stale = sum(1 for r in rows
                    if any((dist.get(r["document_number"], {}).get(c) or "")
                           != (r.get(c) or "") for c in cmp_cols))

    return {
        "file": str(NAGPRA.relative_to(ROOT)).replace("\\", "/"),
        "rows_total_full_census": n,
        "institution_name_classes": dict(labels.most_common()),
        "institution_name_defect_rows": n - sum(
            v for k, v in labels.items() if k.startswith("ok")),
        "institution_name_defect_pct": round(100.0 * (n - sum(
            v for k, v in labels.items() if k.startswith("ok"))) / n, 2),
        "distinct_institution_name": len({(r.get("institution_name") or "").strip()
                                          for r in rows}),
        "institution_state_not_a_usps_state_rows": sum(state_bad.values()),
        "institution_state_bad_values_top20": dict(state_bad.most_common(20)),
        "institution_state_blank_rows": sum(
            1 for r in rows if not (r.get("institution_state") or "").strip()),
        "institution_city_suspicious_rows": city_bad,
        "institution_count_disagrees_with_institution_names_all_rows": count_mismatch,
        "institution_name_basis_distribution": dict(basis.most_common()),
        "institution_split_flag_distribution": dict(flags.most_common()),
        "customer_export_rows_disagreeing_with_the_clean_table": stale,
        "customer_export": str(NAGPRA_DIST.relative_to(ROOT)).replace("\\", "/"),
        "offender_csv": "review/nagpra_institution_defects_1154.csv",
        "worked_examples": offenders[:5],
        "state_worked_examples": state_bad_rows[:5],
        "count_mismatch_worked_examples": count_mismatch_rows[:5],
    }


# --------------------------------------------------------------------------
# B. Federal Register consultation_events grain
# --------------------------------------------------------------------------
def audit_events() -> dict:
    rows = read_rows(EVENTS)
    n = len(rows)

    by_doc: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        key = (r.get("fr_document_number") or "").strip() or \
              (r.get("federal_register_citation") or "").strip() or "(none)"
        by_doc[key].append(r)

    sizes = sorted((len(v) for v in by_doc.values()), reverse=True)
    biggest = sorted(by_doc.items(), key=lambda kv: -len(kv[1]))[:10]

    # Is the fan-out one row per named tribe? Test: within a document, is
    # (tribe_id or participant_name_as_published) unique?
    docs_multi = {k: v for k, v in by_doc.items() if len(v) > 1}
    doc_party_unique = 0
    doc_party_dupe = 0
    dupe_examples = []
    for k, v in docs_multi.items():
        keys = [((r.get("tribe_id") or "").strip(),
                 (r.get("participant_name_as_published") or "").strip()) for r in v]
        if len(set(keys)) == len(keys):
            doc_party_unique += 1
        else:
            doc_party_dupe += 1
            if len(dupe_examples) < 5:
                dupe_examples.append({"document": k, "rows": len(v),
                                      "distinct_parties": len(set(keys))})

    # Everything except the party columns identical within a document?
    party_cols = {"consultation_event_id", "tribe_id", "tribe_name",
                  "participant_name_as_published", "participant_role",
                  "cedar_uid", "match_method", "tier", "confidence"}
    hdr = list(rows[0].keys())
    non_party = [c for c in hdr if c not in party_cols]
    docs_event_identical = 0
    docs_event_varies = 0
    varying_cols = Counter()
    for k, v in docs_multi.items():
        varies = [c for c in non_party if len({(r.get(c) or "") for r in v}) > 1]
        if varies:
            docs_event_varies += 1
            for c in varies:
                varying_cols[c] += 1
        else:
            docs_event_identical += 1

    # The conceptual test: "a consultation happened" vs "a notice announcing
    # consultation was published". event_start_date populated = an actual
    # scheduled meeting is asserted. Empty = the row is a notice that merely
    # REPORTS consultation in past tense.
    has_event_date = sum(1 for r in rows if (r.get("event_start_date") or "").strip())
    has_location = sum(1 for r in rows if (r.get("location") or "").strip())
    ctype = Counter((r.get("consultation_type") or "(blank)") for r in rows)
    basis = Counter((r.get("event_date_basis") or "(blank)") for r in rows)
    channel = Counter((r.get("channel") or "(blank)") for r in rows)

    docs_with_event_date = len({
        (r.get("fr_document_number") or "").strip()
        for r in rows if (r.get("event_start_date") or "").strip()})

    # Does the customer export carry a document-level count column?
    with open(FR_CUST, encoding="utf-8", newline="") as fh:
        fr_hdr = next(csv.reader(fh))
    doc_count_col = [c for c in fr_hdr
                     if "rows_per" in c or "n_tribes" in c or "n_parties" in c
                     or "document_row_count" in c]

    with open(REVIEW / "fr_document_fanout_1154.csv", "w",
              encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["fr_document_number", "rows", "distinct_tribe_id",
                    "distinct_participant_name", "event_start_date_populated",
                    "federal_register_citation", "topic"])
        for k, v in sorted(by_doc.items(), key=lambda kv: -len(kv[1])):
            w.writerow([
                k, len(v),
                len({(r.get("tribe_id") or "").strip() for r in v}),
                len({(r.get("participant_name_as_published") or "").strip() for r in v}),
                sum(1 for r in v if (r.get("event_start_date") or "").strip()),
                (v[0].get("federal_register_citation") or ""),
                (v[0].get("topic") or "")[:120],
            ])

    return {
        "file": str(EVENTS.relative_to(ROOT)).replace("\\", "/"),
        "rows_total_full_census": n,
        "distinct_fr_documents": len(by_doc),
        "rows_per_document": {
            "max": sizes[0],
            "p99": sizes[max(0, int(len(sizes) * 0.01))],
            "p95": sizes[max(0, int(len(sizes) * 0.05))],
            "median": statistics.median(sizes),
            "mean": round(n / len(by_doc), 3),
            "min": sizes[-1],
            "documents_with_exactly_one_row": sum(1 for s in sizes if s == 1),
            "documents_with_more_than_one_row": sum(1 for s in sizes if s > 1),
            "rows_sitting_on_a_multi_row_document": sum(s for s in sizes if s > 1),
        },
        "ten_biggest_documents": [
            {"fr_document_number": k, "rows": len(v),
             "distinct_tribe_id": len({(r.get("tribe_id") or "").strip() for r in v}),
             "distinct_participant": len({(r.get("participant_name_as_published") or "").strip() for r in v}),
             "citation": v[0].get("federal_register_citation", ""),
             "topic": (v[0].get("topic") or "")[:120]}
            for k, v in biggest],
        "grain_test_is_it_one_row_per_party": {
            "multi_row_documents": len(docs_multi),
            "party_key_unique_within_document": doc_party_unique,
            "party_key_repeats_within_document": doc_party_dupe,
            "repeat_examples": dupe_examples,
        },
        "grain_test_do_event_columns_vary_within_a_document": {
            "multi_row_documents": len(docs_multi),
            "event_columns_identical_across_all_rows": docs_event_identical,
            "event_columns_vary": docs_event_varies,
            "which_columns_vary": dict(varying_cols.most_common(12)),
            "non_party_columns_tested": len(non_party),
        },
        "conceptual_test_event_vs_notice": {
            "rows_with_event_start_date": has_event_date,
            "rows_without_event_start_date": n - has_event_date,
            "rows_with_location": has_location,
            "distinct_documents_with_any_event_date": docs_with_event_date,
            "event_date_basis": dict(basis.most_common()),
            "consultation_type": dict(ctype.most_common(15)),
            "channel": dict(channel.most_common(10)),
        },
        "customer_export_has_document_level_count_column": doc_count_col or False,
        "fanout_csv": "review/fr_document_fanout_1154.csv",
    }


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if mode != "report":
        print("usage: py -3 code/1154_nagpra_fr_grain_audit.py report")
        return 2
    for p in (NAGPRA, EVENTS, FR_CUST):
        if not p.exists():
            print(f"UNMEASURED - missing input {p}")
            return 1

    out = {
        "measured_date": "2026-09-02",
        "script": "code/1154_nagpra_fr_grain_audit.py",
        "sampling": "none - every figure is a full census of the named file",
        "nagpra_institution_parsing": audit_nagpra(),
        "federal_register_consultation_grain": audit_events(),
    }
    OUT_JSON.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    print(f"\nwrote {OUT_JSON.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
