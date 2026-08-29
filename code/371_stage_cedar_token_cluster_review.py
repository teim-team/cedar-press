"""371 - the `cedar` token, measured: every identifier cluster_v3 hung on the
Paiute Indian Tribe of Utah, with the dollars each one carries.

HOW THIS WAS FOUND, WHICH IS THE POINT
--------------------------------------
Not by looking for it.  `code/367` asked CourtListener one aimed question about
`Red Cedar Enterprises` because the name turned up as a co-party in an FCA
caption, and the answer was:

    Modoc Nation v. Shah, 10th Cir. No. 24-5135, docketed 2024-11-18
    party: WALGA MTE, LLC | SHARAD DADBHAWALA | LEGAL ADVOCATES FOR INDIAN
    COUNTRY LLP | MODOC MTE, LLC | TROY LITTLEAXE | BUFFALO MTE, LLC |
    MODOC NATION, AKA Modoc Tribe of Oklahoma | RAJESH SHAH |
    SOFTEK SOLUTIONS, INC. | BLAKE FOLLIS | RED CEDAR ENTERPRISES, INC. | ...

Cedar's own ledger already held BOTH answers on that one company and had
applied neither:

    CAGE:3V7E1        -> Modoc Nation      agent_research_one_leg  B  is_authority YES
    UEI:JZQYD48BJMX3  -> Paiute of Utah    cluster_v3              B  "Algorithmic
                                                                      name clustering,
                                                                      unreviewed"

`prime_contracts.csv` follows the **cluster_v3** leg, by `uei_exact`, on 611
rows.  Pulling that thread is what exposed the rest.

WHAT THE PATTERN IS
-------------------
The Paiute Indian Tribe of Utah is seated in **CEDAR CITY, UTAH** and its
constituent Cedar Band owns Cedar Band Corporation.  `cluster_v3` appears to
have clustered on the token **`cedar`** and swept in unrelated companies from
across the country - including `Cedar Key Native Environmental` (Cedar Key is
in FLORIDA) and `Goldbelt-Cedar, L.L.C.` (Goldbelt is the JUNEAU ANCSA urban
corporation).

Same shape as two rules AGENTS.md already carries:
  * *"`core()` FOLDS AWAY THE WORD THAT DISTINGUISHES"*
  * *"A place suffix makes a tribe name a place - 'Boys & Girls Clubs of
    Wichita Falls' is not the Wichita Tribe."*

AND THE CONTROL, WHICH IS WHY THIS IS A DIAGNOSIS AND NOT A COMPLAINT
---------------------------------------------------------------------
**cluster_v3 got the CONSTITUENT BANDS right.** Shivwits Band Corporation,
Kanosh Band of Paiute Indians and Indian Peaks Band of Utah Paiutes are
genuinely the Paiute Indian Tribe of Utah, and they are clustered correctly.
The method is not broken everywhere; it is broken on a PLACE TOKEN.  This
script emits both sets so the next reader can see the difference rather than
take the accusation on trust - which is the same discipline
`docs/BLOCKED_SOURCE_BYPASS_2026-08-26.md` used when it stored
`residual_vs_printed_total` beside `exact_equality`.

WHAT THIS IS NOT
----------------
**It is not a mass retraction and nothing here is applied.**  Every row is a
CANDIDATE for a human ruling, each needs its own answer, and a tier is
inherited from the source row and never assigned by a consumer.  Output is a
review queue.

Reads   data/clean/cedar_identifier_ledger_final.csv   (the PROMOTED ledger)
        data/clean/prime_contracts.csv                 (the PROMOTED table)
Writes  review/cedar_token_cluster_review_2026-08-26.csv    STAGED ONLY

py -3 code/371_stage_cedar_token_cluster_review.py      # 0 network requests
"""
import collections
import csv
import pathlib
import re
import sys

csv.field_size_limit(10 ** 8)

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
REVIEW = ROOT / "review"
TODAY = "2026-08-26"
OUT = REVIEW / f"cedar_token_cluster_review_{TODAY}.csv"

TRIBE = "TRBF-PTTRUT-00"
# The anchor token, and the second name the same pass swept in.  Declared here
# rather than inferred, so the reader can see exactly what was selected on.
TOKENS = re.compile(r"\b(cedar|tikigaq)\b", re.I)
# The genuine constituent bands, used as the CONTROL SET.  These are named in
# the ledger itself and are correct.
BANDS = re.compile(r"\b(shivwits|kanosh|indian peaks|koosharem|cedar band|"
                   r"paiute indian tribe)\b", re.I)

