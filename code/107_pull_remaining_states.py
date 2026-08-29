#!/usr/bin/env python3
"""
Cedar Press 107 - the remaining state gaming regulators.

WHAT THIS BUILD IS FOR
----------------------
Property-level gaming revenue is the binding constraint on the whole gaming
programme. Residual elimination against NIGC regional totals cannot start until
more than two properties in the country carry a revenue figure. So this build
went looking for a third state that publishes per-property revenue, and for
anything that tightens a bound on the way.

WHAT IT FOUND, AND THE ONE CORRECTION THAT MATTERS
--------------------------------------------------
**WISCONSIN WAS MIS-CLOSED.** `docs/GAMING_CAPACITY_OFFICIAL_LOG.md` records
Wisconsin as bucket 3 - "no per-tribe breakdown anywhere" - on the strength of
the Department of Administration's aggregate bar charts. That is true of DOA.
It is not true of the state.

The **Legislative Fiscal Bureau** publishes an informational paper, *Tribal
Gaming in Wisconsin*, every two years. It carries:

  * **Table 1** - every Class III casino in the state, one row per property,
    with **electronic gaming devices and gaming tables at each**. Seven
    editions on disk (2013-2025) make that a dated per-property panel, not a
    snapshot.
  * **Table 3** - **lump-sum payments to the state per tribe**, 1999-00
    forward, by name.
  * **Table 2** - statewide tribal Class III net revenue, 1992 forward.

Wisconsin moves from bucket 3 to bucket 2. Arizona and Connecticut were the
only states whose own published record gave a per-casino floor; Wisconsin is
the third, and unlike the other two it reaches back to 2012.

It still publishes **no** per-tribe revenue, and that absence is now documented
from the instrument rather than inferred from a missing table - see the two
verbatim quotes in `ABSENCES` below. Wisconsin does not withhold the number;
the compacts forbid its disclosure. Those are different facts and a coverage
table must not render them the same way.

THE DEFECT THIS BUILD HAD TO SURVIVE
------------------------------------
`pdftotext -layout` shifted **every single row** of both Wisconsin tables.
Measured here, not assumed:

    Table 1, -layout      Ho-Chunk Wisconsin Dells 361 devices
    Table 1, positional   Ho-Chunk Wisconsin Dells 955 devices
                          (361 is Bad River's, one row above)

    Table 3, -layout      Red Cliff            $109,925,000
    Table 3, positional   Red Cliff                      $0
                          ($109,925,000 is Potawatomi's)

The -layout reading books $109.9M of Forest County Potawatomi's money onto Red
Cliff, whose Legendary Waters casino runs 241 devices. Every row is well-sourced and every row is
attached to the wrong nation - AGENTS.md's containment defect in the costume it
wore in Michigan and Arizona.

So this module never reads a table linearly. It reads **word positions**,
assigns numbers to columns by **right edge** (right edges are stable across
digit counts; left edges are not), and then **foots every numeric column
against the table's own printed TOTALS row**. An edition whose columns do not
foot is REFUSED, not published. Measured: all 7 Wisconsin editions foot exactly
on both device and table columns.

WHAT IS DELIBERATELY NOT PUBLISHED
----------------------------------
* **Statewide aggregates are context, never an allocation.** Arizona's
  $3,033,358,250 FY2025 aggregate GGR and Wisconsin's statewide net win series
  are emitted with `exclusion_flag = state_aggregate_not_allocatable` and
  `REGIONAL_GGR_CONTEXT`, so they can bound a residual and can never be mistaken
  for a property's revenue.
* **Cumulative windows are separated from annual figures by metric name.**
  Wisconsin's Table 3 leads with a single column spanning 1999-00 through
  2016-17. Following the Michigan precedent, it is extracted, footed, and then
  given its own metric name encoding the window plus an `exclusion_flag`. A
  cumulative published beside annuals is a double count waiting to happen.
* **A payment is not revenue.** Wisconsin's lump sums are compact-negotiated
  consideration, not a percentage of anything stated, so nothing is inverted.
  There is no rate and no base; `REVENUE_EVIDENCE` stays
  `NO_REVENUE_OBSERVATION` for every Wisconsin tribe.

RULES HONOURED
--------------
* Zero fabrication: every row carries `source_url` and a verbatim
  `source_quote`. Asserted before write.
* `resolve_entity` from `code/33_apply_party_rulings.py` is the only name
  matcher. Entity classes a gaming regulator cannot be talking about are
  REFUSED and queued, never guessed (the Chickasaw Children's Village defect).
* Facility resolution is exact-name-within-state, or the tribe's sole open
  property in that state, or refusal to the queue with candidates. No third
  tier, on purpose. A regulator's different casino name is an ALIAS, not a new
  property.
* `measurement_type` is typed from `cedar_domain.MeasurementType` on every row
  and `may_promote` is asserted at import.
* This build writes `data/clean/state_gaming_observations.csv`,
  `review/state_gaming_unresolved_<date>.csv`, its own raw tree and manifest,
  and ONE appended dataset block in the shared `codebook_master.csv` (backed up
  first, all other rows preserved, and see `write_codebook` for the clobber
  this file now repairs). It READS `gaming_facilities.csv`, the entity spine,
  the compact corpus and the vendor panel, and writes none of them.

WHAT THE THREE STATES LEFT TO DO LOOK LIKE
------------------------------------------
The queue is small and two of its items are worth real money:

* `single_property_attribution_proposed` would put $73,886,102.56 of 2019 slot
  net drop onto a NAMED property, which is the thing this whole programme is
  short of. It needs one ruling on whether Mohawk Bingo Palace is a Class III
  facility.
* `ny_derivation_blocked_missing_instrument` needs the operative Oneida Indian
  Nation of New York agreement and would then yield $282,734,881.48.
"""

import csv, sys, re, hashlib, collections, importlib.util
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw" / "external" / "state_gaming"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = "2026-08-07"

# ------------------------------------------------------------------ resolver
# AGENTS.md: "code/33_apply_party_rulings.py holds the ONE resolver. Import
# resolve_entity; never write another name matcher."
_spec = importlib.util.spec_from_file_location(
    "party_rulings", str(CEDAR / "code" / "33_apply_party_rulings.py"))
_pr = importlib.util.module_from_spec(_spec)
sys.modules["party_rulings"] = _pr
_spec.loader.exec_module(_pr)
resolve_entity = _pr.resolve_entity
norm = _pr.norm

_dspec = importlib.util.spec_from_file_location(
    "cedar_domain", str(CEDAR / "code" / "cedar_domain.py"))
_cd = importlib.util.module_from_spec(_dspec)
sys.modules["cedar_domain"] = _cd
_dspec.loader.exec_module(_cd)
MeasurementType = _cd.MeasurementType
may_promote = _cd.may_promote
REVENUE_EVIDENCE = _cd.REVENUE_EVIDENCE
NAME_TRAPS = _cd.NAME_TRAPS

# The promotion guard is enforced in code, not in prose. An authorised maximum
# and a projection may never become an operating count by relabelling.
for _bad in (MeasurementType.AUTHORIZED_MAXIMUM, MeasurementType.PROJECTED,
             MeasurementType.ENVIRONMENTAL_REVIEW_COUNT,
             MeasurementType.DERIVED_BOUND):
    assert not may_promote(_bad, MeasurementType.ACTIVE_FLOOR_COUNT), _bad
assert "NO_REVENUE_OBSERVATION" in REVENUE_EVIDENCE

# The classes a gaming regulator's device count or casino payment can never be
# about. Script 92 measured this: ten Michigan payment rows landed on a tribal
# college. A guard that refuses is not a matcher that guesses.
REFUSED_CLASSES = {
    "Tribal College or University", "BIE School", "Urban Indian Organization",
    "Native Community Development Financial Institution",
    "Native Financial Institution",
}

FIELDS = [
    "observation_id", "state", "facility_id", "facility_name",
    "facility_name_as_published", "tribe_id", "tribe_canonical_name",
    "tribe_name_as_published", "metric", "metric_class", "measurement_status",
    "measurement_type", "revenue_evidence", "value", "unit", "applies_to",
    "as_of_date", "as_of_date_precision", "period_start", "period_end",
    "source_authority", "source_document_type", "source_url", "source_page",
    "source_quote", "facility_match_method", "tribe_match_method",
    "exclusion_flag", "exclusion_reason", "fetched_date", "built_date",
]

QUEUE_FIELDS = [
    "queue_id", "issue_type", "state", "name_as_published", "n_occurrences",
    "context", "evidence", "candidate_properties", "question", "source_url",
    "YOUR_RULING",
]

rows = []
_queue = {}          # (issue, state, name) -> row. One item per decision.
_qn = collections.Counter()


def q(issue, state, name, context, evidence, question, url, candidates=""):
    """One queue item per DECISION, not per occurrence.

    The same casino name appears in all seven Wisconsin editions. Emitting
    seven identical rows would make the queue look seven times more expensive
    than it is and would ask a human the same question seven times. Occurrences
    are counted and the contexts collected instead."""
    key = (issue, state, name)
    if key in _queue:
        r = _queue[key]
        r["n_occurrences"] += 1
        if context and context not in r["context"]:
            r["context"] = (r["context"] + "; " + context)[:600]
        if candidates and not r["candidate_properties"]:
            r["candidate_properties"] = candidates
        return
    _qn[issue] += 1
    _queue[key] = {
        "queue_id": f"SG-{issue[:18].upper()}-{_qn[issue]:04d}",
        "issue_type": issue, "state": state, "name_as_published": name,
        "n_occurrences": 1, "context": context, "evidence": evidence,
        "candidate_properties": candidates, "question": question,
        "source_url": url, "YOUR_RULING": "",
    }


# ===========================================================================
# POSITIONAL TABLE READER
#
# Never read a regulator's table linearly. The failure is invisible in the
# output and it moves money onto the wrong nation.
# ===========================================================================

def page_rows(page, tol=3.0):
    """Words grouped into baselines. Returns [(top, [word, ...]), ...]."""
    buckets = {}
    for w in page.extract_words(use_text_flow=False, keep_blank_chars=False):
        key = next((k for k in buckets if abs(k - w["top"]) <= tol), None)
        buckets.setdefault(w["top"] if key is None else key, []).append(w)
    return [(t, sorted(ws, key=lambda z: z["x0"]))
            for t, ws in sorted(buckets.items())]


NUM_RE = re.compile(r"^\$?\(?-?[\d,]+\)?$")


def as_number(tok):
    t = tok.replace("$", "").replace(",", "").strip()
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    if not re.fullmatch(r"-?\d+", t or ""):
        return None
    v = int(t)
    return -v if neg else v


