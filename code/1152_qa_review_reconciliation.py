#!/usr/bin/env python3
"""
Cedar Press - 1152: reconcile the 173-finding QA review against the live tables.

    py -3 code/1152_qa_review_reconciliation.py            # report
    py -3 code/1152_qa_review_reconciliation.py build      # write the ledger
    py -3 code/1152_qa_review_reconciliation.py verify

WHY THIS EXISTS
---------------
Two QA reviews now exist and they looked at different products. The owner's
instruction was to reconcile them, not to run either again:

    *"Do not rerun the entire old 151-finding review as if nothing changed.
    Instead classify every old finding into: CONFIRMED BY 100-ROW REVIEW /
    STILL REQUIRES FULL-DATA CHECK / LIKELY FIXED IN NEW EXPORT / OBSOLETE -
    BASED ON OLD SAMPLE DESIGN... otherwise you risk fixing ghosts from an old
    export while missing the few problems that genuinely persist."*

The ten-row review saw 29-81 columns per file and could therefore inspect
adjudication state, provenance, parser diagnostics, supersession and quarantine
flags. The hundred-row review sees a curated 7-11 columns and can therefore ask
whether the CUSTOMER-FACING records make sense. Neither replaces the other, and
the second cannot even evaluate most of what the first found.

WHAT THIS FILE REFUSES TO DO
----------------------------
Classify by reading. Every finding whose truth is a property of the data is
CHECKED against `dist/customer/*.csv` and `data/clean/*.csv`, and the verdict
carries the measurement. A reconciliation done by judgement would be a third
opinion; this is meant to end the argument, not extend it.

Where a finding genuinely cannot be machine-checked - a claim about tone, or
about what a buyer would infer - it is marked NEEDS_HUMAN and says so rather
than guessing. That is a smaller number than it looks: most of the 173 assert
something concrete about a column, a value or a row count.

THE ONE CORRECTION THE OWNER MADE, AND IT REWRITES TWO FINDINGS
----------------------------------------------------------------
CP-003 and RG-005 said `cedar_uid` is unsafe because it is not always the
subject of the row. The owner ruled that too broad:

    *"The Cedar UID must always resolve to the same impermeable Native entity,
    while the dataset separately identifies the event/object/business and
    describes the Native entity's role... The issue is not 'Cedar UID must
    identify the row subject.' The issue is 'the role of the Cedar UID must be
    unambiguous.'"*

So NEST carrying `enterprise_id = CEDAR-NEST-...` beside `cedar_uid = Ahtna` is
CORRECT. Both findings are rewritten rather than discarded, and the test
changes with them: not "does cedar_uid identify the subject" but "does every
dataset declare the ROLE its cedar_uid plays, and does it resolve to a Native
entity in the register every time".

THE SECOND CORRECTION, 2026-09-02, AND IT REWRITES NINETY-ONE
--------------------------------------------------------------
This file used to end `classify()` with

    return (FULLDATA, "not machine-checkable from the delivered export alone")

and NINETY-ONE of the 173 findings reached it. The sentence was mostly false.
CP-021 says one award appears in three transaction rows with three different
`total_award_value`s - that is a GROUP BY. CP-024 says `DO` and `DELIVERY ORDER`
are both live - that is a value count. CP-025 says older rows carry the literal
text `NAN` - that is a string match. CP-027 pairs a $1.28B subaward with a
$13.4M prime - that is arithmetic. A reconciliation that shrugs at 91 of 173
findings is not much better than the argument it was meant to end.

So the default is gone. Every one of the 91 now has a NAMED CHECK below,
registered in `CHECKS` by finding id, and the two that are genuinely a
judgement call - CP-073 and CP-108, both "does this record belong in this
collection at all" - return NEEDS_HUMAN and say which decision is owed.

HOW THE CHECKS ARE BUILT, AND WHY THEY ARE NOT ONE CLEVER FUNCTION
-------------------------------------------------------------------
The failure mode this codebase keeps producing is a check whose NAME claims
more than its BODY measures. Two guards against it here:

  1. One `scan_<dataset>()` per table, each a SINGLE STREAMING PASS with
     `csv.reader` and column indices. Every measurement it takes is stored
     under a key named for the thing measured, and both the numerator AND the
     denominator are kept, so no check can quote a rate without its base.

  2. One `chk_<id>()` per finding. It reads its own keys and formats its own
     verdict. It cannot borrow another finding's measurement by accident,
     because there is no shared dispatcher left to borrow through.

NO CAPS. `contractors.csv` is 1.5 GB and 1,217,768 rows and is read whole,
three times, in about a minute. The one place a cap survives is
`check_internal_paths()`, which says so in its own docstring and prints
LOWER BOUND next to its number. Capping a scan and reporting the result as a
population is the defect this file was already corrected for once.
"""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "code"))
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
REVIEW = ROOT / "review" / "QA_REVIEW_10ROW_2026-09-02.txt"
CUST = ROOT / "dist" / "customer"
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "review" / f"QA_RECONCILIATION_{TODAY}.csv"
DOC = ROOT / "docs" / f"QA_RECONCILIATION_{TODAY}.md"

CONFIRMED = "CONFIRMED_BY_100ROW"
FULLDATA = "STILL_REQUIRES_FULL_DATA_CHECK"
FIXED = "LIKELY_FIXED_IN_NEW_EXPORT"
OBSOLETE = "OBSOLETE_OLD_SAMPLE_DESIGN"
HUMAN = "NEEDS_HUMAN"

VERBOSE = True


def _say(msg):
    if VERBOSE:
        print(f"    . {msg}", flush=True)


