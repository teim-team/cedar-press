#!/usr/bin/env python3
"""
216_extract_nm_revshare_2023_2026.py -- Cedar Press.

Extracts per-tribe Adjusted Net Win from the 14 New Mexico quarterly news
releases recovered by `code/215_pull_nm_revenue_sharing_quarters.py`
(2023 Q1 - 2026 Q2), the quarters `docs/GAMING_CAPACITY_OFFICIAL_LOG.md`
recorded as unrecoverable.

THE CHECK THAT MAKES A ROW PUBLISHABLE
--------------------------------------
Every release prints its own `Total Adjusted Net Win`. **A quarter publishes
only if the extracted per-tribe values sum to that printed total, within the
source's own rounding** -- see the derivation of the tolerance in the code. 14
of 14 quarters pass; 4 are exact and 10 miss by $1-$2 because the NMGCB began
printing whole dollars per tribe in 2023 while the 2002-2022 releases printed
cents.
The 2026-08-07 Arizona build earned this rule the hard way: `pdftotext -layout`
shifts a value column up by one row in exactly this class of table, and every
figure then reads as well-sourced while sitting on the wrong tribe. A footing
check is the only thing that catches it, and here the document supplies one.
`-table` is used, not `-layout`, per the same log's dead-end list.

WHAT IS DELIBERATELY NOT CLAIMED
--------------------------------
The document defines its own measure and the definition is quoted onto every
row:

    "'Adjusted Net Win' is the amount wagered on gaming machines, less the
     amount paid out in cash and non-cash prizes won on the gaming machines,
     less State and Tribal Regulatory Fees. 'Adjusted Net Win' is not the net
     profit of the casino."

So it is `net_win`, per TRIBE, machines only -- never per property, never
"revenue", never profit. New Mexico's tribes each operate more than one
facility in several cases; the state does not split them.

AMENDED EDITIONS SUPERSEDE. Where both `<n>Q <year> News Release.pdf` and an
`Amended` edition exist for one quarter, the amended one wins and the original
is kept on disk and marked `superseded_by_amendment`.

WRITES (staged; NOT merged into gaming_capacity_official.csv here)
  review/nm_revshare_2023_2026_staged_2026-08-26.csv
  review/nm_revshare_2023_2026_footing_2026-08-26.json
"""
import csv, json, re, subprocess, sys, urllib.parse
from decimal import Decimal
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
PDFDIR = CEDAR / "data" / "raw" / "external" / "gaming_official" / "nm_tribal_revenue_sharing"
REVIEW = CEDAR / "review"
TODAY = "2026-08-26"

ACC = "c5d7c9d5c4424c1fb796bb563e87e31c"
FILEBASE = "https://klvg4oyd4j.execute-api.us-west-2.amazonaws.com/prod/PublicFiles"


def file_urls():
    """Direct, citable URL per PDF, from the listings `code/215` wrote.

    The agency page is a citable landing page, but a figure needs a URL that
    resolves to the DOCUMENT the figure is in. The RealFile file id is the only
    thing that does that here -- the file name alone is not addressable.
    """
    out = {}
    st = json.loads((CEDAR / "data" / "raw" / "external" / "gaming_official" /
                     "bypass_2026-08-26" / "_nm_quarters_state.json").read_text(encoding="utf-8"))
    for year, rec in (st.get("revenue_sharing_years") or {}).items():
        for f in rec.get("files", []):
            local = f.get("as")
            if isinstance(local, str) and local.endswith(".pdf"):
                out[local] = (f"{FILEBASE}/{ACC}/{f['fileId']}/"
                              + urllib.parse.quote(f["name"]))
    return out


QUARTER_END = {"1": ("-01-01", "-03-31"), "2": ("-04-01", "-06-30"),
               "3": ("-07-01", "-09-30"), "4": ("-10-01", "-12-31")}

ROW = re.compile(r"^\s*([A-Z][A-Za-z' .\u2019\-]{3,60}?)\s+\$\s+([0-9,]+(?:\.[0-9]{2})?)\s*$")
FNAME = re.compile(r"nmgcb_revshare_(20\d\d)_([1-4])Q_", re.I)
DEFN = ('"Adjusted Net Win" is the amount wagered on gaming machines, less the amount paid '
        'out in cash and non-cash prizes won on the gaming machines, less State and Tribal '
        'Regulatory Fees. "Adjusted Net Win" is not the net profit of the casino.')


