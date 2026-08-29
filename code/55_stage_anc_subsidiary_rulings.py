#!/usr/bin/env python3
"""
Cedar Press - 55: Stage Elijah's ANC-subsidiary ruling batch of 2026-08-05.

WHY A SCRIPT AND NOT A HAND-TYPED CSV
-------------------------------------
79 rulings, each a UEI + CAGE + owner. Transcribing those by hand invites a
one-character error in an identifier, which is unrecoverable noise. This
records them once, mechanically.

THE DISAMBIGUATION THIS FILE EXISTS TO GET RIGHT
------------------------------------------------
Four names now appear TWICE in the spine - once as a federally recognised
Alaska Native village GOVERNMENT (`AKNF-`) and once as an ANCSA village
CORPORATION (`ANVC-`): Afognak, Tyonek, Tatitlek, Eyak.

Elijah answered several cards with the bare village name ("Yes - Afognak")
against firms that are plainly federal contracting subsidiaries. Those belong
to the CORPORATION. He said so himself on the card that explains the whole
family:

    "alutiiq is the name of afognak native village corps federal contracting arm"

and he named the corporation outright for Tyonek ("THE TYONEK NATIVE
CORPORATION") and Eyak ("Eyak Corp there is a village and a village corp").

Resolving those to the village government would repeat exactly the category
error this project has been correcting all day - a village government does not
own an 8(a) defence contractor. So the bare village answers are mapped to the
corporation, and every mapping carries its reason in YOUR_NOTE.

The one deliberate exception is Copper River Information Technology, where
Elijah wrote "Native village of eyak" in full. That is the VILLAGE, named
deliberately, and it is left alone.

THE TRAP WORTH THE MOST
-----------------------
Four "Bristol" firms were proposed as Bristol Bay Native Corporation and are
actually CHOGGIUNG, LTD. - the Dillingham village corporation. "Bristol" is a
place name shared by a region and a corporate family that do not share an
owner. Without the village-corporation layer added earlier today there would
have been nothing correct to point them at.
"""

import csv
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
OUT = CEDAR / "review" / "rulings_inbox_2026-08-05L.csv"

