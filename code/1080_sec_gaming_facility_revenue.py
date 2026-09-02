#!/usr/bin/env python3
"""1080 - per-facility tribal gaming money out of SEC filings already on disk.

WHY THIS EXISTS
---------------
NIGC does not publish per-operation revenue. `gaming_revenue_bounds.csv` records
that honestly: 13,494 of its 13,803 bound rows are a REGIONAL_GGR_CEILING - one
NIGC-region ceiling repeated on every property in the region - and only 176 rows
(115 SINGLE_PROPERTY_ATTRIBUTED + 61 REPORTED_PROPERTY_REVENUE), reaching 11 of
787 facilities, are an honest per-property figure.

But a company that *manages*, *develops* or *operates* a tribal casino and files
with the SEC must disclose the economics of that contract: the fee, the term, the
formula the fee is a percentage of, and - where the property is a reportable
segment - the property's own revenues. Those disclosures are audited and filed
under federal securities law. They are a THIRD class of evidence, distinct from
both a casino's marketing page and an NIGC figure.

WHAT IT READS  (zero network - everything is already cached)
------------------------------------------------------------
  review/sec_edgar_1030_fetch_manifest.csv   1,172 documents fetched by 1030
  data/raw/external/sec_edgar_1030/          the documents themselves (1.1 GB)
  data/clean/gaming_facilities.csv           to key a property to a facility_id
  code/_1080_facility_aliases.py             the curated alias -> facility map
  review/sec_gaming_1080_adjudication.csv    hand rulings on mined candidates,
                                             regenerate with code/_1080_adjudication.py

WHAT IT WRITES
--------------
  review/sec_gaming_1080_candidates.csv              mine  - every raw hit
  data/clean/sec_gaming_financial_disclosures.csv    build - accepted figures
  data/clean/sec_gaming_management_contract_terms.csv  build - contract terms

STAGES
------
  mine      zero network. HTML -> text, anchored patterns, one row per hit,
            each carrying its verbatim quote and the accession it came from.
  build     joins the adjudication file and writes the two clean tables.
  verify    invariants. Exits 1 on breach.
  selftest  injects a synthetic violation, asserts verify exits 1 AND names the
            invariant, restores, asserts verify exits 0.

THE FENCE - READ BEFORE YOU TOTAL ANYTHING
------------------------------------------
`assertion_class = SEC_FILED_FINANCIAL_DISCLOSURE`. It is deliberately outside
`cedar_domain.MeasurementType` and outside the SELF_PUBLISHED_* family. A row
here may NEVER be summed against `gaming_revenue_bounds.csv`, `nigc_regional_ggr
.csv`, `nigc_revenue_bands.csv`, `gaming_capacity_official.csv`,
`state_gaming_observations.csv` or the self-published tables. Adding an
SEC-derived property revenue to an NIGC regional ceiling double-counts the same
dollar - the property is inside the region.

And the figure types here are NOT interchangeable. A management fee, a property's
net revenues, its gross revenues and its EBITDA are four different numbers about
one property. `figure_type` says which. Summing across `figure_type` is the
error this column exists to prevent.

DERIVATION - AND THE ONE CORRECTION THIS SCRIPT OWES ITS OWN PREMISE
--------------------------------------------------------------------
A fee does NOT imply revenue. IGRA defines "net revenues" at 25 U.S.C. 2703(9)
as gross gaming revenues less prizes and less gaming-related operating expenses
excluding management fees - nearer operating profit than revenue - and the
contracts in this corpus variously use "net revenue as defined", "net income as
defined", a threshold and a floor. Inverting a fee recovers THAT CONTRACT'S OWN
BASE and nothing else.

So: a figure is derived ONLY where the same registrant states the percentage and
the base is flat over the period. `derived_from_fee = Y` rows show the arithmetic
in `derivation_arithmetic`, name the rate's accession in
`derivation_percentage_source_accession`, and are typed
`DERIVED_FACILITY_*_AS_DEFINED` - never plain "revenue". V10 exits 1 if a derived
figure wears a reported figure's figure_type. Two of the eight formulas found
were invertible; six were refused, with reasons, in the adjudication file.

RE-RUN
------
  py -3 code/1080_sec_gaming_facility_revenue.py mine
  py -3 code/1080_sec_gaming_facility_revenue.py build
  py -3 code/1080_sec_gaming_facility_revenue.py codebook
  py -3 code/1080_sec_gaming_facility_revenue.py verify
  py -3 code/1080_sec_gaming_facility_revenue.py selftest
"""

from __future__ import annotations

import csv
import hashlib
import html
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT = "code/1080_sec_gaming_facility_revenue.py"
CEDAR = Path(__file__).resolve().parent.parent
CODE = CEDAR / "code"
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
CACHE = CEDAR / "data" / "raw" / "external" / "sec_edgar_1030"

MANIFEST = REVIEW / "sec_edgar_1030_fetch_manifest.csv"
CANDIDATES = REVIEW / "sec_gaming_1080_candidates.csv"
ADJUDICATION = REVIEW / "sec_gaming_1080_adjudication.csv"
OUT_FIG = CLEAN / "sec_gaming_financial_disclosures.csv"
OUT_TERMS = CLEAN / "sec_gaming_management_contract_terms.csv"

TODAY = datetime.now().strftime("%Y-%m-%d")
START_T = datetime.now().timestamp()
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

sys.path.insert(0, str(CODE))
from _1080_facility_aliases import ALIASES, FILERS  # noqa: E402

ASSERTION_CLASS = "SEC_FILED_FINANCIAL_DISCLOSURE"
ASSERTION_CLASS_NOTE = (
    "SEC-FILED FINANCIAL DISCLOSURE. The figure was filed with the Securities and "
    "Exchange Commission by the named registrant under a federal disclosure "
    "obligation, in the form and accession named on the row, and (for a 10-K) sits "
    "inside or beside audited financial statements. That makes it STRONGER than a "
    "casino's self-published marketing number and DIFFERENT IN KIND from an NIGC "
    "figure - it is the filer's own accounting of its own contract, not a "
    "regulator's measurement of the industry. It is neither, and it is pooled with "
    "neither."
)
NOT_SUMMABLE = (
    "gaming_revenue_bounds.csv, nigc_regional_ggr.csv, nigc_revenue_bands.csv, "
    "gaming_capacity_official.csv, state_gaming_observations.csv, "
    "gaming_property_self_published_assertions.csv, "
    "gaming_property_self_published_claims.csv - and never across figure_type "
    "within this table"
)

FIG_COLS = [
    "disclosure_id", "assertion_class", "assertion_class_note", "not_summable_with",
    "figure_type", "figure_type_note", "value_usd", "value_verbatim",
    "value_precision", "value_scale_applied",
    "fiscal_period_label", "period_type", "period_end", "fiscal_year",
    "facility_id", "facility_name_cedar", "facility_name_as_filed",
    "tribe_name", "tribe_id", "cedar_uid", "state",
    "facility_is_on_indian_lands",
    "filer_name", "filer_cik", "filer_role", "manager_name",
    "form", "filing_date", "accession", "source_url", "local_file", "source_md5",
    "source_quote",
    "derived_from_fee", "derivation_input_fee_usd", "derivation_stated_percentage",
    "derivation_percentage_base", "derivation_percentage_source_accession",
    "derivation_arithmetic", "derivation_caveat",
    "is_first_filing_of_this_fact", "n_filings_stating_this_fact",
    "restated_in_accessions", "restatements_agree",
    "extraction_pattern", "adjudication", "adjudication_note",
    "record_scope", "record_scope_basis", "built_by", "built_date",
]

TERM_COLS = [
    "term_id", "assertion_class", "assertion_class_note", "not_summable_with",
    "manager_name", "manager_cik", "manager_role",
    "tribe_name", "tribe_id", "facility_id", "facility_name_cedar",
    "facility_name_as_filed", "state",
    "fee_formula_verbatim", "fee_percentage", "fee_percentage_base",
    "fee_is_tiered", "contract_term_years", "contract_expiry_as_stated",
    "form", "filing_date", "accession", "source_url", "source_quote",
    "extraction_pattern", "adjudication", "adjudication_note",
    "record_scope", "record_scope_basis", "built_by", "built_date",
]

