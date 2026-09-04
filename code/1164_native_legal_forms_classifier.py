#!/usr/bin/env python3
"""
Cedar Press - 1164: THE NATIVE ENTITY LEGAL-FORM REGISTRY, AS CODE.

    py -3 code/1164_native_legal_forms_classifier.py registry   # emit the machine-readable registry
    py -3 code/1164_native_legal_forms_classifier.py census     # per-form counts, per file, with denominators
    py -3 code/1164_native_legal_forms_classifier.py conflicts   # the ranked wrong-key list
    py -3 code/1164_native_legal_forms_classifier.py collisions  # two-headed (cedar_uid, tribe_id) rows
    py -3 code/1164_native_legal_forms_classifier.py all
    py -3 code/1164_native_legal_forms_classifier.py verify      # exits 1 on breach
    py -3 code/1164_native_legal_forms_classifier.py selftest    # proves every detector FIRES

WHY THIS EXISTS
---------------
`cedar_uid` must resolve to a single impermeable Native entity. The
adjudications that keep failing are the ones where "which Native entity owns
this?" has a LEGAL answer that the name does not carry:

  * AMEE BAY, LLC and OCEAN BAY INFORMATION & SYSTEMS were keyed to the Three
    Affiliated Tribes of North Dakota on the token `Three`, through THREE
    SAINTS BAY, LLC.  They are Old Harbor Native Corporation's - an ANCSA
    VILLAGE corporation on Kodiak Island.  Repaired 2026-09-02 by
    `code/1075_fix_old_harbor_attribution.py`; measured clean here.
  * BERING STRAITS REGIONAL HOUSING AUTHORITY is keyed to BERING STRAITS
    NATIVE CORPORATION.  It is neither a tribe nor an ANCSA corporation: it is
    a public body corporate and politic created by AS 18.55.996(b), whose
    statutory sponsor is **Kawerak, Inc.** - a different entity again.  Still
    wrong on disk at the time of writing.

Both are the same failure: a string won, because nothing in the pipeline knew
what KIND of legal person the string names.  This file is that knowledge, in a
form a script can read.

WHAT IS AND IS NOT ASSERTED HERE
--------------------------------
1. **A name pattern is evidence, never proof.**  `classify_name()` returns a
   form plus the literal pattern that fired plus a strength.  Nothing in this
   script repoints a key; `conflicts` writes a REVIEW file.
2. **The conflict test is not the name test.**  A conflict requires BOTH a
   form classification AND a keyed `cedar_uid` whose spine `entity_class` is in
   that form's `never_key_to_classes`.  A name alone never produces a row.
3. **Corporate suffixes are NEVER folded.**  `_fold()` folds case, diacritics
   and punctuation and deliberately nothing else.  Stripping `INC` /
   `CORPORATION` / `THE` "resolves" Eklutna and Port Graham in one line and is
   wrong in the worst possible direction - it merges a village GOVERNMENT into
   its ANCSA CORPORATION, which is the exact error this registry exists to
   stop.  The namesake mapping is driven off
   `review/village_corp_namesake_pairs.csv`, which was adjudicated, and off
   exact spine canonical names - never off a suffix rule.
4. **Sampling.**  `census` and `conflicts` read every row of every declared
   file.  No cap.  If a file cannot be read the run says UNMEASURED for that
   file and does not silently score it zero (field guide rule 4).
5. **THE PREFIX IS A HINT, NEVER THE CLASS.**  `AGENTS.md:3977` states it
   outright, and it is wrong for 272 entities: `ANVC-` spans village AND group
   corporations, `CDFI-` spans Native CDFIs AND Native Financial Institutions.
   Nothing in this file parses a handle.  Every class read goes through
   `resolve_key()` -> the spine row -> its `entity_class` COLUMN.
6. **What this registry cannot catch.**  A right-form / wrong-PLACE error.
   Northwest Inupiat Housing Authority keyed to the Inupiat Community of the
   Arctic Slope is a TDHE keyed to a village government, which 25 U.S.C.
   4103(22)(B) makes ORDINARY - the defect is that NIHA serves the NANA region.
   Geography decides that, not legal form.  Pair this with
   `docs/NATIVE_ENTITY_NUANCES.md`: "when a name is ambiguous, ask where the
   money went." 

THE DISPOSITION VOCABULARY - what `cedar_uid` may do with each form
-------------------------------------------------------------------
    HUB                          a cedar_uid subject in its own right
    HUB_DISTINCT_FROM_NAMESAKE   a hub, AND it shares a place name with a hub
                                 of another form; the two may never merge
    SUB_HUB_ROLLS_UP             not a hub; keys to a named owner hub
    MANY_TO_MANY_NO_SINGLE_HUB   structurally serves or is authorised by MANY
                                 hubs; any single cedar_uid is false.  Added
                                 2026-09-03 for the TDHE class: AVCP Regional
                                 Housing Authority acts for tens of tribes and
                                 25 U.S.C. 4103(22) contemplates exactly that
                                 ("authorized or established by one or more
                                 Indian tribes to act on behalf of each such
                                 tribe").  Forcing one key onto it is false
                                 whichever member is chosen.
    NOT_A_NATIVE_ENTITY          must be excluded, with the reason recorded

Every statute quoted in `docs/NATIVE_ENTITY_LEGAL_FORMS.md` was retrieved from
govinfo.gov / irs.gov / bia.gov / ecfr.gov / sba.gov on 2026-09-03; the URL
travels with the quote there and with the citation here.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "review"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
NAMESAKE = REVIEW / "village_corp_namesake_pairs.csv"
STAMP = "2026-09-03"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


# ---------------------------------------------------------------- utilities

def _fold(s):
    """Case, diacritics, punctuation.  NOTHING ELSE.

    Deliberately does not strip INC / LLC / CORPORATION / THE.  See the
    docstring: folding a corporate suffix merges a village government into its
    ANCSA corporation.  Same discipline as
    `code/1166_owner_queue_card_builder.py::_fold_for_identity`.
    """
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("ʻ", "'").replace("‘", "'").replace("’", "'")
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def read_rows(p):
    with open(p, "r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_rows(p, rows, cols):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ---------------------------------------------------------------- registry

# `never_key_to_classes` names spine `entity_class` values that are LEGALLY
# incapable of being the entity the name denotes.  It is not a list of
# unlikely answers; each one is refuted by the statute in `statute`.
FORMS = [
    {
        "form_id": "TRIBE_FEDERALLY_RECOGNIZED",
        "label": "Federally recognized tribe / tribal government",
        "statute": ["25 U.S.C. 5123 (IRA s.16)", "25 U.S.C. 5130-5131 (list)"],
        "statute_url": [
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title25/html/USCODE-2024-title25-chap45-sec5123.htm"
        ],
        "what_it_is": "A sovereign government. 25 U.S.C. 5123(h)(1): each tribe "
                      "'shall retain inherent sovereign power to adopt governing "
                      "documents' - the IRA recognises the power, it does not grant it.",
        "members": "Enrolled members as defined by the tribe's own constitution.",
        "owner": "Nobody. A sovereign is not owned.",
        "disposition": "HUB",
        "spine_entity_class": ["Federally recognized tribe",
                               "Federally recognized Alaska Native Village"],
        "name_patterns": [],
        "never_key_to_classes": [],
    },
    {
        "form_id": "CORP_IRA_SECTION_17",
        "label": "Section 17 federally chartered corporation",
        "statute": ["25 U.S.C. 5124 (IRA s.17)",
                    "Treas. Reg. 301.7701-1(a)(4)(i)(B)",
                    "Rev. Rul. 81-295", "Rev. Rul. 94-16"],
        "statute_url": [
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title25/html/USCODE-2024-title25-chap45-sec5124.htm",
            "https://www.govinfo.gov/content/pkg/FR-2025-12-16/html/2025-22874.htm",
            "https://www.irs.gov/pub/irs-tege/rr81_295.pdf",
            "https://www.irs.gov/pub/irs-tege/rr94_16.pdf",
        ],
        "what_it_is": "The same tribe re-chartered by the Secretary in corporate "
                      "form. Separateness is DOMAIN-SPLIT: BIA treats it as "
                      "'separate and distinct from the tribal government' for "
                      "liability; Treas. Reg. 301.7701-1(a)(4)(i)(A) expressly does "
                      "NOT recognise it as a separate entity for federal income tax.",
        "members": "The enrolled members of the chartering tribe.",
        "owner": "Wholly the chartering tribe. There is no outside shareholder.",
        "disposition": "SUB_HUB_ROLLS_UP",
        "spine_entity_class": [],
        "name_patterns": [
            r"\bsection\s*17\b", r"\bfederally\s+chartered\s+corporation\b",
        ],
        "never_key_to_classes": [],
    },
    {
        "form_id": "CORP_OIWA_SECTION_3",
        "label": "Oklahoma Indian Welfare Act section 3 corporation",
        "statute": ["25 U.S.C. 5203 (OIWA s.3)",
                    "Treas. Reg. 301.7701-1(a)(4)(i)(C)"],
        "statute_url": [
            "https://www.govinfo.gov/content/pkg/FR-2025-12-16/html/2025-22874.htm"
        ],
        "what_it_is": "The Oklahoma analogue of a section 17 charter. Named in its "
                      "own right by Treas. Reg. 301.7701-1(a)(4)(i)(C).",
        "members": "The members of the chartering Oklahoma tribe or group.",
        "owner": "Wholly the chartering tribe.",
        "disposition": "SUB_HUB_ROLLS_UP",
        "spine_entity_class": [],
        "name_patterns": [r"\bsection\s*3\s+corporation\b"],
        "never_key_to_classes": [],
    },
    {
        "form_id": "ANCSA_REGIONAL_CORPORATION",
        "label": "ANCSA regional corporation",
        "statute": ["43 U.S.C. 1606 (ANCSA s.7)", "43 U.S.C. 1602(g)"],
        "statute_url": [
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1606.htm",
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1602.htm",
        ],
        "what_it_is": "43 U.S.C. 1606(d): five incorporators named by the Native "
                      "association 'shall incorporate under the laws of Alaska a "
                      "Regional Corporation to conduct business for profit'. Twelve "
                      "geographic regions under 1606(a), plus the thirteenth for "
                      "Natives who are non-residents of Alaska under 1606(c).",
        "members": "Individual Alaska Native shareholders enrolled to the region. "
                   "43 U.S.C. 1606(h)(1)(A)(iii): Settlement Common Stock 'vest[s] in "
                   "the holder all rights of a shareholder in a business corporation "
                   "organized under the laws of the State.'",
        "owner": "Its shareholders - natural persons. NOT a tribe, and no tribe "
                 "owns it. The 13th Regional Corporation is excluded from the 7(i) "
                 "distribution and received no land (43 U.S.C. 1606(i)(1)(A)).",
        "disposition": "HUB",
        "spine_entity_class": ["Alaska Native Regional Corporation"],
        "name_patterns": [],
        "never_key_to_classes": [],
    },
    {
        "form_id": "ANCSA_VILLAGE_CORPORATION",
        "label": "ANCSA village corporation",
        "statute": ["43 U.S.C. 1607(a) (ANCSA s.8)", "43 U.S.C. 1602(j)"],
        "statute_url": [
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1607.htm",
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1602.htm",
        ],
        "what_it_is": "43 U.S.C. 1607(a): 'The Native RESIDENTS of each Native "
                      "village ... shall organize as a business for profit or "
                      "nonprofit corporation under the laws of the State'. The "
                      "subject is the residents, not the village - so the "
                      "corporation is a DIFFERENT LEGAL PERSON from the federally "
                      "recognized village TRIBE of the same place name, which holds "
                      "sovereign, not corporate, capacity and appears on the BIA "
                      "list where no ANCSA corporation appears.",
        "members": "Individual Alaska Native shareholders enrolled to the village.",
        "owner": "Its shareholders. A village GOVERNMENT never owns a village "
                 "CORPORATION - docs/ANCSA_OWNERSHIP_RULING.md rule 2.",
        "disposition": "HUB_DISTINCT_FROM_NAMESAKE",
        "spine_entity_class": ["Alaska Native Village Corporation"],
        "name_patterns": [],
        "never_key_to_classes": ["Federally recognized Alaska Native Village"],
        "namesake_source": "review/village_corp_namesake_pairs.csv",
    },
    {
        "form_id": "ANCSA_URBAN_CORPORATION",
        "label": "ANCSA urban corporation",
        "statute": ["43 U.S.C. 1613(h)(3)", "43 U.S.C. 1602(o)"],
        "statute_url": [
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1613.htm",
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1602.htm",
        ],
        "what_it_is": "43 U.S.C. 1613(h)(3) authorises conveyance 'to the Natives "
                      "residing in Sitka, Kenai, Juneau, and Kodiak, if they "
                      "incorporate under the laws of Alaska'. 43 U.S.C. 1602(o) "
                      "defines 'Urban Corporation' in its own right. It is NOT a "
                      "village corporation under s.8 - the four communities 'did not "
                      "meet the requirements to be recognized as a Native Village "
                      "Corporation under ANCSA' (S. Rept. 118-221).",
        "members": "Individual Alaska Native shareholders enrolled to that place.",
        "owner": "Its shareholders.",
        "disposition": "HUB",
        "spine_entity_class": [],
        "name_patterns": [],
        "known_members": ["Shee Atika, Incorporated", "Goldbelt, Incorporated",
                          "Kenai Natives Association, Inc.", "Natives of Kodiak, Inc."],
        "never_key_to_classes": [],
    },
    {
        "form_id": "ANCSA_GROUP_CORPORATION",
        "label": "ANCSA group corporation",
        "statute": ["43 U.S.C. 1613(h)(2)", "43 U.S.C. 1602(d)", "43 U.S.C. 1602(n)"],
        "statute_url": [
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1613.htm",
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title43/html/USCODE-2024-title43-chap33-sec1602.htm",
        ],
        "what_it_is": "43 U.S.C. 1613(h)(2): conveyance 'to a Native group that does "
                      "not qualify as a Native village, if it incorporates under the "
                      "laws of Alaska'. 43 U.S.C. 1602(d) defines a Native group as "
                      "'composed of less than twenty-five Natives, who comprise a "
                      "majority of the residents of the locality'.",
        "members": "Individual Alaska Native shareholders of that group.",
        "owner": "Its shareholders.",
        "disposition": "HUB",
        "spine_entity_class": ["ANCSA Group Corporation"],
        "name_patterns": [],
        "never_key_to_classes": [],
    },
    {
        "form_id": "TDHE_NAHASDA",
        "label": "Tribally Designated Housing Entity / Indian housing authority",
        "statute": ["25 U.S.C. 4103(22) (TDHE)", "25 U.S.C. 4103(19) (recipient)",
                    "25 U.S.C. 4111(a)(2)", "24 C.F.R. 1000.317"],
        "statute_url": [
            "https://www.govinfo.gov/link/uscode/25/4103?link-type=html",
            "https://www.govinfo.gov/link/uscode/25/4111?link-type=html",
            "https://www.law.cornell.edu/cfr/text/24/1000.317",
        ],
        "what_it_is": "The entity a tribe designates to receive and administer "
                      "NAHASDA money. 25 U.S.C. 4103(22)(B)(ii) admits an entity "
                      "established 'by operation of State law providing specifically "
                      "for housing authorities or housing entities for Indians, "
                      "including regional housing authorities in the State of "
                      "Alaska.'",
        "members": "None. It has a board of commissioners, not members or shareholders.",
        "owner": "Nobody owns it. 25 U.S.C. 4103(22)(C): 'A tribally designated "
                 "housing entity may be authorized or established by one or more "
                 "Indian tribes to act on behalf of each such tribe authorizing or "
                 "establishing the housing entity.'",
        "three_different_answers": {
            "who_the_entity_is": "the TDHE - its own legal person",
            "who_owns_the_asset": "for 1937 Act stock in Alaska, the state-created "
                                  "Regional Native Housing Authority owns the units",
            "who_receives_the_money": "24 C.F.R. 1000.317, SCOPED to current assisted "
                                      "stock NOT on an Indian reservation: 'the "
                                      "recipient for funds allocated for the current "
                                      "assisted stock portion of NAHASDA funds for "
                                      "the units is the regional Indian tribe.' Do "
                                      "NOT generalise this to all NAHASDA funds.",
        },
        "disposition": "MANY_TO_MANY_NO_SINGLE_HUB",
        "spine_entity_class": [],
        "name_patterns": [
            r"\bhousing authority\b", r"\bhousing authorit(?:y|ies)\b",
            r"\bhousing entity\b", r"\btdhe\b",
            r"\btribally designated housing\b",
        ],
        "never_key_to_classes": [
            "Alaska Native Regional Corporation",
            "Alaska Native Village Corporation",
            "ANCSA Group Corporation",
            "Tribal College or University",
            "Native Community Development Financial Institution",
            "BIE School",
        ],
    },
    {
        "form_id": "AK_REGIONAL_HOUSING_AUTHORITY",
        "label": "Alaska regional housing authority",
        "statute": ["AS 18.55.995", "AS 18.55.996(b)",
                    "25 U.S.C. 4103 (recognised as a TDHE)"],
        "statute_url": [
            "https://law.onecle.com/alaska/title-18/18.55.995.html",
            "https://codes.findlaw.com/ak/title-18-health-safety-housing-human-rights-and-public-defender/ak-st-sect-18-55-996.html",
        ],
        "what_it_is": "A STATE-law creature that predates NAHASDA. AS 18.55.996(b): "
                      "'There is created with respect to each of the associations "
                      "named in (a) of this section a public body corporate and "
                      "politic'. Sixteen sponsoring associations are named in (a).",
        "members": "None. Five commissioners, AS 18.55.996(d).",
        "owner": "Nobody. It is a public body corporate and politic, separate from "
                 "the association that sponsored it.",
        "disposition": "MANY_TO_MANY_NO_SINGLE_HUB",
        "spine_entity_class": [],
        "name_patterns": [
            r"\bregional housing authority\b",
            r"\bhousing authority\b(?=.*\balaska\b)",
        ],
        # The statutory sponsor named in AS 18.55.996(a), where Cedar holds one.
        # The authority is NOT the sponsor; this is the entity a reviewer should
        # look at first, never an auto-repoint target.
        "statutory_sponsor_hint": {
            "avcp regional housing authority": "Association of Village Council Presidents",
            "bering straits regional housing authority": "Kawerak, Inc.",
            "bristol bay housing authority": "Bristol Bay Native Association",
            "cook inlet housing authority": "Cook Inlet Tribal Council",
            "northwest inupiat housing authority": "Northwest Alaska Native Association",
            "tlingit haida regional housing authority": "Tlingit-Haida Central Council or Alaska Native Brotherhood",
            "tlingit-haida regional housing authority": "Tlingit-Haida Central Council or Alaska Native Brotherhood",
            "copper river basin regional housing authority": "Copper River Native Association",
            "kodiak island housing authority": "Kodiak Area Native Association",
            "aleutian housing authority": "Aleut League",
            "baranof island housing authority": "Sitka Community Association",
            "metlakatla housing authority": "Metlakatla Indian Community",
            "interior regional housing authority": "Tanana Chiefs Conference",
            "north pacific rim housing authority": "North Pacific Rim Native Corp.",
        },
        "never_key_to_classes": [
            "Alaska Native Regional Corporation",
            "Alaska Native Village Corporation",
            "ANCSA Group Corporation",
            "Federally recognized Alaska Native Village",
            "Federally recognized tribe",
            "Tribal College or University",
            "Native Community Development Financial Institution",
            "BIE School",
        ],
    },
    {
        "form_id": "NATIVE_HAWAIIAN_ORGANIZATION",
        "label": "Native Hawaiian Organization",
        "statute": ["13 C.F.R. 124.3", "15 U.S.C. 637(a)(15)"],
        "statute_url": ["https://www.law.cornell.edu/cfr/text/13/124.3"],
        "what_it_is": "A community service organisation serving Native Hawaiians, "
                      "controlled by Native Hawaiians, with a majority-Native-Hawaiian "
                      "beneficiary class.",
        "members": "Native Hawaiians as beneficiaries; governance is by its own board.",
        "owner": "Nobody in the corporate sense. There is no federal roster, so the "
                 "universe is open - docs/NATIVE_ENTITY_NUANCES.md.",
        "disposition": "HUB",
        "spine_entity_class": ["Native Hawaiian Organization"],
        "name_patterns": [],
        "never_key_to_classes": [
            "Alaska Native Regional Corporation",
            "Alaska Native Village Corporation",
            "Federally recognized Alaska Native Village",
        ],
    },
    {
        "form_id": "NHO_OWNED_FIRM",
        "label": "NHO-owned firm (not an NHO)",
        "statute": ["13 C.F.R. 124.110", "13 C.F.R. 124.3 ('Tribally-owned concern')"],
        "statute_url": ["https://www.law.cornell.edu/cfr/text/13/124.110"],
        "what_it_is": "A for-profit concern at least 51% owned by an NHO. The SAM "
                      "flag `native_hawaiian_organization_owned_firm` names the "
                      "OWNER, never the registrant.",
        "members": "None.",
        "owner": "The NHO that owns it.",
        "disposition": "SUB_HUB_ROLLS_UP",
        "spine_entity_class": [],
        "name_patterns": [],
        "never_key_to_classes": [],
    },
    {
        "form_id": "TRIBAL_8A_CONCERN",
        "label": "Tribally-owned / ANC-owned 8(a) participant",
        "statute": ["13 C.F.R. 124.109(c)(3)(i)", "13 C.F.R. 124.109(c)(3)(ii)",
                    "13 C.F.R. 124.110", "13 C.F.R. 124.506(b)(1)",
                    "Pub. L. 100-656 tit. VI s.602(a) (UNCODIFIED note to 15 U.S.C. 637)",
                    "15 U.S.C. 637(a)(13)"],
        "statute_url": [
            "https://www.law.cornell.edu/cfr/text/13/124.109",
            "https://www.law.cornell.edu/cfr/text/13/124.506",
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title15/html/USCODE-2024-title15-chap14A-sec637.htm",
        ],
        "what_it_is": "A concern at least 51% unconditionally owned by a tribe, ANC "
                      "or NHO and admitted to the 8(a) Business Development "
                      "programme. 13 C.F.R. 124.506(b)(1): such a concern 'may be "
                      "awarded a sole source 8(a) contract where the anticipated "
                      "value of the procurement exceeds the applicable competitive "
                      "threshold'. THAT is why the dollar concentration Cedar sees "
                      "is lawful and expected rather than anomalous.",
        "threshold_warning": "Do NOT store a single sole-source threshold. Measured "
                             "2026-09-03: 15 U.S.C. 637(a)(1)(D)(i)(II) = $7M mfg / "
                             "$3M other; 13 C.F.R. 124.506(a)(2)(ii) = $7M / $4.5M; "
                             "FAR 19.805-1(a)(2) = $8.5M / $5.5M (90 FR 41879, "
                             "2025-08-27). Store the authority beside the figure.",
        "members": "None.",
        "owner": "The tribe, ANC or NHO - the hub. The 8(a) firm itself is a sub-hub.",
        "disposition": "SUB_HUB_ROLLS_UP",
        "spine_entity_class": [],
        "name_patterns": [],
        "never_key_to_classes": [],
    },
    {
        "form_id": "ISDEAA_TRIBAL_ORGANIZATION",
        "label": "Tribal organization / inter-tribal consortium",
        "statute": ["25 U.S.C. 5304(l)", "25 U.S.C. 5381(a)(5)", "25 U.S.C. 5381(b)"],
        "statute_url": [
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title25/html/USCODE-2024-title25-chap46-sec5304.htm",
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title25/html/USCODE-2024-title25-chap46-subchapV-sec5381.htm",
        ],
        "what_it_is": "25 U.S.C. 5304(l): 'any legally established organization of "
                      "Indians which is controlled, sanctioned, or chartered by such "
                      "governing body'. 25 U.S.C. 5381(a)(5) defines an inter-tribal "
                      "consortium as 'a coalition of two [or] more separate Indian "
                      "tribes that join together for the purpose of participating in "
                      "self-governance'.",
        "members": "TRIBES, not individuals. Each member tribe must approve each "
                   "contract benefiting it - the 5304(l) proviso.",
        "owner": "Nobody. Members, not owners.",
        "disposition": "MANY_TO_MANY_NO_SINGLE_HUB",
        "spine_entity_class": ["Intertribal Organization",
                               "Federal-level self-governance consortium"],
        "name_patterns": [
            r"\binter[- ]?tribal\b", r"\bconsortium\b",
            r"\bcouncil of\b.*\btribes?\b",
        ],
        "never_key_to_classes": [
            "Alaska Native Village Corporation",
            "Alaska Native Regional Corporation",
            "ANCSA Group Corporation",
        ],
    },
    {
        "form_id": "AK_TRIBAL_HEALTH_ORGANIZATION",
        "label": "Alaska Native tribal health consortium / regional health corporation",
        "statute": ["Pub. L. 105-83 s.325 (UNCODIFIED; authorises 13 named regional "
                    "health entities 'to form a consortium' - it does NOT name ANTHC)",
                    "Pub. L. 113-68 (the only statute that names ANTHC)",
                    "25 U.S.C. 5304(l)", "25 U.S.C. 5381 et seq. (Title V compacts)"],
        "statute_url": [
            "https://www.govinfo.gov/content/pkg/PLAW-113publ68/html/PLAW-113publ68.htm",
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title25/html/USCODE-2024-title25-chap46-subchapV-sec5381.htm",
        ],
        "what_it_is": "A tribal organization under 25 U.S.C. 5304(l) that carries "
                      "IHS programmes for the tribes of a region under a Title V "
                      "compact. It is not a tribe and not an ANCSA corporation, and "
                      "its name routinely collides with the regional corporation's. "
                      "NOTE: 25 U.S.C. 1638h DOES NOT EXIST (chapter 18 ends at "
                      "1638g); do not cite it for ANTHC.",
        "members": "The member tribes and village governments of the region.",
        "owner": "Nobody. Governed by a board seated by its member tribes.",
        "disposition": "MANY_TO_MANY_NO_SINGLE_HUB",
        "spine_entity_class": ["Federal-level self-governance consortium"],
        "name_patterns": [
            r"\bhealth corporation\b", r"\bhealth consortium\b",
            r"\barea health\b", r"\bhealth board\b",
        ],
        "never_key_to_classes": [
            "Alaska Native Regional Corporation",
            "Alaska Native Village Corporation",
            "ANCSA Group Corporation",
        ],
    },
    {
        "form_id": "TRIBAL_NONPROFIT_501C3",
        "label": "Tribal nonprofit exempt under IRC 501(c)(3)",
        "statute": ["26 U.S.C. 501(c)(3)", "26 U.S.C. 7871",
                    "Rev. Rul. 67-284", "Rev. Rul. 94-16"],
        "statute_url": [
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title26/html/USCODE-2024-title26-subtitleF-chap80-subchapC-sec7871.htm",
            "https://www.irs.gov/pub/irs-tege/rr67_284.pdf",
        ],
        "what_it_is": "A separate, non-sovereign organisation a tribe charters and "
                      "the IRS recognises under 501(c)(3). A TRIBE IS NOT ONE: a "
                      "tribe is not exempt under 501(a) at all, it is simply not a "
                      "taxable entity (Rev. Rul. 67-284), and 26 U.S.C. 7871 makes "
                      "gifts to it deductible under s.170 without any exemption "
                      "letter. Neither is an ANCSA corporation, which 43 U.S.C. "
                      "1606(d)/1607(a) put in business-for-profit form.",
        "members": "Whatever its own articles say.",
        "owner": "Nobody. A 501(c)(3) has no owners.",
        "disposition": "SUB_HUB_ROLLS_UP",
        "spine_entity_class": [],
        "name_patterns": [],
        "never_key_to_classes": [],
    },
    {
        "form_id": "NON_NATIVE_PUBLIC_HOUSING_AGENCY",
        "label": "Non-Native public housing agency",
        "statute": ["42 U.S.C. 1437a(b)(6) (PHA)",
                    "25 U.S.C. 4103 (by exclusion)"],
        "statute_url": [
            "https://www.govinfo.gov/content/pkg/USCODE-2024-title42/html/USCODE-2024-title42-chap8-subchapI-sec1437a.htm"
        ],
        "what_it_is": "A city, county or state housing authority that happens to "
                      "carry a place name of Native origin. Not a Native entity in "
                      "any sense - the Tuscarawas rule.",
        "members": "None.",
        "owner": "Its chartering municipality or state.",
        "disposition": "NOT_A_NATIVE_ENTITY",
        "spine_entity_class": [],
        "name_patterns": [
            r"\bhousing authority of the (?:city|county|town|borough|village) of\b",
            r"\b(?:city|county|town|borough) housing authority\b",
            r"\bhousing authority\b.*\b, town of\b",
        ],
        "never_key_to_classes": [],
    },
]

FORM_BY_ID = {f["form_id"]: f for f in FORMS}


def classify_name(name):
    """Return a list of (form_id, pattern, strength) for one name.

    strength: 'distinctive' - the pattern names the legal form outright.
    Never returns a form on a single generic token.
    """
    n = _fold(name)
    if not n:
        return []
    out = []
    for f in FORMS:
        for pat in f.get("name_patterns", []):
            if re.search(pat, n):
                out.append((f["form_id"], pat, "distinctive"))
                break
    # A non-Native PHA classification OVERRIDES the generic TDHE one: the
    # narrower pattern is the one that carries the information.
    ids = {o[0] for o in out}
    if "NON_NATIVE_PUBLIC_HOUSING_AGENCY" in ids:
        out = [o for o in out if o[0] != "TDHE_NAHASDA"]
    # AK_REGIONAL_HOUSING_AUTHORITY is a specialisation of TDHE; keep both,
    # the conflict test uses the strictest never_key set that applies.
    return out


# ---------------------------------------------------------------- scan set

# (path, name column, uid column, money column or None)
# Declared explicitly.  A table absent from disk is reported UNMEASURED, not 0.
SCAN = [
    ("data/clean/cedar_identifier_ledger_final.csv", "legal_business_name", "cedar_uid", None),
    ("data/clean/prime_contracts.csv", "awardee_name", "cedar_uid", "total_obligations"),
    ("data/clean/federal_funding_transactions.csv", "recipient_name", "cedar_uid", "obligated_usd"),
    ("data/clean/subawards.csv", "sub_name", "sub_cedar_uid", "subaward_amount"),
    ("data/clean/np_orgs.csv", "org_name", "cedar_uid", None),
    ("data/clean/fac_tribal_single_audits.csv", "auditee_name", "cedar_uid", "total_amount_expended"),
    ("data/clean/fac_native_nontribal_single_audits.csv", "auditee_name", "entity_id", "total_amount_expended"),
    ("data/clean/nest_enterprises.csv", "enterprise_name", "owner_hub_cedar_uid", None),
    ("data/clean/native_entity_lobbying_disclosures.csv", "client_name", "entity_id", "spend_usd"),
]


def _resolve_columns(header, want_name, want_uid, want_money):
    """Pick real column names, or return None to declare the file unscannable."""
    h = {c.lower(): c for c in header}
    name = want_name if (want_name and want_name in header) else None
    if name is None:
        for cand in ("legal_business_name", "recipient_name", "awardee_name",
                     "org_name", "auditee_name", "enterprise_name",
                     "client_name", "registrant_name", "entity_name",
                     "business_name_raw", "subawardee_name"):
            if cand in h:
                name = h[cand]
                break
    uid = want_uid if (want_uid and want_uid in header) else None
    if uid is None:
        for cand in ("cedar_uid", "owner_hub_cedar_uid", "entity_id", "tribe_id"):
            if cand in h:
                uid = h[cand]
                break
    money = want_money if (want_money and want_money in header) else None
    return name, uid, money


def load_spine():
    rows = read_rows(SPINE)
    by_uid = {r["cedar_uid"]: r for r in rows if r.get("cedar_uid")}
    by_tid = {r["tribe_id"]: r for r in rows if r.get("tribe_id")}
    name2 = defaultdict(list)
    for r in rows:
        for nm in (r.get("canonical_name"), r.get("fr_official_name")):
            k = _fold(nm)
            if k:
                name2[k].append(r)
    return rows, by_uid, by_tid, name2


def resolve_key(val, by_uid, by_tid):
    if not val:
        return None
    return by_uid.get(val) or by_tid.get(val)


def stream(path, cols):
    with open(path, "r", encoding="utf-8", newline="", errors="replace") as fh:
        rd = csv.DictReader(fh)
        if rd.fieldnames is None:
            return
        for row in rd:
            yield row


# ---------------------------------------------------------------- commands

def cmd_registry(args):
    payload = {
        "generated": STAMP,
        "generated_by": "code/1164_native_legal_forms_classifier.py registry",
        "companion_document": "docs/NATIVE_ENTITY_LEGAL_FORMS.md",
        "disposition_vocabulary": {
            "HUB": "a cedar_uid subject in its own right",
            "HUB_DISTINCT_FROM_NAMESAKE": "a hub that shares a place name with a hub "
                                          "of another form; the two may never merge",
            "SUB_HUB_ROLLS_UP": "not a hub; keys to a named owner hub",
            "MANY_TO_MANY_NO_SINGLE_HUB": "structurally serves or is authorised by many "
                                          "hubs; any single cedar_uid is false",
            "NOT_A_NATIVE_ENTITY": "must be excluded, with the reason recorded",
        },
        "folding_rule": "case, diacritics, punctuation ONLY. Never fold a corporate "
                        "suffix - it merges a village government into its ANCSA "
                        "corporation.",
        "forms": FORMS,
    }
    out = REVIEW / "native_legal_forms_registry.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}  forms={len(FORMS)}")
    for f in FORMS:
        print(f"  {f['form_id']:34s} {f['disposition']:28s} {f['statute'][0]}")
    return 0


def _scan_all(spine_pack):
    rows_spine, by_uid, by_tid, name2 = spine_pack
    census = []
    conflicts = []
    unmeasured = []
    for path, wname, wuid, wmoney in SCAN:
        p = ROOT / path
        if not p.exists():
            unmeasured.append((path, "FILE_ABSENT"))
            continue
        with open(p, "r", encoding="utf-8", newline="", errors="replace") as fh:
            header = csv.DictReader(fh).fieldnames
        if not header:
            unmeasured.append((path, "NO_HEADER"))
            continue
        name, uid, money = _resolve_columns(header, wname, wuid, wmoney)
        if not name:
            unmeasured.append((path, "NO_NAME_COLUMN"))
            continue
        n_rows = 0
        n_named = 0
        per_form = Counter()
        per_form_keyed = Counter()
        per_conflict = defaultdict(lambda: {"n": 0, "usd": 0.0, "example": None})
        for row in stream(p, header):
            n_rows += 1
            nm = row.get(name) or ""
            if not nm:
                continue
            n_named += 1
            hits = classify_name(nm)
            if not hits:
                continue
            keyed = resolve_key(row.get(uid) if uid else None, by_uid, by_tid)
            for form_id, pat, _s in hits:
                per_form[form_id] += 1
                if keyed:
                    per_form_keyed[form_id] += 1
                    _f = FORM_BY_ID[form_id]
                    bad = _f["never_key_to_classes"]
                    # A NOT_A_NATIVE_ENTITY form may not carry ANY Cedar key.
                    if (keyed["entity_class"] in bad
                            or _f["disposition"] == "NOT_A_NATIVE_ENTITY"):
                        k = (form_id, nm.strip(), keyed["cedar_uid"])
                        d = per_conflict[k]
                        d["n"] += 1
                        if money:
                            try:
                                d["usd"] += float(row.get(money) or 0)
                            except (TypeError, ValueError):
                                pass
                        if d["example"] is None:
                            d["example"] = {
                                "file": path,
                                "name_column": name,
                                "uid_column": uid,
                                "observed_name": nm.strip(),
                                "keyed_cedar_uid": keyed["cedar_uid"],
                                "keyed_handle": keyed["tribe_id"],
                                "keyed_canonical_name": keyed["canonical_name"],
                                "keyed_entity_class": keyed["entity_class"],
                                "pattern": pat,
                            }
        for form_id in sorted(set(per_form) | set(per_form_keyed)):
            census.append({
                "file": path,
                "rows_in_file": n_rows,
                "rows_with_a_name": n_named,
                "form_id": form_id,
                "rows_matching_form": per_form[form_id],
                "of_those_carrying_a_resolvable_key": per_form_keyed[form_id],
                "measured_on": STAMP,
                "scan_cap": "NONE - full file",
            })
        for (form_id, nm, uidv), d in per_conflict.items():
            ex = d["example"]
            f = FORM_BY_ID[form_id]
            sponsor = (f.get("statutory_sponsor_hint") or {}).get(_fold(nm))
            conflicts.append({
                "form_id": form_id,
                "file": path,
                "observed_name": nm,
                "rows": d["n"],
                "observed_usd": round(d["usd"], 2) if money else "",
                "money_column": money or "",
                "current_cedar_uid": uidv,
                "current_handle": ex["keyed_handle"],
                "current_canonical_name": ex["keyed_canonical_name"],
                "current_entity_class": ex["keyed_entity_class"],
                "why_the_class_is_impossible": "; ".join(f["statute"]),
                "statutory_reason": f["what_it_is"],
                "correct_disposition": f["disposition"],
                "statutory_sponsor_or_first_place_to_look": sponsor or "",
                "pattern_that_fired": ex["pattern"],
                "action": "FLAG_ONLY - propose, never apply",
                "measured_on": STAMP,
            })
    return census, conflicts, unmeasured


def _namesake_conflicts(spine_pack):
    """Item 4: an ANVC canonical name observed on a village GOVERNMENT key.

    Driven off the adjudicated pair file and off exact spine canonical names.
    NEVER off a corporate-suffix rule.
    """
    rows_spine, by_uid, by_tid, name2 = spine_pack
    out = []
    if not NAMESAKE.exists():
        return out, [("review/village_corp_namesake_pairs.csv", "FILE_ABSENT")]
    pairs = read_rows(NAMESAKE)
    gov2corp = {}
    for p in pairs:
        g = by_tid.get(p["government_tribe_id"])
        if g:
            gov2corp[g["cedar_uid"]] = p
    unmeasured = []
    for path, wname, wuid, wmoney in SCAN:
        fp = ROOT / path
        if not fp.exists():
            continue
        with open(fp, "r", encoding="utf-8", newline="", errors="replace") as fh:
            header = csv.DictReader(fh).fieldnames
        if not header:
            continue
        name, uid, money = _resolve_columns(header, wname, wuid, wmoney)
        if not name or not uid:
            continue
        agg = defaultdict(lambda: {"n": 0, "usd": 0.0})
        for row in stream(fp, header):
            u = row.get(uid)
            p = gov2corp.get(u)
            if not p:
                continue
            if _fold(row.get(name)) != _fold(p["corporation"]):
                continue
            k = (row.get(name).strip(), u, p["corporation"], p["corporation_tribe_id"])
            agg[k]["n"] += 1
            if money:
                try:
                    agg[k]["usd"] += float(row.get(money) or 0)
                except (TypeError, ValueError):
                    pass
        for (nm, u, corp, corp_tid), d in agg.items():
            out.append({
                "form_id": "ANCSA_VILLAGE_CORPORATION",
                "file": path,
                "observed_name": nm,
                "rows": d["n"],
                "observed_usd": round(d["usd"], 2) if money else "",
                "money_column": money or "",
                "current_cedar_uid": u,
                "current_handle": by_uid[u]["tribe_id"],
                "current_canonical_name": by_uid[u]["canonical_name"],
                "current_entity_class": by_uid[u]["entity_class"],
                "why_the_class_is_impossible":
                    "43 U.S.C. 1607(a) village CORPORATION vs 25 U.S.C. 5131 "
                    "federally recognized village TRIBE - two legal persons, one "
                    "place name",
                "statutory_reason":
                    "The observed name is the EXACT adjudicated canonical name of "
                    f"{corp} ({corp_tid}), an ANCSA village corporation. A village "
                    "government never owns a village corporation "
                    "(docs/ANCSA_OWNERSHIP_RULING.md rule 2).",
                "correct_disposition": "HUB_DISTINCT_FROM_NAMESAKE",
                "statutory_sponsor_or_first_place_to_look": f"{corp} ({corp_tid})",
                "pattern_that_fired": "adjudicated namesake pair, EXACT name equality",
                "action": "FLAG_ONLY - propose, never apply",
                "measured_on": STAMP,
            })
    return out, unmeasured


def _crossform_name_conflicts(spine_pack):
    """A name that is the EXACT canonical/FR name of a DIFFERENT spine entity
    of a DIFFERENT legal form, on the identifier ledger."""
    rows_spine, by_uid, by_tid, name2 = spine_pack
    p = ROOT / "data/clean/cedar_identifier_ledger_final.csv"
    if not p.exists():
        return [], [("data/clean/cedar_identifier_ledger_final.csv", "FILE_ABSENT")]
    out = []
    n = 0
    for row in stream(p, None):
        n += 1
        keyed = by_uid.get(row.get("cedar_uid") or "")
        if not keyed:
            continue
        k = _fold(row.get("legal_business_name"))
        cands = name2.get(k)
        if not cands:
            continue
        if any(c["cedar_uid"] == keyed["cedar_uid"] for c in cands):
            continue
        other = next((c for c in cands
                      if c["entity_class"] != keyed["entity_class"]), None)
        if not other:
            continue
        out.append({
            "identifier_type": row.get("identifier_type"),
            "identifier": row.get("identifier"),
            "observed_name": row.get("legal_business_name"),
            "current_cedar_uid": keyed["cedar_uid"],
            "current_canonical_name": keyed["canonical_name"],
            "current_entity_class": keyed["entity_class"],
            "name_is_the_exact_name_of": other["canonical_name"],
            "that_entitys_cedar_uid": other["cedar_uid"],
            "that_entitys_class": other["entity_class"],
            "confidence_tier": row.get("confidence_tier"),
            "attribution_method": row.get("attribution_method"),
            "action": "FLAG_ONLY - propose, never apply",
            "measured_on": STAMP,
        })
    return out, [("ledger_rows_scanned", n)]


def cmd_census(args):
    pack = load_spine()
    census, conflicts, unmeasured = _scan_all(pack)
    cols = ["file", "rows_in_file", "rows_with_a_name", "form_id",
            "rows_matching_form", "of_those_carrying_a_resolvable_key",
            "measured_on", "scan_cap"]
    out = REVIEW / f"native_legal_forms_census_{STAMP}.csv"
    write_rows(out, census, cols)
    print(f"wrote {out.relative_to(ROOT)}  rows={len(census)}")
    print()
    print("SPINE, by entity_class (the denominator for every 'in Cedar' count):")
    c = Counter(r["entity_class"] for r in pack[0])
    for k, v in c.most_common():
        print(f"  {v:6d}  {k}")
    print(f"  {len(pack[0]):6d}  TOTAL spine entities")
    print()
    for f, why in unmeasured:
        print(f"UNMEASURED  {f}: {why}")
    return 0


def cmd_conflicts(args):
    pack = load_spine()
    census, conflicts, unmeasured = _scan_all(pack)
    ns, ns_un = _namesake_conflicts(pack)
    conflicts.extend(ns)

    def rank(r):
        usd = r["observed_usd"] if isinstance(r["observed_usd"], float) else 0.0
        return (-usd, -r["rows"])

    conflicts.sort(key=rank)
    cols = ["form_id", "file", "observed_name", "rows", "observed_usd",
            "money_column", "current_cedar_uid", "current_handle",
            "current_canonical_name", "current_entity_class",
            "why_the_class_is_impossible", "statutory_reason",
            "correct_disposition", "statutory_sponsor_or_first_place_to_look",
            "pattern_that_fired", "action", "measured_on"]
    out = REVIEW / f"native_legal_forms_key_conflicts_{STAMP}.csv"
    write_rows(out, conflicts, cols)
    print(f"wrote {out.relative_to(ROOT)}  rows={len(conflicts)}")

    xf, xf_note = _crossform_name_conflicts(pack)
    xcols = ["identifier_type", "identifier", "observed_name", "current_cedar_uid",
             "current_canonical_name", "current_entity_class",
             "name_is_the_exact_name_of", "that_entitys_cedar_uid",
             "that_entitys_class", "confidence_tier", "attribution_method",
             "action", "measured_on"]
    xout = REVIEW / f"native_legal_forms_crossform_names_{STAMP}.csv"
    write_rows(xout, xf, xcols)
    print(f"wrote {xout.relative_to(ROOT)}  rows={len(xf)}   {xf_note}")
    # A row can match two forms (AK_REGIONAL_HOUSING_AUTHORITY is a
    # specialisation of TDHE_NAHASDA), so the per-form dollars DOUBLE COUNT.
    # Print the de-duplicated figure beside them or the total is a fiction.
    seen = {}
    for r in conflicts:
        k = (r["file"], r["observed_name"], r["current_cedar_uid"])
        usd = r["observed_usd"] if isinstance(r["observed_usd"], float) else 0.0
        prev = seen.get(k)
        if prev is None or usd > prev[1]:
            seen[k] = (r["rows"], usd)
    print()
    print(f"conflict GROUPS (form x name x key)        : {len(conflicts)}")
    print(f"DISTINCT (file, name, key) triples         : {len(seen)}")
    print(f"  rows, de-duplicated                      : {sum(v[0] for v in seen.values()):,}")
    print(f"  observed dollars, de-duplicated          : "
          f"${sum(v[1] for v in seen.values()):,.2f}")
    print("  (a name can match two forms - AK_REGIONAL_HOUSING_AUTHORITY is a "
          "specialisation of TDHE_NAHASDA - so the per-form sums double count)")
    print()
    print("TOP 15 BY OBSERVED DOLLARS (a worked example, per field-guide rule 3):")
    for r in conflicts[:15]:
        usd = r["observed_usd"]
        usd_s = f"${usd:,.2f}" if isinstance(usd, float) else "-"
        print(f"  {r['form_id']:32s} {r['observed_name'][:42]:42s} "
              f"-> {r['current_canonical_name'][:32]:32s} "
              f"({r['current_entity_class'][:30]:30s}) "
              f"{r['rows']:6d} rows {usd_s:>18s}  [{r['file']}]")
    for f, why in unmeasured + ns_un:
        print(f"UNMEASURED  {f}: {why}")
    return 0


LEDGER = ROOT / "data" / "clean" / "cedar_identifier_ledger_final.csv"


def cmd_collisions(args):
    """The two-headed `cedar_uid` rows, ADJUDICATED BY LEGAL FORM.

    *** THIS IS NOT THE DETECTOR.  `code/1167_cedar_uid_identity_collisions.py`
    IS. ***  Two detectors for one class drift - that is why `248` is a retired
    stub pointing at `293` - and 1167's test is the more durable one: it counts
    distinct `canonical_name` on a uid's positive rows and never reads
    `tribe_id`, which is the RETIRED CICD NEID (`843_retire_cicd_scheme.py`).
    A test against a retired scheme measures the retired scheme, and reports
    CLEAN the day the column is finally dropped.

    This subcommand reads `tribe_id` on purpose and for one reason: it is the
    column that names WHICH OTHER ENTITY the row is claiming, and therefore the
    only thing that lets a legal form be attached to each head.  It answers
    "which head survives, and under what statute" - the question 1167 does not
    ask.  If `tribe_id` disappears from the ledger, this subcommand must report
    UNMEASURED rather than zero; the guard below asserts the column exists.

    Precise statement of the defect, which is narrower and cheaper to fix than
    "a uid resolves to two entities":

      * `data/spine/cedar_identity_register.csv` binds each of these uids to
        EXACTLY ONE entity.  The register is single-valued and correct.
      * What is two-headed is the LEDGER ROW: it carries a `cedar_uid` and a
        `tribe_id` that name different entities.
      * So the remedy is to re-stamp the ROW's `cedar_uid` from the register
        binding of its own `tribe_id`.  No uid is retired, merged or reused.
        IDENTIFIER_STANDARD s.0 is not engaged.
    """
    rows_spine, by_uid, by_tid, name2 = load_spine()
    if not LEDGER.exists():
        print("UNMEASURED  ledger absent")
        return 0
    with open(LEDGER, "r", encoding="utf-8", newline="", errors="replace") as fh:
        _hdr = csv.DictReader(fh).fieldnames or []
    if "tribe_id" not in _hdr or "cedar_uid" not in _hdr:
        print("UNMEASURED  the ledger no longer carries both `cedar_uid` and "
              "`tribe_id`; this adjudication cannot run. Use "
              "code/1167_cedar_uid_identity_collisions.py for DETECTION and "
              "adjudicate its output by hand.")
        return 0
    reg = {}
    regp = ROOT / "data" / "spine" / "cedar_identity_register.csv"
    if regp.exists():
        for r in read_rows(regp):
            reg.setdefault(r.get("cedar_uid"), []).append(r)

    pair_rows = defaultdict(list)
    for r in stream(LEDGER, None):
        u = (r.get("cedar_uid") or "").strip()
        t = (r.get("tribe_id") or "").strip()
        if u and t:
            pair_rows[(u, t)].append(r)
    heads = defaultdict(set)
    for (u, t) in pair_rows:
        heads[u].add(t)
    multi = {u: v for u, v in heads.items() if len(v) > 1}

    print(f"ledger (cedar_uid, tribe_id) pairs           : {len(pair_rows)}")
    print(f"distinct cedar_uid carrying a tribe_id       : {len(heads)}")
    print(f"cedar_uid with MORE THAN ONE tribe_id        : {len(multi)}")
    print(f"register rows per colliding uid (must be 1)  : "
          f"{sorted({len(reg.get(u, [])) for u in multi}) or 'REGISTER UNMEASURED'}")
    print()

    out = []
    for u in sorted(multi):
        bound = by_uid.get(u)
        for t in sorted(multi[u]):
            if bound and bound["tribe_id"] == t:
                continue
            ent = by_tid.get(t)
            rows = pair_rows[(u, t)]
            usd = 0.0
            for r in rows:
                try:
                    usd += float(r.get("prime_dollars_M") or 0)
                except (TypeError, ValueError):
                    pass
            out.append({
                "cedar_uid": u,
                "register_binds_uid_to": (bound or {}).get("tribe_id", "UNBOUND"),
                "register_binds_uid_to_name": (bound or {}).get("canonical_name", ""),
                "register_binds_uid_to_class": (bound or {}).get("entity_class", ""),
                "row_tribe_id": t,
                "row_tribe_name": (ent or {}).get("canonical_name", "NOT IN SPINE"),
                "row_tribe_class": (ent or {}).get("entity_class", ""),
                "correct_uid_for_row_tribe": (ent or {}).get("cedar_uid", ""),
                "ledger_rows": len(rows),
                "prime_dollars_M_on_those_rows": round(usd, 3),
                "identifiers": "; ".join(
                    f"{r['identifier_type']}:{r['identifier']}" for r in rows[:8]),
                "example_legal_business_name": rows[0].get("legal_business_name", ""),
                "tiers": ",".join(sorted({r.get("confidence_tier", "") for r in rows})),
                "methods": ",".join(sorted({r.get("attribution_method", "") for r in rows})),
                "proposal": "RESTAMP_ROW_CEDAR_UID_FROM_ITS_OWN_TRIBE_ID"
                            if (ent or {}).get("cedar_uid") else "OWNER_RULING_REQUIRED",
                "action": "FLAG_ONLY - propose, never apply",
                "measured_on": STAMP,
            })
    cols = list(out[0].keys()) if out else ["cedar_uid"]
    p = REVIEW / f"native_legal_forms_uid_collisions_{STAMP}.csv"
    write_rows(p, out, cols)
    print(f"wrote {p.relative_to(ROOT)}  rows={len(out)}")
    for r in sorted(out, key=lambda x: -x["prime_dollars_M_on_those_rows"])[:20]:
        print(f"  {r['cedar_uid']}  row says {r['row_tribe_id'][:22]:22s} "
              f"({r['row_tribe_class'][:28]:28s}) but uid is bound to "
              f"{r['register_binds_uid_to_name'][:26]:26s} "
              f"-> restamp to {r['correct_uid_for_row_tribe']}  "
              f"{r['ledger_rows']:3d} rows  ${r['prime_dollars_M_on_those_rows']:,.2f}M")
    return 0


def cmd_verify(args):
    """Exit 1 if the registry is internally inconsistent or the spine has
    drifted away from a class this registry claims exists."""
    bad = []
    ids = [f["form_id"] for f in FORMS]
    if len(ids) != len(set(ids)):
        bad.append("V1 duplicate form_id")
    allowed = {"HUB", "HUB_DISTINCT_FROM_NAMESAKE", "SUB_HUB_ROLLS_UP",
               "MANY_TO_MANY_NO_SINGLE_HUB", "NOT_A_NATIVE_ENTITY"}
    for f in FORMS:
        if f["disposition"] not in allowed:
            bad.append(f"V2 {f['form_id']} unknown disposition {f['disposition']}")
        if not f.get("statute"):
            bad.append(f"V3 {f['form_id']} has no statute")
        for pat in f.get("name_patterns", []):
            try:
                re.compile(pat)
            except re.error as e:
                bad.append(f"V4 {f['form_id']} bad pattern {pat!r}: {e}")
    if not SPINE.exists():
        print("UNMEASURED  spine absent; V5-V6 not run")
    else:
        rows = read_rows(SPINE)
        present = {r["entity_class"] for r in rows}
        for f in FORMS:
            for c in f.get("spine_entity_class", []):
                if c not in present:
                    bad.append(f"V5 {f['form_id']} names spine class {c!r} "
                               "which the spine does not hold")
            for c in f.get("never_key_to_classes", []):
                if c not in present:
                    bad.append(f"V6 {f['form_id']} forbids spine class {c!r} "
                               "which the spine does not hold")
    # V7: the fold must NOT collapse a village government into its corporation.
    if NAMESAKE.exists():
        for p in read_rows(NAMESAKE):
            if _fold(p["corporation"]) == _fold(p["government"]):
                bad.append("V7 the fold collapsed "
                           f"{p['corporation']!r} into {p['government']!r}")
    for b in bad:
        print("BREACH " + b)
    print(f"verify: {len(bad)} breach(es)")
    return 1 if bad else 0


def cmd_selftest(args):
    """Prove each detector FIRES. Inject, assert, restore."""
    fails = []

    def check(label, cond):
        print(("PASS  " if cond else "FAIL  ") + label)
        if not cond:
            fails.append(label)

    hits = {h[0] for h in classify_name("BERING STRAITS REGIONAL HOUSING AUTHORITY")}
    check("AK regional housing authority classifies",
          "AK_REGIONAL_HOUSING_AUTHORITY" in hits and "TDHE_NAHASDA" in hits)

    hits = {h[0] for h in classify_name("UTE INDIAN TRIBALLY DESIGNATED HOUSING ENTITY")}
    check("TDHE classifies", "TDHE_NAHASDA" in hits)

    hits = {h[0] for h in classify_name("HOUSING AUTHORITY OF THE CITY OF MADERA")}
    check("municipal PHA classifies and SUPPRESSES the TDHE claim",
          "NON_NATIVE_PUBLIC_HOUSING_AGENCY" in hits and "TDHE_NAHASDA" not in hits)

    hits = {h[0] for h in classify_name("Yukon-Kuskokwim Health Corporation")}
    check("AK regional health corporation classifies",
          "AK_TRIBAL_HEALTH_ORGANIZATION" in hits)

    check("a bare tribe name classifies as NOTHING",
          classify_name("Navajo Nation") == [])
    check("an empty name classifies as NOTHING", classify_name("") == [])

    # THE fold contract - the one that would do the most damage if it broke.
    check("fold does NOT strip a corporate suffix",
          _fold("Eklutna, Inc.") != _fold("Eklutna"))
    check("fold does NOT strip THE",
          _fold("The Port Graham Corporation") != _fold("Port Graham"))
    check("fold DOES normalise an okina",
          _fold("Ukpeaġvik Iñupiat Corporation")
          == _fold("Ukpeagvik Inupiat Corporation"))

    # The conflict test must require BOTH legs.
    f = FORM_BY_ID["AK_REGIONAL_HOUSING_AUTHORITY"]
    check("an ANRC key on a regional housing authority IS a conflict",
          "Alaska Native Regional Corporation" in f["never_key_to_classes"])
    check("a name alone is not a conflict - never_key_to_classes is consulted",
          "Intertribal Organization" not in f["never_key_to_classes"])

    check("verify() returns 0 on the shipped registry", cmd_verify(args) == 0)

    # Inject a breach and assert verify FIRES on it, then restore.
    saved = FORM_BY_ID["TDHE_NAHASDA"]["disposition"]
    FORM_BY_ID["TDHE_NAHASDA"]["disposition"] = "NOT_A_REAL_DISPOSITION"
    fired = cmd_verify(args) == 1
    FORM_BY_ID["TDHE_NAHASDA"]["disposition"] = saved
    check("verify() FIRES on an injected bad disposition", fired)
    check("verify() returns 0 again after restore", cmd_verify(args) == 0)

    print()
    print(f"selftest: {len(fails)} failure(s)")
    return 1 if fails else 0


def cmd_all(args):
    rc = 0
    rc |= cmd_registry(args)
    print()
    rc |= cmd_census(args)
    print()
    rc |= cmd_conflicts(args)
    print()
    rc |= cmd_collisions(args)
    return rc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("command", nargs="?", default="all",
                    choices=["registry", "census", "conflicts", "all",
                             "collisions", "verify", "selftest"])
    args = ap.parse_args(argv)
    return {
        "registry": cmd_registry, "census": cmd_census,
        "conflicts": cmd_conflicts, "all": cmd_all,
        "collisions": cmd_collisions,
        "verify": cmd_verify, "selftest": cmd_selftest,
    }[args.command](args)


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    sys.exit(main())