# (uei, cage, firm, Elijah's answer verbatim)
D = [
    ("C147PB4NTAK6", "6A6U7", "Tyonek Global Services, Llc", "Yes - Tyonek"),
    ("C5DRJNDU5LD7", "745S2", "Bowhead Mission Solutions, Llc", "UKPEAGVIK INUPIAT CORPORATION"),
    ("CKB4JDLXQ9M3", "515D4", "Alutiiq Pacific, Llc", "Yes - Afognak"),
    ("D1DBARDKVRW1", "1BCB7", "Bristol Environmental & Engine", "CHOGGIUNG LTD."),
    ("D9KZT4XZLP21", "1TBH2", "Asrc Communications, Ltd", "Yes - Arctic Slope Regional Corporation"),
    ("DGK7B98L1MR3", "41VK0", "Akima Logistics Services LLC", "Yes - NANA Regional Corporation, Incorporated"),
    ("E3PXRWGLJ1H9", "6WYV5", "Yulista Tactical Services, Llc", "Yes - Calista Corporation"),
    ("EN37BU6PRPP3", "3DEQ9", "Alutiiq Global Solutions Llc", "Yes - Afognak"),
    ("ER4NK9VHCRR6", "4XH20", "Chugach World Services, Inc", "Yes - Chugach Alaska Corporation"),
    ("F7LSWJF8A2W3", "6A1Z0", "Sts Systems Integration", "Yes - Bristol Bay Native Corporation"),
    ("F8Q6Q81LJW84", "3NBM3", "Tkc Technology Solutions LLC", "Yes - NANA Regional Corporation, Incorporated"),
    ("F9M5KXFBC8N3", "3Q5W1", "Doyon Project Services Llc", "Yes - Doyon, Limited"),
    ("FC7GAXDMZG68", "3FJ62", "Bristol Construction Services", "CHOGGIUNG LTD"),
    ("FHGZCGT5FFZ3", "5E9U4", "Chugach Education Services, Inc.", "Yes - Chugach Alaska Corporation"),
    ("FJMFKR6UF9E9", "36HM0", "Glacier Technologies LLC", "Yes - Bristol Bay Native Corporation"),
    ("FM2KJG6M5363", "4CS13", "Copper River Information Technology LLC", "Native village of eyak"),
    ("GAJMUR8ZGMW5", "3PTG3", "Chugach Industries Incorporated", "Yes - Chugach Alaska Corporation"),
    ("GJKZD9ZEAEJ6", "4TEK8", "Alutiiq Business Services, Llc", "Yes - Afognak"),
    ("GM24PBBPUKK5", "66JD0", "Defense Base Services, Inc.", "Yes - Chugach Alaska Corporation"),
    ("GN2VKJH7LBC3", "7HDF1", "Tuknik Government Services Llc", "Yes - Koniag, Incorporated"),
    ("GRZ5EJZB3JC4", "637U4", "Bowhead Professional Solutions, Llc", "UKPEAGVIK INUPIAT CORPORATION"),
    ("GX34R4Y3RZ58", "5EHH6", "Wolf Creek Fabrication Services, Inc.", "Yes - Chugach Alaska Corporation"),
    ("H6WGLRDCU6D8", "70T18", "Asrc Federal Field Services, Llc", "Yes - Arctic Slope Regional Corporation"),
    ("HR78NDAERF44", "1TCQ2", "Njvc, Llc", "Yes - Chenega"),
    ("HYDWL7JCHBG4", "5B1S6", "Nexus Technology Solutions Llc", "Seneca Nation of Indians"),
    ("HZMLPMNZ37J8", "4MEL9", "Tatitlek Training Services, Inc.", "Yes - Tatitlek"),
    ("J6G4KHLDGTQ6", "6DJK8", "Chenega Technical Innovations, Llc", "Yes - Chenega"),
    ("JGSGGJJTAMK1", "1FZR6", "Petro Star, Inc.", "Yes - Arctic Slope Regional Corporation"),
    ("JW7MP65X8K11", "59PZ4", "Chugach Federal Solutions, Inc.", "Yes - Chugach Alaska Corporation"),
    ("JYP9MBX3TF16", "3B3H1", "Asrc Management Services Incorporated", "Yes - Arctic Slope Regional Corporation"),
    ("K5Y3MDHD2MB5", "0Z229", "Analytical Services, Inc.", "Yes - Arctic Slope Regional Corporation"),
    ("KK3NEJB74521", "38EC1", "Chenega Federal Systems LLC", "Yes - Chenega"),
    ("KNL4XHGBTFU5", "37MK0", "Tyonek Services Corporation", "THE TYONEK NATIVE CORPORATION"),
    ("KYN9K7FSCVN4", "3CX44", "Koniag Services Inc", "Yes - Koniag, Incorporated"),
    ("LHXMU1JZKJU5", "70XD3", "Tuva, Llc", "Yes - NANA Regional Corporation, Incorporated"),
    ("LJVAMDMLZJX6", "4KRX5", "Wolverine Services, Llc", "Yes - NANA Regional Corporation, Incorporated"),
    ("LT9JX6X1HLQ8", "1C2X1", "American Hospital Services Group Llc", "Yes - Chenega"),
    ("LUDNH5K4XQU9", "5UVQ9", "Akima Global Services, Llc", "Yes - NANA Regional Corporation, Incorporated"),
    ("M46UYYHVH4B1", "3NBK4", "Tkc Integration Services Llc", "Yes - NANA Regional Corporation, Incorporated"),
    ("MCJQHGA6NEL9", "4KLG9", "Gtw Consultants & Associates, Llc", "Yes - Chenega"),
    ("MJNJZE4LAHP6", "6TLQ7", "Chenega Facilities Management, Llc", "Yes - Chenega"),
    ("MMNMLCK4KTJ4", "4LQ20", "Tkc Global Solutions Llc", "Yes - NANA Regional Corporation, Incorporated"),
    ("NBEWZB8LQ8Z5", "5NTT4", "Inuteq, Llc", "Yes - Arctic Slope Regional Corporation"),
    ("NEQUZGMGAKJ7", "75QC0", "Alutiiq Information Management, Llc.", "Afognak Native Vilkage"),
    ("NKZQDVEJXJ34", "5U5K8", "Akima Support Operations, Llc", "Yes - NANA Regional Corporation, Incorporated"),
    ("NLCRUT3KG9R6", "39HU1", "Specpro Environmental Services LLC", "Yes - Bristol Bay Native Corporation"),
    ("P4U6EJ3PYRJ5", "52D75", "Cni Advantage, Llc", "Yes - The Chickasaw Nation"),
    ("P5GKBX8FR3M3", "7MU17", "Bering Global Solutions, Llc", "Yes - Bering Straits Native Corporation"),
    ("P62MLNFBEZA9", "38XB1", "Y-Tech Services, Inc.", "Yes - Calista Corporation"),
    ("P8P1LNPBERT1", "7CG51", "Rivertech, Llc", "Yes - NANA Regional Corporation, Incorporated"),
    ("PQNNHF72NNM6", "70UT1", "Cherokee Nation Research Laboratories, Llc", "Yes - Cherokee Nation"),
    ("PQVNSJMA2FU3", "32VS0", "Sava Workforce Solutions LLC", "Yes - NANA Regional Corporation, Incorporated"),
    ("PUNCXXLP4JS9", "6ZU55", "North Wind Solutions, Llc", "COOK INLET REGION, INC."),
    ("PYKLJT1PS8F5", "42HY5", "Bristol General Contractors, Llc", "CHOGGIUNG LTD"),
    ("Q5VGLSJYBGQ8", "35RZ1", "Aleut Facilities Support Servi", "THE ALEUT CORPORATION"),
    ("QA3CH4ZHCBG1", "08BM2", "Weldin Construction Inc", "Yes - Cook Inlet Region, Incorporated"),
    ("QMJEKNF3JN15", "6NGU5", "Alutiiq Commercial Enterprises Llc", "AFOGNAK NATIVE CORP"),
    ("QTJZT9K41S61", "6GTB0", "Laulima Government Solutions, Llc", "BERING STRAITS NATIVE CORPORATION"),
    ("RJ1MM7XUCBQ4", "4JLC9", "Alutiiq Diversified Services Llc", "Yes - Afognak"),
    ("RMLMYLD81VF1", "4TLV5", "Alutiiq 3Sg, Llc", "Yes - Afognak"),
    ("RNWRB1GWHQ45", "4WDR2", "Chenega Global Services, Llc", "Yes - Chenega"),
    ("SGK5EGB9VQM8", "6HBK6", "Arctic Slope Consulting Services, Inc.", "Yes - Arctic Slope Regional Corporation"),
    ("SKKXHJP1Y7L8", "6Q2H1", "Bowhead Business And Technology Solutions, Llc", "UKPEAGVIK INUPIAT CORPORATION"),
    ("TB9KZSRLKSB9", "4A3E3", "Ahtna Support And Training Services LLC", "Yes - Ahtna, Incorporated"),
    ("TJV3WEKNCAJ5", "4D3B0", "Choctaw Manufacturing Defense Contractors", "Yes - The Choctaw Nation of Oklahoma"),
    ("TYBBMBUXPFH6", "4HEW7", "Bristol Design Build Services, Llc", "CHOGGIUNG LTD."),
    ("UENJB2AT8GJ9", "58MN2", "Sand Point Services, Llc", "TANADGUSIX CORPORATION"),
    ("VF2ANJQHJ1N7", "49J93", "Asrc Research And Technology Solutions LLC", "Yes - Arctic Slope Regional Corporation"),
    ("VHRQPE9ZC7Q7", "3SKC7", "Tatitlek Support Services, Inc", "Yes - Tatitlek"),
    ("VS6LCU6LNYE5", "6NGU3", "Alutiiq Technical Services Llc", "Afognak"),
    ("VTW2SUMKNAA5", "1LKY0", "Chickasaw Nation Industries, I", "Yes - The Chickasaw Nation"),
    ("WTN8QPXDBFR5", "4WCU3", "Alutiiq Education & Training", "Yes - Afognak"),
    ("Y6EBGJ91P6R5", "4WZG2", "Tatitlek Technologies, Inc.", "Yes - Tatitlek"),
    ("YKBMG32J2LL5", "3BS35", "Eyak Technology, Llc", "Eyak Corp there is a village and a village corp"),
    ("YYZXLJD6NTZ9", "3GQG0", "Primus Solutions, Inc.", "Yes - Arctic Slope Regional Corporation"),
    ("Z1LGCNGU28Q6", "70U35", "Talu, Llc", "Yes - NANA Regional Corporation, Incorporated"),
    ("ZKBEHUM81WU7", "3L6C0", "Akima Facilities Management LLC", "Yes - NANA Regional Corporation, Incorporated"),
]

