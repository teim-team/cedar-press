"""567_stage_cicd_published_series.py — stage CICD's PUBLISHED year-by-year
federal contracting series, and reconcile Cedar to it year by year.

WHERE THE SERIES CAME FROM, AND WHY THAT MATTERS
------------------------------------------------
`docs/CICD_BENCHMARK.md` could only compare Cedar to CICD's headline totals
because the article prints prose, not tables.  It prints charts — and the
charts are Highcharts, whose complete `series.data` arrays are embedded in the
page's `__NEXT_DATA__` payload.  This is `docs/HIDDEN_DATA_TECHNIQUES.md`
item 2 ("embedded application state") applied to a published research article:
the page renders a picture, and ships the numbers.

Nothing here is scraped from behind anything.  It is the bytes the server sends
any anonymous visitor, from a page CICD published, and the extraction is
self-validating: the three entity series sum to $197.987B for 1981–2021 against
the article's own stated "$198 billion from prime contracts".

Source (retrieved 2026-09-01):
  Larry Chavis, Matthew Gregg, Elijah Moreno, "Federal contracting's expanding
  revenue role in Indian Country", Center for Indian Country Development,
  Federal Reserve Bank of Minneapolis, 21 December 2022.
  https://www.minneapolisfed.org/article/2022/federal-contractings-expanding-revenue-role-in-indian-country
  Chart caption, verbatim: "Note: Federal contracting revenue is from prime
  contracts only.  Source: FPDS-NG accessed via Bloomberg Government Contracts
  Intelligence Tool (1981-2021), FRED, and authors' calculations"

UNITS, AND DO NOT MIX THEM
--------------------------
CICD's series is **2021 dollars, prime contracts only**.  Cedar's
`total_obligations` is nominal; `total_obligations_real2025` is 2025 dollars.
This script converts Cedar to 2021 dollars using the table's OWN
`deflator_factor_2025` for FY2021, so both sides are one unit.  CICD does not
state which price index it used (the caption says only "FRED"), so the
comparison carries an unquantified index difference — recorded, not hidden.

CICD's year is BGOV's contract year and Cedar's is the federal fiscal year.
They are not the same year and the difference is not estimated away here.

READ-ONLY against every Cedar table.  Writes:
  data/staging/cicd_published/cicd_prime_series_1981_2021.csv
  data/staging/cicd_published/cedar_vs_cicd_by_year.csv
  data/staging/cicd_published/_provenance.json

It stages a PUBLISHED figure beside Cedar's own; it writes no derived or
interpolated dollar into any clean table, and it attributes nothing.
"""
import csv
import datetime
import html
import json
import os
import re
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "staging", "cicd_published")
RECON = os.path.join(ROOT, "data", "staging", "pre2000_probe",
                     "benchmark_reconciliation.json")
