#!/usr/bin/env python3
"""1111 — probe candidate NEW sources Cedar's 55-source registry does not hold.

READ-ONLY with respect to every Cedar table. Writes ONLY to
`data/staging/source_exploration_1111/` and `docs/SOURCE_EXPLORATION_*`.

WHAT THIS IS
------------
A survey with evidence, not a scrape. For each candidate it establishes:
  * does the object exist at the stated URL (status, content-type, bytes)
  * what is the robots posture, evaluated against EVERY agent token the site
    might name, not only ours
  * a short body sample so a later reader can see the grain without re-fetching

WHY THE ROBOTS CHECK IS SHAPED THIS WAY
---------------------------------------
`RobotFileParser.read()` fetches with the default `Python-urllib` UA and a 403
on the robots file then reads as `disallow_all` — 22 phantom blocks in
`docs/PULL_DISCIPLINE.md`. So we fetch robots ourselves with a declared UA and
`.parse()` the body.

AND a `can_fetch()` called with only our own UA MISSES a `User-agent: ClaudeBot`
rule entirely: RobotFileParser matches the longest User-agent token that is a
substring-prefix of the string you hand it, so asking about "CedarPress/1.0"
never consults a ClaudeBot group. That error fetched 13 refusing hosts on
2026-09-02. This script therefore asks `can_fetch()` once PER AGENT TOKEN in
`AGENT_TOKENS` and reports the union: if ANY token that could plausibly name
this client is disallowed, the row is `ROBOTS_DISALLOWS_SOME_AGENT` and names
which one.

  A 404 or an empty robots file means ALLOWED.
  A 403 on robots.txt is a fact about that route, not about the host.

RATE
----
One request at a time, `SLEEP_S` between requests, at most `MAX_PER_HOST`
requests to any one host, and a hard `RUN_DEADLINE`. No retry loop: a refusal
is recorded as a finding and the run moves on (PULL_DISCIPLINE rule "stop on
first refusal when nothing has succeeded" does not bind — every candidate is a
different host, so one host's refusal predicts nothing about the next).

USAGE
    py -3 code/1111_probe_new_source_candidates.py probe [--only <substr>]
    py -3 code/1111_probe_new_source_candidates.py report
    py -3 code/1111_probe_new_source_candidates.py selftest
"""
from __future__ import annotations

import csv
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "staging" / "source_exploration_1111"
OUT.mkdir(parents=True, exist_ok=True)
PROBE_JSONL = OUT / "probe_log.jsonl"
RESULT_CSV = OUT / "probe_results.csv"

UA = "CedarPress/1.0 (research; contact hello@cedarpress.co)"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Every agent token a robots.txt on these hosts might name that could plausibly
# be US. `*` is always consulted by RobotFileParser as the fallback group.
AGENT_TOKENS = [UA, "CedarPress", "ClaudeBot", "Claude-User", "Claude-SearchBot",
                "anthropic-ai", "CCBot", "Python-urllib", "*"]

SLEEP_S = 2.0
TIMEOUT = 30
RUN_DEADLINE_S = 90 * 60
MAX_PER_HOST = 6

_started = time.time()
_host_calls: dict[str, int] = {}
_robots_cache: dict[str, dict] = {}

_CTX = ssl.create_default_context()


def _deadline_ok() -> bool:
    return (time.time() - _started) < RUN_DEADLINE_S