TERMS_ASSERTION_CLASS = "SEC_FILED_CONTRACT_TERM"
TERMS_CLASS_NOTE = (
    "SEC-FILED CONTRACT TERM. A management- or development-agreement term as the "
    "registrant described it in its own filing. It is a description of a contract, "
    "NOT a dollar figure and NOT a measurement. It carries no money and may not be "
    "totalled with anything. Where a fee percentage is stated here and a fee dollar "
    "figure appears in sec_gaming_financial_disclosures.csv for the same contract "
    "and period, that pair - and only that pair - supports a derived revenue, and "
    "the derivation is shown on the figure row, never assembled by a consumer."
)


def out(s=""):
    sys.stdout.write(str(s).encode("ascii", "replace").decode() + "\n")
    sys.stdout.flush()


# ------------------------------------------------------------------ text --

def totext(path: Path) -> str:
    t = path.read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"(?is)<(script|style).*?</\1>", " ", t)
    t = re.sub(r"(?is)</t[dh]>", " | ", t)
    t = re.sub(r"(?is)</tr>", " \n", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'),
                 ("—", "-"), ("–", "-"), ("�", "'"), (" ", " ")):
        t = t.replace(a, b)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"(?: *\| *)+", " | ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t


def flat(t: str) -> str:
    return re.sub(r"\s+", " ", t)


MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"])}


def parse_date(s: str):
    m = re.match(r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})", s.strip())
    if not m or m.group(1) not in MONTHS:
        return ""
    return f"{int(m.group(3)):04d}-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}"


SCALE = {"": 1, "million": 1_000_000, "billion": 1_000_000_000, "thousand": 1_000}


def to_usd(amount: str, scale: str):
    a = amount.replace(",", "").strip()
    if not re.fullmatch(r"\d+(\.\d+)?", a):
        return None
    return float(a) * SCALE.get((scale or "").lower(), 1)


PERIOD_WORDS = (
    r"(?:fiscal year|fiscal|year|twelve months|three months|six months|"
    r"nine months|quarter|period)"
)


# --------------------------------------------------------------- mining --

_ALIAS_LOOKUP = {}
for _a in ALIASES:
    _ALIAS_LOOKUP[re.sub(r"[\s\-]+", " ", _a).strip().lower()] = _a


def canonical_alias(s: str) -> str:
    """The regex matches the filer's spacing; the map is keyed on ours."""
    return _ALIAS_LOOKUP.get(re.sub(r"[\s\-]+", " ", s or "").strip().lower(), "")


def alias_regex():
    pats = []
    for alias in sorted(ALIASES, key=len, reverse=True):
        body = re.escape(alias).replace(r"\ ", r"[\s\-]+")
        pats.append((alias, re.compile(r"(?<![A-Za-z])" + body + r"(?![A-Za-z])")))
    return pats


# The optional "For Fiscal 2006, " prefix was originally part of this pattern.
# It had to come OUT: consuming the period cue moved m.start() past it, so the
# period lookback then searched the 300 characters BEFORE the cue and found
# nothing. Six Seneca rows came out with a figure and no fiscal year. The
# pattern now starts at the property and the cue is left in the lookback window.
PAT_A = re.compile(
    r"(?P<prop>@@PROP@@)"
    r"[^.]{0,90}?\b(?:generated|produced|recorded|reported|had|achieved)\s+"
    r"(?P<label>net revenues?|gross revenues?|net gaming revenues?|"
    r"gross gaming revenues?|net win)\s+of\s+"
    r"\$\s?(?P<amt>[\d,]+(?:\.\d+)?)\s*(?P<scale>million|billion|thousand)?")

# NOTE: the character class here is `.` and not `[^.]`. `[^.]` was the first
# attempt and it matched NOTHING across 609 documents, because every dollar
# figure in this prose carries a decimal point - "declined by $77.0 million, or
# 7.2%, to $992.0 million". A pattern that cannot cross a decimal point cannot
# read a financial statement. The anchor that keeps this safe is the tail:
# "$N million for the <period> ended <date>", which does not occur by accident.
PAT_B1 = re.compile(
    r"(?P<prop>@@PROP@@)\s+Revenues?\s+"
    r"(?P<label>Net revenues?|Gross revenues?)\s+"
    r"(?:increased|decreased|declined|grew|rose|totaled|totalled|were|was)"
    r"(?:.{0,170}?\bto\b)?\s+"
    r"\$\s?(?P<amt>[\d,]+(?:\.\d+)?)\s*(?P<scale>million|billion)\s+"
    r"(?:for|in)\s+the\s+"
    + PERIOD_WORDS + r"\s+ended\s+(?P<date>[A-Z][a-z]+\s+\d{1,2},\s*\d{4})")

PAT_B2 = re.compile(
    r"compared\s+to\s+\$\s?(?P<amt>[\d,]+(?:\.\d+)?)\s*(?P<scale>million|billion)\s+"
    r"in\s+the\s+prior\s+(?:fiscal\s+)?(?:year|period)")

PAT_D = re.compile(
    r"management\s+fee\s+(?:revenues?|income)?\s*"
    r"(?:from|earned\s+from|attributable\s+to|related\s+to)\s+"
    r"(?:the\s+)?(?P<prop>@@PROP@@)"
    r"[^.]{0,220}?\$\s?(?P<amt>[\d,]+(?:\.\d+)?)\s*(?P<scale>million|billion)?",
    re.I)

PAT_E = re.compile(
    r"(?P<quote>(?:management\s+)?fee\s+(?:equal\s+to|of|based\s+on|equal\s+to\s+"
    r"approximately)\s+[^.]{0,40}?(?P<pct>\d{1,2}(?:\.\d+)?)\s*%\s*of\s+"
    r"(?:the\s+)?(?P<base>net\s+revenues?|net\s+income|net\s+profits?|profits?|"
    r"gross\s+revenues?|net\s+win|revenues?)[^.]{0,180})", re.I)


# ---------------------------------------------------------- PATTERN C --
# The segment table. This is where the dense multi-year property revenue lives
# (Mohegan reports Mohegan Sun, Mohegan Sun Pocono and MGE Niagara as separate
# lines under one "Net revenues:" header, three fiscal years wide).
#
# It is a TABLE parser, not a regex, and it refuses rather than guesses:
#   - it will not emit unless it found a year header with >= 2 four-digit years
#     within 10 rows above the "Net revenues:" line;
#   - it will not emit unless it found an explicit units statement
#     ("in thousands" / "in millions") within 3,000 characters above;
#   - it will not emit if the row carries fewer numeric cells than years.
# Every refusal is counted and printed, because a table parser that silently
# reads nothing looks exactly like a corpus that contains nothing.

YEAR_RE = re.compile(r"\b(19[89]\d|20[0-4]\d)\b")
NUMCELL_RE = re.compile(r"^\(?\$?\s*(\d[\d,]*(?:\.\d+)?)\s*\)?$")
UNITS_RE = re.compile(r"\(?(?:amounts?\s+)?in\s+(thousands|millions)", re.I)
SEGHDR_RE = re.compile(r"^\s*(?:Net revenues|Total net revenues|Revenues)\s*:\s*\|?\s*$", re.I)
PERIOD_HDR_RE = re.compile(
    r"(?:for\s+the\s+)?(?:fiscal\s+)?years?\s+ended\s+"
    r"(?P<mon>January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(?P<day>\d{1,2})\s*,?\s*(?:\||$)", re.I)
# NOTE the trailing `(?:\||$)` rather than `$`. Mohegan's FY2022 10-K writes the
# header as "For the Fiscal Years Ended September 30, | Variance 2022 vs. 2021 |",
# and an end-of-line anchor refused it - three tables, six property-years, lost
# to a trailing variance column.