URL = ("https://www.minneapolisfed.org/article/2022/"
       "federal-contractings-expanding-revenue-role-in-indian-country")
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
LOCK = os.path.join(ROOT, "logs", "_HOSTLOCK_www.minneapolisfed.org.json")
YEARS = list(range(1981, 2022))
ENTITY_SERIES = ["Alaska Native Corporations", "Native Hawaiian Organizations", "Tribes"]
# The article's own stated prime total, 1981-2021, 2021 dollars.  The extraction
# is rejected if it does not reproduce this within 0.5%.
STATED_PRIME_TOTAL = 198_000_000_000.0


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def claim(active, **extra):
    d = {"host": "www.minneapolisfed.org", "pid": os.getpid(),
         "script": "code/567_stage_cicd_published_series.py", "claimed_at": now(),
         "active": active, "queue": [],
         "policy": "1 GET of one published article page, no crawl",
         "note": "extract published Highcharts series from CICD 2022 article"}
    d.update(extra)
    with open(LOCK, "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1)


def fetch():
    claim(True)
    try:
        r = requests.get(URL, headers=HDR, timeout=90)
        r.raise_for_status()
        return r.text
    finally:
        claim(False, requests_issued=1, released=now())


def extract_series(page):
    m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
    if not m:
        raise SystemExit("__NEXT_DATA__ not found — the page shape changed; do not guess")
    blob = json.dumps(json.loads(m.group(1)))
    # The Highcharts configs live inside JSON string fields, so the escapes are
    # doubled.  Decode once to get at the raw JS.
    js = blob.encode().decode("unicode_escape", errors="replace")
    js = html.unescape(js)
    out = {}
    for mm in re.finditer(r"name:\s*'([^']+)',\s*\n?\s*\n?\s*data:\s*\[([^\]]*)\]", js):
        name = mm.group(1)
        vals = [float(x) for x in re.findall(r"-?\d+\.?\d*", mm.group(2))]
        if len(vals) == len(YEARS) and name not in out:
            out[name] = vals
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    page = fetch()
    series = extract_series(page)
    missing = [s for s in ENTITY_SERIES if s not in series]
    if missing:
        raise SystemExit(f"published series not found in page: {missing}")

    total = [sum(series[s][i] for s in ENTITY_SERIES) for i in range(len(YEARS))]
    grand = sum(total)
    err = abs(grand - STATED_PRIME_TOTAL) / STATED_PRIME_TOTAL
    if err > 0.005:
        raise SystemExit(
            f"extraction rejected: series sums to ${grand/1e9:.3f}B against the "
            f"article's stated $198B ({err:.2%} off). Do not stage a figure that "
            f"does not reproduce its own source's headline.")
    print(f"  extraction validated: ${grand/1e9:.3f}B vs stated $198B ({err:.3%})")

    share = series.get("Share of federal contracting dollars among Native entities")
    p1 = os.path.join(OUT, "cicd_prime_series_1981_2021.csv")
    with open(p1, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "anc_prime_2021usd", "nho_prime_2021usd",
                    "tribes_prime_2021usd", "total_prime_2021usd",
                    "share_of_all_federal_contract_dollars_pct",
                    "publisher", "publication_date", "source_url", "basis"])
        for i, y in enumerate(YEARS):
            w.writerow([y,
                        f"{series['Alaska Native Corporations'][i]:.0f}",
                        f"{series['Native Hawaiian Organizations'][i]:.0f}",
                        f"{series['Tribes'][i]:.0f}",
                        f"{total[i]:.0f}",
                        f"{share[i]:.2f}" if share else "",
                        "CICD / Federal Reserve Bank of Minneapolis",
                        "2022-12-21", URL,
                        "prime contracts only; 2021 dollars; FPDS-NG via Bloomberg "
                        "Government Contracts Intelligence Tool"])
    print(f"  wrote {p1}")

    # ---- year-by-year reconciliation against Cedar ---------------------------
    if not os.path.exists(RECON):
        print("  benchmark_reconciliation.json absent — run code/564 first; "
              "skipping the comparison table", file=sys.stderr)
        return
    rec = json.load(open(RECON, encoding="utf-8"))
    f21 = rec["deflator_factor_2025_by_fy"]["2021"]
    p2 = os.path.join(OUT, "cedar_vs_cicd_by_year.csv")
    with open(p2, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["year", "cicd_prime_2021usd", "cedar_attributed_prime_2021usd",
                    "delta_usd", "delta_pct", "cedar_rows", "note"])
        for i, y in enumerate(YEARS):
            c = total[i]
            cy = rec["by_fy"].get(str(y))
            if cy is None:
                w.writerow([y, f"{c:.0f}", "", "", "", 0,
                            "Cedar holds no rows for this year"])
                continue
            cedar = cy["att_real2025"] / f21
            w.writerow([y, f"{c:.0f}", f"{cedar:.0f}", f"{cedar-c:.0f}",
                        f"{100*(cedar-c)/c:.2f}" if c else "",
                        cy["att_rows"],
                        "CICD year is BGOV contract year; Cedar is federal fiscal year"])
    print(f"  wrote {p2}")

    def rng(a, b):
        return sum(total[i] for i, y in enumerate(YEARS) if a <= y <= b)

    cedar_00_21 = sum(v["att_real2025"] for k, v in rec["by_fy"].items()
                      if 2000 <= int(k) <= 2021) / f21
    prov = {
        "retrieved": now(),
        "source_url": URL,
        "publisher": "Center for Indian Country Development, Federal Reserve Bank of Minneapolis",
        "publication_date": "2022-12-21",
        "authors": ["Larry Chavis", "Matthew Gregg", "Elijah Moreno"],
        "technique": "embedded application state (__NEXT_DATA__ -> Highcharts series.data); "
                     "docs/HIDDEN_DATA_TECHNIQUES.md item 2",
        "chart_caption_verbatim":
            "Note: Federal contracting revenue is from prime contracts only. Source: "
            "FPDS-NG accessed via Bloomberg Government Contracts Intelligence Tool "
            "(1981-2021), FRED, and authors' calculations",
        "unit": "2021 dollars, prime contracts only",
        "extraction_validation": {
            "series_sum_1981_2021": round(grand, 2),
            "article_stated_prime_total": STATED_PRIME_TOTAL,
            "relative_error": round(err, 6),
        },
        "headline_findings": {
            "cicd_1981_1999_2021usd": round(rng(1981, 1999), 2),
            "cicd_1981_1999_share_of_41yr_total_pct": round(100 * rng(1981, 1999) / grand, 4),
            "cicd_2000_2021_2021usd": round(rng(2000, 2021), 2),
            "cedar_fy2000_2021_attributed_2021usd": round(cedar_00_21, 2),
            "delta_pct_on_the_like_for_like_window":
                round(100 * (cedar_00_21 - rng(2000, 2021)) / rng(2000, 2021), 2),
            "cicd_years_1982_1987_and_1989_are_literally_zero": True,
        },
        "caveats": [
            "CICD does not state its price index; the caption says only 'FRED'. Cedar "
            "deflates with its own deflator_factor_2025. The residual carries an "
            "unquantified index difference.",
            "CICD's year is BGOV's contract year; Cedar's is the federal fiscal year.",
            "CICD's dataset is frozen at 2021 and its authors call it a lower-bound estimate.",
            "This file stages a PUBLISHED figure for comparison. It is not a Cedar "
            "measurement and must never be merged into a Cedar table as one.",
        ],
    }
    with open(os.path.join(OUT, "_provenance.json"), "w", encoding="utf-8") as fh:
        json.dump(prov, fh, indent=2)
    print(json.dumps(prov["headline_findings"], indent=2))


if __name__ == "__main__":
    main()