FIX = {
    "yes - tyonek": ("The Tyonek Native Corporation",
                     "CORPORATION, not the Native Village of Tyonek. A village "
                     "government does not own a federal contracting subsidiary."),
    "the tyonek native corporation": ("The Tyonek Native Corporation", ""),
    "yes - afognak": ("Afognak Native Corporation",
                      "Elijah: Alutiiq is Afognak Native Corporation's federal "
                      "contracting arm. CORPORATION, not the Native Village of Afognak."),
    "afognak": ("Afognak Native Corporation", "Corporation, not the village government."),
    "afognak native vilkage": ("Afognak Native Corporation",
                               "Read as Village; the contracting arm is the CORPORATION."),
    "afognak native corp": ("Afognak Native Corporation",
                            "Elijah: Alutiiq is Afognak Native Corporation's "
                            "federal contracting arm."),
    "yes - tatitlek": ("The Tatitlek Corporation",
                       "CORPORATION, not the Native Village of Tatitlek."),
    # Missed on the first pass and caught by the guard below - 7 firms had been
    # routed to the village government. Chenega is the same village/corporation
    # pair as Afognak, Tyonek, Tatitlek and Eyak.
    "yes - chenega": ("Chenega Corporation",
                      "CORPORATION, not the Native Village of Chenega."),
    "eyak corp there is a village and a village corp":
        ("Eyak Corporation",
         "Elijah: there is a village AND a village corp - this is the CORPORATION."),
    "native village of eyak": ("Native Village of Eyak",
                               "Elijah named the VILLAGE deliberately here, not "
                               "Eyak Corporation. Left as the village."),
    "ukpeagvik inupiat corporation": ("Ukpeaġvik Iñupiat Corporation",
                                      "Village CORPORATION, not the Native Village "
                                      "of Barrow. Bowhead is UIC's brand."),
    "choggiung ltd": ("Choggiung, Ltd.",
                      "The Bristol family belongs to CHOGGIUNG (Dillingham village "
                      "corporation), NOT Bristol Bay Native Corporation."),
    "choggiung ltd.": ("Choggiung, Ltd.",
                       "The Bristol family belongs to CHOGGIUNG, NOT Bristol Bay "
                       "Native Corporation."),
    "tanadgusix corporation": ("Tanadgusix Corporation (TDX)",
                               "St Paul village corporation, not Qagan Tayagungin."),
    "the aleut corporation": ("Aleut Corporation", "Not NANA."),
    "cook inlet region, inc.": ("Cook Inlet Region, Incorporated",
                                "North Wind is CIRI's, not Eastern Shoshone's."),
    "bering straits native corporation": ("Bering Straits Native Corporation",
                                          "Laulima is BSNC's, not Barrow's."),
    "seneca nation of indians": ("Seneca",
                                 "Seneca Nation of Indians - NOT Seneca-Cayuga "
                                 "Nation, which is a separate tribe."),
}