def numbers_right_of(words, x_min):
    """Numeric tokens to the right of x_min, in left-to-right order, carrying
    their RIGHT edge. Right edges are stable across digit counts; left edges
    are not, which is why every column assignment in this file uses x1."""
    out = []
    for w in words:
        if w["x0"] < x_min:
            continue
        v = as_number(w["text"])
        if v is not None and NUM_RE.match(w["text"]):
            out.append((w["x1"], v, w["text"]))
    return out


def text_between(words, lo, hi):
    return clean_glyphs(" ".join(w["text"] for w in words
                                 if lo <= w["x0"] < hi).strip())


def clean_glyphs(s):
    """The LFB sets its casino names with an en-dash in a font whose encoding
    pdfplumber cannot map, so it arrives as U+FFFD: "Ho-Chunk Gaming <?>
    Wisconsin Dells". The character is a separator, not part of the name, and
    `norm()` discards it either way - but an undecodable glyph must not reach a
    published `facility_name_as_published`. Transcribed to a hyphen, and
    recorded here rather than silently."""
    return s.replace("�", "-").replace("–", "-").replace("—", "-")


# ===========================================================================
# WISCONSIN - Legislative Fiscal Bureau, "Tribal Gaming in Wisconsin"
# ===========================================================================

WI_EDITIONS = [
    # (edition year, file, the "as of" the paper prints on Table 1)
    ("2025", "lfb_tribal_gaming_2025.pdf"),
    ("2023", "lfb_tribal_gaming_2023.pdf"),
    ("2021", "lfb_tribal_gaming_2021.pdf"),
    ("2019", "lfb_tribal_gaming_2019.pdf"),
    ("2017", "lfb_tribal_gaming_2017.pdf"),
    ("2015", "lfb_tribal_gaming_2015.pdf"),
    ("2013", "lfb_tribal_gaming_2013.pdf"),
]

WI_URL = ("https://docs.legis.wisconsin.gov/misc/lfb/informational_papers/"
          "january_{yr}/{slug}")

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}


def wi_table1(pdf, url, year):
    """Table 1 - one row per Class III casino, devices and tables at each.

    Published, refused or partially published on ONE criterion: the extracted
    device and table columns must equal the printed Totals row. The document
    asserts its own answer; if the positional read disagrees with it, the read
    is wrong and nothing publishes."""
    import pdfplumber  # noqa
    got, meta = [], {}
    # The caption changed wording mid-series: the 2013-2017 editions say
    # "Table 1: Indian Gaming Casinos", the 2019-2025 editions say "Table 1:
    # Class III Indian Gaming Casinos". Matching the later wording only
    # silently dropped three whole editions - which is exactly the failure
    # mode a footing check cannot catch, because a table that is never found
    # is never footed.
    CAP_RE = re.compile(r"Table 1:\s*(Class III\s*)?Indian Gaming Casinos")
    for pno, page in enumerate(pdf.pages, start=1):
        txt = page.extract_text() or ""
        if not CAP_RE.search(txt):
            continue
        prs = page_rows(page)

        # The caption dates the whole table: "Table 1: Class III Indian Gaming
        # Casinos, October, 2024". Never assume the edition year is the
        # observation date - the January 2025 paper reports an October 2024
        # floor.
        cap = next((" ".join(w["text"] for w in ws) for _, ws in prs
                    if CAP_RE.search(" ".join(w["text"] for w in ws))), "")
        m = re.search(r"(" + "|".join(MONTHS) + r")[,\s]+(\d{4})", cap)
        if m:
            meta["as_of"] = f"{m.group(2)}-{MONTHS[m.group(1)]:02d}-01"
            meta["prec"] = "month"
        else:
            m2 = re.search(r"(\d{4})", cap)
            meta["as_of"] = f"{m2.group(1)}-12-31" if m2 else f"{year}-01-01"
            meta["prec"] = "year"
        meta["caption"] = cap
        meta["page"] = pno

        hdr = next((ws for _, ws in prs
                    if any(w["text"].startswith("Devices") for w in ws)
                    or ("Devices" in [w["text"] for w in ws])), None)
        if hdr is None:
            continue
        xnum = min(w["x0"] for w in hdr
                   if w["text"] in ("Devices", "Tables", "Gaming")) - 30

        # Column bands for the label side, learned from the header.
        def hx(*names):
            for w in hdr:
                if w["text"] in names:
                    return w["x0"]
            return None
        x_name = hx("Casino") or 200
        x_loc = next((w["x0"] for w in hdr if w["text"] == "Casino"
                      and w["x0"] > x_name + 50), None) or 400
        x_cty = hx("County") or 520

        for top, ws in prs:
            if top <= hdr[0]["top"]:
                continue
            label = text_between(ws, 0, x_name)
            nums = numbers_right_of(ws, xnum)
            if not label or not nums:
                continue
            if label.lower().startswith("total"):
                meta["printed_totals"] = [v for _, v, _ in nums]
                break
            name = text_between(ws, x_name, x_loc)
            loc = text_between(ws, x_loc, x_cty)
            cty = text_between(ws, x_cty, xnum)
            got.append({
                "tribe": label, "casino": name, "city": loc, "county": cty,
                "devices": nums[0][1] if len(nums) > 0 else None,
                "tables": nums[1][1] if len(nums) > 1 else None,
                "raw": " ".join(w["text"] for w in ws),
            })
        break

    # THE FOOTING CHECK. This is the whole guard.
    tot = meta.get("printed_totals") or []
    dev = sum(g["devices"] or 0 for g in got)
    tab = sum(g["tables"] or 0 for g in got)
    meta["footed"] = bool(tot) and len(tot) >= 2 and dev == tot[0] and tab == tot[1]
    meta["derived_totals"] = [dev, tab]
    meta["url"] = url
    return got, meta


def wi_table3(pdf, url):
    """Table 3 - lump-sum payments to the state, BY TRIBE, by fiscal year.

    Footed against the printed 'Subtotal Lump-Sum Payments' row, column by
    column. The -layout reading of this table books Potawatomi's $109,925,000
    onto Red Cliff."""
    for pno, page in enumerate(pdf.pages, start=1):
        txt = page.extract_text() or ""
        if "Lump-Sum Payments" not in txt or "Tribe or Band" not in txt:
            continue
        prs = page_rows(page)
        hdr = next((ws for _, ws in prs
                    if "Tribe" in [w["text"] for w in ws]
                    and any(re.fullmatch(r"\d{4}-\d{2}", w["text"]) for w in ws)),
                   None)
        if hdr is None:
            continue
        # Period labels, left to right, plus the trailing "Total" column.
        periods = [(w["x1"], w["text"]) for w in hdr
                   if re.fullmatch(r"\d{4}-\d{2}", w["text"])]
        # The leading column spans a multi-year window whose opening year sits
        # on the line above; find it so the metric name can carry the window.
        first_yr = None
        for _, ws in prs:
            for w in ws:
                if re.fullmatch(r"\d{4}-\d{2}", w["text"]) and w["top"] < hdr[0]["top"]:
                    first_yr = w["text"]
        x_lab = min(x for x, _ in periods) - 60

        out, subtotal = [], None
        for top, ws in prs:
            if top <= hdr[0]["top"]:
                continue
            label = text_between(ws, 0, x_lab)
            label = re.sub(r"\s*\d\s*$", "", label).strip()   # footnote marks
            nums = numbers_right_of(ws, x_lab)
            if not label:
                continue
            if label.lower().startswith("subtotal"):
                subtotal = [v for _, v, _ in nums]
                break
            if len(nums) < len(periods):
                continue
            out.append({"tribe": label,
                        "values": [v for _, v, _ in nums],
                        "raw": " ".join(w["text"] for w in ws)})

        cols = len(periods)
        derived = [sum(o["values"][i] for o in out) for i in range(cols)] \
            if out else []
        footed = bool(subtotal) and derived[:cols] == subtotal[:cols]
        return out, {"periods": [p for _, p in periods], "first_year": first_yr,
                     "subtotal": subtotal, "derived": derived,
                     "footed": footed, "page": pno, "url": url}
    return [], {"footed": False}


def wi_table2(pdf, url):
    """Table 2 - statewide tribal Class III net gaming revenue by reporting
    period, $ millions. STATEWIDE. Context for a bound, never an allocation."""
    for pno, page in enumerate(pdf.pages, start=1):
        txt = page.extract_text() or ""
        if "Tribal Class III Net Gaming" not in txt:
            continue
        out = []
        for _, ws in page_rows(page):
            toks = [w["text"] for w in ws]
            # A data line is "<year> <revenue> <pct change>" in the narrow
            # left-hand table column; anything else on the baseline is body
            # text from the facing column and is ignored by x-position.
            left = [w for w in ws if w["x0"] < 200]
            if len(left) < 2:
                continue
            yr = left[0]["text"].rstrip("*")
            if not re.fullmatch(r"(19|20)\d{2}", yr):
                continue
            v = as_number(left[1]["text"].replace("$", ""))
            if v is None:
                try:
                    v = float(left[1]["text"].replace("$", "").replace(",", ""))
                except ValueError:
                    continue
            try:
                val = float(left[1]["text"].replace("$", "").replace(",", ""))
            except ValueError:
                continue
            out.append({"year": int(yr), "net_revenue_musd": val,
                        "raw": " ".join(toks)})

        # Table 2 prints its own Total, so this series gets the same treatment
        # as the other two - footed against the document, or refused. The
        # -layout reading of this table drops 2004 and 2021 entirely and
        # attaches 2019's percentage change to 2018.
        printed = None
        for _, ws in page_rows(page):
            left = [w for w in ws if w["x0"] < 200]
            if left and left[0]["text"].lower().startswith("total") and len(left) > 1:
                try:
                    printed = float(left[1]["text"].replace("$", "").replace(",", ""))
                except ValueError:
                    pass
        derived = round(sum(o["net_revenue_musd"] for o in out), 1)
        footed = printed is not None and abs(derived - printed) < 0.15
        return out, {"page": pno, "url": url, "printed_total": printed,
                     "derived_total": derived, "footed": footed}
    return [], {"footed": False}



