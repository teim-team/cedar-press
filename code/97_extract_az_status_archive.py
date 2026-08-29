#!/usr/bin/env python3
"""
97_extract_az_status_archive.py -- Cedar Press.

ARCHIVED editions of the Arizona Department of Gaming "Status of Tribal Gaming
in Arizona" table, retrieved from Wayback by `code/95_wayback_az_gaming_status.py`
into `data/raw/external/gaming_official/az_wayback/`.

WHY THIS MATTERS MORE THAN ITS ROW COUNT
----------------------------------------
Arizona is the only regulator in the country that publishes PER-CASINO device
counts. The live site carries the current snapshot only (2026-07-01), and the
vendor panel stops in 2023, so before this script there was no year in which a
CedarPress official count and a vendor count existed for the same Arizona
property. Every archived edition is a year of genuine same-year overlap.

ADG's own page states what the table is, verbatim:

    "The Department produces a periodic report which shows the status of Indian
     gaming in Arizona.  This report lists the tribes with gaming facilities,
     their location, how many machines in each facility, and which casino games
     are available."
     -- gaming.az.gov/status.htm, Wayback capture 20070410042237

WHY THIS IS NOT `code/93_extract_az_gaming_status.py`
-----------------------------------------------------
Script 93 reads the CURRENT edition, which is a rotated page with a printed
TOTALS row it can foot against. The archived editions are a different document:
landscape, unrotated, DIFFERENT COLUMNS (Live Keno, Bingo and Off-Track Betting
instead of DCETG, baccarat, craps and roulette), and -- the part that matters --
**no printed TOTALS row**. So the column-footing check that caught two separate
extraction failures in the current edition is not available here, and a
substitute had to be found rather than assumed.

THE SUBSTITUTE CHECK, AND WHY IT IS A REAL ONE
----------------------------------------------
The table states `Current # Sites` per TRIBE and then lists that tribe's casinos
one per row. So the document asserts its own row count. If the positional reader
mis-groups baselines -- which is exactly how the linear text layer fails here --
the number of casino rows recovered for a tribe stops matching the site count
the tribe's own row declares. Every tribe is checked, and a tribe that does not
reconcile is reported and NOT published.

THE FAILURE THIS AVOIDS
-----------------------
`pdftotext -layout` on the 2012 edition shifts the value columns up by one row,
exactly as it does in the Michigan tables. Read linearly, Harrah's Ak-Chin's
1,089 Class III devices land on Cocopah Casino, Cocopah's 506 land on Blue
Water, and so on down the page -- every figure well-sourced and every figure on
the wrong casino. Read positionally, Ak-Chin keeps its own 1,089.

WHAT IS DELIBERATELY NOT EXTRACTED
----------------------------------
The `Bingo` column carries bare numbers (470, 350, 1,500 ...) under a header
that states no unit. They are probably bingo seats and they are certainly not
devices. Publishing them under a guessed metric name would be a guess wearing a
citation, so the column is skipped and named here instead.

`Live Keno` and `Off-Track Betting` are Yes/No availability, not counts.

WRITES
  data/raw/external/gaming_official/az_status_archive_extracted_<date>.csv
    (agent-evidence schema; script 92 ingests it with no code change)
"""
import csv, re, sys
from pathlib import Path

import pdfplumber

CEDAR = Path(__file__).resolve().parent.parent
RAW = CEDAR / "data" / "raw" / "external" / "gaming_official"
ARCH = RAW / "az_wayback"
TODAY = "2026-08-07"

AUTHORITY = "Arizona Department of Gaming"
DOCTYPE = "state_regulator_status_report_archived"

# Column identity is the x-band of the HEADER token, learned per document rather
# than hard-coded, because the archived editions move columns between years.
# (header token -> published metric, unit)
WANTED = {
    "class_iii": ("class_iii_gaming_machines", "class_iii_gaming_devices"),
    "class_ii": ("class_ii_gaming_machines", "class_ii_gaming_devices"),
    "poker": ("poker_tables", "poker_tables"),
    "blackjack": ("blackjack_tables", "blackjack_tables"),
}

NUM = re.compile(r"^[\d,]+$")
DATE_OPENED = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sept?|Oct|Nov|Dec)\.?$")


def lines_of(page, tol=3.0):
    bands = []
    for w in sorted(page.extract_words(), key=lambda z: z["top"]):
        if bands and w["top"] - bands[-1][0] <= tol:
            bands[-1][1].append(w)
        else:
            bands.append([w["top"], [w]])
    return [(t, sorted(ws, key=lambda z: z["x0"])) for t, ws in bands]


