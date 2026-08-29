"""372 - the UNATTRIBUTED families a court caption named, with their dollars.

WHAT THIS IS FOR
----------------
`docs/PULL_DISCIPLINE.md` ("THE CENTRAL LIMITATION") says an identifier-seeded
pull *"can never discover an entity we do not already know"*, and that the only
honest response is *"to measure it, label it, and run something else that looks
outside."*

A court caption is something that looks outside.  Every family below is a name
that a **federal docket put on the record next to another name**, and that
`prime_contracts.csv` then turned out to hold with real money and no owner.
None of them was on any queue this pass started from.

The unit here is a NAME FAMILY, not an identifier, and that is deliberate:
the 8(a) programme's nine-year term is why tribes and ANCs stand up successor
entities sharing a name with fresh identifiers (`docs/RECONCILIATION_TOOL.md`).
A family is the shape the ownership question actually has.

WHAT IT IS NOT
--------------
**Not attributions, and nothing is applied.**  Each row is a candidate at the
tier its source row carries - which for `unattributed` prime rows is tier C -
and a sweep that promoted its own finds would be the laundering defect with a
new front door (`PULL_DISCIPLINE.md`, closing rule).

Reads   data/clean/prime_contracts.csv    (the PROMOTED table, nothing else)
Writes  review/caption_named_discovery_leads_2026-08-26.csv   STAGED ONLY

py -3 code/372_stage_caption_named_discovery_leads.py     # 0 network requests
"""
import collections
import csv
import pathlib
import re
import sys

csv.field_size_limit(10 ** 8)

ROOT = pathlib.Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = ROOT / "data" / "clean"
REVIEW = ROOT / "review"
TODAY = "2026-08-26"
OUT = REVIEW / f"caption_named_discovery_leads_{TODAY}.csv"
CL = "https://www.courtlistener.com/docket/"