def ny_compact_roster(pdf, url):
    """NYSGC's Compact Partner / Casino / Location table - the state's own
    statement of which properties are inside the Class III compacts.

    THIS TABLE IS HIERARCHICAL, NOT SHIFTED, and telling the two apart is the
    whole job. Read linearly it looks like the familiar one-row displacement:

        St. Regis Mohawk Tribe    Yellow Brick Road    Chittenango
        Seneca Nation of Indians  Point Place          Bridgeport

    Both pairings are wrong, and a reader who has been burned by the Michigan
    and Arizona shift will "correct" it in the wrong direction. Positionally
    the truth is plain: the nation label sits at x=120 on the baseline of its
    FIRST casino, and its remaining casinos have no label at all. So the rule
    is CARRY THE LABEL FORWARD until a new one appears in the label column -
    not shift it. Under that rule Oneida keeps Turning Stone, Yellow Brick
    Road and Point Place, which is correct.
    """
    for pno, page in enumerate(pdf.pages, start=1):
        txt = page.extract_text() or ""
        if "Compact Partner" not in txt:
            continue
        prs = page_rows(page)
        hdr = next((ws for _, ws in prs
                    if "Compact" in [w["text"] for w in ws]
                    and "Casino" in [w["text"] for w in ws]), None)
        if hdr is None:
            continue
        x_part = next(w["x0"] for w in hdr if w["text"] == "Compact")
        x_cas = next(w["x0"] for w in hdr if w["text"] == "Casino")
        x_loc = next((w["x0"] for w in hdr if w["text"] == "Location"), 10 ** 6)

        out, current = [], None
        for top, ws in prs:
            if top <= hdr[0]["top"]:
                continue
            # WHERE THE TABLE ENDS. The paragraph after it runs full width and
            # starts at the page's left margin, well left of the label column.
            # Slicing that prose by the table's x-bands yields rows that look
            # exactly like data - the first version of this reader returned 13
            # properties across 9 "nations" from a 7-property, 3-nation table,
            # every one of them well-formed and false. A body line is the stop
            # signal, and it has to be checked before the bands are applied.
            if any(w["x0"] < x_part - 20 for w in ws):
                break
            label = text_between(ws, x_part - 5, x_cas - 5)
            casino = text_between(ws, x_cas - 5, x_loc - 5)
            loc = text_between(ws, x_loc - 5, 10 ** 6)
            if label:
                current = label
            if not casino:
                continue
            out.append({"tribe": current, "casino": casino, "location": loc,
                        "raw": " ".join(w["text"] for w in ws)})
        return out, {"page": pno, "url": url}
    return [], {}


# ===========================================================================
# DOCUMENTED ABSENCES
#
# "Unchecked" and "publishes nothing" must never look alike in a coverage
# table, and "publishes nothing" and "is forbidden to publish it" are a third
# thing again. Every entry below is a quote from the source saying so in its
# own words. An absence with a citation is a permanent saving; an absence
# without one is an invitation to re-check.
# ===========================================================================

ABSENCES = [
    dict(state="WI", scope="per-tribe and per-property REVENUE",
         kind="prohibited_by_instrument",
         authority="Wisconsin Legislative Fiscal Bureau",
         doc="Informational Paper 91, Tribal Gaming in Wisconsin (Jan 2025)",
         url=WI_URL.format(yr="2025",
                           slug="0091_tribal_gaming_in_wisconsin_informational_paper_91.pdf"),
         quote="Tribes are required to submit annual independent financial "
               "audits of casino operations to the Department of Administration "
               "(DOA) and to the Legislative Audit Bureau (LAB). These audits "
               "are confidential, and the revenue data for individual tribal "
               "operations may not be publicly disclosed."),
    dict(state="WI", scope="per-tribe NET WIN-BASED PAYMENTS",
         kind="prohibited_by_instrument",
         authority="Wisconsin Legislative Fiscal Bureau",
         doc="Informational Paper 91, Tribal Gaming in Wisconsin (Jan 2025)",
         url=WI_URL.format(yr="2025",
                           slug="0091_tribal_gaming_in_wisconsin_informational_paper_91.pdf"),
         quote="It should be noted that confidentiality provisions in each "
               "compact prohibit the disclosure of individual net win-based "
               "payments by tribe."),
    dict(state="LA", scope="all tribal gaming statistics",
         kind="no_authority_to_compel",
         authority="Louisiana Gaming Control Board",
         doc="30th Annual Report to the Louisiana State Legislature (FY 2024-25)",
         url="https://lgcb.dps.louisiana.gov/media/avxl0yu3/"
             "30th-annual-report-to-the-louisiana-state-legislature-4.pdf",
         quote="This report contains no statistical information on tribal "
               "gaming. The three (3) tribes authorized to conduct gaming "
               "operations on their tribal lands pursuant to IGRA class III "
               "gaming compacts are not required to pay any fees directly to "
               "the state and cannot be required to provide the Board with any "
               "financial figures."),
    dict(state="AZ", scope="per-tribe gross gaming revenue and contributions",
         kind="aggregated_by_statute",
         authority="Arizona Department of Gaming",
         doc="Annual Report on Tribal Contributions, FY 2025",
         url="https://gaming.az.gov/sites/default/files/"
             "Annual%20Report%20on%20Tribal%20Contributions%20FY%202025.pdf",
         quote="In accordance with A.R.S. \u00a7 5-601.02(H)(1), which requires "
               "an annual report that includes \"a statement of aggregate gross "
               "gaming revenue for all Indian tribes, aggregate revenues "
               "deposited in the Arizona Benefits Fund, including interest "
               "thereon, expenditures made from the Arizona Benefits Fund, and "
               "aggregate amounts contributed by all Indian tribes to cities, "
               "towns, and counties,\" the Arizona Department of Gaming (\"ADG\") "
               "is pleased to submit the following report on tribal "
               "contributions for Fiscal Year 2025."),
]

# The sweep's six remaining states, and the distinction that matters most in
# this whole file: a state that NEVER COLLECTS the number and a state that
# HOLDS it and is SEALED are both blank in a coverage table and are completely
# different facts. Only one of them has a document in existence at all, and
# knowing which decides whether any records strategy could ever work. (Neither
# of these two can be reached - but for different reasons, and a coverage table
# that flattens them will send somebody after the wrong one.)
MORE_ABSENCES = [
    # ---- MINNESOTA. Confirmed from the instruments, as required, not asserted.
    dict(state="MN", scope="all tribal gaming revenue and payments",
         kind="no_payment_obligation_exists",
         authority="Minnesota Legislature",
         doc="Minn. Stat. \u00a7 3.9221 subd. 4, Indian gambling compacts",
         url="https://www.revisor.mn.gov/statutes/cite/3.9221",
         quote="a provision that in the event of a request for a renegotiation "
               "or a new compact the existing compact will remain in effect "
               "until renegotiated or replaced."),
    dict(state="MN", scope="compact duration - perpetuity",
         kind="no_payment_obligation_exists",
         authority="Shakopee Mdewakanton Sioux Community / State of Minnesota",
         doc="Tribal-State Compact for Control of Video Games of Chance, "
             "1989-10-20, section 2.2",
         url="https://assets.dps.mn.gov/files/age/age-shakopee-video-games-of-"
             "chance-tribal-state-compact-1989-10-20.pdf",
         quote="The State o.r the Community may, by appropriate and lawful "
               "means, request negotiations to amend, replace or repeal this "
               "compact. In the event of a request for renegotiation or the "
               "negotiation of a new compact, this compact shall remain in "
               "effect until renegotiated or replaced."),
    dict(state="MN", scope="state revenue from tribal gaming",
         kind="no_payment_obligation_exists",
         authority="Minnesota Department of Public Safety, Alcohol and "
                   "Gambling Enforcement Division",
         doc="Tribal-State Gaming Compacts",
         url="https://dps.mn.gov/divisions/age/gambling/"
             "tribal-state-gaming-compacts",
         quote="Minnesota's federally recognized 11 Tribal Nations were the "
               "first in the United States to negotiate and sign gaming "
               "compacts with a state government. The Tribal Nations and the "
               "state agreed to limit casinos to video games of chance (slots) "
               "and blackjack. Additionally, both parties agreed that the "
               "compacts should be effective forever."),

    # ---- NEVADA. The most informative absence in the sweep: the number EXISTS,
    # monthly, per property, in the regulator's hands, on the same form the
    # commercial licensees file - and the compact itself forbids publishing it.
    dict(state="NV", scope="per-property tribal gross revenue",
         kind="held_by_state_but_sealed",
         authority="Washoe Tribe of Nevada and California / State of Nevada",
         doc="First Amended Tribal-State Gaming Compact, 2018",
         url="https://www.bia.gov/service/gaming-compacts",
         quote="For each Group I and Group II Tribal Gaming Operation, the "
               "Tribe shall submit to the Board a completed \"Monthly Gross "
               "Revenue Statistical Report\" (NGC-31) for each month of "
               "operation."),
    dict(state="NV", scope="per-property tribal gross revenue",
         kind="held_by_state_but_sealed",
         authority="Washoe Tribe of Nevada and California / State of Nevada",
         doc="First Amended Tribal-State Gaming Compact, 2018",
         url="https://www.bia.gov/service/gaming-compacts",
         quote="The State shall maintain all audit and financial records "
               "obtained under this section, or any other section of this "
               "Compact, strictly confidential, and shall not disseminate them "
               "to any member of the public for any purpose, except as "
               "required by Court order or applicable federal law."),

    # ---- NORTH DAKOTA. Sealed by statute rather than by compact.
    dict(state="ND", scope="all tribal gaming records",
         kind="held_by_state_but_sealed",
         authority="North Dakota Legislative Assembly",
         doc="N.D.C.C. \u00a7 54-58-02",
         url="https://ndlegis.gov/cencode/t54c58.pdf",
         quote="54-58-02. Tribal gaming records not subject to disclosure - "
               "Exceptions. Except as provided in each tribal-state gaming "
               "compact, all tribal gaming records, including trade secret and "
               "proprietary information as defined in section 44-04-18.4, "
               "submitted to an agency of this state are confidential and are "
               "not public records subject to section 44-04-18 and section 6 "
               "of article XI of the Constitution of North Dakota."),

    # ---- KANSAS. Sealed by compact; the state takes cost recovery, not revenue.
    dict(state="KS", scope="per-casino financial information",
         kind="held_by_state_but_sealed",
         authority="Kansas Legislative Research Department",
         doc="Briefing Book 2021, Lottery, State-Owned Casinos, Parimutuel "
             "Wagering, and Tribal Casinos",
         url="https://klrd.gov/publications/briefing-book-2021/lottery-state-"
             "owned-casinos-parimutuel-wagering-and-tribal-casinos/",
         quote="Revenue. Financial information concerning the operation of the "
               "four casinos is confidential. Under the existing compacts, the "
               "State does not receive revenue from the casinos, except for "
               "its oversight activities."),

    # ---- COLORADO. Never collected. The tribes are not required to report.
    dict(state="CO", scope="all tribal gaming revenue",
         kind="never_collected",
         authority="Colorado Department of Revenue, Division of Gaming",
         doc="Tribal Casinos in Colorado",
         url="https://sbg.colorado.gov/tribal-casinos-in-colorado",
         quote="The two tribes, the Ute Mountain Ute Tribe and the Southern "
               "Ute Indian Tribe, are not subject to taxation and are not "
               "required to report their revenues to the State."),

    # ---- SOUTH DAKOTA. The regulator's authorising statute is geographically
    # confined to one city, so no tribal record can exist to be published.
    dict(state="SD", scope="all tribal gaming",
         kind="outside_regulator_jurisdiction",
         authority="South Dakota Legislature",
         doc="SDCL \u00a7 42-7B-1",
         url="https://sdlegislature.gov/Statutes/42-7B-1",
         quote="42-7B-1. Limited gaming authorized within city of Deadwood. "
               "Limited card games, slot machines, craps, roulette, keno, and "
               "wagering on sporting events are hereby authorized, and may be "
               "operated, conducted, and maintained, within the city limits of "
               "the city of Deadwood, South Dakota, subject to the provisions "
               "of this chapter."),

    # ---- The three states whose regulator simply has no tribal jurisdiction.
    dict(state="MS", scope="all tribal gaming",
         kind="outside_regulator_jurisdiction",
         authority="Mississippi Gaming Commission",
         doc="History of the Mississippi Gaming Commission",
         url="https://www.msgamingcommission.com/index.php/about/history",
         quote="The Gaming Control Act established the Mississippi Gaming "
               "Commission to regulate dockside casinos."),
    dict(state="NE", scope="all tribal gaming",
         kind="outside_regulator_jurisdiction",
         authority="Nebraska Racing and Gaming Commission",
         doc="2025 Annual Report",
         url="https://nrgc.nebraska.gov/",
         quote="In 2020, Nebraska voters approved constitutional amendments "
               "authorizing casino gaming at licensed racetrack facilities. "
               "This voter approval expanded the Commission's authority and "
               "formally transitioned the agency into the Nebraska Racing and "
               "Gaming Commission, responsible for regulating both racing and "
               "casino gaming."),
    dict(state="IA", scope="all tribal gaming",
         kind="outside_regulator_jurisdiction",
         authority="Iowa Racing and Gaming Commission",
         doc="Annual Report CY2024",
         url="https://irgc.iowa.gov/publications-reports/annual-reports",
         quote="The mission of the Iowa Racing & Gaming Commission is to "
               "administer the laws and rules of gambling and wagering in Iowa "
               "in order to ensure the integrity of licensees and their "
               "operations"),
    dict(state="IN", scope="all tribal gaming",
         kind="outside_regulator_jurisdiction",
         authority="Indiana Gaming Commission",
         doc="Indiana Casino Licensees & Operating Agent",
         url="https://www.in.gov/igc/files/general/Indiana-Casino-Licensees.pdf",
         quote="INDIANA CASINO LICENSEES & OPERATING AGENT"),

    # ---- RHODE ISLAND. There is no facility, so there is nothing to publish.
    dict(state="RI", scope="all tribal gaming",
         kind="no_tribal_facility_exists",
         authority="National Indian Gaming Commission",
         doc="Gaming Tribes by State",
         url="https://www.nigc.gov/tribes/gaming-tribes",
         quote="NIGC's national list of gaming tribes contains zero entries "
               "for Rhode Island and zero for the Narragansett Indian Tribe. "
               "Rhode Island's two casinos, Bally's Twin River Lincoln and "
               "Bally's Tiverton, are regulated by the Department of Business "
               "Regulation as state video lottery, not under a tribal-state "
               "compact."),
]

