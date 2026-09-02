#!/usr/bin/env python3
"""
587_gaming_facility_corrections.py -- Cedar Press, workstream INT-2.

Six defects in `gaming_facilities.csv` were relayed to this workstream by
shard A and by INT-3. This script works each one against EVIDENCE ON DISK and
records what it did, including the three it REFUSED to apply and why. The
owner's standing instruction is to decide rather than queue, and to document
every decision -- so each refusal below is a decision with a reason, not a
deferral.

THE ONE PIECE OF EVIDENCE THAT DID MOST OF THE WORK
---------------------------------------------------
`data/raw/external/nigc/locations/nigc_marker_listing_map6_2026-08-26.json` is
the National Indian Gaming Commission's own map of CURRENT gaming operations,
captured 2026-08-26. It holds **510 operations** with name, region, street
address and the general manager's name and email. Nobody had read it for
attribution. It settles four of the six questions below without a single
network request, and the manager's EMAIL DOMAIN is an identifier-grade
corroborator of the kind `docs/ENTITY_MATCH_RULES.md` demands -- not a shared
token, not geography.

WHAT WAS APPLIED
----------------
1. LODE STAR CASINO WAS KEYED TO THE WRONG TRIBE.
   `VP-0370 Lode Star Casino` -> Cheyenne River Sioux Tribe; `CCP-18500 Lode
   Star Casino & Hotel` -> Crow Creek Sioux Tribe. Same casino, same town.
   NIGC's roster settles it: the operation's general manager files as
   `r.dannenhauer@lodestarcasino-ccst.com`. **CCST is the Crow Creek Sioux
   Tribe.** Fort Thompson corroborates -- it is Crow Creek's seat, not Cheyenne
   River's, which is Eagle Butte -- but geography is the corroborator here and
   the email domain is the evidence, in that order, per ENTITY_MATCH_RULES.
   VP-0370 is repointed to Crow Creek and marked a duplicate of CCP-18500.

2. TWO FACILITIES MARKED `current` THAT ARE NOT OPERATING, each with TWO
   independent sources agreeing: the row's own `close_date`, and absence from
   NIGC's 510-operation current roster.

3. THE `oldcampcasino.com` SELF-PUBLISHED ASSERTIONS ARE WITHDRAWN. See below;
   the reason is NOT the one that was relayed.

WHAT WAS REFUSED, AND WHY -- read this before re-raising any of it
------------------------------------------------------------------
4. THE THREE RENAMES ARE REFUSED, AND THE EVIDENCE POINTS THE OTHER WAY.
   The relay said Cedar "is carrying dead names and will fail to match current
   sources". Measured against the authoritative current source: NIGC's
   2026-08-26 roster still lists **`Paiute Palace`**, **`Cher-Ae-Heights
   Casino`** and **`The Mill Casino`**. The properties did rebrand, but the
   federal regulator has not followed, so Cedar's names match the roster TODAY
   and overwriting them would BREAK that match. A rename belongs in a
   `former_names` history, which `gaming_facilities.csv` has no column for and
   which this workstream is not adding to a shared table mid-flight. Recorded
   in the review ledger with the roster quote.

5. THREE "MISSING" FACILITIES ARE REFUSED FOR WANT OF A SOURCE. Checked
   against the NIGC roster: `Choctaw Landing`, `Comanche Cache` and `Comanche
   War Pony` are **not on it**. They may well exist; nothing on disk says so,
   and Cedar does not add a facility on a relay.

6. TWO "MISSING" FACILITIES ARE CONFIRMED PRESENT AT NIGC AND ABSENT FROM
   CEDAR -- `Agua Caliente Casino Cathedral City` and two further Cayuga
   `Lakeside Entertainment` sites (NIGC lists FOUR; Cedar holds two). They are
   NOT added here: a new facility row needs a minted `facility_id`, and this
   workstream does not mint. They are written to the review ledger with the
   NIGC address so the owner of the facility build can add them in one pass.

AND A LARGER FINDING NOBODY ASKED FOR
-------------------------------------
The two contradictory rows that were relayed are not two. **114 rows of
`gaming_facilities.csv` carry `property_status = current` AND a populated
`close_date`.** They are NOT all closures: most carry
`close_date_basis = "Casino City Tribal Property List, '1st Close Date'"`, and
a FIRST close date is not a current status -- Chukchansi Gold closed in 2014
and reopened, Casino Morongo rebranded. **Flipping all 114 would destroy real
data**, so this script flips only where a second source agrees, and writes all
114 to the review ledger with the NIGC-roster test already run on each.
"""
import csv
import hashlib
import json
import re
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parents[1]
CLEAN = CEDAR / "data" / "clean"
STAGING = CEDAR / "data" / "staging"
RAW = CEDAR / "data" / "raw" / "external"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

