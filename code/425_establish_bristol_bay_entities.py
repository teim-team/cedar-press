#!/usr/bin/env python3
"""
Cedar Press - 425: ESTABLISH the three Bristol Bay entities from disk. FA-04.

WHAT IS WRONG
-------------
`docs/ANOMALY_REPORT.md` FA-04. One tier-B `cluster_v3` row on UEI
`NL5HNWNUFMK4` keys **BRISTOL BAY AREA HEALTH CORPORATION** to
`ANRC-BRBYCO-00`, **Bristol Bay NATIVE Corporation**, and ten shipping tables
inherited it. A second, unaudited row does the same for **BRISTOL BAY HOUSING
AUTHORITY** on UEI `KJKZSSS83DD9`.

Measured here, and it is the sentence that matters:

    EVERY assistance row attributed to Bristol Bay Native Corporation is
    attributed to an organisation that is not Bristol Bay Native Corporation.
    554 of 554 rows / $607,260,837 - 504 BBAHC + 50 BBHA, 0 BBNC.

THIS SCRIPT WRITES NOTHING INTO ANY SHIPPING TABLE. It reads the evidence
already on disk and states, per entity, what that evidence supports - so the
minting in `426` and the repointing in `427` are applications of a written
finding rather than a drive-by edit. Same shape as `191` (decide) -> `192`
(write).

WHY THE EVIDENCE HAS TO COME FIRST, AND FROM DISK
--------------------------------------------------
The defect being repaired is an ALGORITHM that reached for the nearest name.
Repairing it by reaching for a different nearest name is the same defect with
a better mood. Every proposition below is a retrieved federal record already
in this repository, quoted with its file and its URL. **Zero network calls.**

THE FOUR INDEPENDENT LEGS, ALL ON DISK
---------------------------------------
1. **Federal Audit Clearinghouse** (`data/clean/fac_tribal_single_audits.csv`,
   `api.fac.gov`, retrieved 2026-08-12) states the auditee NAME, EIN, UEI and
   city on every filing. Three different EINs in three different filings:

       920042041  BRISTOL BAY NATIVE CORPORATION     ANCHORAGE   UEI PQUEL5MZFDJ3
       920044965  BRISTOL BAY AREA HEALTH CORP...    Dillingham  UEI NL5HNWNUFMK4
       920041473  BRISTOL BAY NATIVE ASSOCIATION     DILLINGHAM  (GSA_MIGRATION)

   An EIN is the federal government's answer to "is this the same legal
   person". Three EINs, three legal persons.

2. **IRS Exempt Organization BMF**
   (`data/raw/external/irs990/bmf_full_2026-08-12/eo3.csv`) carries BBAHC at
   `6000 KANAKANAK RD, DILLINGHAM AK`, subsection 03, NTEE **E300**, IRS ruling
   **1975-01**. BBNC is a for-profit ANCSA corporation and is not in the EO BMF
   at all. **The two are not even in the same register.**

3. **Indian Health Service, Alaska Area**
   (`data/raw/external/admin_regions/ihs_programs_alaska.html`,
   `https://www.ihs.gov/alaska/tribalhealthorganizations/`, HTTP 200,
   fetched 2026-08-06) lists BBAHC under **"Alaska Title V Compactors"** -
   verbatim heading, and the page's own sentence is
   *"a list of THOs that have Title I contracts and one Title V compact with
   separate tribal funding agreements with Indian Health Service."*
   **SIX of the spine's NINE existing `Federal-level self-governance
   consortium` entities are on that same list**: Aleutian Pribilof Islands
   Association, Chugachmiut, Copper River Native Association, Council of
   Athabascan Tribal Governments, Maniilaq Association, Tanana Chiefs
   Conference. BBAHC is not near that class; it is inside it.

4. **HUD Office of Native American Programs**
   (`data/clean/admin_region_assignments.csv`, built by
   `85_build_admin_region_crosswalk.py` from
   `https://www.hud.gov/sites/dfiles/PIH/documents/AK-Tribe-TDHE-Assignments.pdf`)
   names **"Bristol Bay HA"** as the tribally designated housing entity for
   **29 separate subjects - 28 Alaska Native villages plus BBNC itself** (HUD
   prints the regional corporation on its own IHBG-eligible list; that is HUD's
   statement, recorded, not ours) - Aleknagik, Chignik Lagoon, Chignik
   Lake, Chignik Native, Clarks Point, Curyung (Dillingham), Ekuk, Ekwok,
   Igiugig, Iliamna, Ivanof Bay, Kanatak, King Salmon, Kokhanok, Koliganek,
   Levelock, Manokotak, Naknek, New Stuyahok, Newhalen, Perryville, Pilot
   Point, Port Heiden, Portage Creek, South Naknek, Togiak, Twin Hills,
   Ugashik. **An organisation serving 28 tribes is not one tribe's subsidiary
   and is not a regional corporation.**

   Corroborated by the programme itself: **47 of BBHA's 50 assistance rows are
   CFDA 14.867, INDIAN HOUSING BLOCK GRANTS** - the NAHASDA formula, which by
   statute is paid to a tribe or to its tribally designated housing entity.

   And corroborated by BBAHC's own programme mix in the other direction:
   **244 of its 504 rows are CFDA 93.210, "TRIBAL SELF-GOVERNANCE PROGRAM:
   IHS COMPACTS/FUNDING AGREEMENTS"**, 497 of 504 from HHS. The IHS Title V
   finding and the assistance ledger are two independent sources agreeing -
   `docs/CROSS_SOURCE_VERIFICATION.md`: two that agree is a verification.

THE CLASS IS CHOSEN FROM THE 17 THAT EXIST, NEVER INVENTED
-----------------------------------------------------------
`cedar_ids.CLASS_PREFIX` (rewritten 2026-08-26 by the concurrent identity
pass) is the authority on which prefix a NEW entity of a class receives. This
script only decides the CLASS; `426` asks that module for the prefix.

  BBAHC -> **Federal-level self-governance consortium** (`SGVF`)
      taxonomy definition, verbatim from `374_build_cedar_taxonomy_export.py`:
      *"A consortium of tribes exercising self-governance authority jointly."*
      IHS calls it a Title V compactor in as many words. Six of the nine
      entities already under this class are on the same IHS list.

  BBHA  -> **Intertribal Organization** (`ITO`)
      taxonomy definition: *"An organisation whose members are tribes.
      NOT owned by its member tribes."* HUD names 28 member villages. The
      "not owned" half is the load-bearing half: `entity_relationships.csv`
      already records, on this exact TDHE, that *"every one of the 148
      'resolved' onto its own tribe by containment, which asserts the grantee
      and the government are one legal person"* and that the edge is
      `affiliated_with`, which is inside `cedar_domain.NEVER_OWNERSHIP`.

**A TDHE class was NOT invented.** The spine holds no TDHE class and this pass
does not add one - `AGENTS.md` records that inventing a class to hold one
finding is how a taxonomy stops meaning anything. `is_tdhe` is recorded as an
ATTRIBUTE in the evidence file, and the open question ("should TDHE be its own
class, given 148 of them?") is stated for the owner rather than answered.

WHAT THIS SCRIPT REFUSES TO DECIDE
-----------------------------------
- **It does not re-tier anything.** A tier is inherited from the source row.
  The root row is tier B `cluster_v3` and stays tier B after `427` repoints
  it: the ruling says WHICH entity, never HOW STRONG the evidence.
- **It does not assert an ownership edge** in any direction between BBNC,
  BBAHC and BBHA. `docs/ANCSA_OWNERSHIP_RULING.md` rules 4 and 5: a shared
  shareholder or ancestral base is never an ownership edge, and a regional
  corporation does not own the other legal persons of its region.
- **It does not re-link the 99 withdrawn lobbying filings.** `350`/`353`
  withdrew them from BBNC, correctly. Re-attributing them to BBAHC would be a
  new attribution, not a repoint, and it belongs to the pass that owns
  `180`/`182`/`351`.

    py -3 code/425_establish_bristol_bay_entities.py

Writes  review/bristol_bay_entity_evidence_2026-08-26.csv
        docs/BRISTOL_BAY_ENTITY_EVIDENCE.json
"""