# Louisiana's per-tribe reporting form EXISTS and is printed blank. That is a
# different and stronger fact than a state that never asked: the Board prints
# a per-tribe, per-quarter Parish Contribution table every year and the tribes
# decline it, exactly as the Board's own text says they may.
LA_BLANK_FORM = dict(
    state="LA", scope="per-tribe quarterly parish contributions",
    kind="form_published_but_declined",
    authority="Louisiana Gaming Control Board",
    doc="30th Annual Report to the Louisiana State Legislature (FY 2024-25), "
        "table 'TRIBAL PARISH CONTRIBUTIONS'",
    url="https://lgcb.dps.louisiana.gov/media/avxl0yu3/"
        "30th-annual-report-to-the-louisiana-state-legislature-4.pdf",
    quote="TRIBAL PARISH CONTRIBUTIONS (MADE BY SEPARATE AGREEMENT OR PURSUANT "
          "TO TRIBAL/STATE COMPACT) Fiscal Year 7/1/2024 - 6/30/2025 Quarter "
          "Chitimacha St. Mary Coushatta Allen Tunica-Biloxi Avoyelles 1 Not "
          "Provided Not Provided Not Provided")


# Facility universes published by states that publish nothing else. A roster is
# the weakest evidence class in this build and it is still worth having: it is
# the state's own statement of which properties exist, which is exactly what a
# residual-elimination pass needs in order to know what it is eliminating
# against, and it cross-checks the properties NIGC lists that Cedar does not.
FACILITY_UNIVERSE = [
    dict(state="KS", casino="Casino White Cloud", tribe="Iowa Tribe of Kansas and Nebraska",
         city="White Cloud",
         quote="Casino White Cloud, White Cloud - Address 777 Jackpot Drive "
               "White Cloud, Kansas 66094-4002"),
    dict(state="KS", casino="Golden Eagle Casino", tribe="Kickapoo Tribe in Kansas",
         city="Horton",
         quote="Golden Eagle Casino, Horton - Address 1121 Goldfinch Road "
               "Horton, Kansas 66439-9537"),
    dict(state="KS", casino="Prairie Band Potawatomi Casino",
         tribe="Prairie Band Potawatomi Nation", city="Mayetta",
         quote="Prairie Band Potawatomi Casino, Mayetta - Address 12305 150th "
               "Road Mayetta, Kansas 66509-8815"),
    dict(state="KS", casino="Sac & Fox Casino", tribe="Sac and Fox Nation of Missouri",
         city="Powhattan",
         quote="Sac & Fox Casino, Powhattan - Address 1322 US Highway 75"),
    dict(state="NV", casino="Avi Resort & Casino", tribe="Fort Mojave Indian Tribe",
         city="Laughlin",
         quote="17698-01 | Nonrestricted-Indian | Avi Resort & Casino | 10000 "
               "AHA MACAV PK | Laughlin. The sole Nonrestricted-Indian licence "
               "in the NGCB Restricted and Nonrestricted Locations Report, "
               "quarter ending 06/30/2026."),
]
FACILITY_UNIVERSE_SRC = {
    "KS": dict(authority="Kansas State Gaming Agency",
               doctype="regulator casino directory",
               url="https://www.kansas.gov/ksga/Casinos.htm"),
    "NV": dict(authority="Nevada Gaming Control Board",
               doctype="licence location report",
               url="https://gaming.nv.gov/"),
}

# Statewide aggregates. Context for a residual, never an allocation, and the
# exclusion flag is what keeps that true after the file leaves this script.
STATE_AGGREGATES = [
    dict(state="AZ", metric="gross_gaming_revenue_state_aggregate",
         value=3033358250, unit="usd",
         period_start="2024-07-01", period_end="2025-06-30",
         as_of="2025-06-30",
         authority="Arizona Department of Gaming",
         doctype="statutory annual report",
         url="https://gaming.az.gov/sites/default/files/"
             "Annual%20Report%20on%20Tribal%20Contributions%20FY%202025.pdf",
         quote="Aggregate Gross Gaming Revenue: $3,033,358,250"),
    dict(state="AZ", metric="tribal_contributions_state_aggregate",
         value=163568927, unit="usd",
         period_start="2024-07-01", period_end="2025-06-30",
         as_of="2025-06-30",
         authority="Arizona Department of Gaming",
         doctype="statutory annual report",
         url="https://gaming.az.gov/sites/default/files/"
             "Annual%20Report%20on%20Tribal%20Contributions%20FY%202025.pdf",
         quote="Aggregate Revenues (Tribal contributions) deposited in the "
               "Arizona Benefits Fund, including interest thereon: $163,568,927"),
    dict(state="AZ", metric="tribal_contributions_to_local_government_aggregate",
         value=21822667, unit="usd",
         period_start="2024-07-01", period_end="2025-06-30",
         as_of="2025-06-30",
         authority="Arizona Department of Gaming",
         doctype="statutory annual report",
         url="https://gaming.az.gov/sites/default/files/"
             "Annual%20Report%20on%20Tribal%20Contributions%20FY%202025.pdf",
         quote="The aggregate amounts contributed by all Indian Tribes to "
               "cities, towns, and counties are $21,822,667."),
]


# ===========================================================================
# RESOLUTION
# ===========================================================================