def header_bands(lines):
    """Find the x-centre of each wanted column from the multi-line header."""
    band = {}
    for t, ws in lines[:12]:
        toks = [(w["text"].lower().strip(".:"), w) for w in ws]
        for i, (txt, w) in enumerate(toks):
            nxt = toks[i + 1][0] if i + 1 < len(toks) else ""
            if txt == "class" and nxt == "iii":
                band["class_iii"] = (w["x0"] + toks[i + 1][1]["x1"]) / 2
            elif txt == "class" and nxt == "ii":
                band["class_ii"] = (w["x0"] + toks[i + 1][1]["x1"]) / 2
            elif txt == "poker":
                band.setdefault("poker", (w["x0"] + w["x1"]) / 2)
            elif txt == "blackjack":
                band.setdefault("blackjack", (w["x0"] + w["x1"]) / 2)
            elif txt == "bingo":
                band["_bingo"] = (w["x0"] + w["x1"]) / 2
            elif txt == "sites":
                band["_sites"] = (w["x0"] + w["x1"]) / 2
    return band


def as_of_from(page_text):
    m = re.search(r"AS OF\s+(\d{1,2})/(\d{1,2})/(\d{2,4})", page_text, re.I)
    if not m:
        return None
    mm, dd, yy = m.groups()
    yy = ("20" + yy) if len(yy) == 2 else yy
    return f"{yy}-{int(mm):02d}-{int(dd):02d}"


