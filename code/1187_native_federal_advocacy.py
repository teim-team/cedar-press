#!/usr/bin/env python3
"""
Cedar Press - 1187: Native Federal Advocacy & Engagement, 2025-2026.

    py -3 code/1187_native_federal_advocacy.py            # report
    py -3 code/1187_native_federal_advocacy.py build
    py -3 code/1187_native_federal_advocacy.py verify
    py -3 code/1187_native_federal_advocacy.py selftest

WHY THE NAME CHANGED
--------------------
Reviewer, 2026-09-04: *"'Lobbying' alone would be misleading because formal
tribal consultations, public comments and official tribal-government
communications are not necessarily lobbying under the LDA."*

That is a legal point, not a presentational one. A tribe attending a federal
consultation is exercising a government-to-government relationship; calling it
lobbying misdescribes what happened and could misdescribe the tribe's legal
posture. So the collection is advocacy AND engagement, and `activity_type`
carries the distinction on every row.

ONE FLAT TABLE, NOT FIVE
------------------------
Five sources, one grain: ONE ROW PER DOCUMENTED ACTIVITY PER ENTITY.

    registered_lobbying            LDA quarterly filings, superseded excluded
    tribal_consultation            consultation events + Section 106
    agency_meeting                 Federal Register ex parte notices
    regulatory_comment             regulations.gov comments
    nonprofit_lobbying_disclosure  IRS 990 Schedule C

If twenty tribes attend one consultation there are twenty rows sharing one
`activity_id` - the entity is what makes a row, and the event is what makes
the id. That is why the previous 222-row client summary could be retired:
client totals, annual spend and meeting counts are all derivable from this,
and none of them needed to be stored.

TWO ACTIVITY TYPES ARE ABSENT AND SAY SO
----------------------------------------
`congressional_testimony` and `formal_letter` are in the specified vocabulary
and Cedar holds no source for either. They are declared in ACTIVITY_TYPES and
produce zero rows, rather than being quietly dropped from the vocabulary - a
category that exists and is empty is a known gap; a category deleted from the
schema is an invisible one.

AMOUNTS ARE NEVER INVENTED
--------------------------
`amount_type` exists so unlike figures cannot be added together. An LDA income
figure, an LDA expense figure and an IRS Schedule C expenditure measure
different things over different periods. A consultation, meeting or comment
gets NO amount, because no such source reports one - the field is blank, not
zero, because zero is a claim.
"""
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cedar_publication import translate_neid_values, apply_official_names

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
CUSTOMER = ROOT / "dist" / "customer"
NAMES = ROOT / "data" / "spine" / "cedar_entity_names.csv"
OUT = CUSTOMER / "native_federal_advocacy_2025_2026.csv"
TODAY = date.today().isoformat()

csv.field_size_limit(10 ** 9)
WINDOW = ("2025", "2026")

COLUMNS = ("cedar_uid", "name", "entity_type", "activity_id", "activity_type",
           "activity_date", "year", "quarter", "reported_party_name",
           "representative_or_registrant", "federal_entity", "topic",
           "reported_amount_usd", "amount_type", "source_type",
           "source_record_id", "source_url", "notes")

#: The full vocabulary. Two have no source yet and are declared anyway.
ACTIVITY_TYPES = ("registered_lobbying", "tribal_consultation",
                  "agency_meeting", "regulatory_comment",
                  "congressional_testimony", "formal_letter",
                  "nonprofit_lobbying_disclosure")
NO_SOURCE_YET = ("congressional_testimony", "formal_letter")

AMOUNT_TYPES = ("lobbying_income", "lobbying_expense",
                "irs_lobbying_expenditure", "")


def _year(v: str) -> str:
    v = (v or "").strip()
    return v[:4] if len(v) >= 4 and v[:4].isdigit() else ""