def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press 107: remaining state gaming regulators ===\n")
    try:
        import pdfplumber
    except ImportError:
        sys.exit("pdfplumber required")

    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    cls_by_id = {r["tribe_id"]: r.get("entity_class", "") for r in spine}
    fac = read_csv(CLEAN / "gaming_facilities.csv")

    _tcache = {}

    def tribe(name, state):
        """The one resolver, plus a refusal on classes the source cannot be
        about. Never a second matcher."""
        key = (name, state)
        if key in _tcache:
            return _tcache[key]
        tid, tname, meth = resolve_entity(name, spine)
        if tid and cls_by_id.get(tid, "") in REFUSED_CLASSES:
            meth = (f"refused_entity_class:"
                    f"{cls_by_id[tid].replace(' ', '_')}->{tname}")
            tid, tname = None, None
        # A cross-state resolution on a gaming regulator's own roster is the
        # cross-state failure in AGENTS.md's table. Require agreement where the
        # spine states a state at all.
        if tid:
            srow = next((r for r in spine if r["tribe_id"] == tid), {})
            sst = (srow.get("state") or "").strip().upper()
            if sst and state and sst != state:
                meth = f"refused_state_disagreement:spine={sst}"
                tid, tname = None, None
        _tcache[key] = (tid, tname, meth)
        return _tcache[key]

    def facility(pub_name, state, tid):
        """Exact-normalised name within state, or the tribe's sole open
        property in that state, or refusal. No third tier, on purpose."""
        pool = [r for r in fac
                if (r.get("state") or "").strip().upper() == state]
        n = norm(pub_name)
        hit = [r for r in pool if norm(r.get("facility_name", "")) == n]
        if len(hit) == 1:
            return hit[0]["facility_id"], hit[0]["facility_name"], "exact_name_in_state"
        if len(hit) > 1:
            return None, None, f"ambiguous_exact_name:{len(hit)}"
        if tid:
            own = [r for r in pool if (r.get("tribe_id") or "") == tid]
            openish = [r for r in own
                       if (r.get("property_status") or "").lower() != "closed"]
            if len(openish) == 1:
                return (openish[0]["facility_id"], openish[0]["facility_name"],
                        "sole_property_of_tribe_in_state")
        return None, None, "unresolved"

    def spine_candidates(state):
        """For a TRIBE that did not resolve, the useful hint is candidate
        ENTITIES, not candidate properties.

        Wisconsin's Table 3 says bare "Oneida" and bare "Potawatomi". Both are
        in `NAME_TRAPS`, so the property hint correctly produces nothing - and
        a human then gets an unanswerable item on a question with eleven
        possible answers, all of them in the spine and all of them in one
        state. Listing that state's tribal entities turns a dead end into a
        thirty-second ruling. It rules nothing; nothing downstream reads it."""
        want = {"Federally recognized tribe", "State-recognized tribe",
                "Federally recognized Alaska Native Village"}
        return " | ".join(
            f"{r['tribe_id']}={r['canonical_name']}" for r in spine
            if (r.get("state") or "").strip().upper() == state
            and r.get("entity_class") in want)[:900]

    def candidates(state, tid, pub_tribe=""):
        """Properties to put in front of a human. It RULES NOTHING.

        Where the tribe resolved, this is exactly that tribe's properties in
        that state - the `23g_gaming_duplicate_candidates.py` pattern.

        Where the tribe did NOT resolve (Wisconsin's Table 3 says bare
        "Oneida" and "Potawatomi", both of which name several different
        nations), an empty candidate list makes a solvable item look like a
        dead end. So fall back to properties whose recorded tribe shares a
        distinctive token with the published name - with `NAME_TRAPS` removed
        first, because "oneida" and "creek" are precisely the tokens that have
        cost this project misattributions. This is a review hint, never a key:
        nothing downstream reads this column."""
        pool = [r for r in fac
                if (r.get("state") or "").strip().upper() == state]
        hits = []
        if tid:
            hits = [r for r in pool if (r.get("tribe_id") or "") == tid]
        # A resolved tribe with ZERO properties keyed to it does not mean the
        # tribe has no properties - it means `gaming_facilities.csv` has not
        # keyed them. New York's Mohawk rows carry a blank `tribe_id`, so the
        # tribe-keyed lookup returned nothing and shipped an empty candidate
        # list on a perfectly answerable item. Fall through to the name hint.
        if not hits:
            toks = {t for t in norm(pub_tribe).split()
                    if t not in NAME_TRAPS and len(t) > 3}
            if not toks:
                return ""
            hits = [r for r in pool
                    if toks & (set(norm(r.get("tribe_canonical_name", "")).split())
                               | set(norm(r.get("facility_name", "")).split()))]
        return " | ".join(f"{r['facility_id']}={r['facility_name']}"
                          for r in hits)[:900]

    seq = collections.Counter()

    def emit(**kw):
        st = kw["state"]
        seq[st] += 1
        r = {f: "" for f in FIELDS}
        r.update(kw)
        r["observation_id"] = f"SG-{st}-{seq[st]:05d}"
        r["built_date"] = TODAY
        # FIXED 2026-08-26 (code/293_lint_bug_classes.py, defect CLASS 2a).
        # This was `r.setdefault("fetched_date", TODAY)`. `fetched_date` is one
        # of the 31 names in FIELDS, so `r = {f: "" for f in FIELDS}` two lines
        # up had ALREADY created the key with an empty string - and setdefault
        # only writes when the key is ABSENT. It was a no-op.
        # MEASURED COST: `data/clean/state_gaming_observations.csv` carried
        # `fetched_date` BLANK on 494 of 494 rows, and a reader would have read
        # that as "the source states no retrieval date". Same defect as
        # `119_build_digital_and_loyalty.py` (tier 154/154 blank).
        # `or` on the empty string is the behaviour setdefault was reaching for.
        r["fetched_date"] = r.get("fetched_date") or TODAY
        rows.append(r)

    # ------------------------------------------------------------- WISCONSIN
    print("-- Wisconsin: LFB 'Tribal Gaming in Wisconsin', 7 editions")
    wi_slugs = {
        "2025": "0091_tribal_gaming_in_wisconsin_informational_paper_91.pdf",
        "2023": "0089_tribal_gaming_in_wisconsin_informational_paper_89.pdf",
        "2021": "0087_tribal_gaming_in_wisconsin_informational_paper_87.pdf",
        "2019": "0086_tribal_gaming_in_wisconsin_informational_paper_86.pdf",
        "2017": "0086_tribal_gaming_in_wisconsin_informational_paper_86.pdf",
        "2015": "0087_tribal_gaming_in_wisconsin_informational_paper_87.pdf",
        "2013": "0088_tribal_gaming_in_wisconsin_informational_paper_88.pdf",
    }
    footing = []
    for yr, fname in WI_EDITIONS:
        p = RAW / "wi" / fname
        if not p.exists():
            print(f"   {yr}: MISSING {fname}")
            continue
        url = WI_URL.format(yr=yr, slug=wi_slugs[yr])
        with pdfplumber.open(p) as pdf:
            t1, m1 = wi_table1(pdf, url, yr)
            t3, m3 = wi_table3(pdf, url)
            t2, m2 = wi_table2(pdf, url) if yr == "2025" else ([], {})

        footing.append((yr, len(t1), m1.get("derived_totals"),
                        m1.get("printed_totals"), m1.get("footed")))
        if not m1.get("footed"):
            # An edition whose columns do not equal the document's own printed
            # totals is REFUSED. The document asserts its own answer; a reader
            # that disagrees with it is the thing that is wrong.
            q("wi_edition_failed_footing", "WI", f"LFB {yr} Table 1",
              f"rows={len(t1)}",
              f"derived={m1.get('derived_totals')} printed={m1.get('printed_totals')}",
              "Positional read of Table 1 does not equal the printed Totals row. "
              "Nothing from this edition was published. Re-extract or refuse?",
              url)
            print(f"   {yr}: Table 1 REFUSED (derived {m1.get('derived_totals')} "
                  f"vs printed {m1.get('printed_totals')})")
        else:
            print(f"   {yr}: Table 1 footed  {len(t1)} casinos  "
                  f"devices={m1['derived_totals'][0]:,} tables={m1['derived_totals'][1]}  "
                  f"as of {m1['as_of']}")
            for g in t1:
                tname = g["tribe"].replace("*", "").strip()
                tid, tcanon, tmeth = tribe(tname, "WI")
                if not tid:
                    q("wi_tribe_unresolved", "WI", tname, f"LFB {yr} Table 1",
                      g["raw"][:200], "Which spine entity is this?", url,
                      spine_candidates("WI"))
                fid, fname_c, fmeth = facility(g["casino"], "WI", tid)
                if not fid:
                    q("agent_facility_unresolved", "WI", g["casino"],
                      f"LFB {yr} Table 1, {g['city']}, {g['county']} County",
                      g["raw"][:200],
                      "Which Cedar property is this regulator name an alias of?",
                      url, candidates("WI", tid, tname))
                for metric, val in (("gaming_machines", g["devices"]),
                                    ("table_games", g["tables"])):
                    if val is None:
                        continue
                    emit(state="WI", facility_id=fid or "",
                         facility_name=fname_c or "",
                         facility_name_as_published=g["casino"],
                         tribe_id=tid or "", tribe_canonical_name=tcanon or "",
                         tribe_name_as_published=tname,
                         metric=metric, metric_class="capacity",
                         measurement_status="reported_measurement",
                         measurement_type=MeasurementType.REGULATORY_REPORTED_COUNT.value,
                         revenue_evidence="", value=val, unit="count",
                         applies_to="property",
                         as_of_date=m1["as_of"],
                         as_of_date_precision=m1["prec"],
                         source_authority="Wisconsin Legislative Fiscal Bureau",
                         source_document_type="legislative informational paper",
                         source_url=url, source_page=str(m1["page"]),
                         source_quote=g["raw"][:400],
                         facility_match_method=fmeth, tribe_match_method=tmeth)

        # ---- Table 3, per-tribe payments (2025 edition is the current one)
        if yr == "2025":
            if not m3.get("footed"):
                q("wi_table3_failed_footing", "WI", "LFB 2025 Table 3", "",
                  f"derived={m3.get('derived')} subtotal={m3.get('subtotal')}",
                  "Per-tribe lump-sum column does not foot to the printed "
                  "Subtotal. Nothing published. Re-extract?", url)
                print("   2025: Table 3 REFUSED (does not foot)")
            else:
                print(f"   2025: Table 3 footed  {len(t3)} tribes  "
                      f"subtotal {m3['subtotal'][0]:,}")
                periods = m3["periods"]
                for o in t3:
                    tid, tcanon, tmeth = tribe(o["tribe"], "WI")
                    if not tid:
                        q("wi_tribe_unresolved", "WI", o["tribe"],
                          "LFB 2025 Table 3 (per-tribe lump-sum payments)",
                          o["raw"][:200],
                          "Which spine entity is this? The LFB uses a bare "
                          "short name and several nations share it.", url,
                          spine_candidates("WI"))
                    for i, per in enumerate(periods):
                        if i >= len(o["values"]):
                            continue
                        # The first column spans 1999-00 through 2016-17. A
                        # cumulative published beside annual figures is a double
                        # count waiting to happen, so it gets its own metric
                        # name AND an exclusion flag - two independent guards.
                        cumulative = (i == 0)
                        if cumulative:
                            metric = ("lump_sum_payment_to_state_cumulative_"
                                      f"{(m3.get('first_year') or '1999-00').replace('-', '')}"
                                      f"_to_{per.replace('-', '')}")
                            ps = f"{(m3.get('first_year') or '1999-00')[:4]}-07-01"
                        else:
                            metric = "lump_sum_payment_to_state"
                            ps = f"{per[:4]}-07-01"
                        pe = f"{int(per[:4]) + 1}-06-30"
                        emit(state="WI", tribe_id=tid or "",
                             tribe_canonical_name=tcanon or "",
                             tribe_name_as_published=o["tribe"],
                             metric=metric, metric_class="payment",
                             measurement_status="reported_payment",
                             measurement_type=MeasurementType.REGULATORY_REPORTED_COUNT.value,
                             revenue_evidence="NO_REVENUE_OBSERVATION",
                             value=o["values"][i], unit="usd",
                             applies_to="tribe",
                             as_of_date=pe, as_of_date_precision="fiscal_year",
                             period_start=ps, period_end=pe,
                             source_authority="Wisconsin Legislative Fiscal Bureau",
                             source_document_type="legislative informational paper",
                             source_url=url, source_page=str(m3["page"]),
                             source_quote=o["raw"][:400],
                             tribe_match_method=tmeth,
                             facility_match_method="not_attempted_tribe_level",
                             exclusion_flag=("cumulative_window" if cumulative else ""),
                             exclusion_reason=(
                                 "Multi-year cumulative column. NEVER sum "
                                 "alongside the annual columns." if cumulative else ""))
            # ---- Table 2, statewide aggregate
            if t2 and not m2.get("footed"):
                q("wi_table2_failed_footing", "WI", "LFB 2025 Table 2", "",
                  f"derived={m2.get('derived_total')} printed={m2.get('printed_total')}",
                  "Statewide net win series does not foot to the printed Total. "
                  "Nothing published. Re-extract?", url)
                print("   2025: Table 2 REFUSED (does not foot)")
                t2 = []
            elif t2:
                print(f"   2025: Table 2 footed  {len(t2)} years  "
                      f"total ${m2['derived_total']:,.1f}M")
            for o in t2:
                emit(state="WI", metric="net_win_state_aggregate",
                     metric_class="revenue",
                     measurement_status="reported_revenue",
                     measurement_type=MeasurementType.REGULATORY_REPORTED_COUNT.value,
                     revenue_evidence="REGIONAL_GGR_CONTEXT",
                     value=o["net_revenue_musd"], unit="usd_millions",
                     applies_to="state",
                     as_of_date=f"{o['year']}-12-31",
                     as_of_date_precision="reporting_period",
                     period_start=f"{o['year']}-01-01",
                     period_end=f"{o['year']}-12-31",
                     source_authority="Wisconsin Legislative Fiscal Bureau",
                     source_document_type="legislative informational paper",
                     source_url=m2.get("url", ""), source_page=str(m2.get("page", "")),
                     source_quote=o["raw"][:400],
                     exclusion_flag="state_aggregate_not_allocatable",
                     exclusion_reason="Statewide total for all tribal casinos. "
                                      "Context for a bound; never an allocation "
                                      "to a tribe or a property.")

    # ------------------------------------------------------------- NEW YORK
    # THE SECOND REAL FIND. The New York State Gaming Commission's 2019 annual
    # report prints a per-nation payment table that appears in NO other
    # edition - checked 2015, 2017, 2018, 2020, 2021, 2022, 2023 and 2024. It
    # is a three-row list, not a multi-column table, so the column-shift defect
    # does not apply; the positional read matches the linear one exactly.
    print("\n-- New York: NYSGC 2019 annual report, per-nation exclusivity payments")
    ny_url = "http://gaming.ny.gov/2019-annual-report"
    ny_src = dict(source_authority="New York State Gaming Commission",
                  source_document_type="annual report",
                  source_url=ny_url, source_page="12")
    for name, short, val, quote in [
        ("Saint Regis Mohawk Tribe", "Mohawk", 18471525.64,
         "2019 Regulatory Exclusivity Payment (25%) Mohawk $18,471,525.64"),
        ("Oneida Indian Nation of New York", "Oneida", 70683720.37,
         "2019 Regulatory Exclusivity Payment (25%) Oneida $70,683,720.37"),
    ]:
        tid, tcanon, tmeth = tribe(name, "NY")
        if not tid:
            q("ny_tribe_unresolved", "NY", name, "NYSGC 2019 annual report",
              quote, "Which spine entity is this?", ny_url,
              spine_candidates("NY"))
        emit(state="NY", tribe_id=tid or "", tribe_canonical_name=tcanon or "",
             tribe_name_as_published=short,
             metric="regulatory_exclusivity_payment_to_state",
             metric_class="payment", measurement_status="reported_payment",
             measurement_type=MeasurementType.REGULATORY_REPORTED_COUNT.value,
             revenue_evidence="NO_REVENUE_OBSERVATION",
             value=val, unit="usd", applies_to="tribe",
             as_of_date="2019-12-31", as_of_date_precision="year",
             period_start="2019-01-01", period_end="2019-12-31",
             source_quote=quote, tribe_match_method=tmeth,
             facility_match_method="not_attempted_tribe_level", **ny_src)

    # The Seneca cell is a printed asterisk with a printed reason. A disclosed
    # non-value is a fact about 2019 and is recorded as one; leaving it blank
    # would make a withheld figure indistinguishable from one nobody looked for.
    stid, stcanon, stmeth = tribe("Seneca Nation of Indians", "NY")
    emit(state="NY", tribe_id=stid or "", tribe_canonical_name=stcanon or "",
         tribe_name_as_published="Seneca",
         metric="regulatory_exclusivity_payment_to_state",
         metric_class="absence", measurement_status="documented_absence",
         measurement_type="", revenue_evidence="NO_REVENUE_OBSERVATION",
         value="", unit="usd", applies_to="tribe",
         as_of_date="2019-12-31", as_of_date_precision="year",
         period_start="2019-01-01", period_end="2019-12-31",
         source_quote="Seneca * | * - Current arbitration between the State of "
                      "New York and the Seneca Nation",
         tribe_match_method=stmeth,
         facility_match_method="not_attempted_tribe_level",
         exclusion_flag="withheld_by_source",
         exclusion_reason="NYSGC prints an asterisk in place of the Seneca "
                          "figure and states the reason. Withheld for a named "
                          "cause, not absent.", **ny_src)

    # ---- EXACT DERIVATION, and only where the operative instrument is held.
    #
    # Spec 9.4: payment / rate is exact arithmetic and the one honest route to
    # real revenue - "provided the revenue concept is preserved".
    #
    # Michigan set the standard this follows: MGCB printed "2%" against all
    # twelve tribes and the build derived for only the FOUR whose compact text
    # was on disk, because "a regulator's summary table is not the operative
    # instrument". New York splits the same way.
    #
    # MOHAWK - derived. The 2005 amendment approved by the Secretary states
    # both the rate and the base in its own words, and NYSGC's 2019 column
    # header independently labels the payment 25%. Two legs that agree.
    #
    # ONEIDA - NOT derived. The only "Oneida" compacts in this project's corpus
    # are WISCONSIN documents (see the queue item below), so the operative New
    # York instrument is not held. 70,683,720.37 / 0.25 = 282,734,881.48 is
    # arithmetic anybody can do; it is not evidence until the instrument is on
    # disk, and it is queued rather than published.
    mohawk_base_quote = (
        "(d) State Contribution. In exchange and consideration for this "
        "exclusive franchise, the Tribe shall contribute to the State a portion "
        "of the proceeds from slot machines, based on the net drop of such "
        "machines (money dropped into machines, after payout but before "
        "expense), according to the following schedule: in years one through "
        "four, eighteen percent; years five through seven, twenty-two percent; "
        "and in years after seven, twenty-five percent.")
    tid, tcanon, tmeth = tribe("Saint Regis Mohawk Tribe", "NY")
    emit(state="NY", tribe_id=tid or "", tribe_canonical_name=tcanon or "",
         tribe_name_as_published="Mohawk",
         metric="slot_machine_net_drop_class_iii",
         metric_class="revenue", measurement_status="exact_derived_revenue",
         measurement_type=MeasurementType.COMPACT_REPORTED_COUNT.value,
         revenue_evidence="TRIBE_LEVEL_REVENUE",
         value=round(18471525.64 / 0.25, 2), unit="usd", applies_to="tribe",
         as_of_date="2019-12-31", as_of_date_precision="year",
         period_start="2019-01-01", period_end="2019-12-31",
         source_authority="Saint Regis Mohawk Tribe / State of New York "
                          "compact amendment, Secretary-approved 2005-03-07; "
                          "payment from NYSGC 2019 annual report",
         source_document_type="tribal-state compact amendment + annual report",
         source_url=ny_url, source_page="12",
         source_quote=mohawk_base_quote,
         tribe_match_method=tmeth,
         facility_match_method="not_attempted_tribe_level",
         exclusion_flag="derived_payment_over_rate",
         exclusion_reason="18,471,525.64 / 0.25, exact arithmetic. THE REVENUE "
                          "CONCEPT IS NARROW: slot-machine net drop under the "
                          "Class III compact only - no table games, no Class "
                          "II, no non-gaming. Aggregated across the Tribe, so "
                          "it is TRIBE_LEVEL_REVENUE and facility_id is "
                          "deliberately blank.")

    # The single-property attribution is PROPOSED, never taken.
    # cedar_domain.may_attribute_to_single_property requires all three of: one
    # open property, a gaming-revenue base, and a VERIFIED property count.
    # NYSGC's own compact table names exactly one Mohawk Class III facility and
    # the base is gaming revenue - but Cedar holds a second Mohawk property
    # (Mohawk Bingo Palace, a Class II hall), so the count is not verified and
    # the third condition fails. That is a ruling for a human, and it is worth
    # making: it would put a REVENUE figure on a named property.
    mohawk_props = [r for r in fac
                    if (r.get("state") or "").upper() == "NY"
                    and "mohawk" in norm(r.get("facility_name", ""))]
    q("single_property_attribution_proposed", "NY",
      "Akwesasne Mohawk Casino Resort",
      "St. Regis Mohawk 2019 Class III slot net drop, derived 73,886,102.56",
      "may_attribute_to_single_property: base IS gaming revenue (OK); NYSGC's "
      "2019 compact table names exactly one Mohawk Class III casino (OK); "
      "Cedar holds %d Mohawk NY properties (%s), so property_count_verified is "
      "FALSE and the inference is refused." % (
          len(mohawk_props),
          ", ".join("%s=%s" % (r["facility_id"], r["facility_name"])
                    for r in mohawk_props)),
      "Is Mohawk Bingo Palace outside the Class III compact universe? If yes, "
      "the derived 73,886,102.56 attaches to CCP-252700 Akwesasne Mohawk "
      "Casino Resort as SINGLE_PROPERTY_ATTRIBUTED and New York yields a "
      "property-level revenue figure. ALREADY CHECKED, so do not repeat it: no "
      "gaming-class record for Mohawk Bingo Palace exists anywhere in the NIGC "
      "files on disk, which is why this is a ruling and not a lookup.", ny_url,
      " | ".join("%s=%s" % (r["facility_id"], r["facility_name"])
                 for r in mohawk_props))

    q("ny_derivation_blocked_missing_instrument", "NY",
      "Oneida Indian Nation of New York",
      "2019 exclusivity payment 70,683,720.37; NYSGC labels the column 25%",
      "The corpus files named '2003.07.22 Oneida Nation Gaming Compact' and "
      "'2021.08.20 Oneida Gaming Compact' are addressed to the Chairperson of "
      "the Oneida Tribe of Indians of WISCONSIN and amend the Wisconsin "
      "compact of 1991. The New York Oneida instrument is NOT held.",
      "Obtain the operative Oneida Indian Nation of New York agreement. It "
      "would make 70,683,720.37 / 0.25 = 282,734,881.48 of Class III slot net "
      "win publishable at tribe level.", ny_url)

    # A misfiled compact is worse than a missing one, because it answers.
    q("compact_corpus_mislabelled_oneida", "NY",
      "508 Compliant 2003.07.22 Oneida Nation Gaming Compact",
      "data/raw/external/compacts/text/",
      "File header: 'Honorable Christina Danforth, Chairwoman, Oneida Tribe of "
      "Indians, P.O. Box 365, Oneida, Wisconsin 54155 ... the Second Amendment "
      "to the Oneida Tribe of Indians of Wisconsin and the State of Wisconsin "
      "Gaming Compact of 1991'. The 2021.08.20 file is addressed the same way.",
      "These are WISCONSIN documents filed under a New-York-sounding name. "
      "cedar_domain.STANDING_DISAMBIGUATIONS names Oneida NY vs Oneida WI "
      "exactly. Any compact-terms parse keyed on the filename will have "
      "attributed Wisconsin terms to New York. Re-label at source?",
      "https://www.bia.gov/service/gaming-compacts")

    # ---- the compact facility universe, as the STATE defines it.
    # Four properties are the point of this: it is the regulator's own list of
    # what is inside the compacts, so a property Cedar is missing from it is a
    # spine gap and a property Cedar has that is absent from it is a scope
    # question. Both are findings, and neither is resolved here.
    ny_rost_url = "http://gaming.ny.gov/2019-annual-report"
    rp = RAW / "ny" / "nysgc_2019_annual_report.pdf"
    if rp.exists():
        with pdfplumber.open(rp) as _pdf:
            roster, rmeta = ny_compact_roster(_pdf, ny_rost_url)
        print(f"   compact facility roster: {len(roster)} properties, "
              f"{len({r['tribe'] for r in roster})} nations")
        seen_fac = set()
        for o in roster:
            tid, tcanon, tmeth = tribe(o["tribe"] or "", "NY")
            fid, fname_c, fmeth = facility(o["casino"], "NY", tid)
            if fid:
                seen_fac.add(fid)
            else:
                q("agent_facility_unresolved", "NY", o["casino"],
                  f"NYSGC 2019 compact roster, {o['tribe']}, {o['location']}",
                  o["raw"][:200],
                  "Which Cedar property is this regulator name an alias of? "
                  "If none, the state names a compacted property Cedar does "
                  "not hold.", ny_rost_url, candidates("NY", tid, o["tribe"]))
            emit(state="NY", facility_id=fid or "",
                 facility_name=fname_c or "",
                 facility_name_as_published=o["casino"],
                 tribe_id=tid or "", tribe_canonical_name=tcanon or "",
                 tribe_name_as_published=o["tribe"] or "",
                 metric="compact_facility_listed", metric_class="universe",
                 measurement_status="reported_measurement",
                 measurement_type=MeasurementType.REGULATORY_REPORTED_COUNT.value,
                 value=1, unit="facility", applies_to="property",
                 as_of_date="2019-12-31", as_of_date_precision="year",
                 source_authority="New York State Gaming Commission",
                 source_document_type="annual report",
                 source_url=ny_rost_url, source_page=str(rmeta.get("page", "")),
                 source_quote=o["raw"][:400],
                 facility_match_method=fmeth, tribe_match_method=tmeth)

    # ------------------------------------------------------- state aggregates
    for a in STATE_AGGREGATES:
        emit(state=a["state"], metric=a["metric"], metric_class="revenue",
             measurement_status="reported_revenue",
             measurement_type=MeasurementType.REGULATORY_REPORTED_COUNT.value,
             revenue_evidence="REGIONAL_GGR_CONTEXT",
             value=a["value"], unit=a["unit"], applies_to="state",
             as_of_date=a["as_of"], as_of_date_precision="fiscal_year",
             period_start=a["period_start"], period_end=a["period_end"],
             source_authority=a["authority"], source_document_type=a["doctype"],
             source_url=a["url"], source_quote=a["quote"],
             exclusion_flag="state_aggregate_not_allocatable",
             exclusion_reason="Aggregated across all tribes by statute "
                              "(A.R.S. 5-601.02(H)(1)). No per-tribe split "
                              "exists to recover.")

    # ------------------------------------------------- facility universes
    for f in FACILITY_UNIVERSE:
        src = FACILITY_UNIVERSE_SRC[f["state"]]
        tid, tcanon, tmeth = tribe(f["tribe"], f["state"])
        if not tid:
            q("universe_tribe_unresolved", f["state"], f["tribe"],
              f"{src['authority']} facility roster", f["quote"],
              "Which spine entity is this?", src["url"],
              spine_candidates(f["state"]))
        fid, fname_c, fmeth = facility(f["casino"], f["state"], tid)
        if not fid:
            q("agent_facility_unresolved", f["state"], f["casino"],
              f"{src['authority']} facility roster, {f['city']}", f["quote"],
              "Which Cedar property is this regulator name an alias of? If "
              "none, the state names a property Cedar does not hold.",
              src["url"], candidates(f["state"], tid, f["tribe"]))
        emit(state=f["state"], facility_id=fid or "", facility_name=fname_c or "",
             facility_name_as_published=f["casino"],
             tribe_id=tid or "", tribe_canonical_name=tcanon or "",
             tribe_name_as_published=f["tribe"],
             metric="regulator_listed_facility", metric_class="universe",
             measurement_status="reported_measurement",
             measurement_type=MeasurementType.REGULATORY_REPORTED_COUNT.value,
             value=1, unit="facility", applies_to="property",
             as_of_date=TODAY, as_of_date_precision="day",
             source_authority=src["authority"],
             source_document_type=src["doctype"], source_url=src["url"],
             source_quote=f["quote"],
             facility_match_method=fmeth, tribe_match_method=tmeth)

    # ------------------------------------------------------------- absences
    for a in ABSENCES + MORE_ABSENCES + [LA_BLANK_FORM]:
        emit(state=a["state"], metric="documented_absence",
             metric_class="absence",
             measurement_status="documented_absence",
             measurement_type="",
             revenue_evidence="NO_REVENUE_OBSERVATION",
             value="", unit="", applies_to=a["scope"],
             as_of_date=TODAY, as_of_date_precision="day",
             source_authority=a["authority"],
             source_document_type=a["doc"],
             source_url=a["url"], source_quote=a["quote"],
             exclusion_flag=a["kind"],
             exclusion_reason=f"{a['scope']}: {a['kind']}. This state was "
                              f"CHECKED and the source states the absence in "
                              f"its own words.")

    # Louisiana names three tribal operators; Cedar's facility spine holds four
    # Louisiana tribal properties. A source disagreeing with our universe is a
    # finding, not a bug to smooth over.
    la_props = [r for r in fac
                if (r.get("state") or "").strip().upper() == "LA"]
    q("la_universe_disagreement", "LA",
      "Jena Choctaw Pines Casino",
      "LGCB 30th Annual Report names exactly three gaming tribes "
      "(Chitimacha, Coushatta, Tunica-Biloxi)",
      "Cedar holds %d LA tribal properties: %s"
      % (len(la_props), ", ".join(r["facility_name"] for r in la_props)),
      "LGCB does not mention the Jena Band of Choctaw or its casino anywhere in "
      "the report. Is Jena Choctaw Pines outside the LGCB's compact universe, "
      "or is the LGCB count stale?",
      "https://lgcb.dps.louisiana.gov/media/avxl0yu3/"
      "30th-annual-report-to-the-louisiana-state-legislature-4.pdf")

    # ------------------------------------------------------------- assertions
    bad = [r for r in rows if not r["source_url"] or not r["source_quote"]]
    assert not bad, f"{len(bad)} rows missing source_url or source_quote"
    for r in rows:
        if r["measurement_type"]:
            MeasurementType(r["measurement_type"])       # refuses a typo
        if r["revenue_evidence"]:
            assert r["revenue_evidence"] in REVENUE_EVIDENCE, r["revenue_evidence"]

    # ------------------------------------------------------------------ write
    CLEAN.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    out = CLEAN / "state_gaming_observations.csv"
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"\n  wrote {out.relative_to(CEDAR)}  ({len(rows):,} rows)")

    qout = REVIEW / f"state_gaming_unresolved_{TODAY}.csv"
    with open(qout, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=QUEUE_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(_queue.values(), key=lambda r: r["queue_id"]))
    print(f"  wrote {qout.relative_to(CEDAR)}  ({len(_queue):,} items)")

    print("\n  footing check, Wisconsin Table 1 by edition:")
    for yr, n, dv, pt, ok in footing:
        print(f"    {yr}  {n:>3} casinos  derived {dv}  printed {pt}  "
              f"{'FOOTS' if ok else 'REFUSED'}")

    by = collections.Counter((r["state"], r["metric_class"]) for r in rows)
    print("\n  observations by state and metric class:")
    for k in sorted(by):
        print(f"    {k[0]}  {k[1]:<10} {by[k]:>5}")
    nfac = len({r["facility_id"] for r in rows if r["facility_id"]})
    ntrb = len({r["tribe_id"] for r in rows if r["tribe_id"]})
    print(f"\n  {nfac} distinct Cedar properties keyed; {ntrb} distinct tribes")
    write_manifest()
    write_codebook()