def extract(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text() or ""
        lines = lines_of(page)
    aod = as_of_from(text)
    if not aod:
        return None, [], ["no 'AS OF <date>' line -- the report's own date is "
                          "the observation date and it will not be guessed"]
    band = header_bands(lines)
    if not all(k in band for k in ("class_iii", "class_ii")):
        return aod, [], ["header does not carry both Class III and Class II "
                         "columns -- layout not recognised"]

    def col_of(w):
        """Nearest wanted column to this token's centre, within 22pt."""
        c = (w["x0"] + w["x1"]) / 2
        best, bd = None, 1e9
        for k, x in band.items():
            d = abs(x - c)
            if d < bd:
                best, bd = k, d
        return best if bd <= 22 else None

    # the tribe-name column is the leftmost text; casino names sit further right
    rows, notes = [], []
    closed_marks = []          # last casino row emitted, for a trailing "(closed...)"
    tribe, sites_declared, seen_for_tribe = None, {}, {}
    header_bottom = max(t for t, ws in lines[:12]
                        if any(w["text"].lower().startswith("compact") or
                               w["text"].lower().startswith("opened") for w in ws))
    for t, ws in lines:
        if t <= header_bottom:
            continue
        left = [w for w in ws if w["x0"] < 160]
        mid = [w for w in ws if 260 <= w["x0"] < 390]
        if left:
            tribe = re.sub(r"[*\u2019']+$", "",
                           " ".join(w["text"] for w in left)).strip()
            sd = [w for w in ws if abs((w["x0"] + w["x1"]) / 2
                                       - band.get("_sites", -999)) <= 14
                  and NUM.match(w["text"])]
            if sd:
                sites_declared[tribe] = int(sd[0]["text"].replace(",", ""))
        casino = " ".join(w["text"] for w in mid).strip()
        if not casino or not tribe:
            continue
        if casino.startswith("(") or "closed" in casino.lower():
            # ADG sets "(closed eff. March 1, 2010)" on its own baseline UNDER
            # the closed casino's name. The casino keeps a row (with zero
            # devices); the annotation does not. And critically the tribe's
            # declared `Current # Sites` EXCLUDES the closed casino, so the
            # row-count check must exclude it too -- otherwise the check
            # rejects a correct extraction. Fort Mojave 2012 is the live case:
            # 1 declared site, 2 casino rows, one of them Crossing Casino
            # "(closed eff. March 1, 2010)" showing 0 Class III devices.
            if closed_marks:
                closed_marks[-1]["closed_note"] = casino
            notes.append(f"{tribe} :: '{casino}' -- annotation line, not a casino row")
            continue
        vals = {}
        for w in ws:
            if not NUM.match(w["text"]):
                continue
            c = col_of(w)
            if c and not c.startswith("_"):
                vals[c] = float(w["text"].replace(",", ""))
        if not vals:
            continue
        mark = dict(tribe=tribe, casino=casino, closed_note="",
                    idx=[len(rows), 0])
        closed_marks.append(mark)
        seen_for_tribe[tribe] = seen_for_tribe.get(tribe, 0) + 1
        for k, v in vals.items():
            metric, unit = WANTED[k]
            rows.append(dict(
                facility_name_as_published=casino,
                tribe_name_as_published=tribe,
                state="AZ", metric=metric, value=f"{v:g}", unit=unit,
                as_of_date=aod, as_of_date_precision="day",
                period_start="", period_end="",
                source_authority=AUTHORITY, source_document_type=DOCTYPE,
                source_url="", source_page=pdf_path.name,
                source_quote=(f'"{tribe}" / "{casino}" / column "{metric}" = {v:g} '
                              f'| ADG Status of Tribal Gaming in Arizona as of {aod} '
                              f'| table line as printed: '
                              + " ".join(w["text"] for w in ws))[:900],
                fetched_date=TODAY))
        mark["idx"][1] = len(rows)

    # A casino annotated "(closed ...)" is still a dated observation and it is
    # kept -- 2006: 1,200 devices and 2026: 2,480 both survive is the standing
    # rule, and so does a closed property's last reported floor. It is flagged,
    # and it is removed from the site-count reconciliation.
    for m in closed_marks:
        if not m["closed_note"]:
            continue
        seen_for_tribe[m["tribe"]] = max(0, seen_for_tribe.get(m["tribe"], 1) - 1)
        for r in rows[m["idx"][0]:m["idx"][1]]:
            r["exclusion_flag"] = "1"
            r["exclusion_reason"] = (
                "the report annotates this casino " + m["closed_note"]
                + "; the figure is the last one the regulator published for it, "
                  "not a current floor")
            r["qualifier"] = m["closed_note"]

    # ---- the document's own row-count assertion -----------------------------
    bad = []
    for tr, k in sites_declared.items():
        got = seen_for_tribe.get(tr, 0)
        if got != k:
            bad.append(f"{tr}: declares {k} sites, recovered {got} open casino rows")
    return aod, rows, bad + notes


def main():
    if not ARCH.exists():
        print(f"no archive directory yet: {ARCH}")
        return
    cands = sorted(p for p in ARCH.glob("*.pdf"))
    print(f"{len(cands)} archived PDFs on disk")
    out, skipped = [], []
    for p in cands:
        head = p.read_bytes()[:4]
        if head != b"%PDF":
            continue
        try:
            aod, rows, problems = extract(p)
        except Exception as e:
            skipped.append((p.name, f"{type(e).__name__}: {e}"))
            continue
        hard = [x for x in problems if "declares" in x]
        if rows and not hard:
            out.extend(rows)
            print(f"  OK    {p.name}  as-of {aod}  {len(rows):3} rows"
                  + (f"   notes: {len(problems)}" if problems else ""))
        elif rows and hard:
            skipped.append((p.name, "row-count check failed: " + "; ".join(hard[:3])))
        else:
            skipped.append((p.name, "; ".join(problems[:2]) or "no capacity rows"))

    # The Wayback capture URL is the citation. It is looked up in the CDX
    # checkpoints rather than reconstructed from a guessed directory: these old
    # captures live at several different paths (`/WhiteStatus.pdf`,
    # `/sites/default/files/...`), and a citation that 404s is worse than none.
    import json as _json
    orig = {}
    for ck in RAW.glob("wayback_az_cdx_raw_*.json"):
        for row in _json.loads(ck.read_text(encoding="utf-8")):
            orig[(row[1], row[2].rsplit("/", 1)[-1].split("?")[0])] = row[2]
    missing = 0
    for r in out:
        ts, _, base = r["source_page"].partition("_")
        base = base.replace("_", "%20")
        o = orig.get((ts, base)) or orig.get((ts, base.replace("%20", "_")))
        if o:
            r["source_url"] = f"https://web.archive.org/web/{ts}id_/{o}"
        else:
            missing += 1
    if missing:
        print(f"  {missing} rows could not be given a verified capture URL")

    if out:
        with open(RAW / f"az_status_archive_extracted_{TODAY}.csv", "w",
                  encoding="utf-8", newline="") as fh:
            cols = list(out[0].keys()) + [c for c in
                    ('qualifier', 'exclusion_flag', 'exclusion_reason')
                    if c not in out[0]]
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
            w.writeheader()
            w.writerows(out)
    print(f"\nwrote az_status_archive_extracted_{TODAY}.csv  ({len(out):,} rows)")
    print(f"editions published: {sorted({r['as_of_date'] for r in out})}")
    print(f"\nNOT published ({len(skipped)}):")
    for nm, why in skipped:
        print(f"  {nm}\n      {why[:200]}")


if __name__ == "__main__":
    main()
