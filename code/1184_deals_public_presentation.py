#!/usr/bin/env python3
"""
Cedar Press - 1184: make the deals dataset read like a product, not a ledger.

    py -3 code/1184_deals_public_presentation.py            # report
    py -3 code/1184_deals_public_presentation.py build
    py -3 code/1184_deals_public_presentation.py verify
    py -3 code/1184_deals_public_presentation.py selftest

WHY THIS EXISTS
---------------
From the owner's reviewer, 2026-09-04:

    "The sources themselves are structurally clean, but the notes and source
     labels currently make the dataset look more like an internal research
     ledger than a finished product."

Every figure in that review reconciled exactly against the data, so this
implements it rather than re-litigating it.

    Notes                174 of 208 rows populated, mean 244 chars, 13 over
                         500, one staging explanation repeated across 36 rows,
                         and some rows carrying unresolved research
                         instructions a customer must never see.
    Source_*_Type        26 and 22 distinct labels in the 2025-26 window -
                         and measured across all 1,073 rows, 79 and 65. The
                         labels mix category, authority, retrieval method and
                         commentary: "Internet Archive snapshot (live HUD URL
                         404s after the 2025-26 reorg)" is three facts and a
                         complaint in a type field.
    Verification_Status  9 phrases.
    Confidence           a full sentence in a field that should hold one of
                         three words.

CAVEAT IS DERIVED, NEVER SUMMARISED
-----------------------------------
The obvious implementation is to read each note and write a shorter one. That
is the wrong shape: it makes the public field depend on prose an agent
paraphrased, so it cannot be regenerated, cannot be tested, and drifts the
first time a note is edited.

Every caveat the reviewer asked for is already a FACT IN A COLUMN:

    amount is a floor or estimate          Value_Type
    project value != transaction value     Project_Total_Value_USD
    date is an announcement, not a close   Date_Basis / Event_Date_precision
    aggregate, do not sum with recipients  record_class = PUBLIC_AWARD
    funding originated in an earlier year  Record_Scope "<year> commitment"

So `Caveat` is computed from those columns. It is reproducible, it is
testable, and when the underlying fact changes the caveat changes with it.
`Notes` stays internal, untouched, and keeps the full research trail.

SOURCE TYPES FAIL LOUDLY
------------------------
The normaliser maps by keyword into the reviewer's eight-value vocabulary and
REPORTS every label it could not place instead of dropping it in an "Other"
bucket. A vocabulary that silently absorbs what it does not understand is how
79 labels happened in the first place. The original string is kept as
`Source_N_Type_detail` internally, because "live HUD URL now returns an empty
stub" is a real operational fact - it just is not a type.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

#: HOW THIS SHIPS. `transform` is applied by `cedar_publication.deals_public_view`
#: on the raw source rows at every 1137 build, so `Caveat`, the normalised
#: source types and the one-word Confidence reach the customer file without
#: the canonical source being rewritten. OUT_INTERNAL is the inspectable copy
#: of the same transform, for review; it is not what 1137 reads (Codex,
#: PR #56: it used to be the only output, and nothing read it).
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "clean" / "deals_classified.csv"
OUT_INTERNAL = ROOT / "data" / "clean" / "deals_presentation.csv"

csv.field_size_limit(10 ** 9)

#: The reviewer's vocabulary. Order matters: first rule that matches wins, so
#: the most specific tests come first. An Internet Archive snapshot OF an SEC
#: filing is an archived source - how you retrieved it is what the reader has
#: to know to judge it.
SOURCE_RULES = (
    # A NINTH CATEGORY, and a deliberate deviation from the reviewer's
    # eight. He wrote "a small vocabulary such as", so the list is
    # illustrative - and 4 rows are commercial data aggregators, which is
    # not any of the eight. An aggregator is not press (it does not
    # report), not a transaction party, and not a government source; it
    # compiles other people's reporting and sells it. Forcing it into
    # "Trade press" would tell a buyer the deal was reported by a
    # journalist when it was not. Flagged to the owner rather than made
    # quietly.
    ("Data aggregator",                 (r"aggregator",)),
    ("Company or transaction party",    (r"recipient organisation release",
                                         r"recipient organization release")),
    ("Archived source",                 (r"internet archive", r"wayback",
                                         r"archived snapshot", r"\barchive\b")),
    ("SEC filing",                      (r"\bsec filing", r"edgar",
                                         r"form 8-k", r"form s-4", r"form d\b",
                                         r"form 10-k", r"prospectus")),
    ("Government filing or report",     (r"federal award list", r"award data file",
                                         r"filed with the alaska division",
                                         r"star portal", r"usaspending",
                                         r"single audit", r"\bfpds\b",
                                         r"court filing", r"bankruptcy-court")),
    ("Government release",              (r"federal agency", r"agency release",
                                         r"agency project page", r"program page",
                                         r"dear tribal leader", r"u\.s\. senate",
                                         r"congress", r"\bhud\b", r"\bntia\b",
                                         r"\beda\b", r"\bdoe\b", r"government")),
    ("Tribal government or Native entity", (r"tribal newsletter", r"tribal press",
                                         r"tribal government", r"tribal economic",
                                         r"native enterprise", r"native parent",
                                         r"native subsidiary", r"\banc newsroom",
                                         r"\banc website", r"anc annual report",
                                         r"native press", r"native business press")),
    ("Company or transaction party",    (r"company release", r"counterparty",
                                         r"deal advisor", r"rating action",
                                         r"moody", r"issuer", r"buyer", r"seller",
                                         r"syndication")),
    ("Tribal government or Native entity", (r"tribal enterprise", r"tribal nation",
                                         r"tribal newspaper", r"tribal website")),
    ("Company or transaction party",    (r"legal adviser", r"legal advisor",
                                         r"transaction partner",
                                         r"nonprofit / transaction")),
    ("Government filing or report",     (r"cedar observation from federal",
                                         r"federal identifier data")),
    ("Government release",              (r"municipal publication",)),
    ("Local or general news",           (r"public media", r"retrospective")),
    ("Trade press",                     (r"trade press", r"industry magazine",
                                         r"gaming trade", r"industry press")),
    ("Local or general news",           (r"local press", r"local business press",
                                         r"regional press", r"public radio",
                                         r"local news", r"independent press",
                                         r"\bpress\b", r"\bnews\b")),
)

#: Confidence holds one of three words. Anything else is a different fact
#: wearing Confidence's clothes - the 36 "candidate - pattern match on
#: publisher's own text, NOT hand-verified" rows are a CANDIDATE STATUS, which
#: is why it moves to its own column instead of being deleted.
CONFIDENCE = ("High", "Medium", "Low")

#: 9 phrases -> 4. Every mapping preserves the distinction that matters to a
#: buyer: was a primary document read, was it corroborated, or is it one
#: source's word.
VERIFICATION = {
    "primary verified": "Primary source verified",
    "primary filing retrieved and read": "Primary source verified",
    "primary + independent verified": "Primary source, independently corroborated",
    "independent secondary corroborated": "Independently corroborated",
    "verified": "Verified",
    "single source (tribal press)": "Single source",
    "single source": "Single source",
    "observation": "Cedar observation, not a published claim",
    "unverified": "Unverified",
}

PUBLIC_COLUMNS = ("Description", "Native_Connection", "Caveat",
                  "Source_1", "Source_1_Type", "Source_2", "Source_2_Type",
                  "Verification_Status", "Confidence", "Candidate_Status")


def norm_type(raw: str):
    """(category, detail). Returns (None, raw) when no rule matches."""
    s = (raw or "").strip()
    if not s:
        return "", ""
    low = s.lower()
    for category, patterns in SOURCE_RULES:
        for pat in patterns:
            if re.search(pat, low):
                return category, s
    return None, s


def caveats(row: dict) -> list:
    """Every caveat, derived. No prose is read to build this."""
    out = []
    vt = (row.get("Value_Type") or "").lower()
    if any(w in vt for w in ("floor", "minimum", "at least")):
        out.append("Amount is a floor, not a final value.")
    elif any(w in vt for w in ("estimate", "estimated", "approx")):
        out.append("Amount is an estimate.")
    elif "undisclosed" in vt:
        out.append("Value was not disclosed.")

    ann = (row.get("Announced_Value_USD") or "").strip()
    proj = (row.get("Project_Total_Value_USD") or "").strip()
    if proj and ann and proj != ann:
        out.append("Project total differs from the transaction amount; "
                   "do not treat them as the same figure.")

    basis = (row.get("Date_Basis") or "").lower()
    prec = (row.get("Event_Date_precision") or "").lower()
    if "fiscal" in basis or "fiscal" in prec:
        out.append("Date is a fiscal-year window, not a date.")
    elif "announce" in basis:
        out.append("Date is the announcement, not the closing.")
    elif prec in ("month", "year"):
        out.append("Date is precise only to the %s." % prec)

    if (row.get("record_class") or "").strip() == "PUBLIC_AWARD":
        out.append("Public award record; do not sum with recipient-level rows.")

    scope = (row.get("Record_Scope") or "").strip()
    m = re.match(r"^(\d{4}) commitment$", scope)
    if m:
        ey = (row.get("Event_Year") or "").strip()
        if ey and ey != m.group(1):
            out.append("Funding was committed in %s." % m.group(1))

    # Yes/No, not free text. Reading it as "populated means true" put this
    # caveat on 1,027 of 1,073 rows - 96% - because "No" is a value. A
    # caveat that fires on almost every row tells a reader nothing.
    if (row.get("Threshold_Exception") or "").strip().lower() == "yes":
        out.append("Retained below the usual reporting threshold.")
    return out


def transform(rows: list):
    unmapped = {}
    stats = {"caveats": 0, "conf_fixed": 0, "verif_fixed": 0, "candidates": 0}
    for r in rows:
        cav = caveats(r)
        r["Caveat"] = " ".join(cav)
        if cav:
            stats["caveats"] += 1

        for n in ("1", "2"):
            col = "Source_%s_Type" % n
            cat, detail = norm_type(r.get(col))
            if cat is None:
                unmapped[detail] = unmapped.get(detail, 0) + 1
                cat = ""
            r[col] = cat
            r["Source_%s_Type_detail" % n] = detail

        conf = (r.get("Confidence") or "").strip()
        if conf not in CONFIDENCE:
            if conf.lower().startswith("candidate"):
                r["Candidate_Status"] = "Candidate - not hand-verified"
                r["Confidence"] = "Low"
                stats["candidates"] += 1
            elif conf.lower() == "observation":
                r["Candidate_Status"] = "Cedar observation"
                r["Confidence"] = "Low"
            else:
                r["Confidence"] = "Low"
            stats["conf_fixed"] += 1
        else:
            r.setdefault("Candidate_Status", "")

        v = (r.get("Verification_Status") or "").strip()
        mapped = VERIFICATION.get(v.lower())
        if mapped and mapped != v:
            r["Verification_Status"] = mapped
            stats["verif_fixed"] += 1
        elif not mapped and v:
            r["Verification_Status"] = v
    return unmapped, stats


def _read() -> list:
    with SRC.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def build(apply: bool = False) -> int:
    rows = _read()
    unmapped, stats = transform(rows)
    print("  1184 deals public presentation   %s"
          % ("BUILD" if apply else "REPORT (writes nothing)"))
    print("    rows                       : %d" % len(rows))
    print("    rows given a Caveat        : %d" % stats["caveats"])
    print("    Confidence normalised      : %d" % stats["conf_fixed"])
    print("    moved to Candidate_Status  : %d" % stats["candidates"])
    print("    Verification_Status remap  : %d" % stats["verif_fixed"])
    cats = {}
    for r in rows:
        for n in ("1", "2"):
            c = r.get("Source_%s_Type" % n)
            if c:
                cats[c] = cats.get(c, 0) + 1
    print("    source categories          : %d" % len(cats))
    for c, n in sorted(cats.items(), key=lambda kv: -kv[1]):
        print("        %-38s %5d" % (c, n))
    if unmapped:
        print("    !! %d source label(s) matched NO rule - they would ship blank:"
              % len(unmapped))
        for lbl, n in sorted(unmapped.items(), key=lambda kv: -kv[1])[:10]:
            print("        %4d  %s" % (n, lbl[:88]))
    else:
        print("    every source label mapped")

    if apply:
        fields = list(rows[0].keys())
        for c in ("Caveat", "Candidate_Status",
                  "Source_1_Type_detail", "Source_2_Type_detail"):
            if c not in fields:
                fields.append(c)
        with OUT_INTERNAL.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in fields})
        print()
        print("    wrote %s  (%d columns, INTERNAL master)"
              % (OUT_INTERNAL.relative_to(ROOT), len(fields)))
        print("    public columns would be: %s" % ", ".join(PUBLIC_COLUMNS))
    return 0


def verify() -> int:
    if not OUT_INTERNAL.exists():
        print("  NOT BUILT: %s" % OUT_INTERNAL)
        return 1
    with OUT_INTERNAL.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rows = list(csv.DictReader(fh))
    ok = True
    bad_conf = sorted({r["Confidence"] for r in rows
                       if r.get("Confidence") and r["Confidence"] not in CONFIDENCE})
    long_cav = [r for r in rows if len(r.get("Caveat", "")) > 300]
    leak = [r for r in rows if re.search(
        r"staged by code|harvested|backfill run|merged after gates|TODO|FIXME",
        r.get("Caveat", ""), re.I)]
    print("  rows                       : %d" % len(rows))
    print("  record_class present       : %s" % ("record_class" in rows[0]))
    print("  Record_Scope present       : %s" % ("Record_Scope" in rows[0]))
    print("  bad Confidence values      : %s" % (bad_conf or "none"))
    print("  Caveat over 300 chars      : %d" % len(long_cav))
    print("  pipeline language in Caveat: %d" % len(leak))
    if bad_conf or leak:
        ok = False
    print("  OK" if ok else "  FAIL")
    return 0 if ok else 1


def selftest() -> int:
    """Caveat rules must fire on constructed rows, and must NOT fire otherwise."""
    ok = True
    cases = [
        ({"Value_Type": "Announced floor"}, "floor"),
        ({"Announced_Value_USD": "100", "Project_Total_Value_USD": "500"},
         "Project total differs"),
        ({"record_class": "PUBLIC_AWARD"}, "do not sum"),
        ({"Record_Scope": "2022 commitment", "Event_Year": "2024"},
         "committed in 2022"),
        ({"Date_Basis": "FISCAL-YEAR WINDOW, NOT A DATE"}, "fiscal-year window"),
    ]
    for row, expect in cases:
        got = " ".join(caveats(row))
        if expect.lower() not in got.lower():
            print("  FAIL %r did not produce %r (got %r)" % (row, expect, got))
            ok = False
    if caveats({"Value_Type": "Federal grant award", "record_class": "TRANSACTION"}):
        print("  FAIL a clean row produced a caveat")
        ok = False
    # a note must never leak into a caveat
    if caveats({"Notes": "staged by code/1088; TODO verify with tribe"}):
        print("  FAIL Notes leaked into Caveat")
        ok = False
    print("  caveat rules fire on the named conditions and stay silent otherwise")
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