def parse_segment_tables(raw: str, form: str, refusals):
    """Yield (alias, iso_period_end, value_usd, units, quote) from segment tables.

    FOUR REFUSALS, and they are the point of this function.

    The first version of this parser took any line holding two four-digit years
    as a period header. On a 10-Q that is wrong in a way that looks right: the
    columns are "Three Months Ended June 30, 2017 / 2016" and "Nine Months
    Ended ...", and the parser stamped every one of them `fiscal year 2017`.
    102 of the 132 rows it produced were quarterly figures wearing an annual
    label, and one was 11,200 - a percentage cell read as dollars.

    So: 10-K only, and the header must SAY "Years Ended <Month> <Day>". A table
    that does not state its period in words does not get read. Every refusal is
    counted by reason and printed by `mine`.
    """
    if form.upper() not in ("10-K", "10-K/A"):
        refusals["not_an_annual_report"] += 1
        return
    lines = raw.split("\n")
    offs, acc = [], 0
    for ln in lines:
        offs.append(acc)
        acc += len(ln) + 1
    for i, ln in enumerate(lines):
        if not SEGHDR_RE.match(ln):
            continue
        years, mon, day = [], None, None
        year_line = period_line = ""
        for j in range(max(0, i - 10), i):
            ys = YEAR_RE.findall(lines[j])
            if len(ys) >= 2 and len(re.sub(r"[^A-Za-z]", "", lines[j])) < 60:
                years = [int(y) for y in ys]
                year_line = lines[j].strip()
            mp = PERIOD_HDR_RE.search(lines[j].strip())
            if mp:
                mon, day = mp.group("mon"), int(mp.group("day"))
                period_line = lines[j].strip()
        if not years:
            refusals["no_year_header"] += 1
            continue
        if not mon:
            refusals["header_states_no_period_in_words"] += 1
            continue
        back = raw[max(0, offs[i] - 3000):offs[i]]
        mu = None
        for mu in UNITS_RE.finditer(back):
            pass
        if mu is None:
            refusals["no_units_statement"] += 1
            continue
        units = mu.group(1).lower()
        mult = 1_000 if units == "thousands" else 1_000_000
        emitted_here = 0
        for k in range(i + 1, min(len(lines), i + 16)):
            cells = [c.strip() for c in lines[k].split("|")]
            cells = [c for c in cells if c != ""]
            if not cells:
                continue
            alias = canonical_alias(cells[0])
            if not alias:
                if re.match(r"(?i)^\s*(income|loss|operating|adjusted|total)\b", cells[0]):
                    break
                continue
            nums = [c for c in cells[1:] if NUMCELL_RE.match(c)]
            if len(nums) < len(years):
                refusals["row_short_of_years"] += 1
                continue
            # THE ROW GOES FIRST. The first version put the header first and
            # truncated at 1,600 characters, and on two Mohegan 10-Ks the
            # "header" was 1,600 characters of MD&A prose - so the quote for a
            # correct figure contained no figure at all. A quote that does not
            # contain the number it is evidence for is not evidence.
            # The quote is the three lines that actually decided the reading:
            # the period header, the year header and the property row. An
            # earlier version pasted six preceding lines of MD&A prose instead,
            # and on two Mohegan 10-Ks the truncated result contained no number.
            row = lines[k].strip()
            quote = re.sub(r"\s+", " ", " || ".join(
                x for x in (period_line, year_line, lines[i].strip(), row) if x)).strip()
            for y, cell in zip(years, nums[:len(years)]):
                m = NUMCELL_RE.match(cell)
                val = float(m.group(1).replace(",", "")) * mult
                iso = "%04d-%02d-%02d" % (y, MONTHS[mon.capitalize()], day)
                yield alias, iso, val, units, quote
                emitted_here += 1
        if emitted_here == 0:
            refusals["header_matched_no_alias_row"] += 1


# "... totaled $A and $B ... for the years ended December 31, 2018 and 2017,
# respectively" is the densest single sentence shape in this corpus and it was
# almost lost. The first version led with `(?P<lead>.{0,320}?)`, which made the
# engine try 320 prefix lengths at every one of ~300,000 offsets per document -
# the mine stage ran past ten minutes on one filer. ANCHOR FIRST: find the word
# "respectively", then read a fixed window backwards. Same result, one pass.
RESPECTIVELY_RE = re.compile(r"\brespectively\b", re.I)
VAL_RE = re.compile(r"\$\s?([\d,]+(?:\.\d+)?)\s*(million|billion)?", re.I)
YEARS_ENDED_RE = re.compile(
    r"years?\s+ended\s+(?P<mon>[A-Z][a-z]+)\s+(?P<day>\d{1,2}),\s*"
    r"(?P<ys>\d{4}(?:\s*(?:,|and)\s*\d{4}){1,4})", re.I)
TAIL_VALS_RE = re.compile(
    r"(?:totaled|totalled|were|was|of|to)\s+"
    r"(?P<vals>\$\s?[\d,]+(?:\.\d+)?\s*(?:million|billion)?"
    r"(?:\s*(?:,|and)\s*\$\s?[\d,]+(?:\.\d+)?\s*(?:million|billion)?){1,4})"
    r"\s*,?\s*$", re.I)


def build_pattern(p: re.Pattern, prop_alt: str) -> re.Pattern:
    return re.compile(p.pattern.replace("@@PROP@@", prop_alt), p.flags)