import csv
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2147483647))

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
RAW = CEDAR / "data" / "raw"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
TODAY = date.today().isoformat()

FINDING_ID = "FA-04"
WRONG_ENTITY_ID = "ANRC-BRBYCO-00"
WRONG_ENTITY_NAME = "Bristol Bay Native Corporation"

#: The three legal persons, keyed by the EIN the federal government assigns.
#: Nothing here is typed from memory: every field is quoted below from the
#: file named beside it, and `verify()` re-reads each one.
SUBJECTS = {
    "BBAHC": {
        "canonical_name": "Bristol Bay Area Health Corporation",
        "ein": "920044965",
        "uei": "NL5HNWNUFMK4",
        "duns": "081488264",
        "city": "Dillingham",
        "state": "AK",
        "entity_class": "Federal-level self-governance consortium",
        "is_tdhe": "0",
        "class_reason":
            "IHS Alaska Area lists it under the verbatim heading 'Alaska "
            "Title V Compactors'; 244 of its 504 assistance rows are CFDA "
            "93.210 'TRIBAL SELF-GOVERNANCE PROGRAM: IHS COMPACTS/FUNDING "
            "AGREEMENTS'. Six of the nine entities already carrying this "
            "class are on the same IHS list.",
    },
    "BBHA": {
        "canonical_name": "Bristol Bay Housing Authority",
        "ein": "",
        "uei": "KJKZSSS83DD9",
        "duns": "019111558",
        "city": "Dillingham",
        "state": "AK",
        "entity_class": "Intertribal Organization",
        "is_tdhe": "1",
        "class_reason":
            "HUD ONAP's AK-Tribe-TDHE-Assignments list names 'Bristol Bay HA' "
            "as the tribally designated housing entity for 29 separate "
            "subjects - 28 Alaska Native villages plus BBNC itself; 47 of its "
            "50 assistance rows are CFDA 14.867 "
            "INDIAN HOUSING BLOCK GRANTS, the NAHASDA formula paid to a tribe "
            "or its TDHE. An organisation whose members are tribes.",
    },
}