def _q(d: str) -> str:
    d = (d or "").strip()
    if len(d) >= 7 and d[5:7].isdigit():
        return "Q%d" % ((int(d[5:7]) - 1) // 3 + 1)
    return ""


def _read(p: Path):
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def entity_names():
    out = {}
    for r in _read(NAMES):
        out[r["cedar_uid"]] = (r.get("name", ""), r.get("entity_class", ""))
    return out


def _row(names, uid, atype, aid, adate, party, rep, fed, topic,
         amount, amount_type, stype, srec, surl, notes):
    uid = (uid or "").strip()
    nm, et = names.get(uid, ("", "")) if uid else ("", "")
    return {
        "cedar_uid": uid, "name": nm, "entity_type": et,
        "activity_id": aid, "activity_type": atype,
        "activity_date": adate, "year": _year(adate), "quarter": _q(adate),
        "reported_party_name": (party or "").strip(),
        "representative_or_registrant": (rep or "").strip(),
        "federal_entity": (fed or "").strip(),
        "topic": (topic or "").strip()[:300],
        "reported_amount_usd": amount, "amount_type": amount_type,
        "source_type": stype, "source_record_id": (srec or "").strip(),
        "source_url": (surl or "").strip(), "notes": (notes or "").strip()[:300],
    }


def collect(names):
    rows, counts = [], {}

    # 1. registered lobbying. SUPERSEDED FILINGS ARE REPLACED, NOT REPEATED -
    #    the reviewer's rule, and the reason the old file needed an
    #    n_superseded_filings column to warn about its own duplicates.
    seen_group = {}
    lob = []
    for r in _read(CUSTOMER / "lobbying.csv"):
        if _year(r.get("filing_year")) not in WINDOW:
            continue
        g = (r.get("supersession_group_id") or "").strip()
        key = g or (r.get("filing_uuid") or "").strip()
        prev = seen_group.get(key)
        if prev is None or (r.get("dt_posted") or "") > (prev.get("dt_posted") or ""):
            seen_group[key] = r
    for r in seen_group.values():
        inc, exp = (r.get("income_usd") or "").strip(), (r.get("expenses_usd") or "").strip()
        amt, atype = ("", "")
        if inc and inc not in ("0", "0.0", "0.00"):
            amt, atype = inc, "lobbying_income"
        elif exp and exp not in ("0", "0.0", "0.00"):
            amt, atype = exp, "lobbying_expense"
        ft = (r.get("filing_type_display") or r.get("filing_type") or "").strip()
        lob.append(_row(names, r.get("cedar_uid"), "registered_lobbying",
                        (r.get("filing_uuid") or "").strip(),
                        (r.get("dt_posted") or "")[:10],
                        r.get("client_name"), r.get("registrant_name"),
                        r.get("government_entities"),
                        r.get("specific_issues_text"),
                        amt, atype, "LDA quarterly filing",
                        r.get("filing_uuid"), r.get("filing_url"),
                        ("no-activity filing - does NOT document lobbying activity"
                         if "no activity" in ft.lower() else ft)))
    rows += lob
    counts["registered_lobbying"] = len(lob)

    # 2. tribal consultations. tribe_id here is a RETIRED CICD identifier, so
    #    the row goes through the same translator every other writer uses.
    con = []
    for src, label in ((CLEAN / "consultation_events.csv", "consultation event"),
                       (CLEAN / "section_106_consultation_events.csv",
                        "Section 106 consultation")):
        for r in _read(src):
            d = (r.get("event_start_date") or r.get("notice_date") or "").strip()
            if _year(d) not in WINDOW:
                continue
            translate_neid_values(r)
            apply_official_names(r)
            uid = (r.get("cedar_uid") or r.get("tribe_id") or "").strip()
            if not uid.startswith("CE-"):
                uid = ""
            con.append(_row(names, uid, "tribal_consultation",
                            (r.get("consultation_event_id")
                             or r.get("section_106_event_id") or "").strip(),
                            d, r.get("tribe_name") or r.get("participant_name_as_published"),
                            "", r.get("agency"), r.get("topic")
                            or r.get("consultation_type"),
                            "", "", label,
                            r.get("consultation_event_id"), "",
                            r.get("participant_role") or ""))
    rows += con
    counts["tribal_consultation"] = len(con)

    # 3. agency meetings - Federal Register ex parte notices
    ex = []
    for r in _read(CLEAN / "fr_ex_parte_parties.csv"):
        d = (r.get("publication_date") or "").strip()
        if _year(d) not in WINDOW:
            continue
        apply_official_names(r)
        ex.append(_row(names, r.get("resolved_native_entity_id"),
                       "agency_meeting",
                       (r.get("fr_ex_parte_party_id") or "").strip(), d,
                       r.get("party_as_printed"), "", r.get("agency_names"),
                       r.get("docket_ids_as_printed"), "", "",
                       "Federal Register ex parte notice",
                       r.get("document_number"), "",
                       r.get("position_relative_to_native_interest") or ""))
    rows += ex
    counts["agency_meeting"] = len(ex)

    # 4. regulatory comments
    com = []
    for r in _read(CLEAN / "regulations_gov_comments.csv"):
        d = (r.get("posted_date") or "").strip()
        if _year(d) not in WINDOW:
            continue
        if (r.get("withdrawn") or "").strip().lower() in ("1", "true", "yes"):
            continue
        # cedar_entity_id here holds a RETIRED CICD NEID, not a CE- uid.
        # Testing for a "CE-" prefix before translating rejected all 892 rows
        # and reported the source as entirely unkeyed - a silent zero, not an
        # error. Every one of them is attribution_class TITLE_NAMES_THE_ENTITY,
        # so they were resolved all along.
        translate_neid_values(r)
        uid = (r.get("cedar_entity_id") or "").strip()
        com.append(_row(names, uid if uid.startswith("CE-") else "",
                        "regulatory_comment",
                        (r.get("comment_id") or "").strip(), d,
                        r.get("cedar_entity_name") or r.get("query_name"),
                        "", r.get("agency_id"), r.get("title"), "", "",
                        "regulations.gov comment", r.get("comment_id"),
                        "https://www.regulations.gov/comment/%s"
                        % (r.get("comment_id") or "").strip(), ""))
    rows += com
    counts["regulatory_comment"] = len(com)

    # 5. IRS Schedule C. A DIFFERENT MEASURE - a tax-year expenditure, not a
    #    quarterly LDA figure - which is exactly what amount_type protects.
    sc = []
    for r in _read(CLEAN / "nonprofit_schedule_c_lobbying.csv"):
        ty = (r.get("tax_year") or "").strip()
        if ty not in WINDOW:
            continue
        # TERM MATCHES ARE NOT DOCUMENTED NATIVE ADVOCACY. 2,052 of the 2,312
        # rows in window are inclusion_basis=term_match / record_scope=
        # unresolved: organizations whose NAME contains a token like "Indian",
        # matched and never resolved. They include INDIAN ROCKS ROTARY
        # FOUNDATION INC, a Florida Rotary club, and CAN AM CROWN, a sled-dog
        # race. Publishing them in a Native advocacy dataset would repeat the
        # shared-word failure this project keeps having to undo, so only
        # named_entity rows are carried.
        if (r.get("inclusion_basis") or "").strip() != "named_entity":
            continue
        translate_neid_values(r)
        uid = (r.get("cedar_entity_id") or "").strip()
        amt = ""
        for c in ("total_lobbying_expenditures", "lobbying_expenditures",
                  "total_lobbying_usd"):
            if (r.get(c) or "").strip():
                amt = r[c].strip()
                break
        sc.append(_row(names, uid if uid.startswith("CE-") else "",
                       "nonprofit_lobbying_disclosure",
                       (r.get("schedule_c_row_id") or "").strip(),
                       "%s-12-31" % ty,
                       r.get("taxpayer_name_as_filed"), "", "IRS", "",
                       amt, "irs_lobbying_expenditure" if amt else "",
                       "IRS 990 Schedule C", r.get("object_id"), "",
                       "tax-year figure; NOT comparable with LDA quarterly "
                       "amounts"))
    rows += sc
    counts["nonprofit_lobbying_disclosure"] = len(sc)

    for t in NO_SOURCE_YET:
        counts[t] = 0
    return rows, counts


def build(apply: bool = False) -> int:
    names = entity_names()
    rows, counts = collect(names)
    keyed = sum(1 for r in rows if r["cedar_uid"])
    print("  1187 Native Federal Advocacy & Engagement   %s"
          % ("BUILD" if apply else "REPORT (writes nothing)"))
    print("    rows (one per activity per entity): %d" % len(rows))
    for t in ACTIVITY_TYPES:
        n = counts.get(t, 0)
        note = "   <- NO SOURCE IN CEDAR YET" if t in NO_SOURCE_YET else ""
        print("      %-32s %7d%s" % (t, n, note))
    print()
    print("    with a cedar_uid : %d (%.1f%%)"
          % (keyed, 100.0 * keyed / len(rows) if rows else 0))
    print("    left blank       : %d" % (len(rows) - keyed))
    amt = sum(1 for r in rows if r["reported_amount_usd"])
    print("    carrying an amount: %d  (amount_type set on all of them: %s)"
          % (amt, all(r["amount_type"] for r in rows if r["reported_amount_usd"])))
    if apply:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(COLUMNS))
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in COLUMNS})
        print()
        print("    wrote %s  (%d columns)" % (OUT.relative_to(ROOT), len(COLUMNS)))
    return 0