def mine():
    if not MANIFEST.exists():
        raise SystemExit(f"missing {MANIFEST}")
    man = list(csv.DictReader(MANIFEST.open(encoding="utf-8")))
    aliases = alias_regex()
    prop_alt = "|".join(
        re.escape(a).replace(r"\ ", r"[\s\-]+") for a in sorted(ALIASES, key=len, reverse=True))
    pa = build_pattern(PAT_A, prop_alt)
    pb1 = build_pattern(PAT_B1, prop_alt)
    pd = build_pattern(PAT_D, prop_alt)

    rows = []
    seen = set()
    from collections import Counter as _C
    refusals = _C()
    n_docs = 0
    n_read = 0
    for x in man:
        lf = x["local_file"].replace("\\", "/")
        p = CEDAR / lf
        if not p.is_file():
            continue
        n_docs += 1
        cik = x["cik"].lstrip("0")
        filer = FILERS.get(cik)
        if filer is None:
            continue
        n_read += 1
        raw = totext(p)
        t = flat(raw)
        base = dict(
            filer_name=filer["name"], filer_cik=x["cik"], filer_role=filer["role"],
            form=x["form"], filing_date=x["file_date"], accession=x["accession"],
            source_url=x["document_url"], local_file=lf, source_md5=x["md5"],
        )

        def add(**kw):
            key = (kw["extraction_pattern"], base["accession"], kw.get("alias", ""),
                   kw.get("value_verbatim", ""), kw.get("fiscal_period_label", ""),
                   kw.get("figure_type", ""))
            if key in seen:
                return
            seen.add(key)
            r = dict(base)
            r.update(kw)
            a = ALIASES.get(canonical_alias(kw.get("alias", "")))
            if a:
                r["facility_id"], r["tribe_name"], r["state"], r["on_indian_lands"] = a
            rows.append(r)

        # ---- PATTERN A: "<PROPERTY> generated net revenue of $X million"
        for m in pa.finditer(t):
            alias = m.group("prop")
            q = t[max(0, m.start() - 200):m.end() + 120]
            per = period_from_context(t, m.start(), m.end())
            add(extraction_pattern="A_NARRATIVE_GENERATED", alias=alias,
                facility_name_as_filed=alias,
                figure_type=label_to_type(m.group("label")),
                figure_type_note=m.group("label"),
                value_verbatim=m.group(0)[m.group(0).rfind("$"):],
                value_scale_applied=(m.group("scale") or "").lower(),
                value_usd=to_usd(m.group("amt"), m.group("scale") or ""),
                fiscal_period_label=per[0], period_end=per[1], period_type=per[2],
                source_quote=q.strip())

        # ---- PATTERN B1: MD&A property heading, "Net revenues ... to $X for FY ended D"
        for m in pb1.finditer(t):
            alias = m.group("prop")
            q = t[max(0, m.start() - 60):m.end() + 260]
            d = parse_date(m.group("date"))
            add(extraction_pattern="B_MDNA_PROPERTY_HEADING", alias=alias,
                facility_name_as_filed=alias,
                figure_type=label_to_type(m.group("label")),
                figure_type_note=m.group("label"),
                value_verbatim="$" + m.group("amt") + " " + (m.group("scale") or ""),
                value_scale_applied=(m.group("scale") or "").lower(),
                value_usd=to_usd(m.group("amt"), m.group("scale")),
                fiscal_period_label="period ended " + m.group("date"),
                period_end=d, period_type=period_type_from(m.group(0)),
                source_quote=q.strip())
            tail = t[m.end():m.end() + 260]
            m2 = PAT_B2.search(tail)
            if m2 and d:
                prior = prior_period(d, period_type_from(m.group(0)))
                add(extraction_pattern="B_MDNA_PROPERTY_HEADING_PRIOR", alias=alias,
                    facility_name_as_filed=alias,
                    figure_type=label_to_type(m.group("label")),
                    figure_type_note=m.group("label") + " (prior comparative)",
                    value_verbatim="$" + m2.group("amt") + " " + (m2.group("scale") or ""),
                    value_scale_applied=(m2.group("scale") or "").lower(),
                    value_usd=to_usd(m2.group("amt"), m2.group("scale")),
                    fiscal_period_label="prior period ended " + (prior or "?"),
                    period_end=prior, period_type=period_type_from(m.group(0)),
                    source_quote=(m.group(0) + " " + m2.group(0)).strip())

        # ---- PATTERN D: management fee revenue named to a property
        for m in pd.finditer(t):
            alias = m.group("prop")
            q = t[max(0, m.start() - 240):m.end() + 300]
            per = period_from_context(t, m.start(), m.end() + 200)
            add(extraction_pattern="D_MANAGEMENT_FEE_NAMED", alias=alias,
                facility_name_as_filed=alias,
                figure_type="MANAGEMENT_FEE_REVENUE",
                figure_type_note="management fee revenue earned by the filer from the named property",
                value_verbatim="$" + m.group("amt") + " " + (m.group("scale") or ""),
                value_scale_applied=(m.group("scale") or "").lower(),
                value_usd=to_usd(m.group("amt"), m.group("scale") or ""),
                fiscal_period_label=per[0], period_end=per[1], period_type=per[2],
                source_quote=q.strip())

        # ---- PATTERN C: segment table (multi-year, property grain, 10-K only)
        for alias, iso, val, units, quote in parse_segment_tables(raw, x["form"], refusals):
            add(extraction_pattern="C_SEGMENT_TABLE", alias=alias,
                facility_name_as_filed=alias,
                figure_type="FACILITY_NET_REVENUES",
                figure_type_note="segment net revenues, table stated in " + units,
                value_verbatim="%s (segment table stated in %s)" % (format(val, ",.0f"), units),
                value_scale_applied=units,
                value_usd=val,
                fiscal_period_label="fiscal year ended " + iso,
                period_end=iso, period_type="FISCAL_YEAR",
                source_quote=quote[:1600])

        # ---- PATTERN D2: "... totaled $A and $B ... for the years ended X and Y, respectively"
        for mr in RESPECTIVELY_RE.finditer(t):
            lead = t[max(0, mr.start() - 420):mr.start()]
            mt = TAIL_VALS_RE.search(lead)
            if not mt:
                continue
            near = [a for a, pat in aliases if pat.search(lead)]
            if not near:
                continue
            if not re.search(r"(?i)management fee|net revenue|gross revenue", lead):
                continue
            vals = VAL_RE.findall(mt.group("vals"))
            my = YEARS_ENDED_RE.search(lead)
            if not my:
                continue
            ys = re.findall(r"\d{4}", my.group("ys"))
            if len(vals) != len(ys):
                continue
            ftype = ("MANAGEMENT_FEE_REVENUE"
                     if re.search(r"(?i)management fee", lead) else "FACILITY_NET_REVENUES")
            for (amt, sc), y in zip(vals, ys):
                add(extraction_pattern="D2_RESPECTIVELY", alias=near[0],
                    facility_name_as_filed=near[0],
                    figure_type=ftype,
                    figure_type_note=("management fee revenue earned by the filer from the "
                                      "named property" if ftype == "MANAGEMENT_FEE_REVENUE"
                                      else "property revenues as stated"),
                    value_verbatim="$" + amt + " " + (sc or ""),
                    value_scale_applied=(sc or "").lower(),
                    value_usd=to_usd(amt, sc or ""),
                    fiscal_period_label="year ended %s %s, %s" % (my.group("mon"), my.group("day"), y),
                    period_end=parse_date("%s %s, %s" % (my.group("mon"), my.group("day"), y)),
                    period_type="FISCAL_YEAR",
                    source_quote=re.sub(r"\s+", " ", lead + " respectively").strip())

        # ---- PATTERN E: fee formula (contract TERM, no money)
        for m in PAT_E.finditer(t):
            ctx = t[max(0, m.start() - 700):m.end() + 200]
            near = [a for a, pat in aliases if pat.search(ctx)]
            if not near:
                continue
            add(extraction_pattern="E_FEE_FORMULA", alias=near[0],
                facility_name_as_filed=near[0],
                figure_type="CONTRACT_TERM_FEE_PERCENTAGE",
                figure_type_note="stated management-fee percentage and its base",
                value_verbatim=m.group("pct") + "% of " + re.sub(r"\s+", " ", m.group("base")),
                derivation_stated_percentage=m.group("pct"),
                derivation_percentage_base=re.sub(r"\s+", " ", m.group("base")).upper().replace(" ", "_"),
                fiscal_period_label="", period_end="", period_type="",
                source_quote=re.sub(r"\s+", " ", ctx).strip())

    # DEFECT CLASS 7 (a positional primary key). The first version numbered
    # candidates 1..N in sort order. `review/sec_gaming_1080_adjudication.csv`
    # keys on candidate_id, so a re-mine that found one extra hit would have
    # shifted every id below it and silently re-pointed every hand ruling at a
    # different figure. The id is now a digest of the candidate's own content:
    # stable across re-mines, and a candidate that changes gets a NEW id rather
    # than inheriting someone else's ruling.
    for r in rows:
        seed = "|".join(str(r.get(k, "")) for k in (
            "accession", "extraction_pattern", "alias", "figure_type",
            "value_verbatim", "fiscal_period_label", "period_end"))
        r["candidate_id"] = "SECGF-" + hashlib.md5(seed.encode("utf-8")).hexdigest()[:10]
    if len({r["candidate_id"] for r in rows}) != len(rows):
        raise SystemExit("candidate_id digest collided - widen the seed tuple")
    rows.sort(key=lambda z: (z["filing_date"], z["accession"], z["extraction_pattern"],
                             str(z.get("alias", "")), z["candidate_id"]))

    cols = ["candidate_id", "extraction_pattern", "alias", "facility_name_as_filed",
            "facility_id", "tribe_name", "state", "on_indian_lands",
            "figure_type", "figure_type_note", "value_usd", "value_verbatim",
            "value_scale_applied", "fiscal_period_label", "period_type", "period_end",
            "derivation_stated_percentage", "derivation_percentage_base",
            "filer_name", "filer_cik", "filer_role", "form", "filing_date",
            "accession", "source_url", "local_file", "source_md5", "source_quote"]
    CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    with CANDIDATES.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    out(f"documents in manifest present on disk : {n_docs}")
    out(f"documents from a curated gaming filer  : {n_read}")
    out(f"candidates written                     : {len(rows)} -> {CANDIDATES}")
    from collections import Counter
    out("segment-table refusals (a parser that reads nothing looks like an empty corpus):")
    for k, v in sorted(refusals.items()):
        out(f"    {k:36s} {v}")
    for k, v in Counter(r["extraction_pattern"] for r in rows).most_common():
        out(f"    {k:36s} {v}")
    for k, v in Counter(r["alias"] for r in rows).most_common(40):
        out(f"    alias {k:40s} {v}")


def label_to_type(label: str) -> str:
    l = label.lower()
    if "gross gaming" in l:
        return "FACILITY_GROSS_GAMING_REVENUE"
    if "net gaming" in l or "net win" in l:
        return "FACILITY_NET_GAMING_REVENUE"
    if "gross" in l:
        return "FACILITY_GROSS_REVENUES"
    return "FACILITY_NET_REVENUES"


def period_type_from(s: str) -> str:
    l = s.lower()
    if "three months" in l or "quarter" in l:
        return "QUARTER"
    if "six months" in l:
        return "SIX_MONTHS"
    if "nine months" in l:
        return "NINE_MONTHS"
    return "FISCAL_YEAR"


def prior_period(iso: str, ptype: str) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    if not m or ptype != "FISCAL_YEAR":
        return ""
    return f"{int(m.group(1)) - 1:04d}-{m.group(2)}-{m.group(3)}"


PERIOD_CUES = [
    (re.compile(r"for\s+the\s+" + PERIOD_WORDS + r"\s+ended\s+"
                r"(?P<d>[A-Z][a-z]+\s+\d{1,2},\s*\d{4})", re.I), "date"),
    (re.compile(r"for\s+(?:the\s+)?(?:fiscal\s+year|Fiscal|fiscal)\s*(?P<y>(?:19|20)\d{2})",
                re.I), "year"),
    (re.compile(r"years?\s+ended\s+(?P<d>[A-Z][a-z]+\s+\d{1,2},\s*\d{4})", re.I), "date"),
]