def fetch(url: str, ua: str = UA, method: str = "GET", maxbytes: int = 60_000) -> dict:
    """One request. Never raises. Returns a dict that is always the same shape."""
    host = urllib.parse.urlsplit(url).netloc
    if _host_calls.get(host, 0) >= MAX_PER_HOST:
        return {"url": url, "status": "HOST_BUDGET_EXHAUSTED", "ok": False,
                "ctype": "", "bytes": 0, "body": "", "final_url": url, "ua": ua}
    if not _deadline_ok():
        return {"url": url, "status": "RUN_DEADLINE", "ok": False,
                "ctype": "", "bytes": 0, "body": "", "final_url": url, "ua": ua}
    _host_calls[host] = _host_calls.get(host, 0) + 1
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": ua,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_CTX) as r:
            raw = r.read(maxbytes) if method == "GET" else b""
            clen = r.headers.get("Content-Length")
            out = {"url": url, "status": r.status, "ok": True,
                   "ctype": r.headers.get("Content-Type", ""),
                   "content_length_header": clen,
                   "bytes": len(raw), "final_url": r.geturl(),
                   "body": raw.decode("utf-8", "replace"), "ua": ua}
    except urllib.error.HTTPError as e:
        body = b""
        try:
            body = e.read(4000)
        except Exception:
            pass
        out = {"url": url, "status": e.code, "ok": False,
               "ctype": e.headers.get("Content-Type", "") if e.headers else "",
               "content_length_header": None,
               "bytes": len(body), "final_url": url,
               "body": body.decode("utf-8", "replace"), "ua": ua}
    except Exception as e:                                # noqa: BLE001
        out = {"url": url, "status": f"ERR:{type(e).__name__}", "ok": False,
               "ctype": "", "content_length_header": None, "bytes": 0,
               "final_url": url, "body": str(e)[:300], "ua": ua}
    out["elapsed_s"] = round(time.time() - t0, 2)
    out["fetched_at"] = datetime.now(timezone.utc).isoformat()
    with PROBE_JSONL.open("a", encoding="utf-8") as fh:
        rec = dict(out)
        rec["body"] = rec["body"][:2000]
        fh.write(json.dumps(rec) + "\n")
    time.sleep(SLEEP_S)
    return out


def robots_posture(url: str) -> dict:
    """Fetch robots.txt with our UA; evaluate can_fetch for EVERY agent token.

    Returns the union verdict plus the tokens that are disallowed, so a
    `User-agent: ClaudeBot / Disallow: /` rule cannot be missed by asking only
    about ourselves.
    """
    parts = urllib.parse.urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin in _robots_cache:
        cached = dict(_robots_cache[origin])
        cached["path_checked"] = parts.path or "/"
        rp = cached.pop("_rp")
        denied = [t for t in AGENT_TOKENS if not rp.can_fetch(t, url)]
        cached["denied_agents"] = ";".join(denied)
        cached["verdict"] = "DISALLOWED_FOR:" + ",".join(denied) if denied else "ALLOWED"
        return cached

    r = fetch(origin + "/robots.txt", ua=UA)
    body = r["body"] if (r["ok"] and r["status"] == 200) else ""
    served = True
    if body and "<html" in body[:400].lower():
        body, served = "", False          # a soft-404 HTML page is not robots
    if not r["ok"] or r["status"] != 200:
        served = False
    rp = RobotFileParser()
    rp.parse(body.splitlines() if body else [])
    denied = [t for t in AGENT_TOKENS if not rp.can_fetch(t, url)]
    named_agents = sorted({l.split(":", 1)[1].strip()
                           for l in body.splitlines()
                           if l.strip().lower().startswith("user-agent:")
                           and ":" in l})
    rec = {
        "robots_status": r["status"],
        "robots_served": served,
        "robots_agents_named": ";".join(named_agents[:25]),
        "robots_bytes": len(body),
        "denied_agents": ";".join(denied),
        "verdict": ("DISALLOWED_FOR:" + ",".join(denied)) if denied else "ALLOWED",
        "path_checked": parts.path or "/",
        "_rp": rp,
    }
    _robots_cache[origin] = rec
    out = dict(rec)
    out.pop("_rp")
    return out


TERMS_HINT = re.compile(
    r"(terms of (use|service)|you may not|prohibited|automated|scrap\w+|"
    r"crawl\w+|robot|public domain|no copyright|open (data )?licen[cs]e|"
    r"creative commons|CC0|works? of the (?:U\.?S\.?|United States) government)",
    re.I)