COLS = ["disposition", "identifier_type", "identifier", "legal_business_name",
        "ledger_tribe_id", "ledger_canonical_name", "attribution_method",
        "confidence_tier", "tier_rationale", "ledger_source_file",
        "prime_awardee_names", "prime_rows", "prime_obligations_usd",
        "prime_cities", "competing_ledger_rows_same_name",
        "why_flagged", "court_evidence", "cedar_action", "applied",
        "flagged_date"]

COURT = ("Modoc Nation v. Shah, Court of Appeals for the Tenth Circuit, "
         "No. 24-5135, docketed 2024-11-18, "
         "https://www.courtlistener.com/docket/71537478/modoc-nation-v-shah/ "
         "-- party array names MODOC NATION, AKA Modoc Tribe of Oklahoma and "
         "RED CEDAR ENTERPRISES, INC. as co-parties. CO_PARTY_ALIGNED, which is "
         "a RELATIONSHIP and not a statement of ownership.")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def main():
    ledger = list(csv.DictReader(
        (CLEAN / "cedar_identifier_ledger_final.csv").open(encoding="utf-8-sig")))

    # every ledger row on this tribe, plus every ledger row ANYWHERE that names
    # the same company - that second set is what shows a competing answer
    ours = [r for r in ledger if r["tribe_id"] == TRIBE]
    by_name = collections.defaultdict(list)
    for r in ledger:
        by_name[norm(r.get("legal_business_name"))].append(r)

    flagged, control = [], []
    for r in ours:
        nm = r.get("legal_business_name") or ""
        if BANDS.search(nm):
            control.append(r)
        elif r.get("attribution_method") == "cluster_v3" and TOKENS.search(nm):
            flagged.append(r)

    ids = {r["identifier"] for r in flagged}

    # dollars, from the PROMOTED table.  A consumer reads the promoted table and
    # nothing else (defect class 1).
    agg = collections.defaultdict(
        lambda: {"usd": 0.0, "rows": 0, "names": collections.Counter(),
                 "cities": collections.Counter()})
    unkeyed = collections.Counter()
    with (CLEAN / "prime_contracts.csv").open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("tribe_id") != TRIBE:
                continue
            key = None
            if row.get("awardee_uei") in ids:
                key = row["awardee_uei"]
            elif row.get("cage_code") in ids:
                key = row["cage_code"]
            if key is None:
                # NAME what is not keyed rather than counting it silently
                # (defect class 2c).
                if TOKENS.search(row.get("awardee_name") or ""):
                    unkeyed[row.get("awardee_name") or ""] += 1
                continue
            a = agg[key]
            try:
                a["usd"] += float(row.get("total_obligations") or 0)
            except ValueError:
                pass
            a["rows"] += 1
            a["names"][row.get("awardee_name") or ""] += 1
            a["cities"][f"{row.get('recipient_city_name')}, "
                        f"{row.get('recipient_state_code')}"] += 1

    out = []
    for r in flagged:
        a = agg.get(r["identifier"], {"usd": 0.0, "rows": 0,
                                      "names": collections.Counter(),
                                      "cities": collections.Counter()})
        nm = r.get("legal_business_name") or ""
        competing = [x for x in by_name[norm(nm)] if x["tribe_id"] != TRIBE]
        comp = " ; ".join(f"{x['identifier_type']}:{x['identifier']} -> "
                          f"{x['canonical_name']} ({x['attribution_method']}, "
                          f"tier {x['confidence_tier']})" for x in competing)

        # A THIRD disposition, and it exists because the first draft of this
        # script got one row wrong.  `UEI:R3GMNTDL7356` is `Tikigaq Technology
        # Services` in the LEDGER and `S & T SERVICES, LLC` on all 312 of its
        # prime rows - 30 of them in **CEDAR CITY, UT**, which is the Paiute
        # Indian Tribe of Utah's own seat.  So the Paiute attribution on that
        # identifier may be perfectly correct and the defect is that the two
        # files disagree about WHICH COMPANY the identifier is.  Typing it as a
        # place-token cluster candidate would have been a well-sourced,
        # mislabelled finding - the exact failure `code/218` was written to
        # avoid.  Detect it instead of asserting past it.
        prime_names = [n for n, _ in a["names"].most_common()]
        # Compare against the name on a MAJORITY of the identifier's prime rows,
        # not against ANY of them.  The first version used `any` and let the
        # Tikigaq row through: 311 of its 312 rows say `S & T SERVICES, LLC` and
        # exactly ONE says `Tikigaq Technology Services`, so `any` matched on the
        # single outlier and reported agreement.  A test that a lone row can
        # satisfy is not a test.
        agree_rows = sum(c for p, c in a["names"].items()
                         if norm(nm) in norm(p) or (norm(p) and norm(p) in norm(nm)))
        name_agrees = a["rows"] > 0 and agree_rows * 2 > a["rows"]
        if competing:
            disp = "COURT_RECORD_NAMES_A_DIFFERENT_TRIBE"
        elif prime_names and not name_agrees:
            disp = "LEDGER_AND_PRIME_DISAGREE_ON_THE_COMPANY_NAME"
        else:
            disp = "PLACE_TOKEN_CLUSTER_CANDIDATE"

        out.append({
            "disposition": disp,
            "identifier_type": r["identifier_type"], "identifier": r["identifier"],
            "legal_business_name": nm,
            "ledger_tribe_id": r["tribe_id"],
            "ledger_canonical_name": r["canonical_name"],
            "attribution_method": r["attribution_method"],
            "confidence_tier": r["confidence_tier"],
            "tier_rationale": r.get("tier_rationale", ""),
            "ledger_source_file": r.get("source_file", ""),
            "prime_awardee_names": " ; ".join(n for n, _ in a["names"].most_common(4)),
            "prime_rows": str(a["rows"]),
            "prime_obligations_usd": f"{a['usd']:.2f}",
            "prime_cities": " ; ".join(c for c, _ in a["cities"].most_common(3)),
            "competing_ledger_rows_same_name": comp,
            "why_flagged": (("the ledger calls this identifier "
                             f"`{nm}` and every prime row on it says "
                             f"`{prime_names[0] if prime_names else ''}` - resolve WHICH "
                             "COMPANY it is before ruling on WHOSE it is; the Paiute "
                             "attribution may be correct")
                            if disp == "LEDGER_AND_PRIME_DISAGREE_ON_THE_COMPANY_NAME"
                            else "cluster_v3 (`Algorithmic name clustering, unreviewed`) "
                                 "on a name carrying the token `cedar`/`tikigaq`, against "
                                 "a tribe seated in CEDAR CITY, UTAH"),
            "court_evidence": COURT if competing else "",
            "cedar_action": "HUMAN RULING NEEDED, one per identifier. Nothing applied.",
            "applied": "NO",
            "flagged_date": TODAY,
        })
    out.sort(key=lambda r: -float(r["prime_obligations_usd"]))

    tmp = OUT.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in out:
            w.writerow(r)
    tmp.replace(OUT)

    back = list(csv.DictReader(OUT.open(encoding="utf-8-sig")))   # re-read from disk
    tot = sum(float(r["prime_obligations_usd"]) for r in back)
    rows = sum(int(r["prime_rows"]) for r in back)
    print(f"{len(back)} flagged identifier(s) -> {OUT.name}")
    print(f"  prime obligations booked to {TRIBE} on those identifiers: "
          f"${tot:,.2f} over {rows:,} rows")
    print(f"  CONTROL - constituent-band rows cluster_v3 got RIGHT: {len(control)}")
    for r in control:
        print(f"      {r['identifier_type']}:{r['identifier']:14s} "
              f"{r['legal_business_name'][:44]}")
    print()
    for r in back:
        print(f"  {float(r['prime_obligations_usd'])/1e6:9,.2f}M "
              f"rows={r['prime_rows']:>5s} {r['disposition']:38s} "
              f"{r['legal_business_name'][:40]:40s} {r['prime_cities'][:26]}")
    if unkeyed:
        print("\n  prime rows on this tribe carrying a cedar/tikigaq name that did "
              "NOT key to a flagged identifier (named, not swallowed):")
        for n, c in unkeyed.most_common():
            print(f"      {c:5d} rows  {n}")
    print("\nSTAGED ONLY. No shared table written, no tier assigned, nothing applied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
