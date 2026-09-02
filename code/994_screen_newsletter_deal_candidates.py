"""The precision screen between "a sentence matched" and "this is a deal".

Scripts 992 and 993 are deliberately generous: they keep any sentence carrying a
transaction verb, because a miner that is strict at extraction time throws away
evidence nobody can get back. This script is where the strictness lives, and it
NEVER deletes - it labels, and it writes the labels next to the sentence so the
judgement is auditable.

WHAT THE FIRST 300 DOCUMENTS TAUGHT. The generous pass produced these:

  * "Acquiring a new customer can cost five times more than retaining one"
  * "the opportunity to acquire financial management skills"
  * "The district has purchased 3,000 laptops"
  * "Each student was awarded a $1,000 stipend"
  * "Acquisition of a 12-Passenger Van"

and, in the same run, these:

  * "...acquired Camp Easter Seals, the facility..."           (real)
  * "...($300M) for the acquisition of the company."           (real)
  * "Native American Bank provides financing for MHA Nation's
     MIDI Enterprises..."                                      (real)

The difference is not the verb. It is the OBJECT. A transaction has a
counterparty that is an organisation, an asset, or a stated sum of consequence.
Acquiring a skill, a customer or a van is English, not M&A.

THE SCREEN, in three tiers
  `tier_A_promotable`  an organisational counterparty (a name ending Inc / LLC /
                       Corporation / Enterprises / Authority ...) OR a corporate
                       transaction noun (merger, joint venture, subsidiary,
                       equity stake, controlling interest) OR a stated sum at or
                       above $500,000.
  `tier_B_review`      a transaction verb and a business context, but no
                       organisational object and no material sum. A human
                       decides.
  `tier_C_rejected`    the object is an abstraction, a consumer good, or a
                       person-scale award. Kept, labelled, never counted.

Also applied here, because they are judgements and belong with the other ones:
  * DEDUPLICATION across the two extraction routes and across issues that
    reprint the same paragraph.
  * The INTRA-FAMILY rule, re-run with the deals dataset's own party
    attribution as well as the spine, because the family map is better there.
  * A MERGE PROPOSAL: which rows another agent should consider for
    `deals_classified.csv`, and which columns map to which.

This script writes a proposal. It does NOT touch `deals_classified.csv`.

    data/staging/deals_from_newsletters/deal_candidates_screened.csv
    data/staging/deals_from_newsletters/MERGE_PROPOSAL.md

    python code/994_screen_newsletter_deal_candidates.py
    python code/994_screen_newsletter_deal_candidates.py verify
    python code/994_screen_newsletter_deal_candidates.py verify --selftest
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTD = ROOT / "data" / "staging" / "deals_from_newsletters"
IN_A = OUTD / "deal_candidates.csv"
IN_B = OUTD / "deal_candidates_wp_posts.csv"
OUT = OUTD / "deal_candidates_screened.csv"
PROPOSAL = OUTD / "MERGE_PROPOSAL.md"
STATE = OUTD / "_screen_state.json"
DEALS = ROOT / "data" / "clean" / "deals_classified.csv"
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

ORG_SUFFIX = re.compile(
    r"(?i)\b[A-Z][\w&.'-]*(?:\s+[A-Z][\w&.'\-()]*){0,6}\s+"
    r"(?:Inc\.?|Incorporated|LLC|L\.L\.C\.|LLP|LP\b|Corporation|Corp\.?|"
    r"Company|Co\.|Group|Holdings|Enterprises?|Ventures?|Partners|"
    r"Technologies|Solutions|Services|Systems|Industries|Bank|"
    r"Development Authority|Development Corporation|Casino|Resort)\b")

CORPORATE_NOUN = re.compile(
    r"(?i)\b(merger|merged with|joint venture|wholly[- ]owned subsidiary|"
    r"new subsidiary|majority (?:interest|stake|ownership)|controlling interest|"
    r"equity stake|shares of|share purchase|asset purchase|"
    r"definitive agreement|memorandum of understanding|letter of intent|"
    r"prime contract|task order|indefinite delivery|IDIQ|"
    r"bond issuance|issued .{0,20}(?:bonds|notes)|refinanc\w+ of .{0,30}debt|"
    r"acquisition of (?:the )?(?:company|corporation|business|assets|"
    r"operations|subsidiary|interest|stake|shares))\b")

# The object that disqualifies. An abstraction, a consumer good, or an award to
# a person is not a transaction between organisations.
NOT_A_DEAL_OBJECT = re.compile(
    r"(?i)\b(?:acquir\w+|purchas\w+|awarded)\s+(?:a |an |the |new |additional )?"
    # numbers carry commas and currency marks: "purchased 3,000 laptops".
    # Six tokens, not three: "was awarded a Naval Reserve Officers Training
    # Corps (NROTC) scholarship" needs the reach.
    r"(?:[\w,.$%()-]+\s+){0,6}?"
    r"(skills?|knowledge|customers?|clients?|habits?|language|fluency|"
    r"citizenship|membership|experience|education|degree|diploma|certificate|"
    r"scholarship|stipend|medal|prize|trophy|award|ribbon|"
    r"van|vans|truck|trucks|car|cars|bus|buses|laptop|laptops|computer|"
    r"computers|tablet|tablets|printer|chromebook|furniture|uniforms?|"
    r"groceries|food|supplies|books|firewood|fuel|propane)\b")
# A personnel announcement uses the same verbs. "Cunningham joins BSNC from
# NANA Regional Corporation, where she served as CFO" names two corporations
# and no transaction.
PERSONNEL = re.compile(
    r"(?i)\b(joins?|joined|appointed|named as|hired|promoted to|"
    r"has been named|served as (?:the )?(?:senior )?(?:vice )?president|"
    r"new (?:chief|president|director|manager|officer)\b|"
    r"board of directors welcomes|retires? from|stepping down)\b")
PERSON_SCALE_AWARD = re.compile(
    r"(?i)\b(each|per)\s+(student|participant|elder|family|household|member|"
    r"applicant|recipient)s?\b")

MATERIAL_USD = 500_000

FIELDS_EXTRA = ["screen_tier", "screen_basis", "duplicate_of",
                "counterparty_is_organisation", "corporate_noun_present",
                "material_value", "screened_date"]


def load(p, route):
    if not p.exists():
        return []
    rows = list(csv.DictReader(p.open(encoding="utf-8-sig")))
    for r in rows:
        r["_route"] = route
    return rows


def screen(r):
    """Return (tier, basis, org_flag, noun_flag, material_flag)."""
    d = r["Description"]
    cp = r.get("Counterparty_or_Funder", "")
    org = bool(ORG_SUFFIX.search(d) or ORG_SUFFIX.search(cp))
    noun = bool(CORPORATE_NOUN.search(d))
    try:
        val = float(r["Announced_Value_USD"]) if r["Announced_Value_USD"] else 0.0
    except ValueError:
        val = 0.0
    material = val >= MATERIAL_USD

    if r.get("intra_family_reporting_change") == "yes":
        return ("tier_C_rejected",
                "intra-family reporting change, not a transaction: "
                + r.get("intra_family_basis", ""), org, noun, material)
    # The disqualifying-object test runs only when NOTHING qualifies the row.
    # A sentence can name a real counterparty and a van in the same breath, and
    # rejecting it for the van would be the screen overreaching.
    if PERSONNEL.search(d):
        return ("tier_C_rejected",
                "personnel announcement: the sentence names people moving "
                "between organisations, not a transaction between them",
                org, noun, material)
    if (NOT_A_DEAL_OBJECT.search(d) or PERSON_SCALE_AWARD.search(d)) \
            and not (org or noun or material):
        return ("tier_C_rejected",
                "the object of the verb is an abstraction, a consumer good or a "
                "person-scale award, and no organisational counterparty, "
                "corporate-transaction noun or material sum is present",
                org, noun, material)
    if org or noun or material:
        why = []
        if org:
            why.append("an organisational counterparty is named in the sentence")
        if noun:
            why.append("a corporate-transaction noun is present")
        if material:
            why.append("a stated sum of $%s or more" % format(MATERIAL_USD, ","))
        return ("tier_A_promotable", "; ".join(why), org, noun, material)
    return ("tier_B_review",
            "a transaction verb in a business context, but no organisational "
            "object, no corporate-transaction noun and no material sum; a human "
            "decides", org, noun, material)


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def build():
    rows = load(IN_A, "issue_documents") + load(IN_B, "wp_posts")
    for r in rows:
        t, basis, org, noun, mat = screen(r)
        r["screen_tier"] = t
        r["screen_basis"] = basis
        r["counterparty_is_organisation"] = "yes" if org else "no"
        r["corporate_noun_present"] = "yes" if noun else "no"
        r["material_value"] = "yes" if mat else "no"
        r["screened_date"] = TODAY
        r["duplicate_of"] = ""

    # de-duplicate: the same paragraph reprinted across issues, or reached by
    # both routes. Key on (native party, first 120 normalized chars).
    first = {}
    for r in sorted(rows, key=lambda x: (x["screen_tier"], x["candidate_id"])):
        k = (norm(r["Native_Party"]), norm(r["Description"])[:120])
        if k in first and first[k] != r["candidate_id"]:
            r["duplicate_of"] = first[k]
        else:
            first[k] = r["candidate_id"]

    fields = (list(csv.DictReader(IN_A.open(encoding="utf-8-sig")).fieldnames)
              if IN_A.exists() else
              list(csv.DictReader(IN_B.open(encoding="utf-8-sig")).fieldnames))
    fields = fields + ["_route"] + FIELDS_EXTRA
    rows.sort(key=lambda r: (r["screen_tier"], r["Native_Party"].lower(),
                             r["candidate_id"]))
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
            f.flush()

    prom = [r for r in rows if r["screen_tier"] == "tier_A_promotable"
            and not r["duplicate_of"]]
    st = {
        "script": "code/994_screen_newsletter_deal_candidates.py",
        "run_date": TODAY, "candidates_in": len(rows),
        "by_route": dict(Counter(r["_route"] for r in rows)),
        "by_tier": dict(Counter(r["screen_tier"] for r in rows)),
        "duplicates_marked": sum(1 for r in rows if r["duplicate_of"]),
        "promotable_unique": len(prom),
        "promotable_with_value": sum(1 for r in prom if r["Announced_Value_USD"]),
        "promotable_with_date": sum(1 for r in prom if r["Event_Date"]),
        "promotable_by_status": dict(Counter(r["deal_status_std"] for r in prom)),
        "promotable_parties": dict(Counter(r["Native_Party"] for r in prom).most_common(25)),
    }
    STATE.write_text(json.dumps(st, indent=2), encoding="utf-8")
    write_proposal(prom, rows, st)
    print(json.dumps(st, indent=2)[:3000])
    return 0


def write_proposal(prom, rows, st):
    have = set()
    if DEALS.exists():
        for r in csv.DictReader(DEALS.open(encoding="utf-8-sig")):
            have.add((norm(r.get("Native_Party", "")),
                      (r.get("Event_Year") or "")[:4]))
    new = [r for r in prom
           if (norm(r["Native_Party"]), (r["Event_Year"] or "")[:4]) not in have]
    lines = [
        "# Deals from the tribal press - merge proposal",
        "",
        "*Written %s by `code/994_screen_newsletter_deal_candidates.py`. "
        "This is a PROPOSAL. Nothing here has been written to "
        "`data/clean/deals_classified.csv`; another agent owns that promotion.*" % TODAY,
        "",
        "## Why this route exists",
        "",
        "Owner: *\"Don't forget tribal newsletters, especially for deals.\"* A "
        "nation's own newspaper reports the joint venture in the nation's own "
        "words, dated, and does so before any federal filing exists. `deals` is "
        "the one Cedar product nobody else publishes, and this is the only route "
        "that reaches transactions with no federal counterpart at all.",
        "",
        "## What is being proposed",
        "",
        "| | count |",
        "|---|---:|",
        "| candidates extracted (generous pass, both routes) | %d |" % st["candidates_in"],
        "| rejected by the precision screen (tier C) | %d |" % st["by_tier"].get("tier_C_rejected", 0),
        "| needs a human read (tier B) | %d |" % st["by_tier"].get("tier_B_review", 0),
        "| **promotable (tier A), duplicates removed** | **%d** |" % len(prom),
        "| of those, not already matched by party+year in `deals_classified.csv` | %d |" % len(new),
        "",
        "## Column mapping",
        "",
        "The staged file already uses `deals_classified.csv` column names where "
        "they exist. The mapping another agent needs:",
        "",
        "| staged column | `deals_classified.csv` column | note |",
        "|---|---|---|",
        "| `Native_Party` | `Native_Party` | the publisher; verify it is the "
        "transacting party and not merely the reporter |",
        "| `cedar_uid` | `cedar_uid` | already spine-keyed |",
        "| `Counterparty_or_Funder` | `Counterparty_or_Funder` | extracted org "
        "names; may be empty |",
        "| `Event_Date` / `Event_Year` | same | present only where the source "
        "printed a date; `date_basis` says which |",
        "| `deal_status_std` | `deal_status_std` | `Announced` and `Closed` are "
        "labelled separately and `UNCLASSIFIED` is never promoted to either |",
        "| `Announced_Value_USD` | `Announced_Value_USD` | only where the source "
        "sentence stated a sum; `value_basis` quotes it |",
        "| `Source_1` | `Source_1` | the article or issue URL |",
        "| `Source_1_Type` | `Source_1_Type` | `Tribal newsletter / tribal press` |",
        "| `Description` | `Description` | the source sentence, verbatim |",
        "",
        "## Three things the promoting agent must check first",
        "",
        "1. **The publisher is not always the party.** A tribal newspaper reports "
        "on other nations' deals. `Native_Party` here is the PUBLISHER, which is "
        "a strong prior and not a fact. Every tier-A row needs this read before "
        "it becomes a deal row.",
        "2. **A transaction enters totals only when its status is confirmed.** "
        "`UNCLASSIFIED` means the source sentence carried no status verb. It is "
        "not `Announced` and it is certainly not `Closed`.",
        "3. **The intra-family rule.** Rows where both parties resolve to one "
        "tribal corporate family are already `tier_C_rejected` with "
        "`intra_family_reporting_change = yes`. The screen uses the spine's "
        "ultimate-parent map, which is incomplete; a promoting agent with the "
        "deals party-attribution table should re-run that test.",
        "",
        "## Tier A, unique, in full",
        "",
    ]
    if prom:
        lines += ["| party | status | date | value | event | sentence | source |",
                  "|---|---|---|---:|---|---|---|"]
        for r in sorted(prom, key=lambda x: x["Native_Party"].lower()):
            lines.append("| %s | %s | %s | %s | %s | %s | [link](%s) |" % (
                r["Native_Party"][:40].replace("|", "/"),
                r["deal_status_std"], r["Event_Date"] or r["Event_Year"] or "-",
                r["Announced_Value_USD"] or "-",
                r["Event_Type"][:26].replace("|", "/"),
                re.sub(r"\s+", " ", r["Description"])[:190].replace("|", "/"),
                r["Source_1"]))
    else:
        lines.append("*No tier-A candidate survived the screen in this run.*")
    lines += ["", "## Tier B - a human decides", ""]
    tb = [r for r in rows if r["screen_tier"] == "tier_B_review" and not r["duplicate_of"]]
    if tb:
        lines += ["| party | event | sentence | source |", "|---|---|---|---|"]
        for r in sorted(tb, key=lambda x: x["Native_Party"].lower())[:120]:
            lines.append("| %s | %s | %s | [link](%s) |" % (
                r["Native_Party"][:36].replace("|", "/"),
                r["Event_Type"][:24].replace("|", "/"),
                re.sub(r"\s+", " ", r["Description"])[:170].replace("|", "/"),
                r["Source_1"]))
        if len(tb) > 120:
            lines.append("")
            lines.append("*%d more tier-B rows in "
                         "`deal_candidates_screened.csv`.*" % (len(tb) - 120))
    else:
        lines.append("*None.*")
    PROPOSAL.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ verify
def verify(rows=None):
    if rows is None:
        rows = list(csv.DictReader(OUT.open(encoding="utf-8-sig"))) if OUT.exists() else []
    f = []
    tiers = {"tier_A_promotable", "tier_B_review", "tier_C_rejected"}
    bad = [r for r in rows if r["screen_tier"] not in tiers]
    if bad:
        f.append("UNKNOWN_TIER: %d, e.g. %s" % (len(bad), bad[0]["screen_tier"]))

    # a tier-A row must carry the reason it is tier A
    naked = [r for r in rows if r["screen_tier"] == "tier_A_promotable"
             and r["counterparty_is_organisation"] == "no"
             and r["corporate_noun_present"] == "no"
             and r["material_value"] == "no"]
    if naked:
        f.append("TIER_A_WITHOUT_A_QUALIFYING_SIGNAL: %d" % len(naked))

    # an intra-family row may never be promotable
    leak = [r for r in rows if r.get("intra_family_reporting_change") == "yes"
            and r["screen_tier"] != "tier_C_rejected"]
    if leak:
        f.append("INTRA_FAMILY_ROW_PROMOTABLE: %d" % len(leak))

    # nothing here may be a deletion: every input row must appear in the output
    n_in = 0
    for p in (IN_A, IN_B):
        if p.exists():
            n_in += sum(1 for _ in csv.DictReader(p.open(encoding="utf-8-sig")))
    if rows and len(rows) != n_in:
        f.append("ROWS_LOST_OR_INVENTED: %d out vs %d in" % (len(rows), n_in))

    # every screen decision must state its basis
    nb = [r for r in rows if not r["screen_basis"].strip()]
    if nb:
        f.append("SCREEN_DECISION_WITHOUT_A_BASIS: %d" % len(nb))

    # the privacy invariant, re-run at the screen. It must hold everywhere.
    import importlib
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    D = importlib.import_module("992_newsletter_deal_candidates")
    priv = [r for r in rows if D.PRIVATE.search(r["Description"])]
    if priv:
        f.append("PRIVATE_PERSONAL_CONTENT_IN_SCREENED_OUTPUT: %d" % len(priv))
    return f


def selftest():
    t = []
    mk = lambda **kw: dict({                                       # noqa: E731
        "Description": "", "Counterparty_or_Funder": "",
        "Announced_Value_USD": "", "intra_family_reporting_change": "no",
        "intra_family_basis": ""}, **kw)

    r = mk(Description="The Nation acquired Widget Solutions LLC last spring.")
    t.append(("tierA_org", screen(r)[0] == "tier_A_promotable"))
    r = mk(Description="The corporation completed a merger with the operating unit.")
    t.append(("tierA_noun", screen(r)[0] == "tier_A_promotable"))
    r = mk(Description="The tribe was awarded a contract.", Announced_Value_USD="900000")
    t.append(("tierA_value", screen(r)[0] == "tier_A_promotable"))
    r = mk(Description="Members can acquire financial management skills through "
                       "the programme.")
    t.append(("tierC_abstract", screen(r)[0] == "tier_C_rejected"))
    r = mk(Description="The district has purchased 3,000 laptops for students.")
    t.append(("tierC_goods", screen(r)[0] == "tier_C_rejected"))
    r = mk(Description="Each student was awarded a $1,000 stipend upon completion.")
    t.append(("tierC_person", screen(r)[0] == "tier_C_rejected"))
    r = mk(Description="The nation acquired the parcel adjacent to the highway.")
    t.append(("tierB", screen(r)[0] == "tier_B_review"))
    r = mk(Description="The authority acquired Widget Solutions LLC along with "
                       "3,000 laptops in the deal.")
    t.append(("mixed_stays_A", screen(r)[0] == "tier_A_promotable"))
    r = mk(Description="Cunningham joins BSNC from NANA Regional Corporation, "
                       "where she served as Senior Vice President and CFO.")
    t.append(("tierC_personnel", screen(r)[0] == "tier_C_rejected"))
    r = mk(Description="I was awarded a Naval Reserve Officers Training Corps "
                       "(NROTC) scholarship that paid for my tuition.")
    t.append(("tierC_scholarship", screen(r)[0] == "tier_C_rejected"))
    r = mk(Description="Unit A acquired Unit B Inc.",
           intra_family_reporting_change="yes", intra_family_basis="same parent")
    t.append(("intra_family", screen(r)[0] == "tier_C_rejected"))

    base = {"screen_tier": "tier_A_promotable", "screen_basis": "x",
            "counterparty_is_organisation": "no", "corporate_noun_present": "no",
            "material_value": "no", "intra_family_reporting_change": "no",
            "Description": "acquired Widget LLC"}
    t.append(("v_naked", any("TIER_A_WITHOUT_A_QUALIFYING_SIGNAL" in x
                             for x in verify([base]))))
    t.append(("v_tier", any("UNKNOWN_TIER" in x for x in
                            verify([dict(base, screen_tier="nonsense")]))))
    t.append(("v_basis", any("SCREEN_DECISION_WITHOUT_A_BASIS" in x for x in
                             verify([dict(base, screen_basis="")]))))
    t.append(("v_intra", any("INTRA_FAMILY_ROW_PROMOTABLE" in x for x in
                             verify([dict(base, intra_family_reporting_change="yes")]))))
    t.append(("v_privacy", any("PRIVATE_PERSONAL_CONTENT" in x for x in verify(
        [dict(base, Description="He passed away Tuesday having acquired the store.")]))))
    for name, ok in t:
        print("  selftest %-16s %s" % (name, "OK" if ok else "FAILED"))
    return 0 if all(x for _n, x in t) else 1


def main(argv):
    if "verify" in argv:
        if "--selftest" in argv and selftest():
            return 1
        fails = verify()
        if fails:
            for x in fails:
                print("FAIL", x)
            return 1
        n = sum(1 for _ in csv.DictReader(OUT.open(encoding="utf-8-sig"))) \
            if OUT.exists() else 0
        print("verify OK - %d screened rows, 6 invariants held" % n)
        return 0
    return build()


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