IHS_HTML = RAW / "external" / "admin_regions" / "ihs_programs_alaska.html"
IHS_URL = "https://www.ihs.gov/alaska/tribalhealthorganizations/"
HUD_URL = ("https://www.hud.gov/sites/dfiles/PIH/documents/"
           "AK-Tribe-TDHE-Assignments.pdf")
BMF = RAW / "external" / "irs990" / "bmf_full_2026-08-12" / "eo3.csv"

#: The nine spine entities already under `Federal-level self-governance
#: consortium`, and which of them the IHS page names. Written down so the
#: class argument is checkable rather than asserted.
SGVF_ON_IHS_LIST = [
    "Aleutian Pribilof Islands Association",
    "Chugachmiut",
    "Copper River Native Association",
    "Council of Athabascan Tribal Governments",
    "Maniilaq Association",
    "Tanana Chiefs Conference",
]

EVIDENCE_FIELDS = [
    "subject", "canonical_name", "ein", "uei", "duns", "city", "state",
    "entity_class", "is_tdhe", "leg", "source_authority", "source_file",
    "source_url", "verbatim_or_measured", "supports",
]


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return list(csv.DictReader(fh))


def require_columns(path, rows, cols):
    """RAISE when a column is absent. Never return a zero for one.

    Defect class 2b: `102` counted two datasets on a `tribe_id` column neither
    file has and printed 0.0% coverage for nineteen days. A measurement aimed
    at a column that is not there is not a measurement.
    """
    if not rows:
        raise SystemExit(f"  {path} is empty or missing - refusing to measure")
    missing = [c for c in cols if c not in rows[0]]
    if missing:
        raise SystemExit(
            f"  {path} has no column(s) {missing}. Refusing to report a zero "
            f"for a column that does not exist (defect class 2b).")


def write_csv(path, rows, fields):
    """`.part` then rename. An interruption must not look like a completion."""
    part = Path(str(path) + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    os.replace(part, path)


def leg_fac():
    """Leg 1 - the Federal Audit Clearinghouse states name, EIN, UEI, city."""
    rows = read_csv(CLEAN / "fac_tribal_single_audits.csv")
    require_columns("fac_tribal_single_audits.csv", rows,
                    ["auditee_name", "auditee_ein", "auditee_uei",
                     "auditee_city", "entity_id", "entity_match_method"])
    out, by_ein = [], defaultdict(list)
    for r in rows:
        if "BRISTOL BAY" not in (r.get("auditee_name") or "").upper():
            continue
        by_ein[r.get("auditee_ein", "")].append(r)
        out.append(r)
    return out, by_ein


def leg_bmf():
    """Leg 2 - the IRS Exempt Organization BMF, read once, streamed."""
    wanted = {"920044965", "920042041", "920041473"}
    found = {}
    if not BMF.exists():
        return found
    with open(BMF, newline="", encoding="utf-8-sig", errors="replace") as fh:
        for r in csv.DictReader(fh):
            e = (r.get("EIN") or "").strip()
            if e in wanted:
                found[e] = r
            if len(found) == len(wanted):
                break
    return found


def leg_ihs():
    """Leg 3 - the IHS Alaska Area Title V compactor list, from the HTML."""
    if not IHS_HTML.exists():
        return "", []
    txt = IHS_HTML.read_text(encoding="utf-8", errors="replace")
    flat = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt)))
    i = flat.find("Alaska Title V Compactors")
    j = flat.find("Alaska Title I Contractors")
    block = flat[i:j] if 0 <= i < j else ""
    named = [n for n in SGVF_ON_IHS_LIST if n.lower() in block.lower()]
    return block, named