def period_from_context(t: str, start: int, end: int):
    """Nearest period cue in a +/- 300 char window. Returns (label, iso, type)."""
    lo = max(0, start - 300)
    win_before = t[lo:start]
    win_after = t[end:end + 300]
    for pat, kind in PERIOD_CUES:
        ms = list(pat.finditer(win_before))
        m = ms[-1] if ms else pat.search(win_after)
        if not m:
            continue
        if kind == "date":
            d = parse_date(m.group("d"))
            return (m.group(0).strip(), d, period_type_from(m.group(0)))
        y = m.group("y")
        return (m.group(0).strip(), f"{y}-12-31", "FISCAL_YEAR_UNANCHORED")
    return ("", "", "")


# ---------------------------------------------------------------- build --

def load_facilities():
    fac = {}
    for r in csv.DictReader((CLEAN / "gaming_facilities.csv").open(encoding="utf-8")):
        fac[r["facility_id"]] = r
    return fac


def build():
    if not ADJUDICATION.exists():
        raise SystemExit(
            f"missing {ADJUDICATION}. `mine` first, then adjudicate every candidate: "
            f"an ACCEPT with no facility_id is refused.")
    cands = {r["candidate_id"]: r for r in csv.DictReader(CANDIDATES.open(encoding="utf-8"))}
    fac = load_facilities()
    figs, terms = [], []
    n_reject = 0
    for a in csv.DictReader(ADJUDICATION.open(encoding="utf-8")):
        cid = a["candidate_id"]
        if a["adjudication"] != "ACCEPT":
            n_reject += 1
            continue
        c = cands.get(cid)
        if c is None:
            if not cid.startswith("MANUAL-"):
                raise SystemExit(f"adjudication names {cid}, which is not in {CANDIDATES}")
            # A MANUAL- row is a figure a human read out of a cached filing that
            # no pattern caught. It is not an exemption from evidence: verify
            # still demands an accession, an EDGAR archive URL and a verbatim
            # quote, and `manual_read_basis` must say which cached file was read.
            miss = [k for k in ("form", "filing_date", "accession", "source_url",
                                "source_quote_final", "value_usd_final",
                                "figure_type_final", "filer_name", "filer_cik",
                                "filer_role", "manual_read_basis")
                    if not a.get(k, "").strip()]
            if miss:
                raise SystemExit(f"{cid} is MANUAL- and is missing {miss}")
            c = {
                "form": a["form"], "filing_date": a["filing_date"],
                "accession": a["accession"], "source_url": a["source_url"],
                "source_quote": a["source_quote_final"],
                "extraction_pattern": "MANUAL_READ",
                "facility_name_as_filed": a.get("facility_name_as_filed", ""),
                "filer_name": a["filer_name"], "filer_cik": a["filer_cik"],
                "filer_role": a["filer_role"],
                "figure_type": a["figure_type_final"],
                "figure_type_note": a.get("figure_type_note_final", ""),
                "value_usd": a["value_usd_final"],
                "value_verbatim": a.get("value_verbatim", ""),
                "value_scale_applied": "",
                "fiscal_period_label": a.get("fiscal_period_label_final", ""),
                "period_type": a.get("period_type_final", ""),
                "period_end": a.get("period_end_final", ""),
                "local_file": a.get("manual_read_basis", ""), "source_md5": "",
                "derivation_stated_percentage": a.get("derivation_stated_percentage", ""),
                "derivation_percentage_base": a.get("derivation_percentage_base", ""),
            }
        fid = a.get("facility_id", "").strip()
        f = fac.get(fid, {})
        common = dict(
            facility_id=fid,
            facility_name_cedar=f.get("facility_name", ""),
            facility_name_as_filed=a.get("facility_name_as_filed") or c["facility_name_as_filed"],
            tribe_name=a.get("tribe_name") or f.get("tribe", ""),
            tribe_id=f.get("tribe_id", ""),
            cedar_uid=f.get("cedar_uid", ""),
            state=a.get("state") or f.get("state", ""),
            form=c["form"], filing_date=c["filing_date"], accession=c["accession"],
            source_url=c["source_url"], source_quote=a.get("source_quote_final") or c["source_quote"],
            extraction_pattern=c["extraction_pattern"],
            adjudication=a["adjudication"], adjudication_note=a.get("adjudication_note", ""),
            record_scope="PUBLISHABLE",
            record_scope_basis=(
                "Third-party SEC filing. PUBLICATION_POLICY.md <!-- BEGIN TERMS-SCOPE -->: "
                "a terms restriction attaches to the source that stated it and does not "
                "bind a third party's mandatory securities disclosure."),
            built_by=SCRIPT, built_date=TODAY,
        )
        if c["extraction_pattern"] == "E_FEE_FORMULA":
            terms.append(dict(
                common,
                term_id="SECMT-%04d" % (len(terms) + 1),
                assertion_class=TERMS_ASSERTION_CLASS,
                assertion_class_note=TERMS_CLASS_NOTE,
                not_summable_with="nothing - this row carries no money",
                manager_name=c["filer_name"], manager_cik=c["filer_cik"],
                manager_role=c["filer_role"],
                fee_formula_verbatim=a.get("fee_formula_verbatim") or c["value_verbatim"],
                fee_percentage=a.get("fee_percentage") or c["derivation_stated_percentage"],
                fee_percentage_base=a.get("fee_percentage_base") or c["derivation_percentage_base"],
                fee_is_tiered=a.get("fee_is_tiered", ""),
                contract_term_years=a.get("contract_term_years", ""),
                contract_expiry_as_stated=a.get("contract_expiry_as_stated", ""),
            ))
            continue
        val = a.get("value_usd_final") or c["value_usd"]
        figs.append(dict(
            common,
            disclosure_id="SECFD-%04d" % (len(figs) + 1),
            assertion_class=ASSERTION_CLASS,
            assertion_class_note=ASSERTION_CLASS_NOTE,
            not_summable_with=NOT_SUMMABLE,
            figure_type=a.get("figure_type_final") or c["figure_type"],
            figure_type_note=a.get("figure_type_note_final") or c["figure_type_note"],
            value_usd=val,
            value_verbatim=c["value_verbatim"],
            value_precision=a.get("value_precision", ""),
            value_scale_applied=c["value_scale_applied"],
            fiscal_period_label=a.get("fiscal_period_label_final") or c["fiscal_period_label"],
            period_type=a.get("period_type_final") or c["period_type"],
            period_end=a.get("period_end_final") or c["period_end"],
            fiscal_year=(a.get("fiscal_year") or (c["period_end"][:4] if c["period_end"] else "")),
            facility_is_on_indian_lands=a.get("facility_is_on_indian_lands", ""),
            filer_name=c["filer_name"], filer_cik=c["filer_cik"], filer_role=c["filer_role"],
            manager_name=a.get("manager_name") or (
                c["filer_name"] if c["filer_role"] in ("MANAGER", "DEVELOPER_MANAGER") else ""),
            local_file=c["local_file"], source_md5=c["source_md5"],
            derived_from_fee=a.get("derived_from_fee", "N"),
            derivation_input_fee_usd=a.get("derivation_input_fee_usd", ""),
            derivation_stated_percentage=a.get("derivation_stated_percentage", ""),
            derivation_percentage_base=a.get("derivation_percentage_base", ""),
            derivation_percentage_source_accession=a.get(
                "derivation_percentage_source_accession", ""),
            derivation_arithmetic=a.get("derivation_arithmetic", ""),
            derivation_caveat=a.get("derivation_caveat", ""),
        ))
    annotate_restatements(figs)
    write(OUT_FIG, carry_live_columns(OUT_FIG, FIG_COLS), figs)
    write(OUT_TERMS, carry_live_columns(OUT_TERMS, TERM_COLS), terms)
    out(f"accepted figures : {len(figs)} -> {OUT_FIG}")
    out(f"accepted terms   : {len(terms)} -> {OUT_TERMS}")
    out(f"rejected/held    : {n_reject}")