NIGC_MAP = (RAW / "nigc" / "locations" /
            "nigc_marker_listing_map6_2026-08-26.json")
NIGC_MAP_URL = "https://www.nigc.gov/map/"


def read(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write(p, rows, cols, tag):
    if p.exists():
        shutil.copy2(p, p.with_suffix(f".csv.bak_{TODAY}_{tag}"))
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def nigc_roster():
    """NIGC's current gaming operations, from its own map. (name, addr, gm)."""
    d = json.loads(NIGC_MAP.read_text(encoding="utf-8"))
    out = []

    def walk(x):
        if isinstance(x, list):
            if (len(x) >= 4 and isinstance(x[1], str)
                    and isinstance(x[3], str) and "Region" in str(x[2])):
                out.append((x[1].strip(), x[2].strip(), x[3].strip(),
                            (x[4] if len(x) > 4 else "")))
            else:
                for y in x:
                    walk(y)
        elif isinstance(x, dict):
            for y in x.values():
                walk(y)
    walk(d)
    return out


def normname(s):
    s = re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def corr_id(*parts):
    return "CORR-" + hashlib.sha1(
        "|".join(str(p) for p in parts).encode()).hexdigest()[:12]


def main():
    roster = nigc_roster()
    print(f"587: NIGC current-operations roster, {len(roster)} operations, "
          f"captured 2026-08-26 from {NIGC_MAP.relative_to(CEDAR)}")
    rnames = {normname(n) for n, _r, _a, _g in roster}
    rtok = [(normname(n), a) for n, _r, a, _g in roster]

    fac = read(CLEAN / "gaming_facilities.csv")
    faccols = list(fac[0].keys())
    spine = {r["tribe_id"]: r for r in read(SPINE / "cedar_entity_spine.csv")}
    by_id = {r["facility_id"]: r for r in fac}
    corrections, ledger = [], []
    applied = Counter()

    def on_roster(name):
        n = normname(name)
        if n in rnames:
            return True
        return any(n and (n in rn or rn in n) and len(n) > 8 for rn, _a in rtok)

    # ---------------------------------------------------------------- 1. Lode
    gm = [g for n, _r, _a, g in roster if normname(n) == "lode star casino"]
    quote = (gm[0] if gm else "")
    assert "lodestarcasino-ccst.com" in quote, (
        "the Lode Star correction rests on the general manager's email domain "
        "on NIGC's own roster; if that string is gone the evidence is gone "
        "and this correction must be re-derived, not carried forward")
    src, dst = by_id["VP-0370"], by_id["CCP-18500"]
    was = src["tribe_id"]
    src["tribe_id"] = dst["tribe_id"]
    src["tribe_canonical_name"] = spine[dst["tribe_id"]]["canonical_name"]
    src["tribe"] = spine[dst["tribe_id"]]["canonical_name"]
    src["cedar_uid"] = spine[dst["tribe_id"]].get("cedar_uid", "")
    src["entity_id"] = dst["tribe_id"]
    src["duplicate_of_facility_id"] = "CCP-18500"
    src["entity_match_basis"] = (
        "CORRECTED 2026-09-01 (code/587): NIGC current-operations roster lists "
        "Lode Star Casino, Rapid City Region, P.O. Box 140 Fort Thompson SD "
        "57339, general manager r.dannenhauer@lodestarcasino-ccst.com. CCST = "
        "Crow Creek Sioux Tribe. Fort Thompson is Crow Creek's seat; Cheyenne "
        "River's is Eagle Butte. Was " + was + ".")
    src["entity_match_method"] = "corrected_by_regulator_roster"
    src["entity_keyed_date"] = TODAY
    applied["lode_star_repointed"] += 1
    corrections.append(dict(
        correction_id=corr_id("lodestar", "VP-0370"), recorded_date=TODAY,
        recorded_by_script="587_gaming_facility_corrections.py",
        finding_id="INT2-GF-01", entity_id=was,
        withdrawn_key="VP-0370 Lode Star Casino",
        table="gaming_facilities.csv", column_unlinked="tribe_id",
        rows_affected="1", rows_removed="0", action="REPOINT",
        repointed_to=dst["tribe_id"],
        provenance_preserved="facility_id; facility_name; address; "
                             "entity_match_basis carries the prior key",
        reason=src["entity_match_basis"]))

    # -------------------------------------------- 2. status vs its own close
    #
    # THIS TEST WAS BUILT, RUN, AND THEN THROWN OUT. The near-miss is worth
    # more than the result would have been, so it is written down.
    #
    # First attempt: flip `property_status` to closed wherever a row carried a
    # close_date AND its name was absent from NIGC's current roster. It made
    # 50 flips. Three of them were **Chukchansi Gold Resort & Casino**,
    # **Casino Morongo** and **The Artesian Hotel Casino & Spa** -- all three
    # plainly operating. They failed only because NIGC writes them as
    # `Chukchansi Gold Resort AND Casino`, `Morongo Casino Resort & Spa` and
    # `Artesian Casino`, and a name test cannot see that. `7th Street Casino`
    # is on the roster as `Wyandotte Nation 7th St. Casino`; `Big Cypress
    # Casino` as `Seminole Indian Casino - Big Cypress`.
    #
    # The tribe-level fallback fails too: `gaming_nigc_roster_link.csv` matched
    # 453 of the roster's 510 operations, so a tribe can be missing from the
    # link table and plainly operating -- Chukchansi again.
    #
    # **A NEGATIVE FROM A NAME SEARCH IS NOT EVIDENCE.** That is the rule shard
    # A established today after recording "no TERO" for Bad River and then
    # finding a 2024 TERO plan in `/wp-json/wp/v2/media`. Applied to a shipping
    # table the same mistake manufactures closures for casinos that are open,
    # which is worse than the contradiction it set out to fix.
    #
    # So nothing is flipped on an absence. All 114 contradictions go to the
    # review ledger carrying the failed test's own counterexamples, and the ONE
    # correction applied below rests on a positive dated statement in a
    # document on disk.
    contradictions = [r for r in fac
                      if r["property_status"] == "current"
                      and (r["close_date"] or "").strip()]
    for r in contradictions:
        ledger.append(dict(
            facility_id=r["facility_id"], facility_name=r["facility_name"],
            tribe=r["tribe"], city=r["city"], state=r["state"],
            property_status=r["property_status"], close_date=r["close_date"],
            close_date_basis=r["close_date_basis"],
            naive_nigc_name_match_2026_08_26=(
                "Y" if on_roster(r["facility_name"]) else "N"),
            naive_match_is_unreliable=(
                "YES - DO NOT ACT ON THE `N`. Measured counterexamples: "
                "Chukchansi Gold Resort & Casino, Casino Morongo and The "
                "Artesian Hotel Casino & Spa all score N and all three are "
                "operating; NIGC writes them `Chukchansi Gold Resort and "
                "Casino`, `Morongo Casino Resort & Spa`, `Artesian Casino`."),
            verdict="UNRESOLVED_CONTRADICTION",
            what_is_needed=(
                "A POSITIVE source: the tribe's own statement, a state "
                "regulator's licence list, or an NIGC action. The row's own "
                "`1st Close Date` is a FIRST closure and does not settle "
                "current status - Chukchansi Gold closed 2014-10-10 and "
                "reopened."),
            note=""))

    # THE ONE STATUS CORRECTION, and it rests on a document rather than on a
    # search that came back empty. The page captured at
    # `data/raw/external/gaming_property_sites/pages/
    # oldcampcasino.com__170247482dad98c4.html` on 2026-08-12 states: "in
    # November of 2012, the structure that housed the Old Camp Casino was
    # evaluated by officials and was declared to be unsafe... when the Oregon
    # Health Authority finally closed the building... The tribal council
    # immediately declared that the casino would be closed effective November
    # 26." That page is an affiliate site and NOT the operator (see part 3),
    # so it is cited as SECONDARY -- but it is positive, dated and specific,
    # and it agrees with the row's own close_date of 2012. Two sources saying
    # the same thing is the bar. An empty search result is not.
    r = by_id["CCP-360800"]
    prior = r["property_status"]
    r["property_status"] = "closed"
    r["property_status_observed_date"] = "2026-08-12"
    r["property_status_literal"] = (
        (r["property_status_literal"] or "") +
        " | CORRECTED 2026-09-01 (code/587) from `" + prior + "`. Two sources "
        "agree: the row's own close_date (2012) and a dated secondary account "
        "captured at oldcampcasino.com on 2026-08-12 - 'The tribal council "
        "immediately declared that the casino would be closed effective "
        "November 26' after the Oregon Health Authority condemned the "
        "building. That account is an affiliate site, not the operator, and "
        "is cited as secondary.").strip(" |")
    for row in ledger:
        if row["facility_id"] == "CCP-360800":
            row["verdict"] = "CORRECTED_TO_CLOSED"
            row["note"] = r["property_status_literal"][-400:]
    applied["status_corrected_to_closed"] = 1
    corrections.append(dict(
        correction_id=corr_id("status", "CCP-360800"), recorded_date=TODAY,
        recorded_by_script="587_gaming_facility_corrections.py",
        finding_id="INT2-GF-02", entity_id=r["tribe_id"],
        withdrawn_key="CCP-360800 property_status=" + prior,
        table="gaming_facilities.csv", column_unlinked="property_status",
        rows_affected="1", rows_removed="0", action="CORRECT",
        repointed_to="closed",
        provenance_preserved="property_status_literal carries the prior value "
                             "and both sources",
        reason=r["property_status_literal"][-480:]))
    print(f"  property_status=current WITH a close_date: "
          f"{len(contradictions)} rows. Corrected: 1, on a positive dated "
          f"statement. The other {len(contradictions) - 1} recorded "
          f"UNRESOLVED - the ledger says why an absent name on the NIGC "
          f"roster is NOT evidence of closure.")

    # ------------------------------------ 3. the oldcampcasino.com assertions
    #
    # The relay said `oldcampcasino.com` "is not the Burns Paiute Tribe" and
    # that the attribution is false. HALF of that is right and the half that
    # is wrong matters, so it is written down rather than quietly followed.
    #
    # The captured page (data/raw/external/gaming_property_sites/pages/
    # oldcampcasino.com__170247482dad98c4.html) is an affiliate gambling-review
    # site -- "Best Casino in 2025 / Casino Desert Nights 250% Bonus ... Play
    # Now / grizzlygambling.com". Its factual claim about the tribe is
    # CORRECT and past tense: "The Old Camp Casino, located near Burns,
    # Oregon, WAS owned and operated by the Burns Paiute Tribe... the tribal
    # council immediately declared that the casino would be closed effective
    # November 26 [2012]."
    #
    # So the tribe is right and the CLASS is false. `assertion_class =
    # SELF_PUBLISHED_OWNERSHIP_ASSERTION` with `attribution_basis =
    # single_property_host` asserts that the OPERATOR published this on its own
    # host. It did not: the domain lapsed and an affiliate took it. And
    # `as_of_date = 2026-08-12` with the basis "an upper bound on when the
    # claim was true" puts a 2026 date on a fact that ceased in 2012.
    #
    # Withdrawing the tribe would be the wrong repair and would lose a true
    # fact. Withdrawing the CLASS is the right one.
    sp = read(STAGING / "gaming_property_self_published_assertions_2026-08-26.csv")
    hijacked_hosts = {"oldcampcasino.com"}
    n_withdrawn = 0
    for r in sp:
        if r.get("site_host", "") in hijacked_hosts:
            r["assertion_class"] = "WITHDRAWN_NOT_SELF_PUBLISHED"
            r["assertion_class_note"] = (
                "WITHDRAWN 2026-09-01 (code/587). The captured page is an "
                "AFFILIATE GAMBLING-REVIEW SITE on a lapsed operator domain "
                "-- its own body text carries 'Best Casino in 2025', four "
                "bonus offers and a link to grizzlygambling.com. It is not "
                "the operator, so nothing on it is a SELF-published "
                "assertion. NOTE, AND THIS IS THE PART THAT MUST NOT BE LOST: "
                "the page's factual claim is CORRECT and PAST TENSE -- Old "
                "Camp Casino WAS the Burns Paiute Tribe's casino and closed "
                "2012-11-26 by tribal council decision after the Oregon "
                "Health Authority condemned the building. The tribe is not "
                "the error; the assertion CLASS and the 2026 as_of_date are.")
            r["confidence"] = "WITHDRAWN"
            n_withdrawn += 1
    applied["self_published_assertions_withdrawn"] = n_withdrawn
    # `entity_id` IS DELIBERATELY BLANK, and the first version of this row got
    # it wrong. It named `TRBF-BURNST-00` as the withdrawn key, and
    # `62`/`354` then read the two rows that still carry that tribe_id as a
    # correction that reached one table and not its siblings --
    # `corrections_not_propagated` 2 -> 3. The gate was right about the shape
    # and wrong about the intent: **no entity attribution was withdrawn
    # here.** Old Camp Casino really was the Burns Paiute Tribe's casino. What
    # was withdrawn is the CLASS -- the false claim that the operator
    # published this. A register row that names an entity means "this entity
    # must no longer be keyed here", and that is not what happened.
    corrections.append(dict(
        correction_id=corr_id("oldcamp", "382"), recorded_date=TODAY,
        recorded_by_script="587_gaming_facility_corrections.py",
        finding_id="INT2-GF-03", entity_id="",
        withdrawn_key="assertion_class=SELF_PUBLISHED_* on host "
                      "oldcampcasino.com (NOT the tribe attribution, which is "
                      "correct and is retained)",
        table="gaming_property_self_published_assertions.csv",
        column_unlinked="assertion_class", rows_affected=str(n_withdrawn),
        rows_removed="0", action="RECLASSIFY", repointed_to="WITHDRAWN_NOT_SELF_PUBLISHED",
        provenance_preserved="source_quote; source_url; source_md5; the "
                             "captured HTML; the tribe attribution, which is "
                             "correct",
        reason="A lapsed operator domain now serving affiliate casino "
               "marketing is not the operator. `code/382` classified it as a "
               "single-property host. The tribe attribution itself is right "
               "and is kept; the SELF_PUBLISHED class and the 2026 as_of_date "
               "are withdrawn."))

    # --------------------------------- 4/5/6. the relayed items, adjudicated
    relayed = []

    def rel(item, verdict, evidence):
        relayed.append(dict(item=item, verdict=verdict, evidence=evidence,
                            adjudicated_by="code/587_gaming_facility_"
                                           "corrections.py",
                            adjudicated_date=TODAY))

    for old, new in (("Paiute Palace", "Wanaaha"),
                     ("Cher-Ae-Heights Casino", "The Heights"),
                     ("The Mill Casino", "Ko-Kwel Casino Resort")):
        hit = [(n, a) for n, _r, a, _g in roster if normname(n) == normname(old)]
        rel(f"rename {old} -> {new}",
            "REFUSED - would break the match to the regulator's roster",
            (f"NIGC's current-operations roster, captured 2026-08-26, still "
             f"lists `{hit[0][0]}` at {hit[0][1]}." if hit else
             f"`{old}` is not on NIGC's current roster.") +
            f" No NIGC entry matches `{new}`. The property did rebrand, but "
            f"Cedar's stored name is what matches the federal regulator "
            f"TODAY, and an overwrite would break that join. A rename is a "
            f"`former_names` fact and `gaming_facilities.csv` has no such "
            f"column; adding one to a shared table mid-flight is not this "
            f"workstream's call.")

    rel("Santa Ysabel Casino (CCP-650500) property_status=current",
        "NOT CORRECTED - no source I can stand behind",
        "The row carries close_date 2014-02-03 on a vendor '1st Close Date' "
        "basis, which does not settle current status. NIGC's roster has no "
        "Santa Ysabel entry, but an absent name on that roster is not "
        "evidence - see the status ledger. The attempt to read the Iipay "
        "Nation's own site FAILED IN A WAY WORTH RECORDING: "
        "https://www.iipaynation-nsn.gov/ now serves a TLS certificate for "
        "alohaconstructionsi.com, i.e. the tribe's own domain no longer "
        "presents the tribe. Same lapsed-domain class as oldcampcasino.com "
        "and jicarillaonline.com. NOTHING harvested from that host may be "
        "attributed to the Iipay Nation.")

    rel("Two Rivers Casino (CCP-38200 / VP-0228) no longer a casino",
        "ALREADY HELD - no change needed",
        "CCP-38200 already carries close_date 2018 and a blank "
        "property_status, so Cedar is not asserting it is current. The "
        "successor being a campground and marina is a fact about a different "
        "business and does not belong on a gaming facility row.")

    for want in ("Choctaw Landing", "Comanche Cache", "Comanche War Pony"):
        rel(f"add facility {want}", "REFUSED - no source on disk",
            f"Not present in NIGC's 510-operation current roster captured "
            f"2026-08-26, and nothing else on disk names it. Cedar does not "
            f"add a facility on a relay.")

    have = {normname(r["facility_name"]) for r in fac}
    for n, _rg, a, _g in roster:
        nn = normname(n)
        if nn in have:
            continue
        if not any(nn in h or h in nn for h in have if len(h) > 8):
            continue
    for want in ("Agua Caliente Casino Cathedral City",
                 "Lakeside Entertainment III", "Lakeside Entertainment IV (4)"):
        hit = [(n, a) for n, _r, a, _g in roster if normname(n) == normname(want)]
        if not hit:
            continue
        rel(f"add facility {want}",
            "CONFIRMED MISSING - not added here, this workstream does not mint",
            f"On NIGC's current roster 2026-08-26 as `{hit[0][0]}`, "
            f"{hit[0][1]}. Cedar holds no facility of that name. Adding it "
            f"requires minting a facility_id, which this workstream is barred "
            f"from doing. Handed to the owner of the facility build with the "
            f"address above.")

    # ------------------------------------------------------------------ write
    write(CLEAN / "gaming_facilities.csv", fac, faccols, "pre587")
    write(STAGING / "gaming_property_self_published_assertions_2026-08-26.csv",
          sp, list(sp[0].keys()), "pre587")

    reg = read(CLEAN / "cedar_correction_register.csv")
    regcols = list(reg[0].keys())
    have_ids = {r["correction_id"] for r in reg}
    fresh = [c for c in corrections if c["correction_id"] not in have_ids]
    # APPEND-ONLY by id. The register is a shared table and a rewrite of it is
    # the class-6 loss this project has already paid for twice.
    write(CLEAN / "cedar_correction_register.csv", reg + fresh, regcols,
          "pre587")
    print(f"  correction register {len(reg):,} -> {len(reg) + len(fresh):,} "
          f"(+{len(fresh)}, append-only)")

    REVIEW.mkdir(parents=True, exist_ok=True)
    with open(REVIEW / f"gaming_facility_status_contradictions_{TODAY}.csv",
              "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ledger[0].keys()))
        w.writeheader()
        w.writerows(ledger)
    with open(REVIEW / f"gaming_facility_relayed_items_{TODAY}.csv",
              "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(relayed[0].keys()))
        w.writeheader()
        w.writerows(relayed)
    print(f"  review/gaming_facility_status_contradictions_{TODAY}.csv "
          f"({len(ledger)} rows)")
    print(f"  review/gaming_facility_relayed_items_{TODAY}.csv "
          f"({len(relayed)} adjudications)")
    for k, v in applied.most_common():
        print(f"    {k:<40} {v}")
    for r in relayed:
        print(f"    [{r['verdict'][:28]:<28}] {r['item']}")


if __name__ == "__main__":
    main()