# family label -> (regex over awardee_name, the caption that named it, the
#                  question the caption raises)
FAMILIES = [
 ("DAWSON_FAMILY", r"^dawson[ ,\-]|^d7[ ,]|^dawson$",
  f"United States of America v. Hawaiian Native Corp., S.D. Cal. 3:18-cv-02849, "
  f"filed 2018-12-19, {CL}16069152/united-states-of-america-v-hawaiian-native-corp/ "
  "-- party array: Total Reliant Solutions, LLC | Dawson Technical, LLC | D7, LLC | "
  "Dawson Enterprises, LLC | Wagon Wheel, LLC | Dawson Solutions, LLC | "
  "Dawson Federal Inc. | United States of America | Sandlot Ventures, LLC | "
  "Eugene Sellers | Dawson Global, LLC | BD Solutions, LLC | "
  "Program Construction and Management",
  "the United States sued the whole family under a caption headed by HAWAIIAN "
  "NATIVE CORP. Is that the 8(a) parent? CO_DEFENDANT_ONLY until the complaint is read."),
 ("NICC_JV_FAMILY", r"\bnicc\b",
  "NOT named by any caption - `q=` and `party_name` both returned 0 for Atlantic "
  "NICC, Central NICC and NICC JV. Included because the sweep's NEGATIVE result "
  "is what makes the local measurement worth staging.",
  "SIX JVs, all Falls Church / Vienna VA, FY2009-2022. Five are `unattributed` "
  "tier C. The ONLY attribution thread the family has is NORTHEAST NICC JV, LLC "
  "-> `TRBS-CHKNAL-00 Cherokee Tribe of Northeast Alabama` (a STATE-recognised "
  "tribe) on 2 rows via uei_exact tier B, which has the shape of a token "
  "collision on the word `Northeast`. Two of the six are among the seven ruled "
  "NATIVE with no owner named."),
 ("HUI_HULIAU_FAMILY", r"hui huliau|pono aina|kaya associates|kwn assets",
  f"Huliau v. KWN Assets LLC, W.D. Okla. 5:21-cv-01119, filed 2021-11-24, "
  f"{CL}61576080/huliau-v-kwn-assets-llc/ -- party array: Hui Huliau | "
  "Kenneth W Novotny | Pono Aina Management LLC | KWN Assets LLC. And "
  f"Johnson v. Hui Huliau Staffing, E.D. Ky. 5:20-cv-00440, filed 2020-10-26, "
  f"{CL}31364393/johnson-v-hui-huliau-staffing/ -- party array: "
  "Hui Huliau Staffing | 4P Management Company | Kaya Associates, Inc. | "
  "Steven Johnson | Brian Eschrich",
  "Hui Huliau captions itself `Hui Huliau, A Native Hawaiian Organization` in "
  "N.D. Ohio 1:20-op-45025. Kenneth W Novotny is also the principal named "
  "beside KNWEBS Inc in W.D. Okla. 5:18-cv-00200, so this family touches one of "
  "the seven. Kaya Associates is HUNTSVILLE AL, and so is Redstone Defense "
  "Systems - a coincidence of place, and NOTHING MORE, unless a record says so."),
 ("PENTACON", r"^pentacon",
  f"Southwind Construction Services LLC v. Ross Group Construction Corporation The, "
  f"W.D. Okla. 5:15-cv-00102, filed 2015-01-29, cause 31:3729 False Claims Act, "
  f"{CL}13566135/southwind-construction-services-llc-v-ross-group-construction-corporation/ "
  "-- party array: C3 LLC | Ross Group Construction Corporation The | "
  "Ross Group LLC The | John Does | Southwind Construction Services LLC | "
  "Pentacon LLC | Red Cedar Enterprises Inc",
  "Catoosa OK, entirely unattributed, on a caption with Red Cedar Enterprises "
  "(a Modoc Nation company per the Tenth Circuit) and Southwind Construction "
  "Services (a sibling name of one of the seven)."),
 ("MODOC_MTE_FAMILY", r"\bmte\b",
  f"Modoc Nation v. Shah, 10th Cir. 24-5135, docketed 2024-11-18, "
  f"{CL}71537478/modoc-nation-v-shah/ -- party array names WALGA MTE, LLC | "
  "MODOC MTE, LLC | BUFFALO MTE, LLC | MODOC NATION, AKA Modoc Tribe of Oklahoma | "
  "RED CEDAR ENTERPRISES, INC.",
  "Cedar already attributes WALGA MTE and BUFFALO MTE (Joplin MO) to the Modoc "
  "Tribe of Oklahoma, and RED CEDAR TG-MTE to Paiute of Utah. Same suffix, two "
  "tribes. `Buffalo Mte, Llc` of PANGUITCH, UT is unattributed."),
 ("ALAKAINA_SIBLINGS", r"^manu kai|ke.?aki|^akimeka",
  f"Michaud v. Manu Kai, LLC, D. Haw. 1:15-cv-00438 and 1:15-cv-00321, "
  f"{CL}13318768/michaud-v-manu-kai-llc/ -- Manu Kai, LLC | Ke'aki Technologies, "
  "LLC | Akimeka, LLC | Akimeka Technologies, LLC appear in one party array",
  "A dated SIBLING SET for the largest of the seven after Redstone. The same "
  "caption carries ITT / Exelis / Vectrus / Harris and twelve Doe classes "
  "including `Doe Holding Companies 1020`, so the common thread may be a NAVY "
  "CONTRACT and not a parent. CO_DEFENDANT_ONLY."),
]

COLS = ["family", "awardee_name", "awardee_uei", "prime_rows",
        "prime_obligations_usd", "unattributed_rows", "unattributed_usd",
        "cities", "fy_first", "fy_last", "current_tribe_id",
        "current_canonical_name", "current_attribution_method",
        "current_confidence_tier", "caption_that_named_it", "the_question",
        "relationship_type", "cedar_action", "applied", "flagged_date"]


