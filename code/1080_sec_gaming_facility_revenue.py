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
  code/1080_facility_aliases.py              the curated alias -> facility map
  review/sec_gaming_1080_adjudication.csv    hand rulings on mined candidates

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

DERIVATION
----------
Revenue is derived from a fee ONLY where the same filing states the percentage
and its base. `derived_from_fee = Y` rows show the arithmetic in
`derivation_arithmetic` and carry `derivation_caveat`. A derived figure is never
the same row as a reported one.

RE-RUN
------
  py -3 code/1080_sec_gaming_facility_revenue.py mine
  py -3 code/1080_sec_gaming_facility_revenue.py build
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
    "derivation_percentage_base", "derivation_arithmetic", "derivation_caveat",
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
    r"(?:.{0,170}?to)?\s+"
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
        for j in range(max(0, i - 10), i):
            ys = YEAR_RE.findall(lines[j])
            if len(ys) >= 2 and len(re.sub(r"[^A-Za-z]", "", lines[j])) < 60:
                years = [int(y) for y in ys]
            mp = PERIOD_HDR_RE.search(lines[j].strip())
            if mp:
                mon, day = mp.group("mon"), int(mp.group("day"))
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
            hdr = " ".join(x.strip() for x in lines[max(0, i - 6):i + 1] if x.strip())
            row = lines[k].strip()
            quote = re.sub(r"\s+", " ", hdr + " || " + row).strip()
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

    for i, r in enumerate(sorted(rows, key=lambda z: (z["filing_date"], z["accession"],
                                                      z["extraction_pattern"],
                                                      str(z.get("alias", "")))), 1):
        r["candidate_id"] = f"SECGF-{i:05d}"

    cols = ["candidate_id", "extraction_pattern", "alias", "facility_name_as_filed",
            "facility_id", "tribe_name", "state", "on_indian_lands",
            "figure_type", "figure_type_note", "value_usd", "value_verbatim",
            "value_scale_applied", "fiscal_period_label", "period_type", "period_end",
            "derivation_stated_percentage", "derivation_percentage_base",
            "filer_name", "filer_cik", "filer_role", "form", "filing_date",
            "accession", "source_url", "local_file", "source_md5", "source_quote"]
    rows.sort(key=lambda z: z["candidate_id"])
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
            raise SystemExit(f"adjudication names {cid}, which is not in {CANDIDATES}")
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
            derivation_arithmetic=a.get("derivation_arithmetic", ""),
            derivation_caveat=a.get("derivation_caveat", ""),
        ))
    write(OUT_FIG, FIG_COLS, figs)
    write(OUT_TERMS, TERM_COLS, terms)
    out(f"accepted figures : {len(figs)} -> {OUT_FIG}")
    out(f"accepted terms   : {len(terms)} -> {OUT_TERMS}")
    out(f"rejected/held    : {n_reject}")


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

VALID_FIGURE_TYPES = {
    "FACILITY_NET_REVENUES", "FACILITY_GROSS_REVENUES",
    "FACILITY_NET_GAMING_REVENUE", "FACILITY_GROSS_GAMING_REVENUE",
    "MANAGEMENT_FEE_REVENUE", "RELINQUISHMENT_PAYMENT",
    "FACILITY_INCOME_FROM_OPERATIONS", "FACILITY_ADJUSTED_EBITDA",
    "DERIVED_FACILITY_NET_REVENUES",
}


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
            if r["figure_type"] != "DERIVED_FACILITY_NET_REVENUES":
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
            write(OUT_FIG, FIG_COLS, mut)
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
    elif stage == "selftest":
        selftest()
    else:
        raise SystemExit(__doc__)