# ---------------------------------------------------------------- provenance
# Every retrieved file gets a URL, a fetched date and an md5. A raw tree with
# no manifest is a pile of PDFs nobody can re-derive.
SOURCE_URLS = {
    "wi/lfb_tribal_gaming_2025.pdf": WI_URL.format(
        yr="2025", slug="0091_tribal_gaming_in_wisconsin_informational_paper_91.pdf"),
    "wi/lfb_tribal_gaming_2023.pdf": WI_URL.format(
        yr="2023", slug="0089_tribal_gaming_in_wisconsin_informational_paper_89.pdf"),
    "wi/lfb_tribal_gaming_2021.pdf": WI_URL.format(
        yr="2021", slug="0087_tribal_gaming_in_wisconsin_informational_paper_87.pdf"),
    "wi/lfb_tribal_gaming_2019.pdf": WI_URL.format(
        yr="2019", slug="0086_tribal_gaming_in_wisconsin_informational_paper_86.pdf"),
    "wi/lfb_tribal_gaming_2017.pdf": WI_URL.format(
        yr="2017", slug="0086_tribal_gaming_in_wisconsin_informational_paper_86.pdf"),
    "wi/lfb_tribal_gaming_2015.pdf": WI_URL.format(
        yr="2015", slug="0087_tribal_gaming_in_wisconsin_informational_paper_87.pdf"),
    "wi/lfb_tribal_gaming_2013.pdf": WI_URL.format(
        yr="2013", slug="0088_tribal_gaming_in_wisconsin_informational_paper_88.pdf"),
    "az/adg_annual_report_fy2025.pdf":
        "https://gaming.az.gov/sites/default/files/"
        "FY2025%20Annual%20Report%20Arizona%20Department%20of%20Gaming_0.pdf",
    "az/adg_compact_trust_fund_fy2025.pdf":
        "https://gaming.az.gov/sites/default/files/"
        "Annual%20Compact%20Trust%20Fund%20Report%20FY%202025.pdf",
    "az/adg_tribal_contributions_fy2025.pdf":
        "https://gaming.az.gov/sites/default/files/"
        "Annual%20Report%20on%20Tribal%20Contributions%20FY%202025.pdf",
    "az/adg_cumulative_tc_states_fy2026.pdf":
        "https://gaming.az.gov/sites/default/files/"
        "Cumulative%20TC%20amts%20-%20States%20FY2026%20as%20of%20063026-4th%20Qtr%20FY.pdf",
    "az/adg_annual_report_fy2012.pdf":
        "https://gaming.az.gov/sites/default/files/FY%2012%20Annual%20Report_0.pdf",
    "la/lgcb_annual_report_30th.pdf":
        "https://lgcb.dps.louisiana.gov/media/avxl0yu3/"
        "30th-annual-report-to-the-louisiana-state-legislature-4.pdf",
    "la/lgcb_annual_report_29th.pdf":
        "https://lgcb.dps.louisiana.gov/media/akjhoqlz/"
        "29th-annual-report-to-the-louisiana-state-legislature-revised.pdf",
    "la/lgcb_annual_report_2023.pdf":
        "https://lgcb.dps.louisiana.gov/media/i2zjzaio/2023_27th_annual_report.pdf",
    "la/lgcb_annual_report_2019.pdf":
        "https://lgcb.dps.louisiana.gov/media/13ljhnys/2019_annual_report.pdf",
    "la/lgcb_annual_report_2016.pdf":
        "https://lgcb.dps.louisiana.gov/media/1jsp0py0/2016_annual_report.pdf",
    "la/lgcb_annual_report_2010.pdf":
        "https://lgcb.dps.louisiana.gov/media/5rplpspf/2010_annual_report.pdf",
    "la/lgcb_annual_report_2005.pdf":
        "https://lgcb.dps.louisiana.gov/media/02ghbqyt/2005_annual_report.pdf",
}

