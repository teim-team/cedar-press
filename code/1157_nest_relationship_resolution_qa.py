#!/usr/bin/env python3
"""1157 - NEST relationship-resolution QA: the wrong-owner class.

WHY THIS EXISTS
---------------
The owner reviewed NEST twice and reached the same verdict twice:

    "The ten-row review caught Goldbelt Hawk -> Tlingit & Haida and United
     Tribes Technical College -> United Auburn, along with affiliation being
     promoted to ownership. The 100-row sample continued to make me uneasy
     about ownership versus affiliation relationships. So the Cedar UID design
     is fine, but relationship resolution still needs serious QA."

Two defects, and they are not the same defect.

DEFECT 1 - AFFILIATION PROMOTED TO OWNERSHIP.  Measured on
`dist/customer/nest.csv` 2026-09-02, and it was real but it was NOT where a
reader would look for it:

  * `relation_class` was honest.  1,512 ownership / 3,286 affiliation, and
    **every one of the 1,512 had at least one edge in
    `nest_enterprise_relations.csv` that itself asserts ownership** - 0 rows
    published as ownership on a collapse rather than on a source.  The
    `unspecified` guard held too: 0 blank `relationship`, 3,187 written
    literally.
  * `assertion_class` was NOT honest.  It was the hard-coded string
    `"OWNERSHIP"` on all 4,798 rows - so **3,286 rows carried the word
    OWNERSHIP in their summary column while their own `relation_class` said
    `affiliation` and their `relationship` said `unspecified`.**  That is the
    promotion the owner saw, and it was a constant, not a judgement.

  Fixed in 1072 (`assertion_class = rel_class.upper()`), with `verify` I9 to
  keep it fixed and one latent hazard closed alongside: the enterprise-level
  collapse defaulted a blank relationship to `subsidiary` - an OWNERSHIP word -
  while the edge rows defaulted the same blank to `unspecified`.  Zero rows hit
  it today, so it was a guard rather than a correction, but the identical shape
  has published ownership on 3,189 rows once already in this project.

DEFECT 2 - THE WRONG OWNER.  Two mechanisms, one structural and one inherited.

  (a) STRUCTURAL, and fixed.  `anc_tribal_subsidiary_lookup.csv` carries 118
      rows whose `parent_entity_type` names an ANCSA corporation
      (`ANC_VILLAGE_*`) while `parent_entity_id` is a GOVERNMENT.  1072 has a
      guard for exactly this, and it was gated on the resolved hub's class
      being `Federally recognized Alaska Native Village` - so it caught 95 and
      skipped **23 `ANC_VILLAGE_GOLDBELT` rows whose parent id is
      `AKNF-TLNGHD-00-SEALSK`, Tlingit & Haida, class `Federally recognized
      tribe`.**  Goldbelt, Incorporated is the ANCSA urban corporation for
      Juneau and is already in the spine (`ANVC-GLDBLT-00`); Tlingit & Haida is
      a tribal government.  ANCSA_OWNERSHIP_RULING rules 2 and 4 forbid the
      edge in that direction and make the real tie ancestral association.  The
      guard now triggers on the SOURCE's own field, which is what its own
      comment always claimed, and `verify` I11 holds it.

  (b) INHERITED, and NOT fixed here, deliberately.  The owner's own v6
      research dataset (`native_entity_enterprise_dataset_v6_geocoded.csv`,
      arriving through 1133 as `OWNERV6`) carries attributions its `cluster_v3`
      resolver produced on generic leading tokens.  `Tlingit & Haida` -
      officially the *Central* Council of the Tlingit and Haida Indian Tribes -
      collects `CENTRAL BAPTIST CHURCH OF SIOUX CITY IOWA`, `CENTRAL DAKOTA
      FFA ALUMNI` and `CENTRAL YAVAPAI TRANSIT FOUNDATION`; `United Auburn`
      collects `UNITED BLIND OF WALLA WALLA`, `NAVY LEAGUE OF THE UNITED
      STATES WICHITA COUNCIL` and `United Tribes Technical College`.  `central`
      and `united` are both already in `cedar_domain.NAME_TRAPS`.

WHY (b) IS A REVIEW FILE AND NOT AN EDIT
----------------------------------------
`cedar_match_guard.guard()` is Cedar's adjudicated name-match rule and it
refuses these on sight.  It also refuses **1,509 of the 1,658 rows whose source
NAMES the edge** - an audited AS 45.55.139 filing listing its own wholly-owned
subsidiaries, or an ANC's own website.  `ASRC Federal Broadleaf` shares no
token with `Arctic Slope Regional Corporation` and is correct.  A name guard
cannot judge an edge a publisher stated; ENTITY_MATCH_RULES rule 7 says the
record's own words outrank the inference, and checklist step 2 says a stated
name is a strong class that needs no corroboration.

So the guard is run ONLY over rows where no source names the edge, it produces
CANDIDATES, and every one carries `proposed_disposition = REVIEW`.  Nothing is
auto-demoted and nothing is repointed.  ENTITY_MATCH_RULES rule 8 - an agent
ruling may not mint tier A - and rule 12 - acting on a raw contradiction sweep
would have repointed 126 correct rows to chase 3 wrong ones - both point the
same way.  These rows are already published as `affiliation` / `unspecified`,
which is the weaker reading and an honest state (ADR-010); the open question is
whether the OWNER is right, and that is the owner's ladder to run
(ENTITY_MATCH_RULES rule 13), not a matcher's.

Stages: report | apply | verify.
"""
import csv
import importlib.util
import re
import sys
from datetime import date
from pathlib import Path