def annotate_restatements(figs):
    """A 10-K restates the two prior fiscal years. That is not new evidence.

    Mohegan's FY2017 Mohegan Sun net revenues of $1,079,920 thousand appear in
    the FY2017, FY2018 AND FY2019 10-Ks. All three rows are kept - each is a
    real disclosure in a real filing - but only the FIRST one is safe to total,
    and the flag says which. Without it, summing this table by facility-year
    triples that property.

    Also MEASURES whether the restatements agree with the original, because a
    restatement that disagrees is a finding and a restatement that agrees is the
    only genuine internal corroboration this table has.
    """
    from collections import defaultdict
    groups = defaultdict(list)
    for r in figs:
        key = (r["facility_id"] or r["facility_name_as_filed"], r["period_end"],
               r["period_type"], r["figure_type"], r["filer_cik"])
        groups[key].append(r)
    for key, rows in groups.items():
        rows.sort(key=lambda z: (z["filing_date"], z["accession"]))
        vals = set()
        for r in rows:
            try:
                vals.add(round(float(r["value_usd"]), 2))
            except (TypeError, ValueError):
                vals.add(None)
        agree = "Y" if len(vals) == 1 else "N"
        others = [r["accession"] for r in rows[1:]]
        for i, r in enumerate(rows):
            r["is_first_filing_of_this_fact"] = "Y" if i == 0 else "N"
            r["n_filings_stating_this_fact"] = str(len(rows))
            r["restated_in_accessions"] = "|".join(others) if i == 0 else rows[0]["accession"]
            r["restatements_agree"] = agree if len(rows) > 1 else ""


def carry_live_columns(path, canonical):
    """Canonical order first, then any column the LIVE file already carries.

    Added 2026-09-02 by code/1129_place_ids.py, which promoted
    `cedar_place_id` onto this table in place. A FIXED header on a wholesale
    writer silently deletes an in-place enricher's work - class 6, and the
    exact defect `code/845_regenerate_guard.py` names. A rebuilder cannot
    REPOPULATE an enricher's column, so it writes it BLANK and the enricher
    refills it: `py -3 code/1129_place_ids.py migrate --apply`. Blank keeps
    the schema and every consumer's join; dropped breaks both.

    A retired column stays retired, because it is not on disk."""
    import csv as _csv
    from pathlib import Path as _P
    p = _P(path)
    live = []
    if p.exists():
        with p.open(encoding="utf-8-sig", errors="replace", newline="") as _f:
            live = next(_csv.reader(_f), [])
    return list(canonical) + [c for c in live if c and c not in canonical]


def write(path: Path, cols, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    os.replace(tmp, path)


# --------------------------------------------------------------- verify --

MONEY_TABLES_FORBIDDEN = (
    "gaming_revenue_bounds.csv", "nigc_regional_ggr.csv", "nigc_revenue_bands.csv",
    "gaming_capacity_official.csv", "state_gaming_observations.csv",
    "gaming_property_self_published_assertions.csv",
    "gaming_property_self_published_claims.csv")

# THE MANDATE SAID "the fee frequently implies the revenue". It implies
# something, and that something is NOT revenue.
#
# IGRA defines "net revenues" at 25 U.S.C. 2703(9) as gross gaming revenues
# LESS amounts paid out as prizes and LESS total gaming-related operating
# expenses, excluding management fees. That is much closer to operating profit
# than to revenue. And the contracts in this corpus do not even use one base:
# Lakes' Red Hawk fee is "30% of net revenue (as defined by the development and
# management agreement)"; Red Rock's Graton fee is "24% of Graton Resort's net
# income (as defined in the management agreement)" in years 1-4 and 27% in
# years 5-7. Dividing a fee by its percentage recovers the CONTRACT'S OWN BASE
# and nothing else - so the derived types name that base and never say
# "revenue" without saying "as defined".
VALID_FIGURE_TYPES = {
    "FACILITY_NET_REVENUES", "FACILITY_GROSS_REVENUES",
    "FACILITY_NET_GAMING_REVENUE", "FACILITY_GROSS_GAMING_REVENUE",
    "MANAGEMENT_FEE_REVENUE", "RELINQUISHMENT_PAYMENT",
    "FACILITY_INCOME_FROM_OPERATIONS", "FACILITY_ADJUSTED_EBITDA",
    "DERIVED_FACILITY_NET_REVENUES_AS_DEFINED",
    "DERIVED_FACILITY_NET_INCOME_AS_DEFINED",
    "DERIVED_FACILITY_GROSS_REVENUES_AS_DEFINED",
}
DERIVED_FIGURE_TYPES = {t for t in VALID_FIGURE_TYPES if t.startswith("DERIVED_")}


def verify():
    fails = []

    def bad(inv, msg):
        fails.append(f"{inv}: {msg}")

    if not OUT_FIG.exists():
        raise SystemExit("V0_TABLE_PRESENT: sec_gaming_financial_disclosures.csv absent - run build")
    figs = list(csv.DictReader(OUT_FIG.open(encoding="utf-8")))
    terms = list(csv.DictReader(OUT_TERMS.open(encoding="utf-8"))) if OUT_TERMS.exists() else []
    facs = load_facilities()

    seen = set()
    for r in figs:
        i = r["disclosure_id"]
        if i in seen:
            bad("V1_UNIQUE_KEY", f"duplicate disclosure_id {i}")
        seen.add(i)

        if r["assertion_class"] != ASSERTION_CLASS:
            bad("V2_ASSERTION_CLASS", f"{i} carries {r['assertion_class']!r}")

        for t in MONEY_TABLES_FORBIDDEN:
            if t not in r["not_summable_with"]:
                bad("V3_FENCE_DECLARED", f"{i} does not name {t} in not_summable_with")
                break

        if r["figure_type"] not in VALID_FIGURE_TYPES:
            bad("V4_FIGURE_TYPE_VOCAB", f"{i} figure_type {r['figure_type']!r} not in the vocabulary")

        if not r["source_quote"].strip():
            bad("V5_QUOTE_PRESENT", f"{i} has no verbatim quote")

        if not r["accession"].strip() or not r["source_url"].startswith("https://www.sec.gov/"):
            bad("V6_ACCESSION_AND_URL", f"{i} accession/url missing or not an EDGAR archive URL")

        try:
            v = float(r["value_usd"])
        except (TypeError, ValueError):
            v = None
        if v is None or v <= 0:
            bad("V7_VALUE_NUMERIC", f"{i} value_usd {r['value_usd']!r} is not a positive number")

        if r["facility_id"] and r["facility_id"] not in facs:
            bad("V8_FACILITY_KEY", f"{i} facility_id {r['facility_id']} is not in gaming_facilities.csv")

        if r["derived_from_fee"] == "Y":
            if not r["derivation_stated_percentage"]:
                bad("V9_DERIVATION_NEEDS_STATED_PCT",
                    f"{i} is derived but no stated percentage is recorded")
            if not r["derivation_arithmetic"]:
                bad("V9_DERIVATION_NEEDS_STATED_PCT", f"{i} is derived but shows no arithmetic")
            if r["figure_type"] not in DERIVED_FIGURE_TYPES:
                bad("V10_DERIVED_LABELLED",
                    f"{i} derived_from_fee=Y but figure_type is {r['figure_type']!r} - a derived "
                    f"figure must not wear a reported figure's type")
        elif r["derivation_arithmetic"]:
            bad("V10_DERIVED_LABELLED", f"{i} shows arithmetic but is not flagged derived_from_fee")

        if r["period_end"] and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["period_end"]):
            bad("V11_PERIOD_ISO", f"{i} period_end {r['period_end']!r} is not ISO")

    for r in terms:
        if r["assertion_class"] != TERMS_ASSERTION_CLASS:
            bad("V12_TERMS_CLASS", f"{r['term_id']} carries {r['assertion_class']!r}")
        if not r["source_quote"].strip():
            bad("V5_QUOTE_PRESENT", f"{r['term_id']} has no verbatim quote")

    # V14 - the safe-to-total subset must be unique on its own key.
    firsts = {}
    for r in figs:
        if r["is_first_filing_of_this_fact"] != "Y":
            continue
        k = (r["facility_id"] or r["facility_name_as_filed"], r["period_end"],
             r["period_type"], r["figure_type"], r["filer_cik"])
        if k in firsts:
            bad("V14_FIRST_FILING_UNIQUE",
                f"{r['disclosure_id']} and {firsts[k]} are both flagged "
                f"is_first_filing_of_this_fact=Y for {k}")
        firsts[k] = r["disclosure_id"]
    if figs and not any(r["is_first_filing_of_this_fact"] for r in figs):
        bad("V14_FIRST_FILING_UNIQUE", "is_first_filing_of_this_fact is unpopulated")

    # V15 - a restatement that disagrees with the original is a finding, not noise.
    disagree = sorted({r["disclosure_id"] for r in figs if r["restatements_agree"] == "N"})
    out(f"V15_RESTATEMENTS: {sum(1 for r in figs if r['n_filings_stating_this_fact'] not in ('', '1'))} "
        f"row(s) are one fact stated in more than one filing; "
        f"{len(disagree)} disagree with the first filing of that fact.")
    for i in disagree:
        bad("V15_RESTATEMENT_DISAGREES",
            f"{i} restates a fact with a different value and carries no adjudication note")

    # V13 - the double-count guard, measured rather than asserted.
    bounds = CLEAN / "gaming_revenue_bounds.csv"
    if bounds.exists():
        bf = set()
        for r in csv.DictReader(bounds.open(encoding="utf-8")):
            if r.get("measurement_status") == "REGIONAL_GGR_CEILING" and r.get("facility_id"):
                bf.add(r["facility_id"])
        overlap = sorted({r["facility_id"] for r in figs if r["facility_id"] in bf})
        out(f"V13_OVERLAP_MEASURED: {len(overlap)} facility_id(s) carry BOTH an SEC figure here "
            f"and a REGIONAL_GGR_CEILING bound. That is expected and is exactly why "
            f"not_summable_with names gaming_revenue_bounds.csv.")
        if overlap and any(t not in figs[0]["not_summable_with"] for t in ("gaming_revenue_bounds.csv",)):
            bad("V13_OVERLAP_DECLARED", "overlap exists and the fence is not declared")

    out("")
    out(f"rows: {len(figs)} figures, {len(terms)} terms")
    if fails:
        out(f"FAIL - {len(fails)} breach(es):")
        for f in fails[:40]:
            out("  " + f)
        raise SystemExit(1)
    out("verify OK - every invariant held")
    return 0