def main():
    pats = [(lab, re.compile(rx, re.I), cap, q) for lab, rx, cap, q in FAMILIES]
    agg = collections.defaultdict(
        lambda: {"usd": 0.0, "rows": 0, "u_usd": 0.0, "u_rows": 0,
                 "ueis": set(), "cities": collections.Counter(),
                 "fy": set(), "attr": collections.Counter()})
    with (CLEAN / "prime_contracts.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            nm = row.get("awardee_name") or ""
            for lab, rx, _, _ in pats:
                if not rx.search(nm):
                    continue
                a = agg[(lab, nm)]
                try:
                    v = float(row.get("total_obligations") or 0)
                except ValueError:
                    v = 0.0
                a["usd"] += v
                a["rows"] += 1
                if row.get("attributed_flag") != "1":
                    a["u_usd"] += v
                    a["u_rows"] += 1
                if row.get("awardee_uei"):
                    a["ueis"].add(row["awardee_uei"])
                a["cities"][f"{row.get('recipient_city_name')}, "
                            f"{row.get('recipient_state_code')}"] += 1
                if row.get("fiscal_year"):
                    a["fy"].add(row["fiscal_year"])
                a["attr"][(row.get("tribe_id", ""), row.get("canonical_name", ""),
                           row.get("attribution_method", ""),
                           row.get("confidence_tier", ""))] += 1

    meta = {lab: (cap, q) for lab, _, cap, q in pats}
    out = []
    for (lab, nm), a in agg.items():
        if a["usd"] < 100000 and a["u_usd"] < 100000:
            continue
        top = a["attr"].most_common(1)[0][0]
        fy = sorted(a["fy"])
        cap, q = meta[lab]
        out.append({
            "family": lab, "awardee_name": nm,
            "awardee_uei": " ; ".join(sorted(a["ueis"])),
            "prime_rows": str(a["rows"]),
            "prime_obligations_usd": f"{a['usd']:.2f}",
            "unattributed_rows": str(a["u_rows"]),
            "unattributed_usd": f"{a['u_usd']:.2f}",
            "cities": " ; ".join(c for c, _ in a["cities"].most_common(3)),
            "fy_first": fy[0] if fy else "", "fy_last": fy[-1] if fy else "",
            "current_tribe_id": top[0], "current_canonical_name": top[1],
            "current_attribution_method": top[2], "current_confidence_tier": top[3],
            "caption_that_named_it": cap, "the_question": q,
            "relationship_type": "CO_DEFENDANT_ONLY_OR_NOT_NAMED_AT_ALL",
            "cedar_action": ("CANDIDATE for adjudication. A tier is inherited from the "
                             "source row; unattributed prime rows are tier C."),
            "applied": "NO", "flagged_date": TODAY,
        })
    out.sort(key=lambda r: (r["family"], -float(r["unattributed_usd"])))

    tmp = OUT.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in out:
            w.writerow(r)
    tmp.replace(OUT)

    back = list(csv.DictReader(OUT.open(encoding="utf-8-sig")))
    print(f"{len(back)} lead(s) -> {OUT.name}   (re-read from disk)")
    fam = collections.defaultdict(lambda: [0.0, 0.0, 0])
    for r in back:
        f_ = fam[r["family"]]
        f_[0] += float(r["prime_obligations_usd"])
        f_[1] += float(r["unattributed_usd"])
        f_[2] += 1
    for lab, (tot, un, n) in sorted(fam.items(), key=lambda kv: -kv[1][1]):
        print(f"  {lab:20s} {n:3d} entities  total ${tot/1e6:9,.1f}M  "
              f"UNATTRIBUTED ${un/1e6:9,.1f}M")
    print(f"\n  TOTAL UNATTRIBUTED across the caption-named families: "
          f"${sum(v[1] for v in fam.values()):,.0f}")
    print("\nSTAGED ONLY. Nothing applied, no tier assigned, no shared table written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
