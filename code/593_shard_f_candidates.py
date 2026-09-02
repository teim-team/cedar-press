#!/usr/bin/env python3
"""
Cedar Press - SHARD F, step 3: candidate URLs, each with its PROVENANCE.

Every candidate URL carries a `candidate_basis` saying where it came from:

    cedar_intertribal_orgs   already on disk in data/clean/intertribal_orgs.csv
    ihs_uio_register         the IHS Title V UIO directory harvested in step 2
    crihb_directory          the CRIHB member Tribal Health Program directory
    name_derived_guess       a domain GUESSED from the organisation's name

A `name_derived_guess` is a hypothesis, not a finding. It becomes a finding only
when step 4 fetches it and the page's own title/body carries the organisation's
name tokens. A guess that 200s but does not name the organisation is recorded as
`wrong_site`, not as a website. Nothing here is written to the web map until it
has been verified against retrieved content.

Output: data/staging/tribe_harvest/shard_f/_candidates.json
"""
import csv, json, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f")
OUT = os.path.join(SH, "_candidates.json")

# ---------------------------------------------------------------------------
# Domains GUESSED from organisation names. Every one of these is unverified at
# the moment it is written here and must survive the content check in step 4.
# Where more than one form is plausible both are listed and the probe decides.
# ---------------------------------------------------------------------------
GUESS = {
    # --- Federal-level self-governance consortia (Alaska regional non-profits)
    "SGVF-ASVCPR-00": ["https://www.avcp.org/"],
    "SGVF-BRBYAS-00": ["https://www.bbna.com/", "https://bbna.org/"],
    "SGVF-BRSTLB-00": ["https://bbahc.org/", "https://www.bbahc.org/"],
    "SGVF-CATHTG-00": ["https://www.catg.org/"],
    "SGVF-CHGCMT-00": ["https://www.chugachmiut.org/"],
    "SGVF-CPPRRV-00": ["https://www.crnative.org/", "https://coppperriver.org/"],
    "SGVF-KAWRAK-00": ["https://kawerak.org/"],
    "SGVF-KODIAK-00": ["https://www.kodiakhealthcare.org/", "https://kanaweb.org/"],
    "SGVF-MANLLQ-00": ["https://www.maniilaq.org/"],
    "SGVF-MNTSNF-00": ["https://mstcak.org/", "https://www.mstc.org/"],
    "SGVF-NRTNSN-00": ["https://www.nortonsoundhealth.org/"],
    "SGVF-PRBLFA-00": ["https://www.apiai.org/"],
    "SGVF-STHCNT-00": ["https://www.southcentralfoundation.com/"],
    "SGVF-STHSTL-00": ["https://searhc.org/"],
    "SGVF-STRNLT-00": ["https://www.easternaleutiantribes.com/", "https://eatribes.org/"],
    "SGVF-TNNACH-00": ["https://www.tananachiefs.org/"],
    "SGVF-YKNKSK-00": ["https://www.ykhc.org/"],
    # --- self-governance consortia, lower 48
    "SGVF-CNSLDT-00": ["https://www.cthp.org/", "https://cthpinc.org/"],
    "SGVF-NDNHLT-00": ["https://www.indianhealthcouncil.org/"],
    "SGVF-NRTHR2-00": ["https://www.nvih.org/"],
    "SGVF-NRTHST-00": ["https://www.nthssite.com/", "https://nths.org/"],
    "SGVF-UTAHNA-00": ["https://www.unhsinc.org/"],
    "SGVF-WINSLO-00": ["https://www.wihcc.org/"],
    # --- Federal-level constituency entities (constituent bands / communities)
    "CNSF-MINNCH-BF": ["https://boisforte.com/"],
    "CNSF-MINNCH-FL": ["https://www.fdlrez.com/"],
    "CNSF-MINNCH-GP": ["https://www.grandportage.com/"],
    "CNSF-MINNCH-LL": ["https://www.llojibwe.org/"],
    "CNSF-MINNCH-ML": ["https://millelacsband.com/"],
    "CNSF-MINNCH-WE": ["https://whiteearth.com/"],
    "CNSF-CPTNGR-VJ": ["https://viejasbandofkumeyaay.org/"],
    "CNSF-NAVAJO-RM": ["https://ramahnavajo.org/", "https://www.rnsb.k12.nm.us/"],
    "CNSF-PSMQDY-IT": ["https://passamaquoddy.com/", "https://www.wabanaki.com/"],
    "CNSF-PSMQDY-PP": ["https://www.sipayik.org/", "https://www.wabanaki.com/"],
    "CNSF-FTHALL-BK": ["https://www.sbtribes.com/"],
    "CNSF-FTHALL-SH": ["https://www.sbtribes.com/"],
    "CNSF-TEMOAK-BT": ["https://temoaktribe.com/"],
    "CNSF-TEMOAK-EK": ["https://temoaktribe.com/"],
    "CNSF-TEMOAK-SF": ["https://temoaktribe.com/"],
    "CNSF-TEMOAK-WL": ["https://temoaktribe.com/"],
    "CNSF-PTTRUT-CD": ["https://utahpaiutes.org/"],
    "CNSF-PTTRUT-IP": ["https://utahpaiutes.org/"],
    "CNSF-PTTRUT-KN": ["https://utahpaiutes.org/"],
    "CNSF-PTTRUT-KS": ["https://utahpaiutes.org/"],
    "CNSF-PTTRUT-SW": ["https://utahpaiutes.org/"],
    "CNSS-SHGTCK-TN": ["https://schaghticoke.com/"],
    "CNSS-SHGTCK-TR": ["https://schaghticokeindiantribe.com/"],
    "CNSS-TURTLM-TR": ["https://www.tmbci.org/"],
    # --- intertribal organisations with no website on disk
    "ITO-BRSTL1-00": ["https://www.bbha.org/", "https://bristolbayhousing.org/"],
    "ITO-ENERGY-00": ["https://nitec.energy/", "https://www.nitecenergy.org/"],
    "ITO-MDWSTN-00": ["https://mtera.org/"],
    "ITO-NRGYRS-00": ["https://certredearth.com/", "https://www.certredearth.com/"],
    "ITO-NVRNMN-00": ["https://www.ntec.org/"],
    "ITO-SLFGVR-00": ["https://www.tribalselfgov.org/"],
    "ITO-GRTPLN-00": ["https://www.gptca.org/", "https://gptca.com/"],
    "ITO-LSKVLL-00": ["https://www.anvca.info/", "https://anvca.org/"],
    "ITO-TLCMMN-00": ["https://www.nttatribal.com/", "https://ntta.us/"],
}