SCRIPT = "code/1157_nest_relationship_resolution_qa.py"
BUILT = date.today().isoformat()
CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
RAW = CEDAR / "data" / "raw"
REVIEW = CEDAR / "review"

ENT = CLEAN / "nest_enterprises.csv"
EDGE = CLEAN / "nest_enterprise_relations.csv"
REGISTER = SPINE / "cedar_identity_register.csv"
LOOKUP = RAW / "external" / "anc_tribal_subsidiary_lookup.csv"
OUT = REVIEW / f"nest_wrong_owner_candidates_{BUILT}.csv"

csv.field_size_limit(10 ** 9)


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(p, cols, rows):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_guard():
    """`cedar_match_guard.guard()` is the ONE adjudicated name-match rule.

    Re-deriving a token test here would be a second detector for one class,
    and the two would drift.  Rule 1 lives there; this script only decides
    WHERE it is allowed to be asked.
    """
    spec = importlib.util.spec_from_file_location(
        "cmg1157", str(CEDAR / "code" / "cedar_match_guard.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------------------
# WHERE THE NAME GUARD MAY BE ASKED
# ---------------------------------------------------------------------------
# A publisher naming its own subsidiary is an OBSERVATION of the edge.  A
# resolver keying two names together is an INFERENCE about the edge.  The name
# guard adjudicates inferences; asking it about an observation is a category
# error, and a measured one - see the module docstring's 1,509.
SOURCE_NAMES_THE_EDGE = {
    "audited_annual_report_as_45_55_139",
    "parent_self_published_company_list",
    "nation_self_published_enterprise_register",
    "parent_declared_subsidiary_list",
}
# The owner's HAND rulings are inferences by the strict reading, but a person
# decided them and ENTITY_MATCH_RULES rule 13 is that person's own ladder.
# They are scored and reported SEPARATELY rather than pooled, so a count of
# machine-made candidates is never inflated by rows the owner already ruled.
OWNER_HAND = "owner_research_dataset_hand_ruling"

ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC", "puerto rico": "PR", "guam": "GU",
}


def st(x):
    x = (x or "").strip()
    if not x or len(x) > 30:
        return ""
    if len(x) == 2:
        return x.upper()
    return ABBR.get(x.lower(), "")


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


# ---------------------------------------------------------------------------
def measure():
    ents = read_csv(ENT)
    edges = read_csv(EDGE)
    reg = {r["cedar_uid"]: r for r in read_csv(REGISTER) if r.get("cedar_uid")}
    guard = load_guard().guard

    own_edge = {e["enterprise_id"] for e in edges
                if e.get("relation_class") == "ownership"}
    m = {
        "enterprises": len(ents),
        "edges": len(edges),
        "relation_class_ownership": sum(1 for r in ents if r["relation_class"] == "ownership"),
        "relation_class_affiliation": sum(1 for r in ents if r["relation_class"] == "affiliation"),
        "assertion_class_contradicts_relation_class": sum(
            1 for r in ents
            if (r.get("assertion_class") or "").lower() != (r.get("relation_class") or "").lower()),
        "published_ownership_with_no_ownership_edge": sum(
            1 for r in ents if r["relation_class"] == "ownership"
            and r["enterprise_id"] not in own_edge),
        "edges_with_blank_relationship_as_recorded": sum(
            1 for e in edges if not (e.get("relationship_as_recorded") or "").strip()),
        "rows_with_relationship_written_literally_unspecified": sum(
            1 for r in ents if r["relationship"] == "unspecified"),
        "rows_with_blank_relationship": sum(
            1 for r in ents if not (r.get("relationship") or "").strip()),
    }

    ruled = ruled_village_corporations(reg)
    anc_names = {norm(s["canonical_name"]): s["handle"] for s in reg.values()
                 if s.get("entity_class") in ANCSA_CORP and s.get("canonical_name")}
    cands, exempt_refused, hand_refused = [], 0, 0
    for r in ents:
        hub = reg.get(r["owner_hub_cedar_uid"])
        if hub is None:
            continue
        ev = r.get("evidence_class") or ""
        ok, why = guard(r["enterprise_name"], hub, how="containment",
                        context={"record_state": r.get("state_province")})

        # CLASS A first, and it does not consult the name guard at all.
        # ANCSA_OWNERSHIP_RULING rule 1: an operating company in an ANCSA
        # structure belongs to the village CORPORATION, and rule 3 makes
        # direct village-government ownership the exception you must
        # EVIDENCE. A hub of class `Federally recognized Alaska Native
        # Village` on a corporate enterprise is therefore a departure from
        # the presumption, whatever its name looks like - which is why
        # `Alutiiq LLC` under `Alutiiq` (the Native Village, not Afognak
        # Native Corporation) reads as a clean match and is still wrong.
        if hub.get("entity_class") == VILLAGE_GOVERNMENT:
            corp = ruled.get(r["owner_hub_cedar_uid"], [])
            # THE SHARPEST SUBSET. Where the ENTERPRISE is itself an ANCSA
            # corporation in Cedar's own spine, the row is not a presumption
            # to re-check - it is ANCSA_OWNERSHIP_RULING rule 2 stated
            # outright in the published table: `Afognak Native Corporation`
            # published as an enterprise owned by the Native Village of
            # Afognak. `cedar_domain.village_government_owns_an_anc()` returns
            # False unconditionally and this row asserts it is True.
            is_anc = anc_names.get(norm(r["enterprise_name"]))
            cands.append(candidate_row(
                r, hub, ev,
                "ANCSA_RULE_2_VIOLATION" if is_anc else "ANCSA_VILLAGE_GOVERNMENT_HUB",
                why=((f"the ENTERPRISE is itself an ANCSA corporation in the "
                      f"spine ({is_anc}) and its owner hub is an Alaska Native "
                      f"Village GOVERNMENT. ANCSA_OWNERSHIP_RULING rule 2: a "
                      f"village government never owns an ANC, in either "
                      f"direction. This is not a presumption to re-check.")
                     if is_anc else
                     ("the owner hub is an Alaska Native Village GOVERNMENT. "
                      "ANCSA_OWNERSHIP_RULING rule 1 presumes the village "
                      "CORPORATION owns an operating company; rule 3 allows "
                      "direct government ownership only where a source shows "
                      "it. No such source is on this row.")),
                corp=corp))
            continue

        if ev in SOURCE_NAMES_THE_EDGE:
            if not ok:
                exempt_refused += 1
            continue
        if ok:
            continue
        if ev == OWNER_HAND:
            hand_refused += 1
        cands.append(candidate_row(r, hub, ev, "NAME_GUARD_REFUSED", why, []))

    cands.sort(key=lambda c: (c["defect_class"], c["owner_hub_name"],
                              c["enterprise_name"]))
    m["candidates_total"] = len(cands)
    m["classA0_ANCSA_RULE_2_VIOLATION_enterprise_IS_an_ANC"] = sum(
        1 for c in cands if c["defect_class"] == "ANCSA_RULE_2_VIOLATION")
    m["classA_ancsa_village_government_hub"] = sum(
        1 for c in cands if c["defect_class"] == "ANCSA_VILLAGE_GOVERNMENT_HUB")
    m["classA_with_an_owner_ruled_corporation_named"] = sum(
        1 for c in cands if c["defect_class"].startswith("ANCSA")
        and c["owner_ruled_corporation_candidates"])
    m["classB_name_guard_refused"] = sum(
        1 for c in cands if c["defect_class"] == "NAME_GUARD_REFUSED")
    m["name_guard_refusals_where_the_source_NAMES_the_edge_EXEMPT"] = exempt_refused
    m["classB_rows_a_person_had_already_ruled"] = hand_refused

    # The structural class 1072 now fixes - reported here too, so a regression
    # is visible from either script.
    anc_named = {norm(x.get("subsidiary_name") or "") for x in read_csv(LOOKUP)
                 if (x.get("parent_entity_type") or "").startswith("ANC_VILLAGE_")}
    govs = {"Federally recognized tribe", "State-recognized tribe",
            VILLAGE_GOVERNMENT, "Federal-level constituency entity",
            "State-level constituency entity"}
    m["ancsa_lookup_edges_still_on_a_government_hub"] = sum(
        1 for e in edges if e.get("source_id") == "ANC_TRIBE_LOOKUP"
        and norm(e.get("child_name_as_recorded") or "") in anc_named
        and (reg.get(e.get("owner_hub_cedar_uid"), {}) or {}).get("entity_class") in govs)
    return m, cands


VILLAGE_GOVERNMENT = "Federally recognized Alaska Native Village"
ANCSA_CORP = {"Alaska Native Village Corporation",
              "Alaska Native Regional Corporation"}
RULING = REVIEW / "ancsa_attribution_changes_2026-08-26.csv"


def ruled_village_corporations(reg):
    """village-government uid -> [(corporation, n attributions)], MOST FIRST.

    Read out of the owner's own 2026-08-26 ANCSA ruling rather than derived.
    IT IS ONE-TO-MANY AND MUST NOT BE APPLIED AS A CROSSWALK: `Barrow` was
    ruled to Ukpeagvik Inupiat Corporation on 288 attributions AND to Natives
    of Kodiak on 133; `Pribilof Islands` to the Aleut Corporation on 11 and to
    St. George Tanaq on 10. Which corporation owns a given firm is a fact
    about that firm. So the ruling NAMES the candidates for a reviewer and
    decides nothing.
    """
    from collections import Counter
    by_handle = {r["handle"]: r for r in reg.values() if r.get("handle")}
    hits = Counter()
    for r in read_csv(RULING):
        f = reg.get(r.get("from_entity_id")) or by_handle.get(r.get("from_entity_id"))
        t = reg.get(r.get("to_entity_id")) or by_handle.get(r.get("to_entity_id"))
        if (f and t and f.get("entity_class") == VILLAGE_GOVERNMENT
                and t.get("entity_class") in ANCSA_CORP):
            hits[(f["cedar_uid"], t["handle"], t["canonical_name"])] += 1
    out = {}
    for (vuid, handle, name), n in hits.most_common():
        out.setdefault(vuid, []).append(f"{handle} ({name}) x{n}")
    return out


def candidate_row(r, hub, ev, defect_class, why, corp):
    a, b = st(r.get("state_province")), st(r.get("owner_hub_state"))
    return {
            "enterprise_id": r["enterprise_id"],
            "enterprise_name": r["enterprise_name"],
            "owner_hub_cedar_uid": r["owner_hub_cedar_uid"],
            "owner_hub_handle": r.get("owner_hub_handle", ""),
            "owner_hub_name": r.get("owner_hub_name", ""),
            "owner_hub_entity_class": r.get("owner_hub_entity_class", ""),
            "owner_hub_state": r.get("owner_hub_state", ""),
            "enterprise_city": r.get("city", ""),
            "enterprise_state": r.get("state_province", ""),
            "relation_class_as_published": r["relation_class"],
            "relationship_as_published": r["relationship"],
            "evidence_class": ev,
            "ruled_by_a_person": "Y" if ev == OWNER_HAND else "N",
            "hub_resolution_method": r.get("hub_resolution_method", ""),
            "source_id": r.get("source_id", ""),
            "source_document": (r.get("source_document") or "")[:180],
            "defect_class": defect_class,
            "why_this_row_is_a_candidate": why,
            "owner_ruled_corporation_candidates": " | ".join(corp),
            # RECORDED, NOT SCORED. Rule 7: geography is a corroborator and a
            # poor gate. An ANC's lower-48 subsidiary disagrees with its
            # parent's state BY DESIGN - the first draft of this script
            # ranked `Alutiiq Manufacturing Contractors, Llc` (WA) against
            # Afognak (AK) as its strongest finding on that basis, when the
            # state gap is the least interesting thing about the row.
            "geography_signal": ("state_disagreement" if (a and b and a != b)
                                 else "same_state" if (a and b)
                                 else "state_not_on_record"),
            "proposed_disposition": "REVIEW",
        "why_not_auto_applied": (
            "This row is a QUESTION about who the owner is, not an answer. "
            "ENTITY_MATCH_RULES rule 6 (a wrong key is worse than no key), "
            "rule 8 (an agent ruling may not mint tier A) and rule 12 (acting "
            "on a raw contradiction sweep would have repointed 126 correct "
            "rows to chase 3 wrong ones). Class A additionally cannot be "
            "auto-applied because the owner's 2026-08-26 ANCSA ruling maps a "
            "village to MORE THAN ONE corporation. Repointing needs the "
            "owner's ladder (rule 13): the address, then the firm's own "
            "website, then what else sits at that address."),
        "built_by_script": SCRIPT,
        "built_date": BUILT,
    }


def stage_report(argv) -> int:
    m, cands = measure()
    print("=== 1157 report - NEST relationship resolution ===")
    for k, v in m.items():
        print("  %-62s %7d" % (k, v))
    from collections import Counter
    for dc in ("ANCSA_RULE_2_VIOLATION", "ANCSA_VILLAGE_GOVERNMENT_HUB",
               "NAME_GUARD_REFUSED"):
        sub = [c for c in cands if c["defect_class"] == dc]
        print(f"\n  --- {dc}: {len(sub)} rows. top hubs:")
        for k, v in Counter(c["owner_hub_name"] for c in sub).most_common(8):
            print("     %-46s %5d" % (k[:46], v))
        for c in sub[:5]:
            print("     e.g. %-40s <- %-24s %s"
                  % (c["enterprise_name"][:40], c["owner_hub_name"][:24],
                     ("ruled candidates: " + c["owner_ruled_corporation_candidates"][:60])
                     if c["owner_ruled_corporation_candidates"] else ""))
    print(f"\n  `apply` would write {len(cands)} rows -> {OUT}")
    return 0


def stage_apply(argv) -> int:
    m, cands = measure()
    if not cands:
        print("  nothing to write - no candidate survived the guard")
        return 1
    write_csv(OUT, list(cands[0].keys()), cands)
    print(f"=== 1157 apply ===\n  {len(cands)} candidates -> {OUT}")
    print(f"  class A (ANCSA village government hub) "
          f"{m['classA_ancsa_village_government_hub']}, of which "
          f"{m['classA_with_an_owner_ruled_corporation_named']} carry an "
          f"owner-ruled corporation candidate")
    print(f"  class B (name guard refused) {m['classB_name_guard_refused']}, of "
          f"which {m['classB_rows_a_person_had_already_ruled']} a person had "
          f"already ruled by hand")
    print("  NOTHING was demoted, repointed or deleted. Every row is REVIEW.")
    return 0


CONTRACT = """
  C1  the review file exists, is non-empty, and every row is REVIEW - this
      script may not have ruled anything
  C2  assertion_class agrees with relation_class on every published row
      (the promotion the 2026-09-02 review caught)
  C3  no row published `ownership` lacks an edge that asserts ownership
  C4  `relationship` is never blank - `unspecified` is written literally, so
      a downstream default can never turn silence into `subsidiary`
  C5  no ANC_TRIBE_LOOKUP edge whose own parent_entity_type names an ANCSA
      corporation is keyed to a GOVERNMENT hub (the Goldbelt class)
  C6  the review file is current: built from the enterprise table on disk
"""


def stage_verify(argv) -> int:
    print("=== 1157 verify ===" + CONTRACT)
    m, cands = measure()
    rows = read_csv(OUT)
    fails = []
    if not rows:
        fails.append(f"C1 no review file at {OUT}")
    else:
        ruled = [r for r in rows if r.get("proposed_disposition") != "REVIEW"]
        if ruled:
            fails.append(f"C1 {len(ruled)} rows carry a disposition other than REVIEW")
    if m["assertion_class_contradicts_relation_class"]:
        fails.append(f"C2 {m['assertion_class_contradicts_relation_class']} rows "
                     f"whose assertion_class contradicts their relation_class")
    if m["published_ownership_with_no_ownership_edge"]:
        fails.append(f"C3 {m['published_ownership_with_no_ownership_edge']} rows "
                     f"published as ownership with no ownership edge underneath")
    if m["rows_with_blank_relationship"]:
        fails.append(f"C4 {m['rows_with_blank_relationship']} rows with a blank "
                     f"relationship - it must read `unspecified` literally")
    if m["ancsa_lookup_edges_still_on_a_government_hub"]:
        fails.append(f"C5 {m['ancsa_lookup_edges_still_on_a_government_hub']} "
                     f"ANCSA-corporation subsidiary edges on a government hub")
    if rows and len(rows) != len(cands):
        fails.append(f"C6 the review file holds {len(rows)} rows but the tables on "
                     f"disk now produce {len(cands)} - re-run `apply`")
    for f in fails:
        print("  FAIL " + f)
    if not fails:
        print(f"  PASS  {len(rows)} candidates on file; "
              f"{m['enterprises']} enterprises clean on C2-C5")
    return 1 if fails else 0


def main() -> int:
    stages = {"report": stage_report, "apply": stage_apply, "verify": stage_verify}
    if len(sys.argv) < 2 or sys.argv[1] not in stages:
        print(f"usage: py -3 {SCRIPT} " + "|".join(stages))
        return 2
    return stages[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