# ---------------------------------------------------------------------------
# THE CANDIDATE LIST
# Each entry: id, name, publisher, probe URL(s), what it would feed.
# The FIRST url is the reachability probe; the rest are enumeration probes
# (a sitemap, an API index, a bulk directory listing) — because a negative
# from search alone is not a negative.
# ---------------------------------------------------------------------------
CANDIDATES: list[dict] = [
    # ---- NHO / SBA route: the named untried route for the 170-NHO gap ----
    dict(id="sba_certification_api", name="SBA MySBA Certifications public search API",
         publisher="U.S. Small Business Administration",
         urls=["https://certification.sba.gov/",
               "https://api.sba.gov/",
               "https://data.sba.gov/api/3/action/package_list"],
         feeds="native_owned_businesses / _entity_layer (NHO, ANC, tribal 8(a))"),
    dict(id="sba_open_data", name="SBA open-data portal (CKAN) — 8(a) / HUBZone firm lists",
         publisher="U.S. Small Business Administration",
         urls=["https://data.sba.gov/",
               "https://data.sba.gov/api/3/action/package_search?q=8%28a%29&rows=50",
               "https://data.sba.gov/api/3/action/package_search?q=hubzone&rows=50"],
         feeds="native_owned_businesses"),
    dict(id="sba_dsbs", name="SBA Dynamic Small Business Search (DSBS)",
         publisher="U.S. Small Business Administration",
         urls=["https://dsbs.sba.gov/search/dsp_dsbs.cfm"],
         feeds="native_owned_businesses"),
    dict(id="nhoa_directory", name="NHOA member directory (live origin)",
         publisher="Native Hawaiian Organizations Association",
         urls=["http://www.nhoassociation.org/membership.html",
               "https://www.nhoassociation.org/"],
         feeds="_entity_layer (NHO)"),
    dict(id="hawaii_business_registry",
         name="Hawaii DCCA Business Registration Division — entity search / bulk",
         publisher="State of Hawaii, DCCA",
         urls=["https://hbe.ehawaii.gov/documents/search.html",
               "https://data.hawaii.gov/api/3/action/package_search?q=business+registration&rows=30"],
         feeds="_entity_layer (170 NHOs with no dated public record)"),

    # ---- Alaska: the 95 village corporations behind one CAPTCHA ----
    dict(id="ak_corp_bulk", name="Alaska DCCED corporations bulk download",
         publisher="Alaska DCCED, Division of Corporations",
         urls=["https://www.commerce.alaska.gov/cbp/DBDownloads/CorporationsDownload.CSV"],
         feeds="_entity_layer (95 Alaska Native village corporations)"),
    dict(id="ak_opendata", name="Alaska statewide open-data / GIS portal",
         publisher="State of Alaska",
         urls=["https://gis.data.alaska.gov/api/search/v1/collections",
               "https://data.alaska.gov/"],
         feeds="_entity_layer (Alaska)"),
    dict(id="ak_dcra_cdo", name="Alaska DCRA Community Database Online (ANCSA corp per community)",
         publisher="Alaska DCCED, Division of Community and Regional Affairs",
         urls=["https://dcced.maps.arcgis.com/sharing/rest/search?q=community%20database&f=json&num=25",
               "https://www.commerce.alaska.gov/dcra/DCRAExternal/community"],
         feeds="_entity_layer (Alaska Native village corporations)"),
    dict(id="wayback_ak_corp", name="Wayback CDX for the Alaska corporations bulk file",
         publisher="Internet Archive",
         urls=["https://web.archive.org/cdx/search/cdx?url=commerce.alaska.gov/cbp/DBDownloads*"
               "&output=json&limit=40&collapse=urlkey"],
         feeds="_entity_layer (Alaska Native village corporations)"),

    # ---- BIE school freshness ----
    dict(id="bie_directory", name="BIE school directory (agency's own enumeration)",
         publisher="Bureau of Indian Education",
         urls=["https://www.bie.edu/schools",
               "https://www.bie.edu/sitemap.xml"],
         feeds="_entity_layer (116 BIE schools stale by construction)"),
    dict(id="ed_crdc", name="ED Civil Rights Data Collection — school-level, includes BIE",
         publisher="U.S. Dept. of Education, OCR",
         urls=["https://civilrightsdata.ed.gov/",
               "https://civilrightsdata.ed.gov/assets/downloads/"],
         feeds="_entity_layer (BIE schools)"),
    dict(id="nces_ccd_api", name="NCES CCD / Urban Institute Education Data API",
         publisher="NCES / Urban Institute",
         urls=["https://educationdata.urban.org/api/v1/schools/ccd/directory/2023/?fips=59&limit=5"],
         feeds="_entity_layer (BIE schools)"),

    # ---- contracting: the $65.2B unattributed candidates ----
    dict(id="sam_extracts", name="SAM.gov Entity Management public data extracts",
         publisher="GSA / SAM.gov",
         urls=["https://open.gsa.gov/api/entity-api/",
               "https://sam.gov/data-services/Entity%20Registration/Public%20V2?privacy=Public"],
         feeds="prime_contracts / native_owned_businesses (UEI, CAGE, business types)"),
    dict(id="cage_dla", name="DLA CAGE public search / bulk CAGE file",
         publisher="Defense Logistics Agency",
         urls=["https://cage.dla.mil/Search",
               "https://cage.dla.mil/"],
         feeds="cedar_identifier_ledger (the owner's own adjudication route)"),
    dict(id="gsa_elibrary", name="GSA eLibrary — schedule contract holders",
         publisher="GSA",
         urls=["https://www.gsaelibrary.gsa.gov/ElibMain/home.do",
               "https://www.gsaelibrary.gsa.gov/robots.txt"],
         feeds="prime_contracts"),
    dict(id="fsrs", name="FSRS.gov — subaward reporting system",
         publisher="GSA",
         urls=["https://www.fsrs.gov/"],
         feeds="subawards"),

    # ---- nonprofit / philanthropy: the owner named this ----
    dict(id="irs990_s3", name="IRS Form 990 e-file XML, AWS Open Data (S3)",
         publisher="IRS / AWS Registry of Open Data",
         urls=["https://irs-form-990.s3.amazonaws.com/?list-type=2&max-keys=5",
               "https://registry.opendata.aws/irs990/"],
         feeds="np_orgs / np_schedule_i_grants / grantmaker_funding_flows"),
    dict(id="fac_api_tables", name="Federal Audit Clearinghouse API — full table set",
         publisher="GSA / FAC",
         urls=["https://api.fac.gov/",
               "https://www.fac.gov/developers/"],
         feeds="fac_tribal_single_audits (per-program SEFA, findings, notes)"),
    dict(id="candid", name="Candid / Foundation Directory API",
         publisher="Candid (formerly Foundation Center + GuideStar)",
         urls=["https://developer.candid.org/",
               "https://candid.org/use-our-data"],
         feeds="grantmaker_funding_flows"),
    dict(id="ca_charity_registry", name="California Registry of Charities & Fundraisers — public data",
         publisher="California DOJ",
         urls=["https://rct.doj.ca.gov/Verification/Web/Search.aspx",
               "https://oag.ca.gov/charities/content/public-data"],
         feeds="np_orgs"),
    dict(id="ny_charity_registry", name="NY Charities Bureau registration + filings (data.ny.gov)",
         publisher="NY Attorney General",
         urls=["https://data.ny.gov/api/views.json?limit=5&q=charit"],
         feeds="np_orgs"),

    # ---- gaming: per-facility revenue exists for 11 of ~734 ----
    dict(id="ok_exclusivity", name="Oklahoma tribal gaming exclusivity fees, per tribe per year",
         publisher="Oklahoma Office of Management and Enterprise Services",
         urls=["https://oklahoma.gov/omes/services/tribal-gaming.html"],
         feeds="gaming_facility_metrics / gaming_revenue_bounds"),
    dict(id="wi_doa_gaming", name="Wisconsin tribal gaming payments per tribe",
         publisher="Wisconsin Dept. of Administration, Division of Gaming",
         urls=["https://doa.wi.gov/Pages/AboutDOA/IndianGaming.aspx"],
         feeds="gaming_facility_metrics"),
    dict(id="ks_gaming", name="Kansas Racing & Gaming Commission — tribal gaming",
         publisher="Kansas Racing and Gaming Commission",
         urls=["https://krgc.ks.gov/tribal-gaming"],
         feeds="gaming_facility_metrics"),
    dict(id="ny_gaming_tribal", name="New York State Gaming Commission — tribal exclusivity payments",
         publisher="NYS Gaming Commission",
         urls=["https://www.gaming.ny.gov/gaming/index.php?ID=8"],
         feeds="gaming_facility_metrics"),
    dict(id="nigc_tribe_list", name="NIGC gaming tribe / gaming operation list",
         publisher="National Indian Gaming Commission",
         urls=["https://www.nigc.gov/general-counsel/gaming-tribe-list"],
         feeds="gaming_facilities"),

    # ---- broadband / transport / treasury: per-tribe dollars ----
    dict(id="usac_opendata", name="USAC open data — E-Rate / Rural Health Care disbursements",
         publisher="Universal Service Administrative Company",
         urls=["https://opendata.usac.org/api/views.json?limit=8"],
         feeds="federal_funding_transactions (tribal schools, libraries, clinics)"),
    dict(id="fhwa_ttp", name="FHWA Tribal Transportation Program allocation tables",
         publisher="Federal Highway Administration",
         urls=["https://highways.dot.gov/federal-lands/programs-tribal/allocations"],
         feeds="federal_funding_transactions"),
    dict(id="treasury_slfrf_tribal", name="Treasury SLFRF / Coronavirus fund tribal allocations",
         publisher="U.S. Treasury",
         urls=["https://home.treasury.gov/policy-issues/coronavirus/assistance-for-state-local-and-tribal-governments"],
         feeds="federal_funding_transactions"),
    dict(id="cdfi_awards", name="CDFI Fund awards database + certification list",
         publisher="Treasury CDFI Fund",
         urls=["https://www.cdfifund.gov/awards/state-awards",
               "https://www.cdfifund.gov/sites/cdfi/files/2026-01/CDFI_Cert_List.xlsx",
               "https://amis.cdfifund.gov/"],
         feeds="_entity_layer (Native CDFIs) / federal_funding_transactions"),

    # ---- health / labour / energy ----
    dict(id="nppes", name="CMS NPPES NPI registry — bulk + API",
         publisher="CMS",
         urls=["https://npiregistry.cms.hhs.gov/api/?version=2.1&organization_name=tribal*&limit=5",
               "https://download.cms.gov/nppes/NPI_Files.html"],
         feeds="_entity_layer (UIO, IHS, tribal health) / np_orgs"),
    dict(id="bls_qcew", name="BLS QCEW — ownership codes",
         publisher="Bureau of Labor Statistics",
         urls=["https://www.bls.gov/cew/classifications/ownerships/ownership-titles.htm"],
         feeds="gaming_employment_observations"),
    dict(id="eia_api", name="EIA API v2 — Form EIA-860/861 utility & generator ownership",
         publisher="U.S. Energy Information Administration",
         urls=["https://api.eia.gov/v2/"],
         feeds="resource_revenue / natural-resources"),
    dict(id="doi_landbuyback", name="DOI Land Buy-Back Program acquisitions",
         publisher="U.S. Dept. of the Interior",
         urls=["https://www.doi.gov/buybackprogram/results"],
         feeds="natural-resources / _entity_layer"),
    dict(id="onrr_production", name="ONRR / Natural Resources Revenue Data production volumes",
         publisher="ONRR / revenuedata.doi.gov",
         urls=["https://revenuedata.doi.gov/downloads/"],
         feeds="resource_revenue (the missing denominator)"),
    dict(id="fcc_ecfs", name="FCC ECFS filings API — tribal filers",
         publisher="Federal Communications Commission",
         urls=["https://publicapi.fcc.gov/ecfs/filings?limit=2"],
         feeds="native_entity_lobbying_disclosures / ferc-style advocacy"),

    # ================= BATCH 2 =================
    # Hawaii: the 170 NHOs are mostly homestead associations and hui, not
    # 501(c)(3) filers. Their dated record, if it exists, is a STATE register
    # or a Hawaii-specific grantmaker, not the IRS.
    dict(id="hi_dcca_portal", name="Hawaii DCCA business entity portal (successor to Hawaii Business Express)",
         publisher="State of Hawaii, DCCA Business Registration Division",
         urls=["https://hbe.dcca.hawaii.gov/",
               "https://hbe.dcca.hawaii.gov/robots.txt"],
         feeds="_entity_layer (170 NHOs with no dated public record)"),
    dict(id="hi_dhhl", name="Dept. of Hawaiian Home Lands — homestead / beneficiary association register",
         publisher="State of Hawaii, DHHL",
         urls=["https://dhhl.hawaii.gov/homesteadassociations/",
               "https://dhhl.hawaii.gov/sitemap.xml"],
         feeds="_entity_layer (NHO)"),
    dict(id="hi_oha_grants", name="Office of Hawaiian Affairs — grants awarded",
         publisher="Office of Hawaiian Affairs (State of Hawaii)",
         urls=["https://www.oha.org/grants/",
               "https://www.oha.org/sitemap.xml"],
         feeds="_entity_layer (NHO) / grantmaker_funding_flows"),

    # federal-register's thin NON-NAGPRA surface: Section 106 is 20 rows
    dict(id="achp_e106", name="ACHP Section 106 case tracking (e106) / case digest",
         publisher="Advisory Council on Historic Preservation",
         urls=["https://www.achp.gov/digital-library-section-106-landing",
               "https://www.achp.gov/sitemap.xml"],
         feeds="section_106_consultation_events"),
    dict(id="nathpo", name="NATHPO Tribal Historic Preservation Officer directory",
         publisher="National Association of Tribal Historic Preservation Officers",
         urls=["https://www.nathpo.org/thpos/thpo-map/",
               "https://www.nathpo.org/sitemap.xml"],
         feeds="_entity_layer / section_106_consultation_events"),
    dict(id="nps_thpo_grants", name="NPS Tribal Heritage / THPO grant awards, per tribe per year",
         publisher="National Park Service, Historic Preservation Fund",
         urls=["https://www.nps.gov/subjects/historicpreservationfund/tribal-grants.htm"],
         feeds="federal_funding_transactions / section_106"),

    # facility & service registers
    dict(id="ihs_facilities", name="IHS facility / service-unit register",
         publisher="Indian Health Service",
         urls=["https://www.ihs.gov/locations/",
               "https://www.ihs.gov/sitemap.xml"],
         feeds="_entity_layer (UIO, IHS service units)"),
    dict(id="hrsa_data", name="HRSA data warehouse — health-centre / grantee service delivery sites",
         publisher="Health Resources & Services Administration",
         urls=["https://data.hrsa.gov/data/download"],
         feeds="_entity_layer / np_orgs"),

    # per-tribe federal dollars nobody has assembled
    dict(id="hud_ihbg_formula", name="HUD ONAP IHBG formula allocations, per tribe per year",
         publisher="HUD Office of Native American Programs",
         urls=["https://www.hud.gov/program_offices/public_indian_housing/ih/codetalk/onap/ihbgformula"],
         feeds="federal_funding_transactions"),
    dict(id="denali_commission", name="Denali Commission project database (Alaska communities)",
         publisher="Denali Commission",
         urls=["https://www.denali.gov/projects/"],
         feeds="federal_funding_transactions (Alaska)"),
    dict(id="usda_rd_obligations", name="USDA Rural Development obligation reports (per-recipient)",
         publisher="USDA Rural Development",
         urls=["https://www.rd.usda.gov/about-rd/performance/rural-development-obligation-reports"],
         feeds="federal_funding_transactions"),

    # alternate route to the Alaska register
    dict(id="opencorporates_ak", name="OpenCorporates — Alaska company register mirror",
         publisher="OpenCorporates Ltd",
         urls=["https://opencorporates.com/companies/us_ak?q=corporation",
               "https://opencorporates.com/info/our-data"],
         feeds="_entity_layer (95 Alaska Native village corporations)"),
    # ================= BATCH 3 =================
    # Found BY the batch-1 probe, not guessed: www.bie.edu/schools is a
    # front-end for biamaps.geoplatform.gov, and its own og:description says
    # "183 Bureau-funded elementary and secondary schools ... 55 BIE-Operated
    # and 128 Tribally Controlled". Ask the ArcGIS server for its own
    # enumeration rather than searching for a file.
    dict(id="biamaps_arcgis", name="BIA/BIE ArcGIS REST services (biamaps.geoplatform.gov)",
         publisher="Bureau of Indian Affairs / DOI GeoPlatform",
         urls=["https://biamaps.geoplatform.gov/arcgis/rest/services?f=json",
               "https://biamaps.geoplatform.gov/server/rest/services?f=json",
               "https://biamaps.geoplatform.gov/BIE-Schools-Directory/"],
         feeds="_entity_layer (116 BIE schools) / BIA facility register"),
    # 404s above were on GUESSED paths. Ask each publisher to enumerate itself.
    dict(id="ok_omes_enum", name="Oklahoma OMES — tribal gaming exclusivity fee pages (site enumeration)",
         publisher="State of Oklahoma",
         urls=["https://oklahoma.gov/sitemap.xml",
               "https://oklahoma.gov/omes/services/tribal-gaming.html"],
         feeds="gaming_facility_metrics"),
    dict(id="wi_doa_enum", name="Wisconsin DOA Division of Gaming (site enumeration)",
         publisher="Wisconsin Dept. of Administration",
         urls=["https://doa.wi.gov/sitemap.xml", "https://doa.wi.gov/Pages/AboutDOA/DivisionGaming.aspx"],
         feeds="gaming_facility_metrics"),
    dict(id="nigc_enum", name="NIGC site enumeration (gaming tribe / operation list)",
         publisher="National Indian Gaming Commission",
         urls=["https://www.nigc.gov/sitemap.xml"],
         feeds="gaming_facilities"),
    dict(id="ak_dnr_arcgis", name="Alaska DCCED ArcGIS org content listing (DCRA community data)",
         publisher="Alaska DCCED",
         urls=["https://dcced.maps.arcgis.com/sharing/rest/search?q=owner%3ADCCED_GIS&f=json&num=50",
               "https://dcced.maps.arcgis.com/sharing/rest/community/self?f=json"],
         feeds="_entity_layer (Alaska)"),
]