# NOT on disk, deliberately. `gaming.az.gov/sites/default/files/FY%2014%20Annual
# %20Report_0.pdf` returns **HTTP 403** while the FY12 file at the identical
# path pattern returns 200. curl wrote the 5,642-byte HTML error body to a file
# named `.pdf`; it was deleted rather than kept, because a 403 body sitting in a
# raw tree under a `.pdf` name is precisely the "check the status, not the file"
# trap AGENTS.md records against bia.gov. Recorded here so the next pass knows
# it was tried.
REFUSED_ON_FETCH = {
    "az/adg_annual_report_fy2014.pdf": (
        "https://gaming.az.gov/sites/default/files/FY%2014%20Annual%20Report_0.pdf",
        "HTTP 403, text/html body"),
}


def write_manifest():
    man = RAW / "_SOURCE_MANIFEST.csv"
    existing = {r["relative_path"]: r for r in read_csv(man)}
    out = []
    for p in sorted(RAW.rglob("*")):
        if not p.is_file() or p.name.startswith("_SOURCE_MANIFEST"):
            continue
        rel = p.relative_to(RAW).as_posix()
        prev = existing.get(rel, {})
        out.append({
            "relative_path": rel,
            "state": rel.split("/")[0].upper(),
            "source_url": SOURCE_URLS.get(rel, prev.get("source_url", "")),
            "bytes": p.stat().st_size,
            "md5": hashlib.md5(p.read_bytes()).hexdigest(),
            "content_type": ("application/pdf" if p.suffix.lower() == ".pdf"
                             else "text/html" if p.suffix.lower() in (".html", ".htm")
                             else "application/octet-stream"),
            "fetched_date": prev.get("fetched_date", TODAY),
            "retrieved_by": prev.get("retrieved_by",
                                     "code/107_pull_remaining_states.py"),
        })
    flds = ["relative_path", "state", "source_url", "bytes", "md5",
            "content_type", "fetched_date", "retrieved_by"]
    with open(man, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=flds, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    miss = sum(1 for r in out if not r["source_url"])
    print(f"  wrote {man.relative_to(CEDAR)}  ({len(out):,} files, "
          f"{miss} without a recorded source_url)")



# ------------------------------------------------------------------ codebook
# VARIABLES ONLY. A codebook says what a column is; it does not say what the
# build found. Findings live in docs/STATE_GAMING_PULL_LOG.md, and keeping the
# two apart is what stops the codebook drifting into a stale narrative.
CODEBOOK = [
    ("observation_id", "text", "code", "Row identifier, SG-<state>-<n>."),
    ("state", "text", "code", "USPS code of the state whose regulator or "
     "legislative agency published the figure."),
    ("facility_id", "text", "code", "Cedar property ID (CCP-/VP-/TPL-). Blank "
     "where the source reports at tribe or state level, or where the "
     "regulator's casino name did not resolve and went to the review queue."),
    ("facility_name", "text", "name", "Cedar's canonical name for that property."),
    ("facility_name_as_published", "text", "name", "The casino name exactly as "
     "the source prints it. A different name is an ALIAS, never a new property."),
    ("tribe_id", "text", "code", "Cedar entity spine ID, from resolve_entity."),
    ("tribe_canonical_name", "text", "name", "Spine canonical name."),
    ("tribe_name_as_published", "text", "name", "Tribe name exactly as the "
     "source prints it."),
    ("metric", "text", "code", "What was measured. gaming_machines, "
     "table_games, lump_sum_payment_to_state, "
     "lump_sum_payment_to_state_cumulative_<window>, net_win_state_aggregate, "
     "gross_gaming_revenue_state_aggregate, "
     "tribal_contributions_state_aggregate, "
     "tribal_contributions_to_local_government_aggregate, documented_absence."),
    ("metric_class", "text", "code", "capacity | payment | revenue | absence."),
    ("measurement_status", "text", "code", "reported_measurement | "
     "reported_payment | reported_revenue | documented_absence."),
    ("measurement_type", "text", "code", "cedar_domain.MeasurementType. An "
     "authorised device count is AUTHORIZED_MAXIMUM and may_promote() refuses "
     "its transition to ACTIVE_FLOOR_COUNT; nothing in this file is an "
     "authorisation, so every typed row is REGULATORY_REPORTED_COUNT."),
    ("revenue_evidence", "text", "code", "cedar_domain.REVENUE_EVIDENCE. "
     "REGIONAL_GGR_CONTEXT on state aggregates; NO_REVENUE_OBSERVATION where "
     "the source states an absence or reports a payment with no stated rate "
     "and base to invert."),
    ("value", "numeric", "varies", "The figure. Unit is in `unit`."),
    ("unit", "text", "code", "count | usd | usd_millions."),
    ("applies_to", "text", "code", "property | tribe | state. The level the "
     "source reports at, NOT the level a reader may want."),
    ("as_of_date", "date", "YYYY-MM-DD", "Date the figure describes, taken "
     "from the table's own caption or period label, never from the "
     "publication date of the document."),
    ("as_of_date_precision", "text", "code", "day | month | year | "
     "fiscal_year | reporting_period."),
    ("period_start", "date", "YYYY-MM-DD", "First day of the reported period. "
     "Blank for point-in-time counts."),
    ("period_end", "date", "YYYY-MM-DD", "Last day of the reported period."),
    ("source_authority", "text", "name", "The body that published it."),
    ("source_document_type", "text", "code", "e.g. legislative informational "
     "paper, statutory annual report."),
    ("source_url", "url", "url", "Direct URL to the document. Never blank - "
     "the build asserts this before writing."),
    ("source_page", "text", "number", "PDF page the figure was read from."),
    ("source_quote", "text", "text", "Verbatim text supporting the row. For a "
     "table row it is the reconstructed baseline in document order, so the "
     "row can be checked against the page. Never blank."),
    ("facility_match_method", "text", "code", "exact_name_in_state | "
     "sole_property_of_tribe_in_state | ambiguous_exact_name:<n> | "
     "not_attempted_tribe_level | unresolved."),
    ("tribe_match_method", "text", "code", "resolve_entity's method (exact, "
     "core, alias, containment) or a refusal: refused_entity_class:<class>, "
     "refused_state_disagreement:spine=<st>, ambiguous_*, no_spine_match."),
    ("exclusion_flag", "text", "code", "Non-blank means the row must not be "
     "pooled with plain observations. state_aggregate_not_allocatable | "
     "cumulative_window | the absence kind."),
    ("exclusion_reason", "text", "text", "Why, in words."),
    ("fetched_date", "date", "YYYY-MM-DD", "When the source file was retrieved."),
    ("built_date", "date", "YYYY-MM-DD", "When this row was built."),
]


def write_codebook():
    """Append this dataset's variables to codebook_master.csv.

    THIS FILE IS SHARED AND IT IS BEING CLOBBERED. Measured on 2026-08-07:

        18:43:23  script 108 snapshots the file          1,099 rows
        18:43:42  script 107 snapshots the file          1,121 rows
                  (another agent added `15_tribal_tax` in that 19s window)
        18:43:42  script 107 writes 107 + everything it saw
        18:58:00  script 108 writes 108 + everything IT saw  1,174 rows
                  -> `15_tribal_tax` (22 rows) GONE
                  -> `14_state_gaming` (31 rows) GONE

    Every script here does the individually correct thing - back up, re-read,
    preserve what it sees, write. The failure is structural, exactly like the
    four-pollers-per-host failure PULL_DISCIPLINE.md was written for: a
    read-modify-write on a shared file is last-writer-wins, and no agent can
    see the others.

    Until that is fixed centrally, this writer does the one thing that makes it
    safe to run at any time: it RESTORES. It compares the file it is about to
    write against its own backup, and any dataset that was present then and is
    absent now is put back rather than accepted as deleted. A dataset vanishing
    between two runs on the same day is a clobber, not a decision - a real
    deletion would come with a script that removes it, not with a gap. What is
    restored is printed, never silent.
    """
    p = CLEAN / "codebook_master.csv"
    prior = read_csv(p)
    if prior:
        bak = p.with_suffix(f".csv.bak_{TODAY}_pre107")
        if not bak.exists():
            bak.write_bytes(p.read_bytes())
        baseline = read_csv(bak)
    else:
        baseline = []

    ds = "14_state_gaming"
    keep = [r for r in prior if r.get("dataset") != ds]
    here = {r.get("dataset") for r in prior}
    restored = collections.Counter()
    for r in baseline:
        d = r.get("dataset")
        if d and d != ds and d not in here:
            keep.append(r)
            restored[d] += 1

    n = len(rows)
    filled = {c: sum(1 for r in rows if str(r.get(c, "")).strip()) for c in FIELDS}
    new = [{"dataset": ds, "variable": v, "type": t, "units": u,
            "pct_filled": f"{100.0 * filled.get(v, 0) / n:.1f}" if n else "0.0",
            "n_rows": str(n), "published": "1", "access_tier": "public",
            "description": d, "generated": TODAY}
           for v, t, u, d in CODEBOOK]
    flds = list(prior[0].keys()) if prior else [
        "dataset", "variable", "type", "units", "pct_filled", "n_rows",
        "published", "access_tier", "description", "generated"]
    keep.sort(key=lambda r: (r.get("dataset") or ""))
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=flds, extrasaction="ignore")
        w.writeheader()
        w.writerows(keep + new)
    print(f"  wrote {p.relative_to(CEDAR)}  (+{len(new)} variables for {ds}, "
          f"{len(keep)} other rows preserved)")
    for d, k in restored.items():
        print(f"    RESTORED {k} rows for `{d}` - present in this script's "
              f"backup, absent from the file it just read. Clobbered by a "
              f"concurrent writer, not deleted.")



if __name__ == "__main__":
    main()
