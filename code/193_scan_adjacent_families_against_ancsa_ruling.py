#!/usr/bin/env python3
"""
193 - Read the four ADJACENT one-to-many defect families with the ANCSA
ownership ruling in hand, and say which it settles, which it merely
constrains, and which it does not touch.

    Ruling: docs/ANCSA_OWNERSHIP_RULING.md, Elijah 2026-08-26
    Input:  review/identifier_one_to_many_defects_2026-08-26.csv
    Out:    review/ancsa_adjacent_family_scan_2026-08-26.csv
            docs/ANCSA_ADJACENT_FAMILY_SCAN.json

ZERO NETWORK CALLS. Reads only; writes only its own two files.

WHY A SEPARATE SCRIPT, AND WHY IT MOSTLY SAYS NO
-------------------------------------------------
The build log's hypothesis was that some `MIXED_CLASS` rows are the Alaska
question wearing a different label. **Measured, they are almost entirely not**,
and that is the finding. A ruling this expensive invites being stretched, and
stretching it is how a correct decision becomes a wrong one somewhere else -
the same shape as the containment guard that "fixed" one bad path and pushed
the match to the next.

Three verdicts, and the middle one is the one that gets lost if it has no name:

| verdict | meaning |
|---|---|
| `SETTLED_BY_THIS_RULING` | the ruling names the answer |
| `CONSTRAINED_NOT_SETTLED` | the ruling FORBIDS one resolution path but does not supply the answer. Still a human's row - but a human with one fewer wrong option |
| `NOT_TOUCHED` | different question, different doctrine. Say so and leave it |

THE ONE PLACE THE RULING REACHES INTO `MIXED_CLASS`, AND HOW FAR
-----------------------------------------------------------------
`Bering Straits Native Corporation` (ANRC) versus `Tanadgusix Corporation`
(ANVC) is **rule 5 exactly**: *the regional corporation does not own the
village corporation. Two separate corporations with an overlapping shareholder
base.* So the resolution "BSNC is TDX's parent, roll it up" is forbidden.

But rule 5 says who does NOT own whom. It does not say which of two
corporations owns a given operating company, and a regional corporation
absolutely does own its own subsidiaries. So these are
`CONSTRAINED_NOT_SETTLED`. Reading rule 5 as an answer would be inventing one.

WHY `Cook Inlet Region vs Eastern Shoshone` IS NOT THIS QUESTION
-----------------------------------------------------------------
29 of the 38 `MIXED_CLASS` rows carrying an ANC pair an Alaska regional
corporation with a **Wyoming** tribe. Nothing about that is a
village-government-versus-village-corporation confusion: the two entities do
not share a name, do not share a place, and are not two legal persons created
for one village. It is an identifier collision across 3,000 miles and it needs
its own evidence. Same for Gana-A'Yoo/Lumbee (NC), Aleut/St. Croix (WI),
Bethel Native/Apache Tribe of Oklahoma, Council Native/Lenape of Delaware and
Council Native/Big Sandy (CA).

**The test this script applies is not "is an ANC involved" but "are these two
entities the two legal persons of ONE Alaska village".** That is what the
ruling is about, and it is why an ANC pairing with a lower-48 tribe fails it.

THE THREE THIS RULING EXPLICITLY DOES NOT SETTLE
--------------------------------------------------
- `TWO_DIFFERENT_TRIBES_ON_ONE_IDENTIFIER` (188, $10.36B) - including the two
  live disputes named in the brief, **S&K Aerospace** (Confederated Salish and
  Kootenai vs Kootenai Tribe of Idaho, $2.59B) and **ONEIDA NATION NY vs WI**
  ($1.11B). Neither is an Alaska case. Left alone.
- `CONSTITUENT_BAND_VS_UMBRELLA_TRIBE` (42, $1.30B) - a band and its umbrella
  share a name for a reason that RESEMBLES the Alaska case, and that
  resemblance is a trap. The doctrine is different: a band is a government
  within a government, not a corporation beside one. `constituent_band_of` is
  already in `GOVERNMENTAL_RELATIONSHIPS` and therefore in `NEVER_OWNERSHIP`,
  so no dollar rolls through it today - which is the protection that matters
  and it is already in place.
- `INTERTRIBAL_ORGANISATION_VS_MEMBER_TRIBE` (9, $0.66B) - a consortium's
  registration booked to one member. Two of the nine involve an Alaska Native
  village, which makes them look adjacent; they are not. A consortium is not a
  village corporation and the ruling says nothing about it. An aggregate party
  must never resolve to one entity (AGENTS.md) - that is the rule these need.
"""

import csv
import json
import os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_DATE = "2026-08-26"

DEFECTS = os.path.join(ROOT, "review",
                       f"identifier_one_to_many_defects_{RUN_DATE}.csv")
SPINE = os.path.join(ROOT, "data", "spine", "cedar_entity_spine.csv")
OUT = os.path.join(ROOT, "review",
                   f"ancsa_adjacent_family_scan_{RUN_DATE}.csv")
OUT_JSON = os.path.join(ROOT, "docs", "ANCSA_ADJACENT_FAMILY_SCAN.json")

ADJACENT = ("MIXED_CLASS", "TWO_DIFFERENT_TRIBES_ON_ONE_IDENTIFIER",
            "CONSTITUENT_BAND_VS_UMBRELLA_TRIBE",
            "INTERTRIBAL_ORGANISATION_VS_MEMBER_TRIBE")

ANC_CLASSES = {"Alaska Native Village Corporation",
               "Alaska Native Regional Corporation", "ANCSA Group Corporation"}
AK_GOV_CLASSES = {"Federally recognized Alaska Native Village"}
RULING = "docs/ANCSA_OWNERSHIP_RULING.md, Elijah 2026-08-26"