def probe_one(c: dict) -> list[dict]:
    rows = []
    for i, url in enumerate(c["urls"]):
        rb = robots_posture(url)
        r = fetch(url, ua=UA)
        # a 403 to the honest UA is very often a UA filter, not an access rule
        second = None
        if (not r["ok"]) and r["status"] in (403, 406):
            second = fetch(url, ua=BROWSER_UA)
        eff = second if (second and second["ok"]) else r
        body = eff["body"]
        terms = TERMS_HINT.findall(body[:20000])
        rows.append({
            "candidate_id": c["id"],
            "name": c["name"],
            "publisher": c["publisher"],
            "probe_index": i,
            "url": url,
            "final_url": eff["final_url"],
            "status_honest_ua": r["status"],
            "status_browser_ua": (second or {}).get("status", ""),
            "ok": eff["ok"],
            "content_type": eff["ctype"],
            "content_length_header": eff.get("content_length_header") or "",
            "bytes_read": eff["bytes"],
            "elapsed_s": eff["elapsed_s"],
            "robots_status": rb["robots_status"],
            "robots_served": rb["robots_served"],
            "robots_agents_named": rb["robots_agents_named"],
            "robots_verdict": rb["verdict"],
            "robots_denied_agents": rb["denied_agents"],
            "terms_signals": ";".join(sorted({t if isinstance(t, str) else t[0]
                                              for t in terms})[:8]),
            "body_head": re.sub(r"\s+", " ", body[:400]),
            "feeds": c["feeds"],
            "fetched_at": eff["fetched_at"],
        })
        if not _deadline_ok():
            break
    return rows