# --------------------------------------------------------------- codebook --
#
# `62_no_regression_check` ratchets `tables_undocumented_in_codebook`, and that
# metric IS the shipping gate: `25_build_publication_layer` resolves curated
# overrides first and then everything the codebook documents. A new table with
# no codebook block is a table that cannot ship, which is exactly how the gaming
# collection once shipped 912 of 104,412 rows. So 1080 writes its own fragments
# rather than leaving two new undocumented tables behind it.

CODEBOOK_FIG = {
    "disclosure_id": "Primary key. Stable within a build; re-derived by `1080 build` in accepted order.",
    "assertion_class": "Always SEC_FILED_FINANCIAL_DISCLOSURE. A THIRD class, outside cedar_domain.MeasurementType and outside the SELF_PUBLISHED_* family: stronger than a casino's marketing page (filed under a federal disclosure obligation), different in kind from an NIGC figure (the filer's own accounting, not a regulator's measurement).",
    "assertion_class_note": "Prose statement of what that class means, carried on every row so it travels with the data.",
    "not_summable_with": "The tables this row may NEVER be added to. Naming gaming_revenue_bounds.csv is the point: an SEC property figure summed against an NIGC REGIONAL_GGR_CEILING double-counts, because the property sits inside the region.",
    "figure_type": "WHAT THE FIGURE IS. Six values, and they are four different quantities about one property. NEVER SUM ACROSS THIS COLUMN. FACILITY_NET_REVENUES / FACILITY_NET_GAMING_REVENUE / MANAGEMENT_FEE_REVENUE / RELINQUISHMENT_PAYMENT / DERIVED_FACILITY_GROSS_REVENUES_AS_DEFINED / DERIVED_FACILITY_NET_INCOME_AS_DEFINED.",
    "figure_type_note": "The filer's own label for the figure, or a sentence saying what a derived figure is.",
    "value_usd": "The figure in US dollars. Scale already applied where the filing stated one (value_scale_applied records it).",
    "value_verbatim": "The figure as the filing writes it, before any scaling.",
    "value_precision": "How exact the source is: EXACT_TO_THE_DOLLAR_AS_FILED, EXACT_AS_FILED_IN_THOUSANDS, ROUNDED_TO_TENTHS_OF_A_MILLION_AS_FILED, or a DERIVED_* value.",
    "value_scale_applied": "thousands / millions / blank - the multiplier taken from the table header or the sentence.",
    "fiscal_period_label": "The period as the filing names it. Where the filer's own label is ambiguous (Waterford's 'Relinquishment Fees earned 2000') the label is kept and not re-dated.",
    "period_type": "FISCAL_YEAR (63) / NINE_MONTHS (2) / QUARTER (2). A nine-month figure is year-to-date and must never be added to a fiscal-year row for the same property.",
    "period_end": "ISO date the period ends. Seneca Gaming's fiscal year ends September 30 and Lakes' is a 52/53-week year - the dates are the filers', not calendar defaults.",
    "fiscal_year": "Year component of period_end, for convenience only.",
    "facility_id": "Joins data/clean/gaming_facilities.csv. NOTE: that file carries the same property twice for many properties with duplicate_of_facility_id blank on both; this table keys to the CCP- row and lists the near-duplicates in code/_1080_facility_aliases.py NEAR_DUPLICATE_IDS.",
    "facility_name_cedar": "The property's name in gaming_facilities.csv.",
    "facility_name_as_filed": "The property's name as the REGISTRANT writes it, kept because it is the string the evidence actually contains.",
    "tribe_name": "The tribe as Cedar writes it, from the curated alias map rather than from the filing.",
    "tribe_id": "Spine id, joined from gaming_facilities.csv.",
    "cedar_uid": "Cedar identity id, joined from gaming_facilities.csv.",
    "state": "Two-letter state of the property.",
    "facility_is_on_indian_lands": "Y or N. N on the twelve Mohegan Sun Pocono rows - a Pennsylvania racino the Mohegan Tribal Gaming Authority owns, which is tribal-owned but NOT Indian-lands gaming. Filter on this before any Indian Country total.",
    "filer_name": "The SEC registrant that filed the document.",
    "filer_cik": "Its CIK, zero-padded to ten.",
    "filer_role": "OPERATOR_TRIBAL_INSTRUMENTALITY / MANAGER / DEVELOPER_MANAGER / RELINQUISHMENT_INTEREST_HOLDER. A tribal gaming authority reporting its own property is a different evidentiary position from a manager reporting its fee.",
    "manager_name": "Who managed the property, where that differs from the filer.",
    "form": "SEC form type. 10-K carries audited statements; a 10-Q does not.",
    "filing_date": "Date the document was filed with the SEC.",
    "accession": "EDGAR accession number - the citation.",
    "source_url": "Direct link to the document on sec.gov/Archives. Verified by V6 to start https://www.sec.gov/.",
    "local_file": "Path to the cached copy under data/raw/external/sec_edgar_1030/, or the file a MANUAL_READ row was read from.",
    "source_md5": "Checksum recorded by 1030 at fetch time. Blank on MANUAL_READ rows.",
    "source_quote": "VERBATIM text containing the figure. V5 refuses a blank. For a segment-table row it is the period header, the year header, the section header and the property row - the four lines that decided the reading.",
    "derived_from_fee": "Y where value_usd was computed by dividing a stated fee by a stated percentage. 10 rows.",
    "derivation_input_fee_usd": "The fee the derivation started from.",
    "derivation_stated_percentage": "The rate, AS STATED BY THE REGISTRANT. Never inferred.",
    "derivation_percentage_base": "What the rate is a percentage OF - and it is usually not revenue. IGRA net revenues (25 U.S.C. 2703(9)) is nearer operating profit.",
    "derivation_percentage_source_accession": "The filing the RATE came from, which is not always the filing the dollars came from.",
    "derivation_arithmetic": "The division, written out, so a reader can repeat it.",
    "derivation_caveat": "What the derived figure is and is not. Required on every derived row.",
    "is_first_filing_of_this_fact": "Y on the earliest filing to state a given (property, period, figure type). TOTAL ONLY THE Y SUBSET - 49 of 67. A 10-K restates its two prior fiscal years, so summing the whole table triples Mohegan Sun.",
    "n_filings_stating_this_fact": "How many filings state it.",
    "restated_in_accessions": "On a first-filing row, the later accessions that restate it; on a restatement, the accession that stated it first.",
    "restatements_agree": "Y where every filing states the same value, N where they differ. 32 restatements, 0 disagreements - the only genuine internal corroboration this table has.",
    "extraction_pattern": "Which miner pattern produced the candidate, or MANUAL_READ.",
    "adjudication": "Always ACCEPT here; the 69 refusals and their reasons are in review/sec_gaming_1080_adjudication.csv.",
    "adjudication_note": "Why this row was accepted, and any correction applied by hand to the mined period or value.",
    "record_scope": "PUBLISHABLE on every row.",
    "record_scope_basis": "The ruling that makes it publishable: a terms restriction attaches to the source that stated it, and an SEC filing is the registrant's publication.",
    "built_by": "code/1080_sec_gaming_facility_revenue.py",
    "built_date": "Build date.",
}