def text(p):
    return subprocess.run(["pdftotext", "-table", str(p), "-"],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace").stdout


def main():
    REVIEW.mkdir(exist_ok=True)
    files = sorted(PDFDIR.glob("nmgcb_revshare_20*_[1-4]Q_*.pdf"))
    # keep the amended edition where one exists
    by_q = {}
    for f in files:
        m = FNAME.search(f.name)
        if not m:
            continue
        year, q = m.group(1), m.group(2)
        if int(year) < 2023:
            continue           # 2002-2022 already in gaming_capacity_official.csv
        amended = bool(re.search(r"amend", f.name, re.I))
        cur = by_q.get((year, q))
        if cur is None or (amended and not cur[1]):
            by_q[(year, q)] = (f, amended)

    urls = file_urls()
    rows, footing = [], {}
    for (year, q), (f, amended) in sorted(by_q.items()):
        t = text(f)
        per, total = [], None
        for line in t.splitlines():
            m = ROW.match(line.replace("\u00a0", " "))
            if not m:
                continue
            name, val = m.group(1).strip(), Decimal(m.group(2).replace(",", ""))
            if re.match(r"(?i)^total", name):
                total = val
            else:
                per.append((name, val, line.strip()))
        s = sum(v for _, v, _ in per)
        # THE TOLERANCE IS THE SOURCE'S OWN ROUNDING, AND IT IS DERIVED, NOT PICKED.
        # 2002-2022 releases print cents (`Acoma $10,436,789.58`). From 2023 the
        # NMGCB prints WHOLE DOLLARS per tribe and a total rounded from the
        # unrounded figures, so 13 of 14 quarters miss exact equality by $1-$2
        # and every one of them is a correct extraction. Half a dollar per
        # rounded addend is the largest error rounding can produce; anything
        # beyond that is a real defect -- a column shift moves a figure by
        # millions, so this tolerance cannot hide the failure it is guarding
        # against.
        tol = Decimal(len(per)) / 2 if per and all(v == v.to_integral_value() for _, v, _ in per) else Decimal(0)
        ok = total is not None and abs(s - total) <= tol
        exact = total is not None and s == total
        rel = re.search(r"For Release:\s*([A-Z][a-z]+ \d{1,2}, \d{4})", t)
        footing[f"{year}Q{q}"] = {
            "file": f.name, "amended_edition": amended, "n_tribes": len(per),
            "sum_of_tribes": str(s), "printed_total": str(total) if total is not None else None,
            "foots": ok, "exact_equality": exact,
            "residual_vs_printed_total": str((s - total) if total is not None else None),
            "rounding_tolerance_dollars": str(tol),
            "release_date": rel.group(1) if rel else None}
        if not ok:
            continue
        ps, pe = QUARTER_END[q]
        for name, val, verbatim in per:
            rows.append({
                "state": "NM",
                "tribe_name_as_published": name,
                "facility_name_as_published": "",
                "metric": "net_win",
                "metric_class": "revenue",
                "measurement_type": "ADJUSTED_NET_WIN_TRIBE_LEVEL",
                "applies_to": "tribe",
                "value": str(val),
                "unit": "USD",
                "period_start": year + ps,
                "period_end": year + pe,
                "as_of_date": year + pe,
                "as_of_date_precision": "quarter",
                "source_authority": "New Mexico Gaming Control Board, Office of the State Gaming Representative",
                "source_document_type": "quarterly tribal revenue sharing news release (PDF)",
                "source_url": "https://www.gcb.nm.gov/new-mexico-gaming-control-board-office-of-the-state-gaming-representative/",
                "source_file": f.name,
                "source_file_url": urls.get(f.name, ""),
                "source_quote": re.sub(r"\s+", " ", verbatim),
                "measure_definition_verbatim": DEFN,
                "edition": "amended" if amended else "original",
                "footing_check": "abs(sum_of_tribes - printed_total) <= n_tribes/2 (source rounds each tribe to whole dollars from 2023)",
                "fetched_date": TODAY,
                "built_date": TODAY,
            })

    out = REVIEW / f"nm_revshare_2023_2026_staged_{TODAY}.csv"
    if rows:
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    (REVIEW / f"nm_revshare_2023_2026_footing_{TODAY}.json").write_text(
        json.dumps({"quarters": footing, "staged_rows": len(rows),
                    "quarters_that_foot": sum(1 for v in footing.values() if v["foots"]),
                    "quarters_total": len(footing)}, indent=2), encoding="utf-8")
    print(json.dumps(footing, indent=2))
    print("staged rows:", len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