def cmd_probe(only: str | None) -> int:
    wanted = [w.strip().lower() for w in (only or "").split(",") if w.strip()]
    cands = [c for c in CANDIDATES
             if (not wanted or any(w in c["id"].lower() for w in wanted))]
    print(f"probing {len(cands)} candidates, UA={UA}")
    all_rows: list[dict] = []
    for c in cands:
        print(f"  -- {c['id']}")
        all_rows.extend(probe_one(c))
        if not _deadline_ok():
            print("RUN_DEADLINE reached; stopping.")
            break
    if not all_rows:
        print("UNMEASURED: no rows produced")
        return 2
    # APPEND-MERGE, keyed on (candidate_id, url): a second invocation with
    # --only must not erase the first invocation's rows. Re-probing the same
    # url REPLACES its row, so the file is always the newest measurement of
    # each object and never a mix of two runs for one object.
    cols = list(all_rows[0].keys())
    merged: dict[tuple[str, str], dict] = {}
    if RESULT_CSV.exists():
        for r in csv.DictReader(RESULT_CSV.open(encoding="utf-8")):
            merged[(r["candidate_id"], r["url"])] = r
            for k in r:
                if k not in cols:
                    cols.append(k)
    for r in all_rows:
        merged[(r["candidate_id"], r["url"])] = r
    tmp = RESULT_CSV.with_suffix(".part")
    with tmp.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(merged.values())
    os.replace(tmp, RESULT_CSV)
    all_rows = list(merged.values())
    print(f"wrote {RESULT_CSV} ({len(all_rows)} rows)")
    return 0