# where the org publishes tribal membership: relative paths tried in step 5
MEMBER_PATHS = [
    "member-tribes/", "members/", "membership/", "our-members/",
    "about/member-tribes/", "about-us/member-tribes/", "tribes/",
    "member-tribal-nations/", "communities/", "about/communities/",
    "tribal-members/", "member-organizations/", "about/members/",
]


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"\b(inc|incorporated|corporation|corp|the|of|a|and|for)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def toks(s):
    stop = {
        "inc", "the", "of", "and", "for", "a", "indian", "native", "american",
        "tribal", "tribes", "tribe", "health", "council", "center", "centre",
        "association", "organization", "board", "service", "services",
        "corporation", "consortium", "project", "program", "programs", "inc",
        "national", "united", "clinic", "system", "incorporated", "county",
    }
    return [t for t in norm(s).split() if t not in stop and len(t) > 2]


def main():
    slice_rows = json.load(open(os.path.join(SH, "_slice.json"), encoding="utf-8"))

    # --- IHS UIO register, matched by normalised name
    ihs = []
    p = os.path.join(SH, "ihs_uio_register.jsonl")
    if os.path.exists(p):
        ihs = [json.loads(l) for l in open(p, encoding="utf-8")]
    ihs_by_norm = {}
    for r in ihs:
        ihs_by_norm.setdefault(norm(r["org_name_as_listed"]), []).append(r)

    # --- CRIHB directory links (harvested in the same run; hard-coded here with
    #     the source URL so the provenance is explicit and re-checkable)
    CRIHB_SRC = "https://crihb.org/about/tribal-health-programs/"
    crihb = {
        "sonoma county indian health project": "https://www.scihp.org/",
        "chapa de indian health program": "https://chapa-de.org/",
        "feather river tribal health": "http://www.frth.org/",
        "riverside san bernardino county indian health": "https://www.rsbcihi.org/",
        "lake county tribal health consortium": "http://www.lcthc.com/",
        "southern indian health council": "https://sihc.org/",
    }

    out = []
    for r in slice_rows:
        cands = []
        h = r["handle"]
        nm = norm(r["canonical_name"])

        w = r["known"].get("ito_website")
        if w:
            cands.append(
                {"url": w.rstrip("/") + "/", "candidate_basis": "cedar_intertribal_orgs",
                 "basis_source": "data/clean/intertribal_orgs.csv"}
            )

        # IHS match: exact normalised, else best token overlap
        hit = ihs_by_norm.get(nm)
        if not hit and r["entity_class"] == "Urban Indian Organization":
            best, bestsc = None, 0
            t1 = set(toks(r["canonical_name"]))
            for k, v in ihs_by_norm.items():
                t2 = set(toks(k))
                if not t1 or not t2:
                    continue
                sc = len(t1 & t2) / max(1, len(t1 | t2))
                if sc > bestsc:
                    best, bestsc = v, sc
            if bestsc >= 0.5:
                hit = best
        if hit:
            for x in hit:
                cands.append(
                    {"url": x["org_website"], "candidate_basis": "ihs_uio_register",
                     "basis_source": x["source_url"],
                     "ihs_area": x["ihs_area"], "ihs_state": x["state_heading"],
                     "ihs_city": x["location_city"], "ihs_service_level": x["service_level"]}
                )

        for k, v in crihb.items():
            if k in nm or nm in k:
                cands.append({"url": v, "candidate_basis": "crihb_directory",
                              "basis_source": CRIHB_SRC})

        for g in GUESS.get(h, []):
            cands.append({"url": g, "candidate_basis": "name_derived_guess",
                          "basis_source": "hypothesis - unverified until fetched"})

        # de-duplicate on url, keeping the strongest basis
        rank = {"ihs_uio_register": 0, "crihb_directory": 1,
                "cedar_intertribal_orgs": 2, "name_derived_guess": 3}
        seen = {}
        for c in sorted(cands, key=lambda c: rank[c["candidate_basis"]]):
            u = c["url"]
            if u not in seen:
                seen[u] = c
        r["candidates"] = list(seen.values())
        r["name_tokens"] = toks(r["canonical_name"])
        out.append(r)

    json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1)

    n0 = sum(1 for r in out if not r["candidates"])
    print(f"{len(out)} entities, {sum(len(r['candidates']) for r in out)} candidate URLs")
    import collections
    c = collections.Counter(
        x["candidate_basis"] for r in out for x in r["candidates"]
    )
    for k, v in c.most_common():
        print(f"  {k:24s} {v}")
    print(f"  NO CANDIDATE AT ALL      {n0}")
    for r in out:
        if not r["candidates"]:
            print(f"      - {r['entity_class'][:28]:28s} {r['canonical_name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