def main():
    out, remapped = [], 0
    for uei, cage, firm, ans in D:
        key = ans.strip().lower()
        note = ""
        if key in FIX:
            new, note = FIX[key]
            if new.strip().lower() != key.replace("yes - ", ""):
                remapped += 1
            ans = new
        elif key.startswith("yes - "):
            ans = ans[6:]
        out.append({"review_id": f"UEI:{uei}", "queue": "tierb", "uei": uei,
                    "cage_code": cage, "entity_or_firm": firm,
                    "question": "owner?", "YOUR_RULING": ans, "YOUR_NOTE": note})

    seen = {}
    for r in out:
        seen.setdefault(r["uei"], 0)
        seen[r["uei"]] += 1
    dupes = [k for k, v in seen.items() if v > 1]
    if dupes:
        raise SystemExit(f"ABORT: duplicate UEIs in the batch: {dupes}")

    # GUARD: no corporate firm may be booked to a village GOVERNMENT.
    #
    # This is the whole category error in one assertion. A firm carrying a
    # corporate form is a company, and companies are owned by ANCSA
    # corporations - never by a federally recognised village government, which
    # is a separate legal person with a separate balance sheet.
    #
    # It earned its place immediately: the first run routed 7 Chenega
    # subsidiaries to the Native Village of Chenega because "Yes - Chenega" was
    # not in FIX. Four such pairs had been handled by hand and the fifth was
    # simply missed - which is exactly why this is a check and not a checklist.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m33 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m33)
    spine = m33.read_csv(CEDAR / "data" / "spine" / "cedar_entity_spine.csv")
    by_id = {r["tribe_id"]: r for r in spine}

    # SCOPE OF THE GUARD - narrowed after the first version over-fired.
    #
    # The naive rule "a corporate firm may not belong to a government" is WRONG
    # in the lower 48. Tribes routinely own companies directly: Chickasaw Nation
    # Industries, Cherokee Nation Businesses, Nexus Technology Solutions are all
    # tribally owned and correctly booked to the TRIBE. Elijah made the same
    # point on Ekwok - "sometimes alaska native tribes can own companies
    # directly in which case it is a tribal enterprise not an ANC."
    #
    # The genuine hazard is narrower: ANCSA deliberately created corporations to
    # hold village assets, so where a village government AND its ANCSA
    # corporation both exist, a contracting subsidiary belongs to the
    # corporation. So fire ONLY when all three hold:
    #   1. the answer resolves to an Alaska village GOVERNMENT (AKNF-), and
    #   2. an ANCSA corporation counterpart exists for that village, and
    #   3. the answer was a BARE village name.
    #
    # Condition 3 is what preserves "Native village of eyak" - Elijah wrote that
    # in full, against a different firm from the one he gave to Eyak Corp, so he
    # was distinguishing them knowingly. An explicit answer is a decision, not an
    # omission, and a guard must not overrule it.
    corp_cores = {m33.core(r["canonical_name"]): r["tribe_id"]
                  for r in spine if r["tribe_id"].startswith("ANVC-")}

    leaks = []
    for r in out:
        if not m33.CORP_FORM_RE.search(r["entity_or_firm"]):
            continue
        ans = r["YOUR_RULING"]
        tid, canon, how = m33.resolve_entity(ans, spine)
        if not tid or not tid.startswith("AKNF-"):
            continue
        if "native village" in m33.norm(ans):
            continue                       # named the village explicitly
        counterpart = corp_cores.get(m33.core(canon))
        if counterpart:
            leaks.append((r["entity_or_firm"], ans, tid,
                          f"{counterpart} exists"))
    if leaks:
        print("\nGUARD FAILED - corporate firms booked to a GOVERNMENT:")
        for f, a, t, c in leaks:
            print(f"    {f[:44]:44s} -> {a[:30]:30s} {t}  [{c}]")
        raise SystemExit("Refusing to write. Add the missing village->corporation "
                         "mapping to FIX, or confirm the government is correct.")

    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["review_id", "queue", "uei", "cage_code",
                                           "entity_or_firm", "question",
                                           "YOUR_RULING", "YOUR_NOTE"])
        w.writeheader()
        w.writerows(out)
    print(f"wrote {OUT.relative_to(CEDAR)}  ({len(out)} rulings)")
    print(f"  village -> corporation disambiguations applied: {remapped}")
    print(f"  distinct owners named: "
          f"{len({r['YOUR_RULING'] for r in out})}")


if __name__ == "__main__":
    main()