def verify() -> int:
    if not OUT.exists():
        print("  NOT BUILT: %s" % OUT)
        return 1
    rows = _read(OUT)
    ok = True
    bad_t = sorted({r["activity_type"] for r in rows} - set(ACTIVITY_TYPES))
    bad_a = sorted({r["amount_type"] for r in rows} - set(AMOUNT_TYPES))
    amt_no_type = [r for r in rows if r["reported_amount_usd"] and not r["amount_type"]]
    no_amt_types = ("tribal_consultation", "agency_meeting", "regulatory_comment")
    invented = [r for r in rows if r["activity_type"] in no_amt_types
                and r["reported_amount_usd"]]
    import re as _re
    pat = _re.compile(r"(TRBF|AKNF|ANVC|ANRC|CNSF|SGVF|NHO|UIO|BIE|CDFI|TRBS|ITO"
                      r"|TCU|CNSS)-[A-Z0-9]{6}-[A-Z0-9]{2}")
    neid = sum(1 for r in rows for v in r.values() if v and pat.search(v))
    print("  rows                          : %d" % len(rows))
    print("  activity_type off-vocabulary  : %s" % (bad_t or "none"))
    print("  amount_type off-vocabulary    : %s" % (bad_a or "none"))
    print("  amount with no amount_type    : %d" % len(amt_no_type))
    print("  amount invented on an event   : %d" % len(invented))
    print("  retired CICD identifiers      : %d" % neid)
    if bad_t or bad_a or amt_no_type or invented or neid:
        ok = False
    print("  OK" if ok else "  FAIL")
    return 0 if ok else 1


def selftest() -> int:
    ok = True
    if set(NO_SOURCE_YET) - set(ACTIVITY_TYPES):
        print("  FAIL a no-source type is not in the vocabulary"); ok = False
    else:
        print("  the 2 sourceless activity types are declared, not deleted")
    if _q("2026-04-15") != "Q2" or _q("2026-01-01") != "Q1" or _q("") != "":
        print("  FAIL quarter derivation"); ok = False
    else:
        print("  quarter derives from the date, never stored independently")
    print("  selftest %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "build":
        raise SystemExit(build(apply=True))
    if cmd == "verify":
        raise SystemExit(verify())
    if cmd == "selftest":
        raise SystemExit(selftest())
    raise SystemExit(build(apply=False))