def cmd_report() -> int:
    if not RESULT_CSV.exists():
        print("UNMEASURED: no probe_results.csv — run `probe` first")
        return 2
    rows = list(csv.DictReader(RESULT_CSV.open(encoding="utf-8")))
    print(f"{len(rows)} probe rows, "
          f"{len({r['candidate_id'] for r in rows})} candidates")
    for r in rows:
        print(f"{r['candidate_id']:26} {str(r['status_honest_ua']):>16} "
              f"{str(r['status_browser_ua']):>5} {r['robots_verdict'][:34]:34} "
              f"{r['bytes_read']:>7}  {r['url'][:72]}")
    return 0


def cmd_selftest() -> int:
    """Prove the robots check FIRES on a ClaudeBot-only rule.

    This is the trap the mandate names: `can_fetch(OUR_UA, ...)` returns True
    against a robots.txt whose only rule names ClaudeBot, because
    RobotFileParser never consults a group whose token is not a prefix of the
    agent string you pass. The union-over-tokens check must catch it.
    """
    body = "User-agent: ClaudeBot\nDisallow: /\n"
    rp = RobotFileParser()
    rp.parse(body.splitlines())
    naive = rp.can_fetch(UA, "https://example.gov/x")
    assert naive is True, "fixture invalid: the naive check should MISS this rule"
    denied = [t for t in AGENT_TOKENS if not rp.can_fetch(t, "https://example.gov/x")]
    assert "ClaudeBot" in denied, f"union check FAILED to fire; denied={denied}"
    print(f"OK  naive can_fetch(OUR_UA)={naive} (misses it); "
          f"union check denies {denied}")

    # and it must NOT fire on an empty / 404 robots file
    rp2 = RobotFileParser()
    rp2.parse([])
    denied2 = [t for t in AGENT_TOKENS if not rp2.can_fetch(t, "https://example.gov/x")]
    assert denied2 == [], f"false positive on empty robots: {denied2}"
    print("OK  empty robots.txt reads as ALLOWED for every token")

    # a Disallow: with an empty value is 'allow everything'
    rp3 = RobotFileParser()
    rp3.parse("User-agent: *\nDisallow:\n".splitlines())
    denied3 = [t for t in AGENT_TOKENS if not rp3.can_fetch(t, "https://example.gov/x")]
    assert denied3 == [], f"false positive on bare Disallow: {denied3}"
    print("OK  'Disallow:' with no path reads as ALLOWED")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    if cmd == "probe":
        return cmd_probe(only)
    if cmd == "report":
        return cmd_report()
    if cmd == "selftest":
        return cmd_selftest()
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