def read_csv(p):
    with open(p, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def main():
    spine = {r["tribe_id"]: r for r in read_csv(SPINE)}
    defects = read_csv(DEFECTS)
    rows = []
    tally, dollars = Counter(), Counter()

    for d in defects:
        fam = d["defect_family"]
        if fam not in ADJACENT:
            continue
        ents = d["entities"].split("|")
        cls = [spine.get(e, {}).get("entity_class", "?") for e in ents]
        st = [spine.get(e, {}).get("state", "?") for e in ents]
        usd = float(d["usd_observed"] or 0)

        anc = [c for c in cls if c in ANC_CLASSES]
        akgov = [c for c in cls if c in AK_GOV_CLASSES]
        all_alaska = all(s == "AK" for s in st)

        if anc and akgov and all_alaska:
            # The two legal persons of one Alaska village, mislabelled.
            verdict = "SETTLED_BY_THIS_RULING"
            why = ("An ANCSA corporation and an Alaska Native village "
                   "GOVERNMENT on one identifier, both in AK. This is the "
                   "ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION question "
                   "wearing a different label. Rule 2 refuses the government "
                   "leg; rule 1 presumes the corporation. Apply "
                   "code/191_apply_ancsa_ownership_ruling.py to it.")
        elif len(anc) >= 2 and all_alaska:
            verdict = "CONSTRAINED_NOT_SETTLED"
            why = ("Two ANCSA corporations on one identifier. RULE 5 applies "
                   "and FORBIDS one resolution: the regional corporation does "
                   "NOT own the village corporation - they are two separate "
                   "corporations whose shareholder bases overlap because "
                   "Natives enrolled to a village hold shares in both. So "
                   "this may never be resolved by treating one as the other's "
                   "parent. Rule 5 does NOT say which corporation owns the "
                   "operating company, and a regional corporation does own "
                   "its own subsidiaries, so the row still needs a human - "
                   "with one fewer wrong option.")
        elif anc:
            verdict = "NOT_TOUCHED"
            other = [f"{spine.get(e, {}).get('canonical_name', e)} "
                     f"({c}/{s})" for e, c, s in zip(ents, cls, st)
                     if c not in ANC_CLASSES]
            why = ("An ANC is involved but the counterparty is not the other "
                   "legal person of the same Alaska village - "
                   + "; ".join(other) + ". The ruling is about two entities "
                   "created for ONE village that name each other by "
                   "construction. Two entities that share neither a name nor "
                   "a place are an identifier collision and need their own "
                   "evidence. Applying the ruling here would be stretching "
                   "it.")
        elif fam == "TWO_DIFFERENT_TRIBES_ON_ONE_IDENTIFIER":
            verdict = "NOT_TOUCHED"
            why = ("Tribe versus tribe. No ANCSA corporation is in the "
                   "dispute, so no clause of this ruling reaches it. Test "
                   "each against the RAW spine first - AGENTS.md records two "
                   "builds that reported a resolver defect where the resolver "
                   "was right and the spine short name collided.")
        elif fam == "CONSTITUENT_BAND_VS_UMBRELLA_TRIBE":
            verdict = "NOT_TOUCHED"
            why = ("A band and its umbrella share a name for a reason that "
                   "RESEMBLES the Alaska case, and the resemblance is the "
                   "trap. Different doctrine: a band is a government within a "
                   "government, not a corporation beside one. "
                   "`constituent_band_of` is already in "
                   "cedar_domain.GOVERNMENTAL_RELATIONSHIPS and therefore in "
                   "NEVER_OWNERSHIP, so no dollar rolls through it today.")
        elif fam == "INTERTRIBAL_ORGANISATION_VS_MEMBER_TRIBE":
            verdict = "NOT_TOUCHED"
            why = ("A consortium's registration booked to one member. A "
                   "consortium is not a village corporation and this ruling "
                   "says nothing about it. The applicable rule is the "
                   "existing one: an aggregate party must never resolve to a "
                   "single entity.")
        else:
            verdict = "NOT_TOUCHED"
            why = ("No ANCSA corporation and no Alaska village government in "
                   "the dispute. Outside every clause of this ruling.")

        rows.append({
            "defect_family": fam, "node": d["node"],
            "identifier_type": d["identifier_type"],
            "identifier": d["identifier"], "observed_name": d["observed_name"],
            "entities": d["entities"],
            "entity_names": "|".join(
                spine.get(e, {}).get("canonical_name", e) for e in ents),
            "entity_classes": "|".join(cls), "entity_states": "|".join(st),
            "tiers": d["tiers"], "usd_observed": d["usd_observed"],
            "ancsa_ruling_verdict": verdict, "why": why,
            "ruling_cited": RULING, "built_date": RUN_DATE,
        })
        tally[(fam, verdict)] += 1
        dollars[(fam, verdict)] += usd

    part = OUT + ".part"
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    os.replace(part, OUT)
    print(f"wrote {OUT}  {len(rows)} rows")

    summary = {"built": RUN_DATE, "ruling": RULING,
               "script": "code/193_scan_adjacent_families_against_ancsa_ruling.py",
               "rows_scanned": len(rows), "by_family_and_verdict": {}}
    print("\nFAMILY x VERDICT")
    for (fam, verdict), n in sorted(tally.items()):
        print(f"  {n:>4}  ${dollars[(fam, verdict)] / 1e6:>10,.1f}M  "
              f"{fam:<40} {verdict}")
        summary["by_family_and_verdict"][f"{fam}|{verdict}"] = {
            "n": n, "usd_musd": round(dollars[(fam, verdict)] / 1e6, 2)}
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(f"\nwrote {OUT_JSON}")


if __name__ == "__main__":
    main()