CODEBOOK_TERMS = {
    "term_id": "Primary key.",
    "assertion_class": "Always SEC_FILED_CONTRACT_TERM.",
    "assertion_class_note": "What that class means.",
    "not_summable_with": "Constant text saying this table carries no money.",
    "manager_name": "The registrant holding the contract.",
    "manager_cik": "Its CIK.",
    "manager_role": "MANAGER / DEVELOPER_MANAGER / RELINQUISHMENT_INTEREST_HOLDER.",
    "tribe_name": "The tribe, as Cedar writes it.",
    "tribe_id": "Spine id from gaming_facilities.csv.",
    "facility_id": "Joins gaming_facilities.csv.",
    "facility_name_cedar": "Cedar's name for the property.",
    "facility_name_as_filed": "The registrant's name for it.",
    "state": "Two-letter state.",
    "fee_formula_verbatim": "The formula in the registrant's own words. Read it before using fee_percentage - four of the seven are tiered or thresholded.",
    "fee_percentage": "The headline rate. A RATE, NOT A DOLLAR. Nothing in this table may be totalled.",
    "fee_percentage_base": "What the rate applies to, named precisely: NET_INCOME, NET_REVENUES, NET_REVENUE_AS_DEFINED_IN_THE_MANAGEMENT_AGREEMENT, NET_INCOME_FROM_OPERATIONS_IN_EXCESS_OF_4M, REVENUES_AS_DEFINED_IN_THE_RELINQUISHMENT_AGREEMENT. These are not interchangeable and only two of them support inverting a fee into a revenue.",
    "fee_is_tiered": "Y where the rate changes with contract year or with a threshold; UNSTATED_IN_THIS_FILING where the filing gives one rate and other filings give tiers.",
    "contract_term_years": "Length as stated, where stated.",
    "contract_expiry_as_stated": "Expiry in the registrant's words.",
    "form": "SEC form type.",
    "filing_date": "Filing date.",
    "accession": "EDGAR accession - the citation.",
    "source_url": "Link to the document on sec.gov/Archives.",
    "source_quote": "Verbatim passage containing the percentage.",
    "extraction_pattern": "Always E_FEE_FORMULA.",
    "adjudication": "ACCEPT.",
    "adjudication_note": "Why, and what the formula's traps are.",
    "record_scope": "PUBLISHABLE.",
    "record_scope_basis": "Same terms-scope ruling as the figures table.",
    "built_by": "code/1080_sec_gaming_facility_revenue.py",
    "built_date": "Build date.",
}

# The codebook namespace has its own collision problem - `cedar_register_codebook.py`
# records `07f` being claimed twice by two different scripts, "the script-number
# collision problem reproduced inside the codebook namespace". The first attempt
# here took `07p` and `07q`, both of which are ALREADY IN THE MASTER
# (`07p_revenue_bounds`, `07q_gaming_game_finder_observations`) - the fragments
# were written, spotted and deleted before any build folded them in. Keys below
# were checked against BOTH data/clean/codebook/*.csv and the dataset column of
# codebook_master.csv on 2026-09-02. The gaming series runs to `07zp`.
CODEBOOK_DATASETS = [
    ("07zq_sec_gaming_financial_disclosures", OUT_FIG, FIG_COLS, CODEBOOK_FIG),
    ("07zr_sec_gaming_management_contract_terms", OUT_TERMS, TERM_COLS, CODEBOOK_TERMS),
]


def codebook():
    import importlib.util
    spec = importlib.util.spec_from_file_location("cedar_codebook", CODE / "cedar_codebook.py")
    cb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cb)
    for name, path, cols, descs in CODEBOOK_DATASETS:
        rows = list(csv.DictReader(path.open(encoding="utf-8")))
        n = len(rows)
        missing = [c for c in cols if c not in descs]
        if missing:
            raise SystemExit(f"{name}: no codebook description for {missing}. "
                             f"An undescribed column is how a table ships a mystery.")
        frag = []
        for c in cols:
            filled = sum(1 for r in rows if str(r.get(c, "")).strip() != "")
            frag.append(dict(
                dataset=name, variable=c,
                type=("number" if c in ("value_usd", "derivation_input_fee_usd",
                                        "n_filings_stating_this_fact", "fee_percentage",
                                        "derivation_stated_percentage", "contract_term_years",
                                        "fiscal_year") else "text"),
                units=("usd" if c.endswith("_usd") else
                       "date" if c.endswith(("_date", "period_end")) else
                       "percent" if "percentage" in c or c == "fee_percentage" else "text"),
                pct_filled=round(100.0 * filled / n, 1) if n else 0.0,
                n_rows=n, published=1, access_tier="public",
                description=descs[c],
                generated=TODAY))
        # Guard, because a codebook key collision is silent: two datasets under
        # one key and the master keeps whichever fragment sorts last.
        frag_path = CLEAN / "codebook" / f"{name}.csv"
        master = CLEAN / "codebook_master.csv"
        if frag_path.exists():
            existing = {r["variable"] for r in csv.DictReader(frag_path.open(encoding="utf-8"))}
            if existing and not existing <= set(cols):
                raise SystemExit(
                    f"codebook key {name} already documents a DIFFERENT table - it has "
                    f"{sorted(existing - set(cols))[:4]}, which this table does not. Pick another "
                    f"key. Two datasets under one key is the 07f incident (see "
                    f"code/cedar_register_codebook.py).")
        if master.exists():
            taken = {r.get("dataset") for r in csv.DictReader(master.open(encoding="utf-8"))}
            if name in taken:
                raise SystemExit(f"codebook key {name} is already in codebook_master.csv")
        cb.write_fragment(name, frag)
        out(f"codebook fragment {name}: {len(frag)} variables over {n} rows")
    out("run `py -3 code/cedar_codebook.py build` (integrator) to fold fragments into the master")


def selftest():
    """Prove verify FIRES. Inject one violation of each of three named invariants."""
    import shutil
    import subprocess
    if not OUT_FIG.exists():
        raise SystemExit("selftest needs a built table - run build first")
    bak = OUT_FIG.with_suffix(".csv.selftest_bak")
    shutil.copy2(OUT_FIG, bak)
    ok = True
    try:
        rows = list(csv.DictReader(OUT_FIG.open(encoding="utf-8")))
        if not rows:
            raise SystemExit("selftest needs at least one row")
        cases = [
            ("V3_FENCE_DECLARED", "not_summable_with", "nothing"),
            ("V5_QUOTE_PRESENT", "source_quote", ""),
            ("V10_DERIVED_LABELLED", "derivation_arithmetic", "1 / 0.30 = 3"),
            ("V4_FIGURE_TYPE_VOCAB", "figure_type", "REVENUE"),
        ]
        for inv, col, val in cases:
            mut = [dict(r) for r in rows]
            mut[0][col] = val
            write(OUT_FIG, carry_live_columns(OUT_FIG, FIG_COLS), mut)
            p = subprocess.run([sys.executable, str(CEDAR / SCRIPT), "verify"],
                               capture_output=True, text=True)
            fired = p.returncode == 1 and inv in p.stdout
            out(f"  inject {inv:32s} -> exit {p.returncode}, invariant named: {fired}")
            if not fired:
                ok = False
        shutil.copy2(bak, OUT_FIG)
        p = subprocess.run([sys.executable, str(CEDAR / SCRIPT), "verify"],
                           capture_output=True, text=True)
        out(f"  restored                                 -> exit {p.returncode}")
        if p.returncode != 0:
            ok = False
    finally:
        shutil.copy2(bak, OUT_FIG)
        bak.unlink()
    if not ok:
        out("SELFTEST FAILED - a check that has never failed on purpose is not known to work")
        raise SystemExit(1)
    out("selftest OK - every injected violation exited 1 and named its own invariant")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    if stage == "mine":
        mine()
    elif stage == "build":
        build()
    elif stage == "verify":
        verify()
    elif stage == "codebook":
        codebook()
    elif stage == "selftest":
        selftest()
    else:
        raise SystemExit(__doc__)