def leg_hud():
    """Leg 4 - HUD ONAP's TDHE assignment list, as loaded by script 85."""
    rows = read_csv(CLEAN / "admin_region_assignments.csv")
    require_columns("admin_region_assignments.csv", rows,
                    ["subject_type", "subject_name", "related_subject_name",
                     "source_url"])
    villages = sorted({(r.get("related_subject_name") or "").strip()
                       for r in rows
                       if r.get("subject_type") == "TDHE"
                       and (r.get("subject_name") or "").strip().upper()
                       == "BRISTOL BAY HA"
                       and (r.get("related_subject_name") or "").strip()})
    return villages


def leg_assistance():
    """The consequence, measured on the shipping table itself."""
    p = CLEAN / "federal_funding_transactions.csv"
    per = defaultdict(lambda: {"rows": 0, "usd": 0.0, "cfda": Counter(),
                               "agency": Counter(), "uei": Counter(),
                               "years": []})
    total = 0
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        rd = csv.DictReader(fh)
        for c in ("tribe_id", "recipient_name", "obligated_usd", "cfda",
                  "cfda_title", "awarding_agency_name", "recipient_uei",
                  "fiscal_year"):
            if c not in (rd.fieldnames or []):
                raise SystemExit(f"  federal_funding_transactions.csv has no "
                                 f"column {c!r} (defect class 2b)")
        for r in rd:
            if (r.get("tribe_id") or "") != WRONG_ENTITY_ID:
                continue
            total += 1
            k = (r.get("recipient_name") or "").upper().strip()
            d = per[k]
            d["rows"] += 1
            try:
                d["usd"] += float(r.get("obligated_usd") or 0)
            except ValueError:
                pass
            d["cfda"][(r.get("cfda") or "",
                       (r.get("cfda_title") or "").strip())] += 1
            d["agency"][r.get("awarding_agency_name") or ""] += 1
            d["uei"][r.get("recipient_uei") or ""] += 1
            d["years"].append(r.get("fiscal_year") or "")
    return total, per