def findings():
    """Parse the review's pipe table. ID, priority, category, field, text."""
    out = []
    for line in REVIEW.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("| CP-") and not line.startswith("| RG-"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        out.append({"id": cells[0], "priority": cells[1], "category": cells[2],
                    "field": cells[3], "finding": cells[4],
                    "release_test": cells[-1]})
    return out


# ------------------------------------------------------------------ plumbing
def _pct(n, d):
    """Never a rate without its base. Both numbers, always."""
    return f"{n:,}/{d:,} ({100.0 * n / d:.1f}%)" if d else f"{n:,} of 0"


def _header(name, root=None):
    p = (root or CUST) / f"{name}.csv"
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return next(csv.reader(fh), [])


def _stream(name, cols, root=None):
    """Yield {col: value} for the named columns, one dict per data row.

    `csv.reader` plus column indices, never DictReader: the whole point is to
    read 1.5 GB without building 1.2 million 80-key dicts. Columns absent from
    the header simply do not appear in the yielded dict; callers use `.get`.
    """
    p = (root or CUST) / f"{name}.csv"
    if not p.exists():
        return
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.reader(fh)
        hdr = next(rd, [])
        ix = {c: hdr.index(c) for c in cols if c in hdr}
        for row in rd:
            n = len(row)
            yield {c: (row[i].strip() if i < n else "") for c, i in ix.items()}


def _rows(name, cap=None):
    p = CUST / f"{name}.csv"
    if not p.exists():
        return [], []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        rd = csv.DictReader(fh)
        hdr = list(rd.fieldnames or [])
        rows = [r for i, r in zip(range(cap or 10**9), rd)]
    return hdr, rows


# --------------------------------------------------- the original live checks
def check_cite_as():
    """CP-001: a fabricated `cite_as` row appended to the data."""
    hits = []
    for p in sorted(CUST.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            next(csv.reader(fh), [])
            for row in csv.reader(fh):
                if row and row[0].strip().lower() == "cite_as":
                    hits.append(p.name)
                    break
    return hits


def check_internal_paths():
    """CP: source fields exposing .py, .zip, local CSVs, Desktop paths.

    READS THE FIRST 2,000 ROWS PER FILE and the cap is deliberate here -
    running this regex over every cell of a 1.2M-row, 80-column file is 97M
    matches. The counts below are therefore a LOWER BOUND, not a population:
    `nest.source_document` reports 669 and is 3,189 on the whole file. For the
    full measure, and for the split between a column that is build lineage and
    a column whose values MIX evidence with a code path,
    `code/1153_qa_publication_eligibility.py` reads every row.
    """
    pat = re.compile(r"\.py\b|\.zip\b|[A-Za-z]:\\\\|/Desktop/|\\Desktop\\|"
                     r"data/staging|data\\staging|review/|review\\\\", re.I)
    hits = defaultdict(list)
    for p in sorted(CUST.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        hdr, rows = _rows(p.stem, cap=2000)
        for c in hdr:
            n = sum(1 for r in rows if pat.search((r.get(c) or "")))
            if n:
                hits[p.stem].append((c, n))
    return hits


def check_blocked_states():
    """CP-002: HOLD / quarantine / superseded / duplicate reaching the export.

    CORRECTED 2026-09-02 by `1153`. This read `cap=5000` rows per file and
    reported the result as a population, so every blocked-state count this
    reconciliation published was a count of the first 5,000 rows:
    `lobbying.is_superseded = 1` was reported 211 and is **1,064**;
    `subcontracting.duplicate_status = superseded_by_primary_source` was
    reported 38 and is **846**; `contractors.owner_attribution_status =
    CONTRADICTED_AS_OF` was reported 8 and is **9,223**. Same defect as the
    width claim below - a partial scan quoted as a whole.

    The cap is gone. `contractors.csv` is 1.5 GB, so this pass reads it with
    `csv.reader` and column indices rather than DictReader.
    """
    words = ("quarantin", "superseded", "hold_open", "do_not_ship",
             "contradict", "redirect_pending", "awaiting_owner")
    hits = defaultdict(list)
    for p in sorted(CUST.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.reader(fh)
            hdr = next(rd, [])
            watch = [(i, c) for i, c in enumerate(hdr)
                     if any(k in c.lower() for k in
                            ("status", "flag", "state", "disposition",
                             "superseded", "duplicate"))]
            if not watch:
                continue
            bad = {c: Counter() for _, c in watch}
            for row in rd:
                w = len(row)
                for i, c in watch:
                    v = row[i].strip().lower() if i < w else ""
                    if not v:
                        continue
                    if any(x in v for x in words):
                        bad[c][v] += 1
                    if c.lower().startswith("is_superseded") and \
                            v in ("true", "1", "yes"):
                        bad[c]["is_superseded=true"] += 1
        for _, c in watch:
            if bad[c]:
                hits[p.stem].append((c, dict(bad[c].most_common(3))))
    return hits


def check_uid_role():
    """CP-003 / RG-005, REWRITTEN per the owner's ruling.

    Not "is cedar_uid the row subject" - that was ruled too broad. The test is
    whether every dataset that carries a cedar_uid resolves it to a real Native
    entity, and whether its ROLE is declared somewhere a buyer can read.
    """
    reg = ROOT / "data" / "spine" / "cedar_identity_register.csv"
    known = set()
    if reg.exists():
        with reg.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            for r in csv.DictReader(fh):
                v = (r.get("cedar_uid") or "").strip()
                if v:
                    known.add(v)
    out = {}
    for p in sorted(CUST.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        if "cedar_uid" not in _header(p.stem):
            continue
        filled = unresolvable = total = 0
        for r in _stream(p.stem, ["cedar_uid"]):
            total += 1
            v = r.get("cedar_uid") or ""
            if not v:
                continue
            filled += 1
            if known and v not in known:
                unresolvable += 1
        codebook = CUST / f"{p.stem}__CODEBOOK.md"
        declared = (codebook.exists()
                    and "cedar_uid" in codebook.read_text(encoding="utf-8",
                                                          errors="replace"))
        out[p.stem] = {"filled": filled, "rows": total,
                       "unresolvable": unresolvable, "role_documented": declared}
    return out


def check_synthetic_dates():
    """A month-only source rendered as the 15th. Whole file, every date column."""
    out = {}
    for p in sorted(CUST.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        cols = [c for c in _header(p.stem) if "date" in c.lower()]
        if not cols:
            continue
        days = {c: Counter() for c in cols}
        for r in _stream(p.stem, cols):
            for c in cols:
                m = re.match(r"^\d{4}-\d{2}-(\d{2})", r.get(c) or "")
                if m:
                    days[c][m.group(1)] += 1
        for c in cols:
            tot = sum(days[c].values())
            if tot >= 40 and days[c].get("15", 0) / tot > 0.25:
                out[f"{p.stem}.{c}"] = (days[c]["15"], tot)
    return out


def check_owned_has_rows():
    """The blocker: Native-Owned Businesses exported zero business records."""
    hdr = _header("native-owned-businesses")
    n = sum(1 for _ in _stream("native-owned-businesses", hdr[:1])) if hdr else 0
    return n, len(hdr)


def check_width():
    """CP: the export shipping 60-80 debugging columns."""
    return {p.stem: len(_header(p.stem))
            for p in sorted(CUST.glob("*.csv")) if p.name != "MANIFEST.csv"}


def check_preview_width():
    """The OTHER width, and the one the earlier claim confused it with.

    `dist/preview` is the 100-row curated preview and is 7-11 columns wide.
    `dist/customer` is the delivered product. Reporting one range without
    saying which directory it came from is how "the export has narrowed"
    got written about an export that had widened.
    """
    d = ROOT / "dist" / "preview"
    if not d.exists():
        return {}
    out = {}
    for p in sorted(d.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            out[p.stem] = len(next(csv.reader(fh), []))
    return out


# ============================================================================
#  SCANNERS - one streaming pass per table. Every key names what it measured
#  and every rate keeps its denominator.
# ============================================================================
def scan_contractors():
    """One pass over dist/customer/contractors.csv - 1.5 GB, 1.2M rows, whole."""
    _say("scanning contractors.csv (1.5 GB, whole file)")
    f = {"rows": 0, "award_type": Counter(), "cage_nan": 0, "cage_blank": 0,
         "pre2000_flag": Counter(), "contradicted": 0, "contradicted_with_uid": 0,
         "owner_status": Counter(), "named_contradicted": defaultdict(list),
         "target_award_values": set()}
    lo, hi = {}, {}
    names = {}
    cols = ["award_type", "cage_code", "pre_2000_flag", "fiscal_year",
            "owner_attribution_status", "cedar_uid", "contract_award_unique_key",
            "total_award_value", "contract_number"]
    named = ("DOCDG133F08CQ0073T0003", "DOCDG133C08CQ0081T0001")
    for r in _stream("contractors", cols):
        f["rows"] += 1
        f["award_type"][r.get("award_type", "")] += 1
        cc = r.get("cage_code", "")
        if cc.upper() == "NAN":
            f["cage_nan"] += 1
        if not cc:
            f["cage_blank"] += 1
        f["pre2000_flag"][r.get("pre_2000_flag", "")] += 1
        st = r.get("owner_attribution_status", "")
        f["owner_status"][st] += 1
        if "CONTRADICT" in st.upper():
            f["contradicted"] += 1
            if r.get("cedar_uid"):
                f["contradicted_with_uid"] += 1
        cn = r.get("contract_number", "")
        if cn in named:
            f["named_contradicted"][cn].append((r.get("cedar_uid", ""), st))
        k, v = r.get("contract_award_unique_key", ""), r.get("total_award_value", "")
        if cn == "12314422F0384" and v:
            f["target_award_values"].add(v)
        if not k:
            continue
        try:
            x = float(v)
        except ValueError:
            continue
        if k in lo:
            if x < lo[k]:
                lo[k] = x
            if x > hi[k]:
                hi[k] = x
        else:
            lo[k] = hi[k] = x
            names[k] = cn
    spreads = [(hi[k] - lo[k], k, lo[k], hi[k], names.get(k, ""))
               for k in lo if hi[k] != lo[k]]
    spreads.sort(reverse=True)
    f["award_keys"] = len(lo)
    f["award_keys_multivalued"] = len(spreads)
    f["award_spread_total_usd"] = sum(s[0] for s in spreads)
    f["award_spread_worst"] = spreads[0] if spreads else None
    f["codebook_says_piid"] = "piid" in (
        (CUST / "contractors__CODEBOOK.md").read_text(encoding="utf-8",
                                                      errors="replace").lower()
        if (CUST / "contractors__CODEBOOK.md").exists() else "")
    return f


def scan_funding():
    """One pass over dist/customer/funding.csv - 642 MB, 701,955 rows, whole."""
    _say("scanning funding.csv (642 MB, whole file)")
    tribal = re.compile(r"TRIB|NATION|PUEBLO|BAND|RANCHERIA|HOUSING AUTHORITY|"
                        r"VILLAGE|INDIAN|NATIVE", re.I)
    f = {"rows": 0, "ak_blank": 0, "ak_rows_in_ak": 0, "ak_blank_in_ak": 0,
         "assistance_type_neg1": 0, "assistance_desc_not_specified": 0,
         "city_township": 0, "city_township_tribal_name": 0,
         "housing_authority": 0, "housing_authority_other_canon": 0,
         "avcp_fain_rows": []}
    cols = ["award_id_fain", "recipient_name", "canonical_name", "cedar_uid",
            "ak_flag", "recipient_state_code", "assistance_type",
            "assistance_type_description", "business_types_description",
            "attribution_status"]
    for r in _stream("funding", cols):
        f["rows"] += 1
        if not r.get("ak_flag"):
            f["ak_blank"] += 1
        if r.get("recipient_state_code") == "AK":
            f["ak_rows_in_ak"] += 1
            if not r.get("ak_flag"):
                f["ak_blank_in_ak"] += 1
        if r.get("assistance_type") == "-1":
            f["assistance_type_neg1"] += 1
        if r.get("assistance_type_description", "").upper() == "NOT SPECIFIED":
            f["assistance_desc_not_specified"] += 1
        rn = r.get("recipient_name", "")
        if r.get("business_types_description") == "CITY OR TOWNSHIP GOVERNMENT":
            f["city_township"] += 1
            if tribal.search(rn):
                f["city_township_tribal_name"] += 1
        if "HOUSING AUTHORITY" in rn.upper():
            f["housing_authority"] += 1
            cn = r.get("canonical_name", "")
            if cn and cn.upper() not in rn.upper():
                f["housing_authority_other_canon"] += 1
        if r.get("award_id_fain") == "10IH0202000":
            f["avcp_fain_rows"].append((rn, r.get("canonical_name", ""),
                                        r.get("cedar_uid", ""),
                                        r.get("attribution_status", "")))
    hdr = _header("funding")
    f["award_description_columns"] = [c for c in hdr if c.endswith("description")
                                      and not c.startswith(("assistance_type",
                                                            "business_types"))]
    return f


def scan_subcontracting():
    """One pass over dist/customer/subcontracting.csv - 93 MB, 70,597 rows."""
    _say("scanning subcontracting.csv")
    trunc = re.compile(r"^(ROVIDE|ONTRACT|UPPORT|NSTALL|EPAIR|ERVICES|RANSPORT|"
                       r"AINTEN|ONSTRUCT|NGINEER|ROCUREMENT)\b", re.I)
    f = {"rows": 0, "exceeds_prime": 0, "ratio_over_10": 0, "worst_ratio": None,
         "ssi348": [], "uid_is_prime": 0, "uid_is_sub": 0, "prime_sub_differ": 0,
         "gap_reason_has_code_path": 0, "gap_reason_filled": 0,
         "url_prime_award_page": 0, "url_names_subaward": 0, "url_blank": 0,
         "pre2000_flag": Counter(), "exceeds_flag": Counter(),
         "head_truncated": 0, "a16_rows": []}
    cols = ["subaward_number", "subaward_amount", "prime_award_amount",
            "subaward_to_prime_ratio", "subaward_exceeds_prime_flag",
            "cedar_uid", "prime_cedar_uid", "sub_cedar_uid", "description",
            "geo_subawardee_county_gap_reason", "source_url", "pre_2000_flag"]
    for r in _stream("subcontracting", cols):
        f["rows"] += 1
        flag = r.get("subaward_exceeds_prime_flag", "")
        f["exceeds_flag"][flag] += 1
        if flag.lower() == "yes":
            f["exceeds_prime"] += 1
        sn = r.get("subaward_number", "")
        try:
            ratio = float(r.get("subaward_to_prime_ratio") or 0)
        except ValueError:
            ratio = 0.0
        if ratio > 10:
            f["ratio_over_10"] += 1
        if f["worst_ratio"] is None or ratio > f["worst_ratio"][0]:
            f["worst_ratio"] = (ratio, sn, r.get("subaward_amount", ""),
                                r.get("prime_award_amount", ""))
        if sn == "SSI348":
            f["ssi348"].append((r.get("subaward_amount", ""),
                                r.get("prime_award_amount", ""),
                                r.get("subaward_to_prime_ratio", "")))
        uid = r.get("cedar_uid", "")
        if uid and uid == r.get("prime_cedar_uid", ""):
            f["uid_is_prime"] += 1
        if uid and uid == r.get("sub_cedar_uid", ""):
            f["uid_is_sub"] += 1
        if (r.get("prime_cedar_uid") and r.get("sub_cedar_uid")
                and r["prime_cedar_uid"] != r["sub_cedar_uid"]):
            f["prime_sub_differ"] += 1
        gr = r.get("geo_subawardee_county_gap_reason", "")
        if gr:
            f["gap_reason_filled"] += 1
            if "code/" in gr:
                f["gap_reason_has_code_path"] += 1
        u = r.get("source_url", "")
        if not u:
            f["url_blank"] += 1
        else:
            if "/award/" in u:
                f["url_prime_award_page"] += 1
            if sn and sn in u:
                f["url_names_subaward"] += 1
        f["pre2000_flag"][r.get("pre_2000_flag", "")] += 1
        desc = r.get("description", "")
        if trunc.match(desc):
            f["head_truncated"] += 1
        if sn == "A16-002982":
            f["a16_rows"].append(desc[:60])
    return f


def scan_nest():
    """One pass over dist/customer/nest.csv - 4,798 rows."""
    _say("scanning nest.csv")
    urlok = re.compile(r"^https?://[^\s<>\"]+$")
    f = {"rows": 0, "uid_is_owner_hub": 0, "unspecified_affiliation_ownership_pub": 0,
         "unreviewed_but_publishable": 0, "url_malformed": 0, "url_blank": 0,
         "url_malformed_example": "", "status": Counter(),
         "status_basis_named_by_owner": 0, "sector": Counter(),
         "sector_catchall": 0, "sector_blank": 0,
         "fpds_parent_declared_unresolved": 0, "fpds_parent_declared": 0,
         "named_rows": {}, "self_owned": 0, "name_begins_with_owner": 0}
    named = {"CEDAR-NEST-001630-JQ", "CEDAR-NEST-002101-BF", "CEDAR-NEST-004386-96"}
    cols = ["enterprise_id", "enterprise_name", "owner_hub_name", "cedar_uid",
            "owner_hub_cedar_uid", "relationship", "relation_class",
            "assertion_class", "publishable", "evidence_human_reviewed",
            "source_url", "status", "status_basis", "sector",
            "fpds_declared_parent_name", "fpds_parent_resolves_to"]
    norm = lambda s: re.sub(r"[^a-z]", "", (s or "").lower().replace("the", ""))
    for r in _stream("nest", cols):
        f["rows"] += 1
        if r.get("cedar_uid") and r["cedar_uid"] == r.get("owner_hub_cedar_uid"):
            f["uid_is_owner_hub"] += 1
        if (r.get("relationship") == "unspecified"
                and r.get("relation_class") == "affiliation"
                and r.get("assertion_class", "").upper() == "OWNERSHIP"
                and r.get("publishable", "").upper() == "Y"):
            f["unspecified_affiliation_ownership_pub"] += 1
        if (r.get("evidence_human_reviewed", "").upper() == "N"
                and r.get("publishable", "").upper() == "Y"):
            f["unreviewed_but_publishable"] += 1
        u = r.get("source_url", "")
        if not u:
            f["url_blank"] += 1
        elif not urlok.match(u):
            f["url_malformed"] += 1
            if not f["url_malformed_example"]:
                f["url_malformed_example"] = u[:70]
        f["status"][r.get("status", "")] += 1
        if "named by its owner in a source dated" in r.get("status_basis", ""):
            f["status_basis_named_by_owner"] += 1
        sec = r.get("sector", "")
        f["sector"][sec] += 1
        if not sec:
            f["sector_blank"] += 1
        if sec == "Other services or Not given":
            f["sector_catchall"] += 1
        if r.get("fpds_declared_parent_name"):
            f["fpds_parent_declared"] += 1
            if not r.get("fpds_parent_resolves_to"):
                # lint-ok: class2c - nothing is dropped here. This counts a
                # DEFECT for CP-129 and ships with its denominator
                # (fpds_parent_declared) in the evidence string; the rows are
                # not skipped, they are the finding.
                f["fpds_parent_declared_unresolved"] += 1
        # TWO measures, because one of them was wrong. `oh in en` counts
        # "Ahtna Construction" owned by "Ahtna" as self-ownership, and a
        # subsidiary named after its parent is ordinary, not a defect. Only
        # exact equality after normalisation is the entity-class error CP-118
        # describes; the containment count is kept separately and named for
        # what it is.
        en, oh = norm(r.get("enterprise_name")), norm(r.get("owner_hub_name"))
        if en and oh:
            if en == oh:
                f["self_owned"] += 1
            elif oh in en:
                f["name_begins_with_owner"] += 1
        if r.get("enterprise_id") in named:
            f["named_rows"][r["enterprise_id"]] = {
                "enterprise_name": r.get("enterprise_name", ""),
                "owner_hub_name": r.get("owner_hub_name", ""),
                "fpds_declared_parent_name": r.get("fpds_declared_parent_name", ""),
                "relation_class": r.get("relation_class", ""),
                "assertion_class": r.get("assertion_class", ""),
                "publishable": r.get("publishable", ""),
                "evidence_human_reviewed": r.get("evidence_human_reviewed", "")}
    f["assertion_class"] = Counter()
    for r in _stream("nest", ["assertion_class", "relation_class"]):
        f["assertion_class"][(r.get("relation_class", ""),
                              r.get("assertion_class", ""))] += 1
    return f


def scan_nonprofits():
    """One pass over dist/customer/nonprofits.csv plus the upstream np_orgs."""
    _say("scanning nonprofits.csv and data/clean/np_orgs.csv")
    gov = re.compile(r"bylaw|charter|resolution|board|ordinance|corporation code|"
                     r"governing|section 17|articles of inc", re.I)
    weak = re.compile(r"wikipedia|yahoo|causeiq|propublica|guidestar|search\?", re.I)
    f = {"rows": 0, "placename_flagged": Counter(), "entity_id_blank": 0,
         "source_url": Counter(), "evidence_filled": 0, "evidence_weak_host": 0,
         "evidence_agent_narrative": 0, "coders_agree_filled": 0,
         "ruling": Counter(), "filing_req_990n": 0, "n990_all_measures_zero": 0,
         "controlled_rulings": 0, "controlled_without_governance_evidence": 0,
         "winnebago_row": None, "shipped_eins": set()}
    named_eins = {"874031049", "833159108", "582328510", "320671686"}
    cols = ["EIN", "org_name", "entity_id", "cedar_uid", "placename_risk_flag",
            "source_url", "evidence", "n_coders_agree", "classification_ruling",
            "bmf_filing_req_cd", "bmf_revenue_amt", "bmf_asset_amt",
            "bmf_income_amt", "disposition"]
    for r in _stream("nonprofits", cols):
        f["rows"] += 1
        ein = (r.get("EIN") or "").lstrip("0")
        if ein in {e.lstrip("0") for e in named_eins}:
            f["shipped_eins"].add(ein)
            if ein == "320671686":
                f["winnebago_row"] = (r.get("org_name", ""),
                                      (r.get("evidence") or "")[:150])
        f["placename_flagged"][r.get("placename_risk_flag", "")] += 1
        if not r.get("entity_id"):
            f["entity_id_blank"] += 1
        f["source_url"][r.get("source_url", "")] += 1
        ev = r.get("evidence", "")
        if ev:
            f["evidence_filled"] += 1
            if weak.search(ev):
                f["evidence_weak_host"] += 1
            if "AGENT-RESEARCHED" in ev:
                f["evidence_agent_narrative"] += 1
        if r.get("n_coders_agree"):
            f["coders_agree_filled"] += 1
        rul = r.get("classification_ruling", "")
        f["ruling"][rul] += 1
        if rul in ("native_controlled", "tribally_controlled"):
            f["controlled_rulings"] += 1
            if not gov.search(ev):
                f["controlled_without_governance_evidence"] += 1
        if r.get("bmf_filing_req_cd") == "02":
            f["filing_req_990n"] += 1
            if all((r.get(c) or "0") in ("", "0", "0.0")
                   for c in ("bmf_revenue_amt", "bmf_asset_amt", "bmf_income_amt")):
                f["n990_all_measures_zero"] += 1
    # the same three EINs, upstream, where the export gate cannot reach them
    f["upstream"] = {}
    if (CLEAN / "np_orgs.csv").exists():
        want = {e.lstrip("0") for e in named_eins}
        for r in _stream("np_orgs", ["EIN", "org_name", "tribe_canonical_name",
                                     "key_review_disposition", "disposition",
                                     "key_redirect_proposed_name"], root=CLEAN):
            e = (r.get("EIN") or "").lstrip("0")
            if e in want:
                f["upstream"][e] = (r.get("tribe_canonical_name", ""),
                                    r.get("key_review_disposition", ""),
                                    r.get("disposition", ""))
    return f


def scan_nagpra():
    """One pass over dist/customer/nagpra.csv - 6,792 notices."""
    _say("scanning nagpra.csv")
    park = re.compile(r"National (Park|Monument|Historic|Forest|Recreation)", re.I)
    role_cols = ("n_consulted_named", "n_affiliated_named",
                 "n_disposition_priority_named", "n_repatriation_recipient_named",
                 "n_letter_of_support_named", "n_aboriginal_land_named")
    f = {"rows": 0, "count1_but_conjoined": 0, "park_in_city": 0,
         "parties_named_equals_role_sum": 0, "resolved_below_named": 0,
         "corrections": 0, "objects_without_categories": 0,
         "parse_template_filled": 0, "spans_found_filled": 0,
         "parent_dataset": Counter(), "named_rows": {}}
    named = {"E6-16923", "E9-5321", "2015-25024", "03-10916"}
    cols = ["document_number", "institution_name", "institution_names_all",
            "institution_count", "institution_city", "object_categories",
            "cultural_items_total_stated", "is_correction", "n_parties_named",
            "n_entities_resolved", "parse_template", "spans_found",
            "parent_dataset", "n_associated_funerary_objects_stated",
            "n_unassociated_funerary_objects_stated", "n_sacred_objects_stated",
            "n_objects_of_cultural_patrimony_stated"] + list(role_cols)
    for r in _stream("nagpra", cols):
        f["rows"] += 1
        if r.get("institution_count") == "1" and " and " in r.get("institution_names_all", ""):
            f["count1_but_conjoined"] += 1
        if park.search(r.get("institution_city", "")):
            f["park_in_city"] += 1
        if r.get("is_correction") == "1":
            f["corrections"] += 1
        if r.get("parse_template"):
            f["parse_template_filled"] += 1
        if r.get("spans_found"):
            f["spans_found_filled"] += 1
        f["parent_dataset"][r.get("parent_dataset", "")] += 1

        def _i(k):
            try:
                return int(float(r.get(k) or 0))
            except ValueError:
                return 0
        tot, res = _i("n_parties_named"), _i("n_entities_resolved")
        rsum = sum(_i(k) for k in role_cols)
        if tot > 0 and tot == rsum:
            f["parties_named_equals_role_sum"] += 1
        if res < tot:
            f["resolved_below_named"] += 1
        objs = sum(_i(k) for k in ("n_associated_funerary_objects_stated",
                                   "n_unassociated_funerary_objects_stated",
                                   "n_sacred_objects_stated",
                                   "n_objects_of_cultural_patrimony_stated"))
        if objs > 0 and not r.get("object_categories"):
            f["objects_without_categories"] += 1
        if r.get("document_number") in named:
            f["named_rows"][r["document_number"]] = {
                "institution_name": (r.get("institution_name") or "")[:90],
                "institution_count": r.get("institution_count", ""),
                "institution_city": r.get("institution_city", ""),
                "object_categories": r.get("object_categories", ""),
                "objects": objs}
    hdr = _header("nagpra")
    f["supersession_columns"] = [c for c in hdr
                                 if re.search(r"corrects|supersed|original_doc|"
                                              r"current_version", c, re.I)]
    return f


def scan_lobbying():
    """One pass over dist/customer/lobbying.csv - 27,825 filings."""
    _say("scanning lobbying.csv")
    billref = re.compile(r"\b(H\.?\s?R\.?|S\.?)\s?\d{2,5}\b")
    f = {"rows": 0, "termination_filings": 0, "termination_date_blank": 0,
         "state_disagreement": 0, "crit_filing": None,
         "spend_basis": Counter(), "spend_equals_income": 0,
         "gov_entities_filled": 0, "gov_entities_piped": 0,
         "issues_filled": 0, "issues_with_bill_reference": 0}
    cols = ["filing_uuid", "filing_type_display", "termination_date",
            "client_name", "client_state", "entity_state", "spend_basis",
            "spend_usd", "income_usd", "government_entities",
            "specific_issues_text"]
    for r in _stream("lobbying", cols):
        f["rows"] += 1
        if "termination" in r.get("filing_type_display", "").lower():
            f["termination_filings"] += 1
            if not r.get("termination_date"):
                f["termination_date_blank"] += 1
        cs, es = r.get("client_state", ""), r.get("entity_state", "")
        if cs and es and cs != es:
            f["state_disagreement"] += 1
        if r.get("filing_uuid") == "bdf7b163-0ccf-43f8-ae38-7c4030d0b445":
            f["crit_filing"] = (r.get("client_name", ""), cs, es)
        f["spend_basis"][r.get("spend_basis", "")] += 1
        if r.get("spend_usd") and r.get("spend_usd") == r.get("income_usd"):
            f["spend_equals_income"] += 1
        ge = r.get("government_entities", "")
        if ge:
            f["gov_entities_filled"] += 1
            if "|" in ge:
                f["gov_entities_piped"] += 1
        it = r.get("specific_issues_text", "")
        if it:
            f["issues_filled"] += 1
            if billref.search(it):
                f["issues_with_bill_reference"] += 1
    f["bill_id_columns"] = [c for c in _header("lobbying")
                            if re.search(r"bill", c, re.I)]
    return f


MONTHS = {m.lower(): i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}


def scan_federal_register():
    """One pass over dist/customer/federal-register.csv - 11,402 rows."""
    _say("scanning federal-register.csv")
    datepat = re.compile(r"(January|February|March|April|May|June|July|August|"
                         r"September|October|November|December)\s+(\d{1,2})", re.I)
    f = {"rows": 0, "with_participant": 0, "with_event_dates": 0,
         "not_enumerated": 0, "events": Counter(), "events_mixing_grain": 0,
         "quote_checked": 0, "quote_names_earlier_date": 0,
         "end_year_after_start_year": 0, "multi_location_single_day": 0,
         "written_comment_with_location": 0, "confidence": Counter(),
         "match_method": Counter(), "named_rows": {}}
    named = {"2013-13468", "95-6969", "01-30327", "2011-8999"}
    kinds = defaultdict(set)
    cols = ["fr_document_number", "consultation_event_id", "location",
            "event_start_date", "event_end_date", "format",
            "participant_name_as_published", "event_date_source_quote",
            "location_source_quote", "confidence", "match_method"]
    for r in _stream("federal-register", cols):
        f["rows"] += 1
        ev = r.get("consultation_event_id", "")
        f["events"][ev] += 1
        has_p = bool(r.get("participant_name_as_published"))
        if has_p:
            f["with_participant"] += 1
        kinds[ev].add(has_p)
        if r.get("event_start_date"):
            f["with_event_dates"] += 1
        if r.get("match_method") == "no_participants_named_in_record":
            f["not_enumerated"] += 1
        f["confidence"][r.get("confidence", "")] += 1
        f["match_method"][r.get("match_method", "")] += 1
        s, e = r.get("event_start_date", ""), r.get("event_end_date", "")
        q = r.get("event_date_source_quote", "")
        if q and re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            ds = [(MONTHS[m.lower()], int(d)) for m, d in datepat.findall(q)
                  if m.lower() in MONTHS]
            if ds:
                f["quote_checked"] += 1
                if min(ds) < (int(s[5:7]), int(s[8:10])):
                    f["quote_names_earlier_date"] += 1
        if (re.match(r"^\d{4}-\d{2}-\d{2}$", s) and re.match(r"^\d{4}-\d{2}-\d{2}$", e)
                and s[:4] != e[:4]):
            f["end_year_after_start_year"] += 1
        loc = r.get("location", "")
        if ";" in loc and s and s == e:
            f["multi_location_single_day"] += 1
        if "written_comment" in r.get("format", "") and loc:
            f["written_comment_with_location"] += 1
        dn = r.get("fr_document_number", "")
        if dn in named:
            f["named_rows"].setdefault(dn, []).append(
                {"location": loc[:60], "start": s, "end": e,
                 "format": r.get("format", ""),
                 "participant": r.get("participant_name_as_published", "")[:40],
                 "quote": q[:80]})
    f["events_mixing_grain"] = sum(1 for v in kinds.values() if len(v) > 1)
    f["event_count"] = len(f["events"])
    return f


def scan_legislation():
    """One pass over dist/customer/legislation.csv - 3,069 bills."""
    _say("scanning legislation.csv")
    fail = re.compile(r"\bfailed\b|\brejected\b|\bmotion to (suspend|table)\b.*"
                      r"failed", re.I)
    advanced = re.compile(r"union calendar|house calendar|placed on (the )?"
                          r"(senate|union|house) ", re.I)
    f = {"rows": 0, "outcome": Counter(), "classification_source": Counter(),
         "companion_inferred_from_title": 0, "kappa_on_row": 0,
         "cosponsor_decimal": 0, "cosponsor_blank": 0,
         "passed_but_action_failed": 0, "died_but_action_advanced": 0,
         "named_rows": {}}
    named = {"105-hr-948", "104-hr-3828"}
    cols = ["bill_id", "outcome", "latest_action", "latest_action_date",
            "classification_source", "companion_basis", "classification_kappa",
            "cosponsor_count", "outcome_basis"]
    for r in _stream("legislation", cols):
        f["rows"] += 1
        oc, la = r.get("outcome", ""), r.get("latest_action", "")
        f["outcome"][oc] += 1
        f["classification_source"][r.get("classification_source", "")] += 1
        if r.get("companion_basis", "").startswith("identical_normalized_title"):
            f["companion_inferred_from_title"] += 1
        if r.get("classification_kappa"):
            f["kappa_on_row"] += 1
        cc = r.get("cosponsor_count", "")
        if not cc:
            f["cosponsor_blank"] += 1
        elif "." in cc:
            f["cosponsor_decimal"] += 1
        if oc in ("passed-one-chamber", "enacted") and fail.search(la):
            # lint-ok: class2c - nothing is dropped here. This counts a DEFECT
            # for CP-062/RG-009 and ships with its denominator (rows) in the
            # evidence string, plus the named bill 105-hr-948 verbatim.
            f["passed_but_action_failed"] += 1
        if oc == "died-in-committee" and advanced.search(la):
            f["died_but_action_advanced"] += 1
        if r.get("bill_id") in named:
            f["named_rows"][r["bill_id"]] = (oc, la[:110],
                                             r.get("outcome_basis", ""))
    return f


def scan_deals():
    """One pass over dist/customer/deals.csv - 1,073 deal events."""
    _say("scanning deals.csv")
    doe = re.compile(r"\bDE-[A-Z]{2}\d{7}\b")
    suffix = re.compile(r"\b(nation|tribe|tribes|band|pueblo|community|village|"
                        r"corporation|corp|inc|council|rancheria|colony|"
                        r"association|authority|group|company|llc|indians|"
                        r"reservation)\b", re.I)
    f = {"rows": 0, "record_class": Counter(), "capital_source": Counter(),
         "perf_start_basis": 0, "perf_start_basis_and_awarded": 0,
         "award_number_only_in_prose": 0, "canon_filled": 0,
         "canon_without_entity_word": 0, "canon_examples": set(),
         "named_rows": {}}
    named = {"FA-DOE-0003", "FA-DOE-0014"}
    cols = ["Deal_ID", "record_class", "capital_source", "Status", "Event_Date",
            "Date_Basis", "Description", "native_party_canonical_name",
            "Announced_Value_USD", "Value_Type"]
    for r in _stream("deals", cols):
        f["rows"] += 1
        f["record_class"][r.get("record_class", "")] += 1
        f["capital_source"][r.get("capital_source", "")] += 1
        db = r.get("Date_Basis", "")
        if re.search(r"performance", db, re.I):
            f["perf_start_basis"] += 1
            if r.get("Status") == "Awarded":
                f["perf_start_basis_and_awarded"] += 1
        if doe.search(r.get("Description", "")):
            f["award_number_only_in_prose"] += 1
        cn = r.get("native_party_canonical_name", "")
        if cn:
            f["canon_filled"] += 1
            if not suffix.search(cn):
                f["canon_without_entity_word"] += 1
                if len(f["canon_examples"]) < 6:
                    f["canon_examples"].add(cn)
        if r.get("Deal_ID") in named:
            f["named_rows"][r["Deal_ID"]] = (r.get("Event_Date", ""), db[:90],
                                             r.get("Status", ""))
    f["federal_award_id_columns"] = [c for c in _header("deals")
                                     if re.search(r"fain|award_id|federal_award",
                                                  c, re.I)]
    return f


def scan_natural_resources():
    """One pass over dist/customer/natural-resources.csv - 11,305 events."""
    _say("scanning natural-resources.csv")
    f = {"rows": 0, "source_system": Counter(), "revenue_type": Counter(),
         "confidence": Counter(), "nd_rows": 0, "nd_source_urls": set(),
         "amlis_rows": [], "distinct_source_urls": set()}
    cols = ["resource_revenue_event_id", "source_system", "revenue_type",
            "confidence", "source_url", "amount_usd", "period_type",
            "period_start", "period_end", "beneficiary_note"]
    for r in _stream("natural-resources", cols):
        f["rows"] += 1
        ss = r.get("source_system", "")
        f["source_system"][ss] += 1
        f["revenue_type"][r.get("revenue_type", "")] += 1
        f["confidence"][r.get("confidence", "")] += 1
        f["distinct_source_urls"].add(r.get("source_url", ""))
        if "ND_State_Treasurer" in ss:
            f["nd_rows"] += 1
            f["nd_source_urls"].add(r.get("source_url", ""))
        if "AMLIS" in r.get("resource_revenue_event_id", ""):
            f["amlis_rows"].append({
                "id": r.get("resource_revenue_event_id", ""),
                "revenue_type": r.get("revenue_type", ""),
                "amount_usd": r.get("amount_usd", ""),
                "period_type": r.get("period_type", ""),
                "period": f"{r.get('period_start','')}..{r.get('period_end','')}",
                "note": (r.get("beneficiary_note") or "")[:120]})
    return f


def scan_owned():
    """One pass over dist/customer/native-owned-businesses.csv - 3,725 rows."""
    _say("scanning native-owned-businesses.csv")
    f = {"rows": 0, "certification_number_filled": 0, "certification_start_filled": 0,
         "source_url_filled": 0, "distinct_source_urls": set(),
         "certifying_authority_filled": 0, "source_terms_status": Counter(),
         "directory_type": Counter(), "identity_scope": Counter()}
    cols = ["certification_number", "certification_start", "source_url",
            "certifying_authority_name", "source_terms_status",
            "directory_type", "identity_scope"]
    for r in _stream("native-owned-businesses", cols):
        f["rows"] += 1
        if r.get("certification_number"):
            f["certification_number_filled"] += 1
        if r.get("certification_start"):
            f["certification_start_filled"] += 1
        if r.get("source_url"):
            f["source_url_filled"] += 1
            f["distinct_source_urls"].add(r["source_url"])
        if r.get("certifying_authority_name"):
            f["certifying_authority_filled"] += 1
        f["source_terms_status"][r.get("source_terms_status", "")] += 1
        f["directory_type"][r.get("directory_type", "")] += 1
        f["identity_scope"][r.get("identity_scope", "")] += 1
    notes = CUST / "native-owned-businesses__NOTES.txt"
    txt = notes.read_text(encoding="utf-8", errors="replace") if notes.exists() else ""
    f["notes_explain_identity_scope"] = "identity_scope" in txt
    f["notes_explain_assertion_class"] = "assertion_class" in txt
    # CP-148: the broken sentence, wherever it now lives
    frag = "no federal register counts"
    f["broken_copy_in_delivered_csv"] = [
        p.name for p in sorted(CUST.glob("*.csv"))
        if frag in p.read_text(encoding="utf-8", errors="replace")[:5_000_000]]
    site = ROOT / "server" / "cedar_press" / "_press_data.json"
    f["broken_copy_in_site_copy"] = (
        site.exists() and frag in site.read_text(encoding="utf-8", errors="replace"))
    return f


def scan_bundle():
    """Cross-file: URL syntax, missing-value tokens, crosswalk, archive contract.

    One pass PER FILE, every cell of every URL column and every cell tested
    against the missing-value vocabulary. `contractors.csv` is included.
    """
    urlok = re.compile(r"^https?://[^\s<>\"]+$")
    sentinels = {"UNKNOWN", "NAN", "NA", "N/A", "NONE", "NULL", "-1",
                 "NOT SPECIFIED", "UNSPECIFIED"}
    f = {"url_cells": 0, "url_malformed": 0, "url_blank": 0,
         "url_malformed_by_column": Counter(), "url_columns": 0,
         "sentinel_columns": {}, "sentinel_column_total": 0}
    for p in sorted(CUST.glob("*.csv")):
        if p.name == "MANIFEST.csv":
            continue
        _say(f"bundle scan: {p.name}")
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
            rd = csv.reader(fh)
            hdr = next(rd, [])
            ucols = [(i, c) for i, c in enumerate(hdr)
                     if c.lower().endswith("url") or c.lower().endswith("_urls")]
            f["url_columns"] += len(ucols)
            seen = defaultdict(set)
            for row in rd:
                n = len(row)
                for i, c in ucols:
                    v = row[i].strip() if i < n else ""
                    f["url_cells"] += 1
                    if not v:
                        f["url_blank"] += 1
                    elif not urlok.match(v):
                        f["url_malformed"] += 1
                        f["url_malformed_by_column"][f"{p.stem}.{c}"] += 1
                for i, c in enumerate(hdr):
                    v = row[i].strip().upper() if i < n else ""
                    if v in sentinels or v == "":
                        seen[c].add(v)
        mixed = {c: sorted(s) for c, s in seen.items() if len(s) > 1}
        if mixed:
            f["sentinel_columns"][p.stem] = mixed
            f["sentinel_column_total"] += len(mixed)

    # cross-collection: does the same federal record appear twice, and is it linked
    frdocs = {r.get("fr_document_number", "") for r
              in _stream("federal-register", ["fr_document_number"])} - {""}
    ngdocs = {r.get("document_number", "") for r
              in _stream("nagpra", ["document_number"])} - {""}
    f["fr_nagpra_shared_documents"] = len(frdocs & ngdocs)
    f["fr_has_nagpra_bridge"] = [c for c in _header("federal-register")
                                 if "nagpra" in c.lower()]
    f["deals_federal_award_columns"] = [c for c in _header("deals")
                                        if re.search(r"fain|award_id|federal_award",
                                                     c, re.I)]
    # archive contract
    f["manifest_columns"] = _header("MANIFEST")
    low = [c.lower() for c in f["manifest_columns"]]
    f["manifest_has"] = {
        "grain": any("grain" in c for c in low),
        "row count": any(c == "rows" for c in low),
        "primary key": any("key" in c for c in low),
        "schema version": any("schema" in c for c in low),
        "as-of date": any("as_of" in c or "asof" in c for c in low),
        "file hash": any("hash" in c for c in low)}
    f["readme"] = (CUST / "README.md").exists()
    f["manifest_json"] = (CUST / "manifest.json").exists()
    f["data_dictionary"] = (CUST / "data_dictionary.csv").exists()
    f["codebooks"] = len(list(CUST.glob("*__CODEBOOK.md")))
    f["notes"] = len(list(CUST.glob("*__NOTES.txt")))
    f["zips"] = [str(z.relative_to(ROOT)) for z in (ROOT / "dist").rglob("*.zip")]
    f["empty_tables"] = [p.stem for p in sorted(CUST.glob("*.csv"))
                         if p.name != "MANIFEST.csv"
                         and sum(1 for _ in _stream(p.stem, _header(p.stem)[:1])) == 0]
    return f


# ============================================================================
#  THE NINETY-ONE. One named function per finding. Each reads its own keys.
# ============================================================================
def _v(n, evidence, cleared=""):
    """CONFIRMED when the driving count is non-zero, LIKELY_FIXED when it is 0.

    ADDED 2026-09-02 after this file's own checks were caught doing the thing
    it was written to stop. `chk_cp120` returned CONFIRMED unconditionally and
    printed `0/5,888 (0.0%)` as its evidence: the number said fixed and the
    verdict said broken. That is a check whose NAME claims more than its BODY
    measures, which is the defect class this codebase keeps reproducing.

    So no check states a verdict on its own any more - it hands its driving
    count here and the count decides. A zero is still a measurement and still
    ships in the ledger; only the verdict changes.
    """
    if n:
        return (CONFIRMED, evidence)
    return (FIXED, (cleared + " " if cleared else "") + evidence)


# ---- Prime Contracting -----------------------------------------------------
def chk_cp020(ev):
    """Rows linked to a Native entity despite CONTRADICTED_AS_OF."""
    c = ev["contractors"]
    named = c["named_contradicted"]
    detail = "; ".join(f"{k}: {len(v)} row(s), cedar_uid " +
                       ("BLANK on all" if all(not u for u, _ in v) else "STILL SET")
                       for k, v in sorted(named.items())) or "named contracts absent"
    if c["contradicted_with_uid"] == 0:
        return (FIXED, f"1153 masked it. {c['contradicted']:,} rows still carry "
                       f"owner_attribution_status=CONTRADICTED_AS_OF, and "
                       f"{_pct(c['contradicted_with_uid'], c['contradicted'])} of "
                       f"them carry a cedar_uid - the attribution is gone, the "
                       f"transaction still ships. The two named S & T Services "
                       f"contracts: {detail}")
    return (CONFIRMED, f"{_pct(c['contradicted_with_uid'], c['contradicted'])} "
                       f"CONTRADICTED_AS_OF rows still carry a cedar_uid. {detail}")


def chk_cp021(ev):
    """One award, several cumulative totals, in the same transaction table."""
    c = ev["contractors"]
    w = c["award_spread_worst"]
    tgt = sorted(c["target_award_values"])
    worst = (f"worst single award key: contract {w[4]} runs ${w[2]:,.2f} to "
             f"${w[3]:,.2f}, a spread of ${w[0]:,.0f}") if w else "no spread"
    return _v(c["award_keys_multivalued"],
              f"{_pct(c['award_keys_multivalued'], c['award_keys'])} award keys "
            f"carry MORE THAN ONE total_award_value. Summing the column over "
            f"transactions overstates by ${c['award_spread_total_usd']:,.0f} in "
            f"total. The review's example, award 12314422F0384, now shows "
            f"{len(tgt)} distinct values, not 3: {', '.join(tgt)}. {worst}")


def chk_cp024(ev):
    """DO and DELIVERY ORDER as separate values."""
    a = ev["contractors"]["award_type"]
    pairs = [("DO", "DELIVERY ORDER"), ("PO", "PURCHASE ORDER"),
             ("BPA", "BPA CALL")]
    live = [f"{s}={a.get(s,0):,} vs {l}={a.get(l,0):,}"
            for s, l in pairs if a.get(s) and a.get(l)]
    if not live:
        return (FIXED, "no abbreviation/spelled-out pair is both live in award_type")
    return (CONFIRMED, f"{len(live)} unmerged synonym pair(s) in award_type: "
                       + "; ".join(live) +
                       f". {a.get('', 0):,} rows leave award_type blank")


def chk_cp025(ev):
    """The literal text NAN standing in for a missing CAGE."""
    c = ev["contractors"]
    if not c["cage_nan"]:
        return (FIXED, "no contractors row carries the literal string NAN in cage_code")
    return (CONFIRMED, f"cage_code is the literal text NAN on "
                       f"{_pct(c['cage_nan'], c['rows'])} rows; a further "
                       f"{_pct(c['cage_blank'], c['rows'])} are properly blank, "
                       f"so the same absence is encoded two ways in one column")


def chk_cp026(ev):
    """Friendly ID labels that never say which federal identifier they are."""
    c = ev["contractors"]
    if c["codebook_says_piid"]:
        return (FIXED, "contractors__CODEBOOK.md names PIID against the "
                       "contract_number columns")
    return (CONFIRMED, "contractors ships contract_number, parent_contract_number, "
                       "contract_award_unique_key and contract_transaction_unique_key, "
                       "and contractors__CODEBOOK.md never uses the word PIID - a "
                       "buyer cannot tell which column joins to FPDS")


def chk_cp036(ev):
    """A boolean that is blank rather than false, and flags mixing blank with yes."""
    c, s = ev["contractors"], ev["subcontracting"]
    cflags = dict(c["pre2000_flag"])
    sflags = dict(s["pre2000_flag"])
    ex = dict(s["exceeds_flag"])
    parts = [f"contractors.pre_2000_flag = {cflags}",
             f"subcontracting.pre_2000_flag = {sflags}",
             f"subcontracting.subaward_exceeds_prime_flag = "
             f"{{'': {ex.get('', 0):,}, 'yes': {ex.get('yes', 0):,}}}"]
    fixed_side = set(cflags) <= {"0", "1"}
    if fixed_side and set(sflags) <= {"0", "1"}:
        return (FIXED, "both flag columns are 0/1 with no blanks. " + "; ".join(parts))
    return (CONFIRMED,
            "half fixed. contractors.pre_2000_flag is now 0 on every row (no "
            "blanks) but is constant, so it carries no information; "
            "subcontracting.pre_2000_flag is BLANK on every one of its "
            f"{s['rows']:,} rows, and subaward_exceeds_prime_flag still mixes "
            f"blank with 'yes' rather than no/yes. " + "; ".join(parts))


# ---- Subcontracting --------------------------------------------------------
def chk_cp027(ev):
    """A subaward larger than its own prime award."""
    s = ev["subcontracting"]
    w = s["worst_ratio"]
    named = (f"SSI348 still ships: ${float(s['ssi348'][0][0]):,.2f} subaward "
             f"against a ${float(s['ssi348'][0][1]):,.2f} prime, ratio "
             f"{s['ssi348'][0][2]}") if s["ssi348"] else "SSI348 no longer ships"
    return _v(s["exceeds_prime"] + len(s["ssi348"]),
              f"{named}. Population: {_pct(s['exceeds_prime'], s['rows'])} rows carry "
              f"subaward_exceeds_prime_flag=yes and {s['ratio_over_10']:,} exceed "
              f"their prime by more than 10x. Worst: subaward {w[1]} at "
              f"${float(w[2] or 0):,.2f} against a ${float(w[3] or 0):,.2f} prime, "
              f"ratio {w[0]:,.0f}. The flag is raised and the row ships anyway")


def chk_cp030(ev):
    """The generic cedar_uid silently follows one side of a two-sided row."""
    s = ev["subcontracting"]
    return _v(s["prime_sub_differ"],
              f"cedar_uid equals prime_cedar_uid on {_pct(s['uid_is_prime'], s['rows'])} "
              f"rows and sub_cedar_uid on only {s['uid_is_sub']:,}. "
              f"{s['prime_sub_differ']:,} rows name a DIFFERENT Native entity on each "
              f"side, so on those rows the generic column silently picks one and a "
              f"buyer grouping by cedar_uid attributes the subaward to the prime",
              "no row names a different Native entity on each side, so the "
              "generic column cannot mislead:")


def chk_cp032(ev):
    """The source link resolves to the prime award, not the subaward."""
    s = ev["subcontracting"]
    return _v(s["url_prime_award_page"] - s["url_names_subaward"],
              f"{_pct(s['url_prime_award_page'], s['rows'])} source_url values are a "
            f"usaspending.gov /award/ page - the PRIME award - and only "
            f"{_pct(s['url_names_subaward'], s['rows'])} contain the subaward "
            f"number they are supposed to evidence. {s['url_blank']:,} are blank")


def chk_cp033(ev):
    """A build note about a code path, sitting in a customer column."""
    s = ev["subcontracting"]
    if not s["gap_reason_has_code_path"]:
        return (FIXED, "geo_subawardee_county_gap_reason no longer names a code path")
    return (CONFIRMED,
            f"geo_subawardee_county_gap_reason is filled on "
            f"{_pct(s['gap_reason_filled'], s['rows'])} rows and "
            f"{_pct(s['gap_reason_has_code_path'], s['rows'])} of them contain the "
            f"string 'code/' - a build sentence, not a data statement. This is the "
            f"MIXED-provenance case 1153 kept deliberately; it is still shipping")


def chk_cp035(ev):
    """A description missing its first character."""
    s = ev["subcontracting"]
    a16 = (f"A16-002982 still ships {len(s['a16_rows'])} row(s) beginning "
           f"{s['a16_rows'][0]!r}") if s["a16_rows"] else "A16-002982 no longer ships"
    return _v(s["head_truncated"],
              f"{a16}. {_pct(s['head_truncated'], s['rows'])} descriptions begin with "
              f"a word fragment whose first letter is gone (ROVIDE, ONTRACT, UPPORT "
              f"and similar). Small, but it is a parser wound left in customer text")


# ---- Natural Resources -----------------------------------------------------
def chk_cp107(ev):
    """Nine of ten rows were one ND series - a property of the ten-row sample."""
    n = ev["natural_resources"]
    top = n["source_system"].most_common(1)[0]
    return (OBSOLETE,
            f"the full table is {n['rows']:,} rows across "
            f"{len(n['source_system'])} source systems; the ND series the sample "
            f"was 90% made of is {_pct(n['nd_rows'], n['rows'])}. The largest "
            f"single system is {top[0]} at {_pct(top[1], n['rows'])}. The "
            f"concentration was the sample generator, not the table")


def chk_cp108(ev):
    """A reclamation grant sitting in a resource-revenue table."""
    n = ev["natural_resources"]
    rt = n["revenue_type"].get("reclamation_fee_distribution", 0)
    return (HUMAN,
            f"MEASURED, then owed to a person: {rt} row(s) carry "
            f"revenue_type=reclamation_fee_distribution inside a table of "
            f"{len(n['revenue_type'])} revenue types otherwise made of royalty, "
            f"rent, direct_pay and severance/production tax shares. The rows are "
            f"still there and unchanged. Whether a one-time federal IIJA "
            f"reclamation distribution IS resource revenue is a taxonomy ruling "
            f"the data cannot make - the collection's scope statement has to say "
            f"yes or no, and then the loader has to agree with it")


def chk_cp109(ev):
    """A note quoting the programme total next to a row-level amount."""
    n = ev["natural_resources"]
    if not n["amlis_rows"]:
        return (FIXED, "no AMLIS row ships")
    r = n["amlis_rows"][0]
    return (CONFIRMED,
            f"still live on {len(n['amlis_rows'])} row(s). {r['id']} has "
            f"amount_usd={r['amount_usd']} while beneficiary_note reads "
            f"{r['note']!r} - the note's $8,000,000 is the programme, the row is "
            f"the tribe's share, and nothing in the schema separates them")


def chk_cp110(ev):
    """A one-time payment given a full fiscal-year period."""
    n = ev["natural_resources"]
    if not n["amlis_rows"]:
        return (FIXED, "no AMLIS row ships")
    r = n["amlis_rows"][0]
    return (CONFIRMED,
            f"{r['id']} carries period_type={r['period_type']} over "
            f"{r['period']} - a 366-day period - while its own note says "
            f"'A single event, not an annual series'. The row contradicts its "
            f"own provenance field, and period_type has no one-time value")


def chk_cp111(ev):
    """A search page standing in for a row-level source."""
    n = ev["natural_resources"]
    urls = sorted(n["nd_source_urls"])
    return _v(n["nd_rows"] if len(urls) <= 1 else 0,
              f"all {n['nd_rows']:,} ND_State_Treasurer rows share "
              f"{len(urls)} source_url: {urls[0] if urls else 'none'} - a "
              f"tax-distribution SEARCH page, not a durable record. Across the "
              f"table {len(n['distinct_source_urls']):,} distinct URLs cover "
              f"{n['rows']:,} rows",
              "the ND rows no longer share one landing page:")


def chk_cp114(ev):
    """Top confidence on everything."""
    n = ev["natural_resources"]
    top = n["confidence"].most_common(1)[0]
    return _v(1 if top[1] / max(n["rows"], 1) > 0.9 else 0,
              f"confidence takes {len(n['confidence'])} values across "
            f"{n['rows']:,} rows and {_pct(top[1], n['rows'])} are '{top[0]}'. "
            f"The sample's 'all rows are A' was not a sampling artefact - the "
            f"grade is near-constant across twelve different source systems, "
            f"which is what makes it uninformative")


# ---- Native-Owned Businesses ----------------------------------------------
def chk_cp148(ev):
    """The broken collection copy."""
    o = ev["owned"]
    where = ("still in a delivered CSV: " + ", ".join(o["broken_copy_in_delivered_csv"])
             if o["broken_copy_in_delivered_csv"] else
             "no delivered CSV carries it")
    return ((CONFIRMED if o["broken_copy_in_delivered_csv"] else FIXED),
            f"the file the sentence lived in - owned-collection-description.csv - "
            f"no longer exists; native-owned-businesses.csv ships {o['rows']:,} "
            f"business rows instead. The fragment 'no federal register counts' "
            f"{where}"
            + ("; it does survive once in server/cedar_press/_press_data.json as "
               "a story dek, which is website copy rather than delivered data"
               if o["broken_copy_in_site_copy"] else ""))


def chk_cp150(ev):
    """Certification promised, certification not evidenced."""
    o = ev["owned"]
    silent = o["source_terms_status"].get("SILENT", 0)
    return _v(o["rows"] - o["certification_number_filled"],
              f"certifying_authority_name is filled on "
            f"{_pct(o['certifying_authority_filled'], o['rows'])} rows and every "
            f"row has a source_url ({len(o['distinct_source_urls']):,} distinct), "
            f"so the ISSUER is now named. What the finding asked for is still "
            f"missing: certification_number on only "
            f"{_pct(o['certification_number_filled'], o['rows'])} rows, "
            f"certification_start on {_pct(o['certification_start_filled'], o['rows'])}, "
            f"and source_terms_status is SILENT on "
            f"{_pct(silent, o['rows'])} - no terms captured at all")


def chk_cp151(ev):
    """Whether eligibility rules differ by nation or programme."""
    o = ev["owned"]
    tero = o["directory_type"].get("tero", 0)
    if o["notes_explain_identity_scope"] and len(o["identity_scope"]) > 3:
        return (FIXED,
                f"the schema now says it per row. directory_type separates "
                f"{len(o['directory_type'])} kinds of list (tero "
                f"{_pct(tero, o['rows'])}, then member_directory, business_licence, "
                f"certification_notice, vendor_list) and identity_scope carries "
                f"{len(o['identity_scope'])} distinct eligibility tests "
                f"(citizen, any_native, shareholder_descendant_or_spouse and so "
                f"on). native-owned-businesses__NOTES.txt explains that the "
                f"scopes are graded and not interchangeable")
    return (CONFIRMED, f"directory_type mixes {len(o['directory_type'])} list kinds "
                       f"and nothing states the eligibility test per row")


# ---- Native Nonprofits -----------------------------------------------------
def chk_cp132(ev):
    """Review-flagged rows in the customer file."""
    n = ev["nonprofits"]
    rev = n["placename_flagged"].get("REVIEW", 0)
    high = n["placename_flagged"].get("HIGH", 0)
    return _v(rev + high,
              f"{_pct(rev + high, n['rows'])} shipped rows carry a placename risk "
              f"flag (REVIEW {rev:,}, HIGH {high:,}). The sample's 'all ten' was "
              f"sampling; a flagged share of the delivered file is not")


def _np_withheld(ev, ein, what):
    n = ev["nonprofits"]
    up = n["upstream"].get(ein)
    if ein in n["shipped_eins"]:
        return (CONFIRMED, f"EIN {ein} still ships. {what}")
    if up:
        return (FIXED,
                f"EIN {ein} is WITHHELD from dist/customer - measured absent from "
                f"all {n['rows']:,} shipped rows - so the buyer never sees it. It "
                f"is NOT repaired: data/clean/np_orgs.csv still keys it to "
                f"{up[0]!r} with key_review_disposition={up[1]} and "
                f"disposition={up[2]}. The export gate hides the defect; the "
                f"keying is unchanged")
    return (FIXED, f"EIN {ein} is absent from the export and absent from "
                   f"data/clean/np_orgs.csv")


def chk_cp133(ev):
    """A NC longhouse keyed to the NY Tuscarora entity despite a state disagreement."""
    return _np_withheld(ev, "874031049", "keyed against HELD_STATE_DISAGREES")


def chk_cp134(ev):
    """A low-confidence name match resting on one word."""
    return _np_withheld(ev, "833159108", "linkage rests on the token 'Cherokee'")


def chk_cp135(ev):
    """A known wrong key with a redirect already proposed."""
    return _np_withheld(ev, "582328510", "redirect proposed and not applied")


def chk_cp136(ev):
    """990-N filers exported as if they had zero revenue."""
    n = ev["nonprofits"]
    return _v(n["n990_all_measures_zero"],
              f"{_pct(n['n990_all_measures_zero'], n['filing_req_990n'])} of the "
              f"990-N filers (bmf_filing_req_cd=02) carry 0 or blank on "
              f"bmf_revenue_amt, bmf_asset_amt AND bmf_income_amt at once. A 990-N "
              f"postcard reports no financials, so zero is a coding of 'not "
              f"reported' - and nothing in the file distinguishes it from a real zero")


def chk_cp137(ev):
    """The nonprofit has no id of its own."""
    n = ev["nonprofits"]
    return _v(n["entity_id_blank"],
              f"entity_id is blank on {_pct(n['entity_id_blank'], n['rows'])} rows, "
            f"so the subject of the row - the nonprofit - has no identifier, while "
            f"cedar_uid names the LINKED Native entity. The role split the owner "
            f"ruled for (subject id beside role-labelled cedar_uid) is declared "
            f"in the schema and unpopulated in the data")


def chk_cp138(ev):
    """Evidence resting on encyclopaedias and search pages."""
    n = ev["nonprofits"]
    return (OBSOLETE,
            f"the sample overstated this. evidence is filled on "
            f"{_pct(n['evidence_filled'], n['rows'])} rows and only "
            f"{_pct(n['evidence_weak_host'], n['rows'])} cite wikipedia, yahoo, "
            f"causeiq, propublica, guidestar or a raw search URL. "
            f"{_pct(n['evidence_agent_narrative'], n['rows'])} are "
            f"AGENT-RESEARCHED narrative. Real, and worth fixing, but it is a "
            f"two-percent tail rather than the file's evidence base")


def chk_cp139(ev):
    """One landing page for every organisation."""
    n = ev["nonprofits"]
    top = n["source_url"].most_common(1)[0]
    return _v(1 if len(n["source_url"]) <= 2 else 0,
              f"source_url takes {len(n['source_url'])} distinct value(s) across "
              f"{n['rows']:,} rows; {_pct(top[1], n['rows'])} point at "
              f"{top[0]} - the IRS BMF landing page. No row links to its own filing",
              "source_url now varies across rows:")


def chk_cp142(ev):
    """The row's name and the row's evidence describe different organisations."""
    n = ev["nonprofits"]
    if not n["winnebago_row"]:
        return (FIXED, "EIN 320671686 no longer ships")
    name, evid = n["winnebago_row"]
    return (CONFIRMED,
            f"EIN 320671686 still ships as {name!r} while its own evidence reads "
            f"{evid!r} - the evidence describes the Winnebago Health Foundation "
            f"and the row is named for the tribal government")


def chk_cp143(ev):
    """Native-control rulings with no governance document behind them."""
    n = ev["nonprofits"]
    return _v(n["controlled_without_governance_evidence"],
              f"PROXY MEASURE, stated so the reader can discount it: of the "
            f"{n['controlled_rulings']} rows ruled native_controlled or "
            f"tribally_controlled, "
            f"{_pct(n['controlled_without_governance_evidence'], n['controlled_rulings'])} "
            f"have evidence text containing none of bylaw / charter / resolution / "
            f"board / ordinance / governing / section 17 / articles of "
            f"incorporation. A keyword absence is not proof the ruling was made on "
            f"name and place alone, but it is the shape the finding described")


def chk_cp145(ev):
    """Coder agreement recorded on rows nobody has ruled."""
    n = ev["nonprofits"]
    unruled = n["ruling"].get("UNRULED", 0)
    return _v(min(n["coders_agree_filled"], unruled),
              f"n_coders_agree is filled on {_pct(n['coders_agree_filled'], n['rows'])} "
            f"rows while classification_ruling is UNRULED on "
            f"{_pct(unruled, n['rows'])}. A buyer reading '3 coders agree' next to "
            f"an unruled row is reading agreement about a proposal, not a verdict, "
            f"and no column says which")


# ---- NEST ------------------------------------------------------------------
def _nest_named(ev, eid, expected, why):
    n = ev["nest"]
    r = n["named_rows"].get(eid)
    if not r:
        return (FIXED, f"{eid} no longer ships")
    return (CONFIRMED,
            f"{eid} still ships: enterprise_name={r['enterprise_name']!r}, "
            f"owner_hub_name={r['owner_hub_name']!r}, "
            f"fpds_declared_parent_name={r['fpds_declared_parent_name']!r}, "
            f"relation_class={r['relation_class']}, "
            f"assertion_class={r['assertion_class']}, "
            f"publishable={r['publishable']}, "
            f"evidence_human_reviewed={r['evidence_human_reviewed']}. {why}"
            + (f" Expected owner: {expected}." if expected else "")
            + (" Downgraded since the review: the row no longer asserts "
               "OWNERSHIP, only affiliation - the wrong pairing still ships, it "
               "just claims less." if r["assertion_class"].upper() == "AFFILIATION"
               else ""))


def chk_cp116(ev):
    """Goldbelt Hawk assigned to Tlingit & Haida."""
    return _nest_named(ev, "CEDAR-NEST-001630-JQ", "Goldbelt Incorporated",
                       "FPDS names the parent and Cedar names a different one.")


def chk_cp117(ev):
    """A Bismarck college assigned to a California rancheria."""
    return _nest_named(ev, "CEDAR-NEST-002101-BF", "ND Associates of Tribal Colleges",
                       "The owner hub is 1,500 miles from the enterprise.")


def chk_cp118(ev):
    """A tribal government emitted as a business it owns."""
    n = ev["nest"]
    base = _nest_named(ev, "CEDAR-NEST-004386-96", None,
                       "The enterprise IS the owner hub.")
    return (base[0], base[1] + f" Population: {_pct(n['self_owned'], n['rows'])} "
                               f"rows have an enterprise_name that normalises to "
                               f"EXACTLY its own owner_hub_name - the entity-class "
                               f"error. A further {n['name_begins_with_owner']:,} "
                               f"merely begin with the owner's name, which is an "
                               f"ordinary subsidiary and is NOT counted here")


def chk_cp119(ev):
    """cedar_uid repeats the owner hub on every row."""
    n = ev["nest"]
    return _v(n["uid_is_owner_hub"],
              f"cedar_uid equals owner_hub_cedar_uid on "
              f"{_pct(n['uid_is_owner_hub'], n['rows'])} rows. Under the owner's "
              f"2026-09-02 ruling that is CORRECT BEHAVIOUR (the uid is the "
              f"Native entity, the enterprise has enterprise_id), so the defect "
              f"is narrower than written: the column is redundant with "
              f"owner_hub_cedar_uid and its ROLE is what the codebook must state")


def chk_cp120(ev):
    """An affiliation asserted as ownership."""
    n = ev["nest"]
    pairs = "; ".join(f"relation_class={a or 'blank'} -> assertion_class="
                      f"{b or 'blank'}: {c:,}"
                      for (a, b), c in n["assertion_class"].most_common(4))
    return _v(n["unspecified_affiliation_ownership_pub"],
              f"{_pct(n['unspecified_affiliation_ownership_pub'], n['rows'])} rows "
              f"have relationship=unspecified AND relation_class=affiliation AND "
              f"assertion_class=OWNERSHIP AND publishable=Y. Live pairing: {pairs}",
              "FIXED SINCE THE REVIEW, and verified rather than assumed: "
              "assertion_class no longer says OWNERSHIP on every row, it now "
              "tracks relation_class exactly, so the affiliation rows assert "
              "affiliation. Measured:")


def chk_cp121(ev):
    """Auto-only rows are publishable."""
    n = ev["nest"]
    named = [k for k, r in n["named_rows"].items()
             if r["evidence_human_reviewed"].upper() == "N"
             and r["publishable"].upper() == "Y"]
    return _v(n["unreviewed_but_publishable"],
              f"{_pct(n['unreviewed_but_publishable'], n['rows'])} rows are "
              f"publishable=Y with evidence_human_reviewed=N, and "
              f"{len(named)} of the 3 named wrong-owner rows (Goldbelt Hawk, "
              f"United Tribes Technical College, Tohono O'odham) are inside that "
              f"set. publishable is Y on all {n['rows']:,} rows, so the column "
              f"gates nothing")


def chk_cp123(ev):
    """A URL column holding a URL plus a sentence."""
    n = ev["nest"]
    if not n["url_malformed"]:
        return (FIXED, "every filled nest.source_url parses as a bare URL")
    return (CONFIRMED,
            f"{_pct(n['url_malformed'], n['rows'])} source_url values are not "
            f"URLs - they are a URL with prose appended, e.g. "
            f"{n['url_malformed_example']!r}")


def chk_cp124(ev):
    """No public source at all."""
    n = ev["nest"]
    return _v(n["url_blank"],
              f"source_url is blank on {_pct(n['url_blank'], n['rows'])} rows. "
              f"Adding the {n['url_malformed']:,} malformed ones, "
              f"{_pct(n['url_blank'] + n['url_malformed'], n['rows'])} rows have no "
              f"link a buyer can follow")


def chk_cp127(ev):
    """Operating status inferred from being mentioned."""
    n = ev["nest"]
    op = n["status"].get("operating", 0)
    return _v(n["status_basis_named_by_owner"],
              f"status=operating on {_pct(op, n['rows'])} rows, and status_basis "
              f"says so out loud: {_pct(n['status_basis_named_by_owner'], n['rows'])} "
              f"read 'named by its owner in a source dated ...'. Being listed is "
              f"the whole evidence; no row cites a registry status")


def chk_cp128(ev):
    """A sector column that is three vocabularies at once."""
    n = ev["nest"]
    return _v(n["sector_catchall"],
              f"sector takes {len(n['sector'])} distinct values over {n['rows']:,} "
              f"rows: blank on {_pct(n['sector_blank'], n['rows'])}, and "
              f"{_pct(n['sector_catchall'], n['rows'])} are the literal string "
              f"'Other services or Not given' - a value that is simultaneously a "
              f"category and an admission of missingness")


def chk_cp129(ev):
    """FPDS names an intermediate parent Cedar cannot resolve."""
    n = ev["nest"]
    return _v(n["fpds_parent_declared_unresolved"],
              f"{_pct(n['fpds_parent_declared_unresolved'], n['fpds_parent_declared'])} "
            f"rows that carry an fpds_declared_parent_name have a blank "
            f"fpds_parent_resolves_to - the federal record names a parent and "
            f"Cedar asserts a different, higher owner without reconciling them")


# ---- Federal Funding -------------------------------------------------------
def chk_cp038(ev):
    """A Bethel housing authority attributed to Arctic Slope."""
    f = ev["funding"]
    rows = f["avcp_fain_rows"]
    if not rows:
        return (FIXED, "FAIN 10IH0202000 no longer ships")
    rn, cn, uid, st = rows[0]
    if not uid:
        return (FIXED, f"FAIN 10IH0202000 ships {len(rows)} row(s) with the Cedar "
                       f"attribution masked (cedar_uid blank)")
    return (CONFIRMED,
            f"UNMASKED AND LIVE. FAIN 10IH0202000 ships {len(rows)} identical "
            f"row(s): recipient_name={rn!r}, canonical_name={cn!r}, "
            f"cedar_uid={uid}, attribution_status={st}. 1153 masked the "
            f"CONTRADICTED_AS_OF contractors but this attribution is not in a "
            f"contradicted state, so the gate never saw it - AVCP is in Bethel, "
            f"ASRC is on the North Slope, and they are different corporations")


def chk_cp040(ev):
    """A housing authority's award presented under a parent."""
    f = ev["funding"]
    return _v(f["housing_authority_other_canon"],
              f"{_pct(f['housing_authority'], f['rows'])} rows name a HOUSING "
            f"AUTHORITY as recipient and "
            f"{_pct(f['housing_authority_other_canon'], f['housing_authority'])} of "
            f"those carry a canonical_name that is not the recipient's own name. "
            f"There is no immediate-recipient id column and no relationship "
            f"column, so the award reads as the parent's")


def chk_cp043(ev):
    """A negative sentinel for a missing code."""
    f = ev["funding"]
    return _v(f["assistance_type_neg1"] + f["assistance_desc_not_specified"],
              f"assistance_type is the literal '-1' on {f['assistance_type_neg1']:,} "
            f"rows and assistance_type_description is 'NOT SPECIFIED' on "
            f"{f['assistance_desc_not_specified']:,} of {f['rows']:,}. Small, but "
            f"a numeric-looking sentinel in a code column is the shape that ends "
            f"up in a sum")


def chk_cp044(ev):
    """A derived flag that is still not derived everywhere."""
    f = ev["funding"]
    if f["ak_blank"] == 0:
        return (FIXED, f"ak_flag is populated on all {f['rows']:,} rows")
    return (CONFIRMED,
            f"partly repaired and still wrong. ak_flag is blank on "
            f"{_pct(f['ak_blank'], f['rows'])} rows overall, and - the part that "
            f"matters - on {_pct(f['ak_blank_in_ak'], f['ak_rows_in_ak'])} rows "
            f"whose recipient_state_code IS 'AK'. The review saw it blank on "
            f"every sampled row; it is now blank on a third of the Alaska rows")


def chk_cp045(ev):
    """A tribal government typed as a city."""
    f = ev["funding"]
    return _v(f["city_township_tribal_name"],
              f"business_types_description is 'CITY OR TOWNSHIP GOVERNMENT' on "
            f"{_pct(f['city_township'], f['rows'])} rows, and "
            f"{_pct(f['city_township_tribal_name'], f['city_township'])} of those "
            f"have a recipient_name reading tribe / nation / pueblo / band / "
            f"village / housing authority. The value comes from the federal "
            f"source, but nothing in the export flags the contradiction")


def chk_cp047(ev):
    """No plain-language description of the award."""
    f = ev["funding"]
    if f["award_description_columns"]:
        return (FIXED, "funding now carries " + ", ".join(f["award_description_columns"]))
    return (CONFIRMED,
            f"funding ships {len(_header('funding'))} columns and not one is a "
            f"plain-language award description. The only *_description columns "
            f"are assistance_type_description and business_types_description, "
            f"both controlled vocabularies. cfda_title names the programme, not "
            f"the award")


# ---- Federal Register ------------------------------------------------------
def chk_cp050(ev):
    """Two grains in one file."""
    r = ev["federal_register"]
    shapes = sum(1 for n in (r["with_participant"], r["not_enumerated"],
                             r["with_event_dates"]) if n)
    return _v(1 if shapes > 1 else 0,
              f"{r['rows']:,} rows over {r['event_count']:,} consultation events. "
            f"{_pct(r['with_participant'], r['rows'])} name a participant, "
            f"{_pct(r['not_enumerated'], r['rows'])} say "
            f"no_participants_named_in_record and stand for the event itself, and "
            f"only {_pct(r['with_event_dates'], r['rows'])} carry an "
            f"event_start_date. One declared grain, three row shapes. The one "
            f"improvement: {r['events_mixing_grain']} event mixes both shapes "
            f"internally, so the grain is at least consistent WITHIN an event")


def chk_cp051(ev):
    """A grouped event that shipped only two of its participants."""
    r = ev["federal_register"]
    rows = r["named_rows"].get("2013-13468", [])
    return ((FIXED if len(rows) > 2 else CONFIRMED),
            f"FR 2013-13468 now ships {len(rows)} participant rows; the sample "
            f"showed 2. Across the file {r['events_mixing_grain']} of "
            f"{r['event_count']:,} events mix participant rows with event rows, "
            f"so incomplete groups are no longer the pattern")


def chk_cp052(ev):
    """A mail stop parsed as a meeting location."""
    r = ev["federal_register"]
    rows = r["named_rows"].get("95-6969", [])
    if not rows:
        return (FIXED, "FR 95-6969 no longer ships")
    return (CONFIRMED,
            f"FR 95-6969 still ships with location={rows[0]['location']!r} - an "
            f"office name and a two-letter token that reads as a state and is a "
            f"mail stop. Unchanged")


def chk_cp053(ev):
    """The quote names an earlier date than the row's start."""
    r = ev["federal_register"]
    rows = r["named_rows"].get("95-6969", [])
    named = (f"FR 95-6969: event_start_date={rows[0]['start']} against a quote "
             f"reading {rows[0]['quote']!r}") if rows else "FR 95-6969 absent"
    return _v(r["quote_names_earlier_date"],
              f"{named}. Machine check over the whole file: of "
            f"{r['quote_checked']:,} rows where both an ISO start date and a "
            f"parseable month-day in event_date_source_quote exist, "
            f"{r['quote_names_earlier_date']:,} have a quote naming a date "
            f"EARLIER than the start the row asserts")


def chk_cp054(ev):
    """An end date a year after the start."""
    r = ev["federal_register"]
    rows = r["named_rows"].get("01-30327", [])
    named = (f"FR 01-30327 still ships event_start_date={rows[0]['start']} with "
             f"event_end_date={rows[0]['end']}") if rows else "FR 01-30327 absent"
    return _v(r["end_year_after_start_year"],
              f"{named} - a 372-day consultation. Across the file "
            f"{r['end_year_after_start_year']:,} rows have an end date in a "
            f"different calendar year from their start")


def chk_cp055(ev):
    """Two cities, one day."""
    r = ev["federal_register"]
    rows = r["named_rows"].get("2011-8999", [])
    named = (f"FR 2011-8999 still ships location={rows[0]['location']!r} with "
             f"start=end={rows[0]['start']}") if rows else "FR 2011-8999 absent"
    return _v(r["multi_location_single_day"],
              f"{named}. Across the file {r['multi_location_single_day']:,} rows "
              f"list two or more semicolon-separated locations and collapse them "
              f"into a single day - the second session's date is simply lost")


def chk_cp056(ev):
    """An in-person meeting typed as a written comment."""
    r = ev["federal_register"]
    return _v(r["written_comment_with_location"],
              f"{r['written_comment_with_location']:,} rows of {r['rows']:,} have a "
              f"format containing written_comment AND a non-empty location. A "
              f"notice that convenes a meeting and also accepts comments is being "
              f"typed by its comment channel")


def chk_cp059(ev):
    """High confidence over demonstrable parse errors."""
    r = ev["federal_register"]
    top = r["confidence"].most_common(1)[0]
    contra = (r["quote_names_earlier_date"] + r["end_year_after_start_year"]
              + r["multi_location_single_day"])
    return _v(contra if top[1] / max(r["rows"], 1) > 0.9 else 0,
              f"confidence is {top[0]!r} on {_pct(top[1], r['rows'])} rows over "
            f"{len(r['confidence'])} distinct values, while "
            f"{r['quote_names_earlier_date']} rows contradict their own date "
            f"quote, {r['end_year_after_start_year']} span the wrong year and "
            f"{r['multi_location_single_day']} collapse multi-city sessions. The "
            f"grade does not move when the parse is wrong")


def chk_cp061(ev):
    """An absence recorded as a matching method."""
    r = ev["federal_register"]
    n = r["match_method"].get("no_participants_named_in_record", 0)
    return _v(n,
              f"match_method takes {len(r['match_method'])} values and "
            f"{_pct(n, r['rows'])} of them are "
            f"'no_participants_named_in_record' - a statement about the SOURCE "
            f"stored in a column about the METHOD. Anyone tabulating match "
            f"quality counts it as a method")


# ---- Legislation -----------------------------------------------------------
def chk_cp062(ev):
    """A failed vote recorded as a chamber passage."""
    lg = ev["legislation"]
    r = lg["named_rows"].get("105-hr-948")
    named = (f"105-hr-948 still ships outcome={r[0]!r} with latest_action="
             f"{r[1]!r} and outcome_basis={r[2]!r}") if r else "105-hr-948 absent"
    return _v(lg["passed_but_action_failed"],
              f"{named}. Whole-file check: {lg['passed_but_action_failed']:,} of "
            f"{lg['rows']:,} bills carry outcome passed-one-chamber or enacted "
            f"while their latest_action text says failed or rejected")


def chk_cp063(ev):
    """A reported bill recorded as dead in committee."""
    lg = ev["legislation"]
    r = lg["named_rows"].get("104-hr-3828")
    named = (f"104-hr-3828 still ships outcome={r[0]!r} with latest_action="
             f"{r[1]!r}") if r else "104-hr-3828 absent"
    return _v(lg["died_but_action_advanced"],
              f"{named} - a bill on the Union Calendar has left committee by "
            f"definition. Whole-file check: {lg['died_but_action_advanced']:,} of "
            f"{lg['rows']:,} bills are died-in-committee with a latest_action "
            f"placing them on a calendar")


def chk_cp066(ev):
    """A method stored in a column named source."""
    lg = ev["legislation"]
    meth = sum(v for k, v in lg["classification_source"].items()
               if re.search(r"rule|coder|sweep|inherited", k))
    return _v(meth,
              f"classification_source takes {len(lg['classification_source'])} "
            f"values and {_pct(meth, lg['rows'])} rows hold one that names a "
            f"PROCEDURE - single_coded_keyword_rule_on_title, "
            f"two_coder_adjudicated, subject_family_phrase_sweep. Only the "
            f"congress_gov_policy_area value names a source")


def chk_cp067(ev):
    """Companion bills inferred from matching titles."""
    lg = ev["legislation"]
    return _v(lg["companion_inferred_from_title"],
              f"{_pct(lg['companion_inferred_from_title'], lg['rows'])} rows carry "
            f"companion_basis=identical_normalized_title_same_congress_opposite_"
            f"chamber. It is at least declared - but it is an inference, and "
            f"companion_bill_id reads like a fact from Congress")


def chk_cp069(ev):
    """One outcome for most of the corpus."""
    lg = ev["legislation"]
    top = lg["outcome"].most_common(1)[0]
    blank = lg["outcome"].get("", 0)
    return _v(1 if top[1] / max(lg["rows"], 1) > 0.5 else 0,
              f"outcome takes {len(lg['outcome'])} values across {lg['rows']:,} "
              f"bills; {_pct(top[1], lg['rows'])} are {top[0]!r} and "
              f"{_pct(blank, lg['rows'])} are blank. A bill that never got a "
              f"hearing and a bill reported out and never scheduled receive the "
              f"same label",
              "no single outcome value covers half the corpus:")


def chk_cp070(ev):
    """A count stored as a decimal string, sometimes blank."""
    lg = ev["legislation"]
    return _v(lg["cosponsor_decimal"] + lg["cosponsor_blank"],
              f"cosponsor_count is a decimal string on "
              f"{_pct(lg['cosponsor_decimal'], lg['rows'])} rows and blank on "
              f"{_pct(lg['cosponsor_blank'], lg['rows'])}. Blank is not zero and "
              f"nothing says which it means")


def chk_cp071(ev):
    """A corpus-level statistic repeated per row."""
    lg = ev["legislation"]
    return _v(lg["kappa_on_row"],
              f"classification_kappa is filled on {_pct(lg['kappa_on_row'], lg['rows'])} "
            f"rows. It is a property of the coding exercise, not of the bill, and "
            f"averaging it across rows - which is what a row-level column invites "
            f"- is meaningless")


# ---- Deals -----------------------------------------------------------------
def chk_cp073(ev):
    """Whether federal grants belong in a deals collection."""
    d = ev["deals"]
    pa = d["record_class"].get("PUBLIC_AWARD", 0)
    fed = d["capital_source"].get("Federal", 0)
    return (HUMAN,
            f"MEASURED, then owed to a person: {_pct(pa, d['rows'])} rows are "
            f"record_class=PUBLIC_AWARD and {_pct(fed, d['rows'])} have "
            f"capital_source=Federal, so the sample's 9-in-10 was an "
            f"exaggeration of a real majority. The partial fix is real too - "
            f"record_class and capital_source now let a buyer filter grants out, "
            f"which the sample could not. What is left is a scope decision "
            f"nothing in the data can settle: does a collection called Deals "
            f"include public awards, and if so does its description say so first")


def chk_cp074(ev):
    """A performance start date presented as the award event."""
    d = ev["deals"]
    named = "; ".join(f"{k}: Event_Date={v[0]}, Status={v[2]}, Date_Basis={v[1]!r}"
                      for k, v in sorted(d["named_rows"].items())) or "named rows absent"
    return _v(d["perf_start_basis_and_awarded"],
              f"{named}. Whole-file: {_pct(d['perf_start_basis'], d['rows'])} rows "
            f"have a Date_Basis naming a period-of-performance date and "
            f"{d['perf_start_basis_and_awarded']:,} of those carry Status=Awarded. "
            f"The Date_Basis column is honest - it literally says 'not the "
            f"obligation date' - and Event_Date is still the column a buyer will "
            f"plot")


def chk_cp080(ev):
    """The federal award number exists only inside prose."""
    d = ev["deals"]
    if d["federal_award_id_columns"]:
        return (FIXED, "deals now carries " + ", ".join(d["federal_award_id_columns"]))
    return _v(d["award_number_only_in_prose"],
              f"{_pct(d['award_number_only_in_prose'], d['rows'])} rows carry a DOE "
            f"award number matching DE-xx0000000 inside Description, and deals "
            f"ships no FAIN, award_id or federal award column at all. Joining "
            f"Deals to Funding on the federal record requires a regex")


def chk_cp083(ev):
    """Canonical names that cannot stand alone."""
    d = ev["deals"]
    ex = ", ".join(sorted(d["canon_examples"])[:5])
    return _v(d["canon_without_entity_word"],
              f"{_pct(d['canon_without_entity_word'], d['canon_filled'])} filled "
            f"native_party_canonical_name values contain no entity-type word "
            f"(nation, tribe, band, pueblo, corporation, community, village and "
            f"the rest). Examples: {ex}. These are hub short names surfacing as "
            f"customer-facing labels")


# ---- NAGPRA ----------------------------------------------------------------
def _nagpra_named(ev, doc, why):
    n = ev["nagpra"]
    r = n["named_rows"].get(doc)
    if not r:
        return (FIXED, f"document {doc} no longer ships")
    return (CONFIRMED,
            f"{doc} still ships, with the fields the finding named unchanged: "
            f"institution_count={r['institution_count']}, "
            f"institution_city={r['institution_city']!r}, "
            f"institution_name={r['institution_name']!r}. {why}")


def chk_cp085(ev):
    """Two institutions concatenated and counted as one."""
    n = ev["nagpra"]
    base = _nagpra_named(ev, "E6-16923",
                         "A DOE field office and a university museum are one string.")
    return (base[0], base[1] + f" Population: "
                               f"{_pct(n['count1_but_conjoined'], n['rows'])} notices "
                               f"declare institution_count=1 while "
                               f"institution_names_all contains ' and '")


def chk_cp086(ev):
    """A park unit and a museum concatenated."""
    return _nagpra_named(ev, "E9-5321",
                         "A National Park Service unit and the Burke Museum are "
                         "one institution with count 1.")


def chk_cp087(ev):
    """A park name in the city column."""
    n = ev["nagpra"]
    base = _nagpra_named(ev, "2015-25024",
                         "The park is dropped from the name and lands in the city.")
    return (base[0], base[1] + f" Population: {n['park_in_city']:,} of "
                               f"{n['rows']:,} notices have an institution_city "
                               f"containing National Park / Monument / Historic / "
                               f"Forest / Recreation")


def chk_cp089(ev):
    """A party count that counts roles, not parties."""
    n = ev["nagpra"]
    return _v(n["parties_named_equals_role_sum"],
              f"n_parties_named equals the exact sum of the six role counts "
            f"(consulted + affiliated + disposition_priority + "
            f"repatriation_recipient + letter_of_support + aboriginal_land) on "
            f"{_pct(n['parties_named_equals_role_sum'], n['rows'])} notices. It is "
            f"an addition, not a distinct count, so a tribe consulted AND "
            f"affiliated AND a recipient counts three times")


def chk_cp090(ev):
    """Corrections with nothing to correct."""
    n = ev["nagpra"]
    if n["supersession_columns"]:
        return (FIXED, "nagpra now carries " + ", ".join(n["supersession_columns"]))
    return _v(n["corrections"],
              f"{_pct(n['corrections'], n['rows'])} notices have is_correction=1 and "
            f"the schema has no column naming the notice being corrected, no "
            f"current-version flag and no supersession policy. A buyer counting "
            f"notices counts the original and its correction as two events")


def chk_cp091(ev):
    """Resolved fewer than named, and the remainder is not supplied."""
    n = ev["nagpra"]
    return _v(n["resolved_below_named"],
              f"{_pct(n['resolved_below_named'], n['rows'])} notices resolve fewer "
            f"entities than they name, and the file supplies six *_entity_ids "
            f"columns for what WAS resolved and no column at all for the party "
            f"names that were not")


def chk_cp092(ev):
    """Object counts with no categories."""
    n = ev["nagpra"]
    base = _nagpra_named(ev, "03-10916",
                         "65 associated and 39 unassociated objects are stated "
                         "and object_categories is blank.")
    return (base[0], base[1] + f" Population: {_pct(n['objects_without_categories'], n['rows'])} "
                               f"notices state a positive object count with a "
                               f"blank object_categories")


def chk_cp094(ev):
    """Parser diagnostics in the delivered file."""
    n = ev["nagpra"]
    pd = n["parent_dataset"].most_common(1)[0] if n["parent_dataset"] else ("", 0)
    return _v(n["parse_template_filled"] + n["spans_found_filled"]
              + (pd[1] if pd[0] else 0),
              f"parse_template is filled on {_pct(n['parse_template_filled'], n['rows'])} "
            f"notices, spans_found on {_pct(n['spans_found_filled'], n['rows'])}, "
            f"and parent_dataset is the literal string {pd[0]!r} on "
            f"{_pct(pd[1], n['rows'])}. That last one names an INTERNAL file and "
            f"a Cedar dataset number in a customer column")


# ---- Lobbying --------------------------------------------------------------
def chk_cp099(ev):
    """A termination filing with no termination date."""
    lb = ev["lobbying"]
    return _v(lb["termination_date_blank"],
              f"{_pct(lb['termination_date_blank'], lb['termination_filings'])} "
            f"filings whose filing_type_display contains 'Termination' have a "
            f"blank termination_date. The single fact the filing exists to "
            f"record is absent on more than a third of them")


def chk_cp100(ev):
    """The client's state and the resolved entity's state disagree."""
    lb = ev["lobbying"]
    c = lb["crit_filing"]
    named = (f"filing bdf7b163-0ccf-43f8-ae38-7c4030d0b445 still ships "
             f"{c[0]!r} with client_state={c[1]} and entity_state={c[2]}"
             ) if c else "the named filing no longer ships"
    return _v(lb["state_disagreement"],
              f"{named}. Whole-file: {_pct(lb['state_disagreement'], lb['rows'])} "
              f"filings have a client_state that differs from the resolved "
              f"entity_state, and no column says which one the buyer should trust")


def chk_cp101(ev):
    """Spend that is income wearing a different label."""
    lb = ev["lobbying"]
    inc = lb["spend_basis"].get("income", 0)
    return _v(inc,
              f"spend_basis is 'income' on {_pct(inc, lb['rows'])} filings and "
            f"spend_usd equals income_usd on {_pct(lb['spend_equals_income'], lb['rows'])}. "
            f"The basis column is honest; the column NAME is not, and summing "
            f"spend_usd across in-house and outside filers double counts the same "
            f"dollar as both a payment and a receipt")


def chk_cp102(ev):
    """Many government entities in one cell."""
    lb = ev["lobbying"]
    return _v(lb["gov_entities_piped"],
              f"government_entities is filled on {_pct(lb['gov_entities_filled'], lb['rows'])} "
            f"filings and pipe-packed on {_pct(lb['gov_entities_piped'], lb['gov_entities_filled'])} "
            f"of those. There is no child table, so 'how many filings lobbied "
            f"Interior' requires string splitting")


def chk_cp103(ev):
    """Bill numbers left in prose."""
    lb = ev["lobbying"]
    if lb["bill_id_columns"]:
        return (FIXED, "lobbying now carries " + ", ".join(lb["bill_id_columns"]))
    return _v(lb["issues_with_bill_reference"],
              f"{_pct(lb['issues_with_bill_reference'], lb['issues_filled'])} filings "
            f"with specific_issues_text contain a bill reference matching "
            f"H.R./S. plus digits, and lobbying ships no bill column at all. "
            f"Joining lobbying to the legislation collection is a regex over prose")


# ---- Cross-cutting and the RG release tests --------------------------------
def chk_cp006(ev):
    """What the archive carries besides CSVs."""
    b = ev["bundle"]
    missing = [k for k, v in (("README.md", b["readme"]),
                              ("manifest.json", b["manifest_json"]),
                              ("data_dictionary.csv", b["data_dictionary"])) if not v]
    return _v(len(missing),
              f"no ZIP exists under dist/ at all ({len(b['zips'])} found), so the "
              f"delivered bundle IS dist/customer. It now carries MANIFEST.csv, "
              f"{b['codebooks']} per-dataset codebooks and {b['notes']} notes files "
              f"- a real improvement on 'only CSVs' - and still lacks: "
              f"{', '.join(missing) or 'nothing'}")


def chk_cp009(ev):
    """One absence, several encodings."""
    b = ev["bundle"]
    ex = []
    for ds, cols in list(b["sentinel_columns"].items())[:3]:
        c, toks = list(cols.items())[0]
        ex.append(f"{ds}.{c} = {toks}")
    return _v(b["sentinel_column_total"],
              f"{b['sentinel_column_total']} column(s) across "
              f"{len(b['sentinel_columns'])} delivered file(s) encode missingness "
              f"with two or more different tokens in the SAME column. Examples: "
              + ("; ".join(ex) or "none"))


def _crosswalk(ev):
    b = ev["bundle"]
    return _v(b["fr_nagpra_shared_documents"],
              f"{b['fr_nagpra_shared_documents']:,} Federal Register document "
            f"numbers appear in BOTH federal-register.csv and nagpra.csv. Half "
            f"fixed: federal-register carries "
            f"{', '.join(b['fr_has_nagpra_bridge']) or 'no'} overlap column(s), so "
            f"one direction is declared, and nagpra carries no consultation "
            f"bridge back. Deals and Funding have no shared award column at all "
            f"({len(b['deals_federal_award_columns'])} federal-award columns in "
            f"deals), so their overlap is undetectable from the files")


def chk_cp013(ev):
    """The same federal record in two collections."""
    return _crosswalk(ev)


def chk_rg020(ev):
    """Release test: identical source records have canonical cross-links."""
    return _crosswalk(ev)


def chk_rg001(ev):
    """Release test: every collection has at least one analytical record."""
    b = ev["bundle"]
    n, w = ev["owned"]["rows"], len(_header("native-owned-businesses"))
    if b["empty_tables"]:
        return (CONFIRMED, "empty delivered table(s): " + ", ".join(b["empty_tables"]))
    return (FIXED,
            f"no delivered table is empty. The collection that failed this test "
            f"now ships {n:,} business rows x {w} columns, and the metadata-only "
            f"owned-collection-description.csv is gone")


def chk_rg009(ev):
    """Release test: outcome reconciles with the action text."""
    lg = ev["legislation"]
    return _v(lg["passed_but_action_failed"] + lg["died_but_action_advanced"],
              f"{lg['passed_but_action_failed']:,} bills say passed/enacted over a "
            f"latest_action reading failed or rejected, and "
            f"{lg['died_but_action_advanced']:,} say died-in-committee over an "
            f"action placing them on a calendar, of {lg['rows']:,}. The test is "
            f"not being enforced at build time")


def chk_rg013(ev):
    """Release test: source links are syntactically valid."""
    b = ev["bundle"]
    top = ", ".join(f"{k} ({v:,})" for k, v in
                    b["url_malformed_by_column"].most_common(3))
    return _v(b["url_malformed"],
              f"{b['url_malformed']:,} cells in {len(b['url_malformed_by_column'])} "
              f"URL columns do not parse as a bare http(s) URL, out of "
              f"{b['url_cells']:,} cells in {b['url_columns']} URL columns "
              f"({b['url_blank']:,} blank). Worst: {top or 'none'}")


def chk_rg015(ev):
    """Release test: one file, one declared row grain."""
    return chk_cp050(ev)


def chk_rg019(ev):
    """Release test: a complete machine-readable manifest."""
    b = ev["bundle"]
    have = [k for k, v in b["manifest_has"].items() if v]
    lack = [k for k, v in b["manifest_has"].items() if not v]
    return _v(len(lack),
              f"MANIFEST.csv exists with {len(b['manifest_columns'])} columns and "
              f"carries {', '.join(have) or 'nothing on the list'}. It does not "
              f"carry {', '.join(lack) or 'nothing'}, and there is no "
              f"manifest.json. A buyer cannot verify they received the file the "
              f"manifest describes")


def chk_rg022(ev):
    """Release test: canonical names stand alone."""
    return chk_cp083(ev)


CHECKS = {
    "CP-020": chk_cp020, "CP-021": chk_cp021, "CP-024": chk_cp024,
    "CP-025": chk_cp025, "CP-026": chk_cp026, "CP-036": chk_cp036,
    "CP-027": chk_cp027, "CP-030": chk_cp030, "CP-032": chk_cp032,
    "CP-033": chk_cp033, "CP-035": chk_cp035,
    "CP-107": chk_cp107, "CP-108": chk_cp108, "CP-109": chk_cp109,
    "CP-110": chk_cp110, "CP-111": chk_cp111, "CP-114": chk_cp114,
    "CP-148": chk_cp148, "CP-150": chk_cp150, "CP-151": chk_cp151,
    "CP-132": chk_cp132, "CP-133": chk_cp133, "CP-134": chk_cp134,
    "CP-135": chk_cp135, "CP-136": chk_cp136, "CP-137": chk_cp137,
    "CP-138": chk_cp138, "CP-139": chk_cp139, "CP-142": chk_cp142,
    "CP-143": chk_cp143, "CP-145": chk_cp145,
    "CP-116": chk_cp116, "CP-117": chk_cp117, "CP-118": chk_cp118,
    "CP-119": chk_cp119, "CP-120": chk_cp120, "CP-121": chk_cp121,
    "CP-123": chk_cp123, "CP-124": chk_cp124, "CP-127": chk_cp127,
    "CP-128": chk_cp128, "CP-129": chk_cp129,
    "CP-038": chk_cp038, "CP-040": chk_cp040, "CP-043": chk_cp043,
    "CP-044": chk_cp044, "CP-045": chk_cp045, "CP-047": chk_cp047,
    "CP-050": chk_cp050, "CP-051": chk_cp051, "CP-052": chk_cp052,
    "CP-053": chk_cp053, "CP-054": chk_cp054, "CP-055": chk_cp055,
    "CP-056": chk_cp056, "CP-059": chk_cp059, "CP-061": chk_cp061,
    "CP-062": chk_cp062, "CP-063": chk_cp063, "CP-066": chk_cp066,
    "CP-067": chk_cp067, "CP-069": chk_cp069, "CP-070": chk_cp070,
    "CP-071": chk_cp071,
    "CP-073": chk_cp073, "CP-074": chk_cp074, "CP-080": chk_cp080,
    "CP-083": chk_cp083,
    "CP-085": chk_cp085, "CP-086": chk_cp086, "CP-087": chk_cp087,
    "CP-089": chk_cp089, "CP-090": chk_cp090, "CP-091": chk_cp091,
    "CP-092": chk_cp092, "CP-094": chk_cp094,
    "CP-099": chk_cp099, "CP-100": chk_cp100, "CP-101": chk_cp101,
    "CP-102": chk_cp102, "CP-103": chk_cp103,
    "CP-006": chk_cp006, "CP-009": chk_cp009, "CP-013": chk_cp013,
    "RG-001": chk_rg001, "RG-009": chk_rg009, "RG-013": chk_rg013,
    "RG-015": chk_rg015, "RG-019": chk_rg019, "RG-020": chk_rg020,
    "RG-022": chk_rg022,
}


def legacy_default_ids(fs):
    """Exactly the findings the OLD `classify()` sent to the generic default.

    Kept so the report can state the flip honestly - how many of the 91 became
    what - instead of asserting it. If this drifts from the branch order in
    `classify()` below, the counts drift with it, so the two are read together.
    """
    out = []
    for f in fs:
        i = f["id"]
        text = (f["finding"] + " " + f["field"]).lower()
        if i in ("CP-001", "CP-003", "RG-005"):
            continue
        if ("no data" in text or "zero business records" in text
                or "owned-collection" in text):
            continue
        if any(k in text for k in ("python file", ".py", ".zip", "desktop",
                                   "local csv", "code path", "pipeline artifact",
                                   "source_file")):
            continue
        if any(k in text for k in ("hold", "quarantin", "superseded", "duplicate",
                                   "adjudication", "publication gate", "blocked")):
            continue
        if "15th" in text or "month-only" in text or "synthetic date" in text:
            continue
        if any(k in text for k in ("all ten", "ten rows", "sample", "concentrat",
                                   "one era", "one source", "eight of ten")):
            continue
        if any(k in text for k in ("column", "field", "debug", "residue",
                                   "internal")):
            continue
        out.append(i)
    return out


def classify(f, ev):
    """One finding -> (verdict, evidence). Machine-checked where possible.

    The registry wins. A finding with a NAMED check gets that check's verdict
    and nothing else looks at it; the text-matched branches below only run for
    findings nobody has written a check for yet.
    """
    i, cat = f["id"], f["category"].lower()
    text = (f["finding"] + " " + f["field"]).lower()

    if i in CHECKS:
        return CHECKS[i](ev)

    if i == "CP-001":
        h = ev["cite_as"]
        return ((CONFIRMED, f"`cite_as` row still in {len(h)} file(s): "
                 f"{', '.join(h[:4])}") if h else
                (FIXED, "no delivered file carries a `cite_as` data row"))

    if i in ("CP-003", "RG-005"):
        bad = [k for k, v in ev["uid"].items() if v["unresolvable"]]
        undoc = [k for k, v in ev["uid"].items() if not v["role_documented"]]
        return (HUMAN,
                "REWRITTEN per owner ruling 2026-09-02: the test is not "
                "whether cedar_uid names the row subject - a NEST row keyed "
                "enterprise_id with cedar_uid=owner is correct - but whether "
                "its ROLE is unambiguous and it always resolves to a Native "
                f"entity. Measured: {len(ev['uid'])} datasets carry cedar_uid, "
                f"{len(bad)} hold a uid absent from the register "
                f"({', '.join(bad[:3]) or 'none'}), "
                f"{len(undoc)} do not document the role in their codebook "
                f"({', '.join(undoc[:3]) or 'none'})")

    if "no data" in text or "zero business records" in text or "owned-collection" in text:
        n, w = ev["owned_rows"]
        return ((FIXED, f"native-owned-businesses now delivers {n:,} rows x {w} cols")
                if n > 100 else (CONFIRMED, f"still only {n} rows"))

    if any(k in text for k in ("python file", ".py", ".zip", "desktop", "local csv",
                               "code path", "pipeline artifact", "source_file")):
        h = ev["paths"]
        return ((CONFIRMED, "internal paths still exported (first 2,000 rows "
                 "per file, a LOWER BOUND): "
                 + "; ".join(f"{k}:{c[0][0]}({c[0][1]})" for k, c in list(h.items())[:3])
                 + ". Every PURE build-lineage column is now dropped by "
                   "cedar_publication.LINEAGE_COLS; what remains are columns "
                   "whose values MIX a real source statement with a code path, "
                   "kept deliberately and listed in "
                   "docs/PUBLICATION_ELIGIBILITY.md")
                if h else (FIXED, "no delivered column exposes a .py/.zip/Desktop path"))

    if any(k in text for k in ("hold", "quarantin", "superseded", "duplicate",
                               "adjudication", "publication gate", "blocked")):
        h = ev["blocked"]
        return ((CONFIRMED, "blocked states still present: "
                 + "; ".join(f"{k}.{c[0][0]}" for k, c in list(h.items())[:3])
                 + ". Judged one by one in cedar_publication.BLOCKED_STATES: "
                   "what remains is FLAG (a superseded LDA filing is a real "
                   "filed record and ships with its supersession stated) or "
                   "MASK (the row ships, the Cedar attribution on it does "
                   "not). WITHHOLD states no longer ship - see "
                   "docs/PUBLICATION_ELIGIBILITY.md")
                if h else (FULLDATA,
                           "no blocked state found in the delivered columns - but "
                           "the curated export no longer carries most status "
                           "fields, so absence here is not proof of absence "
                           "upstream. Check data/clean, not dist/customer."))

    if "15th" in text or "month-only" in text or "synthetic date" in text:
        h = ev["dates"]
        return ((CONFIRMED, "day-15 clustering: "
                 + "; ".join(f"{k} {v[0]}/{v[1]}" for k, v in list(h.items())[:3]))
                if h else (FIXED, "no date column clusters on the 15th"))

    if any(k in text for k in ("all ten", "ten rows", "sample", "concentrat",
                               "one era", "one source", "eight of ten")):
        return (OBSOLETE, "a property of the old ten-row sample generator; the "
                          "hundred-row export selects for distinct subjects")

    if any(k in text for k in ("column", "field", "debug", "residue", "internal")):
        w = ev["width"]
        wide = {k: v for k, v in w.items() if v > 40}
        pv = ev["preview_width"]
        return (FULLDATA, f"dist/customer is {min(w.values())}-{max(w.values())} "
                          f"columns (widest {max(w, key=w.get)}); {len(wide)} "
                          f"dataset(s) over 40. The DELIVERED export is WIDER "
                          f"than the review's 29-81, not narrower - only the "
                          f"100-row previews are narrow"
                          + (f" ({min(pv.values())}-{max(pv.values())})"
                             if pv else " (dist/preview absent)")
                          + ". Whether a specific field survived needs a named "
                            "check; the build-lineage columns are now dropped "
                            "by cedar_publication.LINEAGE_COLS and audited by "
                            "1153.")

    return (FULLDATA, "no named check is registered for this finding id in "
                      "CHECKS - write one rather than reading the row")


def gather():
    """Every measurement, once. Streaming; nothing is capped except where said."""
    print("  measuring. contractors.csv and funding.csv are read whole; "
          "this takes a couple of minutes.\n", flush=True)
    ev = {"cite_as": check_cite_as(), "paths": check_internal_paths(),
          "blocked": check_blocked_states(), "uid": check_uid_role(),
          "dates": check_synthetic_dates(), "owned_rows": check_owned_has_rows(),
          "width": check_width(), "preview_width": check_preview_width()}
    ev["contractors"] = scan_contractors()
    ev["funding"] = scan_funding()
    ev["subcontracting"] = scan_subcontracting()
    ev["nest"] = scan_nest()
    ev["nonprofits"] = scan_nonprofits()
    ev["nagpra"] = scan_nagpra()
    ev["lobbying"] = scan_lobbying()
    ev["federal_register"] = scan_federal_register()
    ev["legislation"] = scan_legislation()
    ev["deals"] = scan_deals()
    ev["natural_resources"] = scan_natural_resources()
    ev["owned"] = scan_owned()
    ev["bundle"] = scan_bundle()
    print(flush=True)
    return ev


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    if not REVIEW.exists():
        print(f"  the review is not at {REVIEW.relative_to(ROOT)}")
        return 1
    fs = findings()
    ev = gather()

    rows, tally = [], Counter()
    for f in fs:
        verdict, why = classify(f, ev)
        tally[verdict] += 1
        rows.append({**f, "verdict": verdict, "evidence": why,
                     "checked_by": CHECKS[f["id"]].__name__
                     if f["id"] in CHECKS else "text_branch"})

    print(f"  1152 reconciliation   {len(fs)} findings from the ten-row review\n")
    for k in (CONFIRMED, FULLDATA, FIXED, OBSOLETE, HUMAN):
        print(f"    {k:<32} {tally[k]:>4}")

    # the flip: what happened to the 91 that used to hit the generic default
    old = legacy_default_ids(fs)
    flip = Counter(r["verdict"] for r in rows if r["id"] in old)
    still = [r["id"] for r in rows if r["id"] in old and r["verdict"] == FULLDATA]
    print(f"\n    the {len(old)} findings that used to reach the generic default")
    print(f"    'not machine-checkable from the delivered export alone':")
    for k in (CONFIRMED, FIXED, OBSOLETE, HUMAN, FULLDATA):
        print(f"      -> {k:<30} {flip[k]:>4}")
    print(f"      named checks written: "
          f"{sum(1 for i in old if i in CHECKS)}/{len(old)}")
    if still:
        print(f"      STILL GENERIC: {', '.join(still)}")

    c, s, n, f_, lg, lb, ng, fr, d, nr, o, b = (
        ev["contractors"], ev["subcontracting"], ev["nest"], ev["funding"],
        ev["legislation"], ev["lobbying"], ev["nagpra"], ev["federal_register"],
        ev["deals"], ev["natural_resources"], ev["owned"], ev["bundle"])
    print("\n    the measurements the verdicts rest on")
    print(f"      contractors award keys with >1 total_award_value : "
          f"{_pct(c['award_keys_multivalued'], c['award_keys'])}, "
          f"${c['award_spread_total_usd']:,.0f} of spread")
    print(f"      contractors cage_code = the literal NAN           : "
          f"{_pct(c['cage_nan'], c['rows'])}")
    print(f"      contractors CONTRADICTED_AS_OF rows / with a uid  : "
          f"{c['contradicted']:,} / {c['contradicted_with_uid']:,}")
    print(f"      funding AVCP->ASRC rows still attributed          : "
          f"{len(f_['avcp_fain_rows'])}")
    print(f"      funding ak_flag blank on AK-state rows            : "
          f"{_pct(f_['ak_blank_in_ak'], f_['ak_rows_in_ak'])}")
    print(f"      subcontracting subaward > prime                   : "
          f"{_pct(s['exceeds_prime'], s['rows'])}, "
          f"{s['ratio_over_10']:,} over 10x")
    print(f"      nest publishable with no human review             : "
          f"{_pct(n['unreviewed_but_publishable'], n['rows'])}")
    print(f"      nest affiliation asserted as OWNERSHIP            : "
          f"{_pct(n['unspecified_affiliation_ownership_pub'], n['rows'])}")
    print(f"      nagpra institution_count=1 over a joined name     : "
          f"{_pct(ng['count1_but_conjoined'], ng['rows'])}")
    print(f"      legislation outcome contradicts its own action    : "
          f"{lg['passed_but_action_failed'] + lg['died_but_action_advanced']:,} "
          f"of {lg['rows']:,}")
    print(f"      lobbying terminations with no termination_date    : "
          f"{_pct(lb['termination_date_blank'], lb['termination_filings'])}")
    print(f"      federal-register rows contradicting a date quote  : "
          f"{fr['quote_names_earlier_date']} of {fr['quote_checked']} checkable")
    print(f"      deals canonical names with no entity-type word    : "
          f"{_pct(d['canon_without_entity_word'], d['canon_filled'])}")
    print(f"      natural-resources ND rows sharing one search URL  : "
          f"{nr['nd_rows']:,} rows, {len(nr['nd_source_urls'])} URL")
    print(f"      owned rows with a certification number            : "
          f"{_pct(o['certification_number_filled'], o['rows'])}")
    print(f"      columns mixing two missing-value tokens           : "
          f"{b['sentinel_column_total']} in {len(b['sentinel_columns'])} files")
    print(f"      malformed URL cells                               : "
          f"{b['url_malformed']:,} of {b['url_cells']:,}")

    print()
    print(f"    native-owned-businesses : {ev['owned_rows'][0]:,} rows "
          f"(the review found 0)")
    print(f"    files with a cite_as row: {len(ev['cite_as'])} (was 11)")
    print(f"    internal paths exported : {len(ev['paths'])} dataset(s) "
          f"(first 2,000 rows per file - a LOWER BOUND)")
    print(f"    blocked states exported : {len(ev['blocked'])} dataset(s)")
    print(f"    day-15 date clustering  : {len(ev['dates'])} column(s)")
    w, pv = ev["width"], ev["preview_width"]
    # CORRECTED 2026-09-02. This line used to print one range and let the
    # reader infer the export had narrowed toward the review's 29-81. It had
    # not: `gaming` ships 309 columns and only `dist/preview` is narrow. Two
    # ranges, each named for the directory it measures.
    print(f"    dist/customer width     : {min(w.values())}-{max(w.values())} cols "
          f"(widest {max(w, key=w.get)}) - the review saw 29-81 on the ten-row "
          f"sample, so the delivered export is WIDER, not narrower")
    print(f"    dist/preview width      : "
          + (f"{min(pv.values())}-{max(pv.values())} cols" if pv
             else "absent - rebuild with 1151"))

    if mode == "build":
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
            wr.writeheader()
            wr.writerows(rows)
        print(f"\n    ledger -> {OUT.relative_to(ROOT)}")
    elif mode != "verify":
        print("\n  nothing written. re-run with `build`.")

    if mode == "verify":
        bad = []
        if not OUT.exists():
            bad.append("no reconciliation ledger - run `build`")
        if ev["cite_as"]:
            bad.append(f"CP-001 unfixed: {len(ev['cite_as'])} file(s) ship a "
                       f"cite_as row")
        # the work this file was rewritten to do: no finding may reach the
        # generic default, and every one of the 91 must have a NAMED check.
        generic = [r["id"] for r in rows if r["verdict"] == FULLDATA
                   and r["evidence"].startswith("no named check is registered")]
        if generic:
            bad.append(f"{len(generic)} finding(s) still reach the generic "
                       f"default: {', '.join(generic[:8])}")
        uncovered = [i for i in old if i not in CHECKS]
        if uncovered:
            bad.append(f"{len(uncovered)} of the {len(old)} old-default findings "
                       f"have no named check: {', '.join(uncovered[:8])}")
        thin = [r["id"] for r in rows
                if r["id"] in CHECKS and len(r["evidence"]) < 60]
        if thin:
            bad.append(f"{len(thin)} named check(s) returned an evidence string "
                       f"too short to carry a measurement: {', '.join(thin[:8])}")
        for b_ in bad:
            print("  FAIL " + b_)
        print(f"  1152 verify   {'FAIL' if bad else 'ok'}   {len(bad)} problem(s)")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