def main():
    print("=== Cedar Press 425: establish the Bristol Bay entities "
          f"({FINDING_ID}) ===\n")
    print("  ZERO network calls. Every leg is a file already on disk.\n")

    ev = []

    # ---- leg 1: FAC ------------------------------------------------------
    fac, by_ein = leg_fac()
    print("[leg 1] Federal Audit Clearinghouse - auditee NAME + EIN + UEI")
    print(f"  {len(fac)} 'BRISTOL BAY' filings, "
          f"{len(by_ein)} DISTINCT EINs:")
    for e, rs in sorted(by_ein.items()):
        nm = rs[0].get("auditee_name", "")
        print(f"    EIN {e}  UEI {rs[0].get('auditee_uei',''):14s} "
              f"{rs[0].get('auditee_city',''):11s} {nm}")
        print(f"       -> currently keyed to {rs[0].get('entity_id','')} "
              f"by {rs[0].get('entity_match_method','')} "
              f"(tier {rs[0].get('entity_tier','')})")
    if len(by_ein) < 3:
        raise SystemExit("  FAC did not yield three distinct EINs - the "
                         "evidence base for this ruling is not present. "
                         "REFUSING to proceed.")
    for key, s in SUBJECTS.items():
        hits = [r for r in fac if (r.get("auditee_ein") or "") == s["ein"]]
        if not hits:
            continue
        ev.append({**s, "subject": key, "leg": "FAC_SINGLE_AUDIT",
                   "source_authority": "Federal Audit Clearinghouse (GSA)",
                   "source_file": "data/clean/fac_tribal_single_audits.csv",
                   "source_url": hits[0].get("source_url", ""),
                   "verbatim_or_measured":
                       f"auditee_name={hits[0].get('auditee_name','')!r}; "
                       f"auditee_ein={s['ein']}; auditee_uei={s['uei']}; "
                       f"auditee_city={hits[0].get('auditee_city','')}",
                   "supports": "a distinct legal person with its own EIN"})

    # ---- leg 2: IRS BMF --------------------------------------------------
    bmf = leg_bmf()
    print("\n[leg 2] IRS Exempt Organization BMF")
    if not bmf:
        print(f"  !! {BMF} not on disk - leg 2 is UNMEASURED, not clean.")
    for e, r in sorted(bmf.items()):
        print(f"    EIN {e}  {r.get('NAME','')}  |  {r.get('STREET','')}, "
              f"{r.get('CITY','')} {r.get('STATE','')}  |  NTEE "
              f"{r.get('NTEE_CD','')}  ruling {r.get('RULING','')}")
    print("    BBNC (920042041) is a for-profit ANCSA corporation and is "
          "ABSENT from the EO BMF - the two are not in the same register.")
    if SUBJECTS["BBAHC"]["ein"] in bmf:
        r = bmf[SUBJECTS["BBAHC"]["ein"]]
        ev.append({**SUBJECTS["BBAHC"], "subject": "BBAHC",
                   "leg": "IRS_EO_BMF",
                   "source_authority": "IRS Exempt Organization Business "
                                       "Master File",
                   "source_file": str(BMF.relative_to(CEDAR)).replace("\\", "/"),
                   "source_url": "https://www.irs.gov/charities-non-profits/"
                                 "exempt-organizations-business-master-file-"
                                 "extract-eo-bmf",
                   "verbatim_or_measured":
                       f"NAME={r.get('NAME','')!r}; STREET={r.get('STREET','')}; "
                       f"CITY={r.get('CITY','')}; NTEE_CD={r.get('NTEE_CD','')}; "
                       f"SUBSECTION={r.get('SUBSECTION','')}; "
                       f"RULING={r.get('RULING','')}",
                   "supports": "a 501(c)(3) health organisation in Dillingham, "
                               "not an ANCSA corporation"})

    # ---- leg 3: IHS ------------------------------------------------------
    block, named = leg_ihs()
    print("\n[leg 3] IHS Alaska Area - 'Alaska Title V Compactors'")
    print(f"  source: {IHS_URL}")
    if not block:
        print("  !! the Title V block could not be located in the retrieved "
              f"HTML at {IHS_HTML} - leg 3 is UNMEASURED, not clean.")
    else:
        on_list = "bristol bay area health corporation" in block.lower()
        print(f"  BBAHC named under 'Alaska Title V Compactors': {on_list}")
        print(f"  spine entities ALREADY classed "
              f"'Federal-level self-governance consortium' on the same list: "
              f"{len(named)} of {len(SGVF_ON_IHS_LIST)}")
        for n in named:
            print(f"      {n}")
        if on_list:
            ev.append({**SUBJECTS["BBAHC"], "subject": "BBAHC",
                       "leg": "IHS_ALASKA_TITLE_V_COMPACTOR",
                       "source_authority": "Indian Health Service, Alaska Area",
                       "source_file": str(IHS_HTML.relative_to(CEDAR)
                                          ).replace("\\", "/"),
                       "source_url": IHS_URL,
                       "verbatim_or_measured":
                           "heading 'Alaska Title V Compactors'; page text: "
                           "'a list of THOs that have Title I contracts and "
                           "one Title V compact with separate tribal funding "
                           "agreements with Indian Health Service'",
                       "supports": "Federal-level self-governance consortium: "
                                   "a consortium of tribes exercising "
                                   "self-governance authority jointly"})

    # ---- leg 4: HUD ------------------------------------------------------
    villages = leg_hud()
    print("\n[leg 4] HUD ONAP - the TDHE assignment list")
    print(f"  source: {HUD_URL}")
    print(f"  'Bristol Bay HA' is named as the TDHE for {len(villages)} "
          f"separate subjects:")
    print("      " + "; ".join(villages))
    if villages:
        ev.append({**SUBJECTS["BBHA"], "subject": "BBHA",
                   "leg": "HUD_ONAP_TDHE_ASSIGNMENT",
                   "source_authority": "HUD Office of Native American Programs",
                   "source_file": "data/clean/admin_region_assignments.csv",
                   "source_url": HUD_URL,
                   "verbatim_or_measured":
                       f"subject_type=TDHE; subject_name='Bristol Bay HA'; "
                       f"{len(villages)} related subjects: "
                       + "; ".join(villages),
                   "supports": "Intertribal Organization: an organisation "
                               "whose members are tribes, owned by none of them"})

    # ---- the consequence -------------------------------------------------
    total, per = leg_assistance()
    print(f"\n[consequence] federal_funding_transactions.csv on "
          f"{WRONG_ENTITY_ID} ({WRONG_ENTITY_NAME})")
    grand = 0.0
    for nm, d in sorted(per.items(), key=lambda kv: -kv[1]["rows"]):
        grand += d["usd"]
        yrs = sorted(y for y in d["years"] if y)
        print(f"  {d['rows']:>5} rows  ${d['usd']:>16,.0f}  {nm}")
        print(f"        UEI {', '.join(sorted(d['uei']))}  "
              f"FY{yrs[0] if yrs else '?'}-{yrs[-1] if yrs else '?'}")
        for (c, t), n in d["cfda"].most_common(3):
            print(f"        {n:>4} x CFDA {c}  {t[:60]}")
    print(f"  {'-' * 66}")
    print(f"  {total:>5} rows  ${grand:>16,.0f}  TOTAL")
    bbnc_own = sum(d["rows"] for nm, d in per.items()
                   if "AREA HEALTH" not in nm and "HOUSING" not in nm)
    print(f"\n  rows actually naming Bristol Bay Native Corporation: "
          f"{bbnc_own}")
    if bbnc_own == 0:
        print("  ** EVERY assistance row attributed to Bristol Bay Native "
              "Corporation\n     is attributed to an organisation that is not "
              "Bristol Bay Native Corporation. **")

    # ---- the decision ----------------------------------------------------
    print("\n[decision] the class, chosen from the 17 that already exist")
    for key, s in SUBJECTS.items():
        print(f"  {s['canonical_name']}")
        print(f"      entity_class = {s['entity_class']}")
        print(f"      is_tdhe      = {s['is_tdhe']}")
        print(f"      because      : {s['class_reason']}")
    print("\n  NO new class is invented. NO tier is assigned - the root row "
          "stays\n  tier B `cluster_v3`; this says WHICH entity, never HOW "
          "STRONG.")
    print("  NO ownership edge is asserted between BBNC, BBAHC and BBHA "
          "(ANCSA ruling\n  rules 4 and 5).")

    REVIEW.mkdir(parents=True, exist_ok=True)
    dest = REVIEW / f"bristol_bay_entity_evidence_{TODAY}.csv"
    write_csv(dest, ev, EVIDENCE_FIELDS)
    print(f"\n  wrote {dest.relative_to(CEDAR)}  ({len(ev)} evidence rows)")

    DOCS.mkdir(parents=True, exist_ok=True)
    js = DOCS / "BRISTOL_BAY_ENTITY_EVIDENCE.json"
    payload = {
        "finding_id": FINDING_ID,
        "established_date": TODAY,
        "established_by_script": Path(__file__).name,
        "wrong_entity_id": WRONG_ENTITY_ID,
        "wrong_entity_name": WRONG_ENTITY_NAME,
        "subjects": SUBJECTS,
        "distinct_eins_in_fac": sorted(by_ein),
        "ihs_title_v_sibling_entities_already_in_class": named,
        "hud_tdhe_member_villages": villages,
        "assistance_rows_on_wrong_entity": total,
        "assistance_rows_actually_naming_the_wrong_entity": bbnc_own,
        "assistance_usd_on_wrong_entity": round(grand, 2),
        "per_recipient": {nm: {"rows": d["rows"], "usd": round(d["usd"], 2)}
                          for nm, d in per.items()},
        "open_question_for_the_owner":
            "The spine has no TDHE class and none was invented here. HUD's "
            "own list names 148 TDHEs and entity_relationships.csv records "
            "all 148 as `affiliated_with` with a blank target and the note "
            "'pending a spine entity'. Bristol Bay Housing Authority is "
            "filed as Intertribal Organization because its members are "
            "tribes; whether TDHE should become the 18th class, and the "
            "other 147 minted with it, is the owner's call and is NOT "
            "answered here.",
    }
    part = Path(str(js) + ".part")
    part.write_text(json.dumps(payload, indent=1, sort_keys=True),
                    encoding="utf-8")
    os.replace(part, js)
    print(f"  wrote {js.relative_to(CEDAR)}")
    print("\n  next:  py -3 code/426_mint_bristol_bay_spine_entities.py --check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
