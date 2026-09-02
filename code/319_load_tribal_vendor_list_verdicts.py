"""319 - load the 2026-08-26 discovery verdicts into the feasibility registry.

The verdicts are held HERE, in code, rather than hand-edited into the CSV, so
that re-running 316 (which preserves fields) followed by 319 reproduces the
registry exactly.  A tracking file that can only be reproduced by remembering
what somebody typed is not a tracking file.

WHAT WAS MEASURED, AND HOW - stated because it bounds every verdict below.
Discovery ran 2026-08-26 across four parallel passes.  In every pass the
WebSearch budget was exhausted before the first call, and DuckDuckGo, Brave and
Mojeek all refused (CAPTCHA / 429 / 403), so **discovery ran by direct
navigation from known official domains, each site's own on-site search, and
`sitemap.xml` / `robots.txt` enumeration.**  That method is gentler on small
tribal servers and it found 13 lists.  It also means a NO_LIST_FOUND rests on
site-internal evidence: a list published on a third-party host - a TERO
consortium page, a regional nonprofit, an archived subdomain - could be missed.
**The negatives are therefore "not published on their own site", which is a
weaker claim than "does not exist", and the registry says so per row.**

That is the same error shape this project has already reversed twice: one
entity's behaviour generalised into a rule about a source.  It is not repeated
here.

ETHICS RECORD
-------------
* No login, paywall or access control was bypassed anywhere. The Oneida WP
  REST route answered 401 and was not worked around, and the NANAtkut,
  mySealaska, Eklutna /members and Beacon Bid portals were not probed.
* ONE LIST_BEHIND_LOGIN, and it was found by the ARCHIVE rather than the live
  web. Choctaw Nation's preferred-supplier portal is NXDOMAIN today, so it
  read as a recoverable dead link and was queued as the highest-value Wayback
  target in the lower 48. The CDX enumeration then showed 527 archived URLs
  whose 2023-07-07 capture includes `/api/account/register`,
  `/api/account/resetpassword` and `/api/account/userinfo` beside
  `/api/suppliers` and `/api/ownershiproles`. It was a REGISTERED-ACCOUNT
  APPLICATION. The archive holds the route names; the payload was gated.
  **WAYBACK IS NOT A ROUTE AROUND A LOGIN.** Reclassified LIST_BEHIND_LOGIN
  and excluded from further sweeping.
* `elyshoshonetribe.com` names `ClaudeBot` and `anthropic-ai` in robots.txt
  under an explicit Disallow. Crawling stopped on discovery, and the host is
  marked `wayback_priority = EXCLUDED`. An origin's stated refusal of this
  agent is not routed around by fetching the same content from an archive.
* Three hosts (`kotzebueira.org`, `nana.com`, `olgoonik.com`) answer HTTP 403
  to an automated client on every path INCLUDING robots.txt. That is a WAF, not
  a robots disallow and not a login. Their terms could not be read, so their
  terms status is NOT_CHECKED, not SILENT - an unreadable term is not an
  absent one.

NO NETWORK CALLS.  This script writes down what the discovery pass measured.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "review" / "tribal_vendor_list_registry_2026-08-26.csv"

SCRIPT = "319_load_tribal_vendor_list_verdicts.py"
CHECKED_DATE = "2026-08-26"
CHECKED_BY = "cedar-press discovery pass 2026-08-26 (four parallel agents)"

ASSERTION_BY_LIST_TYPE = {
    "TERO": "OWNERSHIP",
    "SUBSIDIARY_DIRECTORY": "OWNERSHIP",
    "SHAREHOLDER_VENDOR": "OWNERSHIP",
    "VENDOR": "RELATIONSHIP",
    "TERO_EMPLOYER": "RELATIONSHIP",
    "LICENSE": "OPERATING_ON_LAND",
    "NONE": "NONE",
    "": "NONE",
}

# tribe_id -> field dict.  Only fields named here are written; everything else
# the registry holds is preserved.
V = {
    # ------------------------------------------------------------ LOWER 48 --
    "TRBF-NAVAJO-00": dict(
        verdict="LIST_FOUND_PDF",
        official_site="https://www.navajo-nsn.gov/",
        hosts="navajoeconomy.org;www.navajo-nsn.gov;onlr.navajo-nsn.gov",
        list_url="https://navajoeconomy.org/business-regulatory/nboa-source-listing/",
        list_type="TERO", list_format="PDF", entry_count_approx="346",
        identifiers_present="business name;street address;city;state;zip;phone;fax;email;contact person;ownership control percent;preference priority tier;certification expiry",
        update_frequency="MONTHLY (stated, per Navajo Nation Council Resolution CAP-37-02 / Navajo Business Opportunity Act Title 5 Ch.2 s.201-215)",
        source_terms_status="TERMS_STATED_RESTRICTIVE",
        source_terms_quote="(c) 2025, www.navajoeconomy.org. All Rights Reserved.",
        publisher_relationship="SELF",
        robots_note="robots.txt fully permissive: 'User-Agent: * / Disallow:'",
        wayback_priority="HIGH",
        searched="navajo-nsn.gov nav; navajoeconomy.org/business-regulatory; nboa-source-listing; fetched and text-extracted the PDF",
        notes="STRONGEST LOWER-48 FIND. Statutory ownership certification with a GRADED tier: Priority #1 = 100% Navajo-owned and controlled; Priority #2 = 51-99% Navajo or 51-100% other Indian owned. Each record carries a numeric 'Ownership Control: NN %'. Monthly cadence on a /wp-content/uploads/YYYY/MM/ path is the only entity in the study that could support a genuine monthly panel. Includes off-reservation firms (Phoenix/Tempe/Chandler). NO UEI/CAGE/EIN."),

    "TRBF-GILARV-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.gilariver.org/",
        hosts="www.gilariver.org",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="NONE",
        robots_note="no robots.txt (/robots.txt returns 404)",
        wayback_priority="LOW",
        searched="gilariver.org nav; /opportunities; /opportunities/business-lictax-forms; /opportunities/requests-for-proposals; FULL site map enumerated via /misc/site-map; /departments/tribal-development-services; on-site Joomla search searchword=TERO -> zero results",
        notes="No TERO or Employment Rights Office anywhere on the site - not in the site map, not in the department trees, not in on-site search. The Business License page publishes BLANK APPLICATION FORMS ONLY, no registry of licensed businesses. RFPs moved to a third-party portal (bonfirehub) which is vendor registration, not a published list, and the RFP page never mentions Indian preference."),

    "TRBF-CHKNAT-00": dict(
        verdict="LIST_FOUND_HTML",
        official_site="https://www.cherokee.org/",
        hosts="cherokeetero.com;www.cherokee.org;www.cherokeebids.org",
        list_url="https://cherokeetero.com/directory/",
        list_type="TERO", list_format="HTML", entry_count_approx="700 (the site's own claim: 'Search Over 700 Certified Indian-Owned Businesses'; NOT enumerated)",
        identifiers_present="business name;phone;email;physical address;website;category tags;description",
        update_frequency="NOT_STATED (a 'recent additions' module implies rolling)",
        source_terms_status="SILENT",
        source_terms_quote="footer '(c) 2026 The C3 Group An Indian-Owned Marketing Company' is the site DEVELOPER's credit, not a data-use term",
        publisher_relationship="SELF",
        robots_note="cherokeetero.com returns 403 to a plain client and marks its 403 page noindex; robots.txt UNREADABLE. Fragile host - throttle hard.",
        wayback_priority="MEDIUM",
        searched="cherokee.org/all-services/; /about-the-nation/procurements/ (found the pointer); cherokee.org/?s=TERO (zero results); then cherokeetero.com/directory/",
        notes="Ownership assertion quotable from cherokee.org/about-the-nation/procurements/: 'Cherokee Nation's Tribal Employment Rights Office maintains a listing of Indian-owned businesses,' used 'when letting contracts out for bid'. TERO runs on a SEPARATE DOMAIN the main site barely links. No bulk download. cherokeebids.org is VENDOR-type, not ownership."),

    "TRBF-CTWNAT-00": dict(
        verdict="LIST_BEHIND_LOGIN",
        official_site="https://www.choctawnation.com/",
        hosts="www.choctawnation.com;preferredsuppliers.choctawnation.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="robots.txt: 'User-agent: * / Disallow: /pdfs/' - the site's PDF directory is disallowed, so no PDF-path crawling on this host",
        wayback_priority="EXCLUDED",
        wayback_excluded_reason="The CDX enumeration RESOLVED this entity and closed it. The archived portal is an account-gated application, and an archive is not a route around a login.",
        searched="choctawnation.com nav; /about/commerce/; /services/; /?s=TERO (zero); /about/commerce/preferred-suppliers/ (404); grepped raw HTML of /about/commerce/ for supplier/vendor/procure/tero hrefs; THEN Wayback CDX on preferredsuppliers.choctawnation.com/* (527 archived URLs, 2014-08-23 to 2025-05-24)",
        notes="RECLASSIFIED BY THE CDX SWEEP, AND THIS IS THE STUDY'S SHARPEST CAUTION. The live Commerce page links href='https://preferredsuppliers.choctawnation.com/' for 'qualified Choctaw tribal member-owned business enterprises'; that host is NXDOMAIN on two independent resolvers, so it looked like the highest-value archive recovery in the lower 48. The archive answered the question and the answer is NO. Capture 2023-07-07 enumerates /api/account/register, /api/account/forgotpassword, /api/account/resetpassword, /api/account/userinfo alongside /api/suppliers, /api/supplierprofile/, /api/owners, /api/ownershiproles and /api/macros/Minority. IT WAS A REGISTERED-ACCOUNT APPLICATION, NOT A PUBLISHED LIST. The archive holds the ROUTE NAMES; the payload was gated. LIST_BEHIND_LOGIN means stop, and WAYBACK IS NOT A ROUTE AROUND A LOGIN - a directory a tribe put behind an account is not ours to take from an archive either. Dated strictly: the account gate is what the 2023-07-07 capture shows. A 2014-08-23 capture returns 200 on the root and its state is UNKNOWN; a 2023 snapshot cannot testify about 2014 any more than it can about 2026."),

    "TRBF-CSKTFR-00": dict(
        verdict="LIST_FOUND_PDF",
        official_site="https://cskt.org/",
        hosts="cskt.org;www.csktribes.org",
        list_url="https://cskt.org/indian-preference-office/",
        list_type="TERO", list_format="PDF", entry_count_approx="118",
        identifiers_present="business name;street address;city;state;zip;phone;fax;email;website;OWNER PERSONAL NAME;preference tier;yearly update date;services",
        update_frequency="Annual per-firm recertification; file header 'UPDATED: June 10, 2026'; each record carries its own 'YEARLY UPDATE' date",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="robots.txt sets 'Crawl-delay: 10' - HONOUR IT",
        wayback_priority="HIGH",
        searched="csktribes.org -> cskt.org nav; Indian Preference Office under both Administration and Business Opportunities; downloaded and text-extracted the PDF",
        notes="CSKT calls it the INDIAN PREFERENCE OFFICE, not TERO. Searching 'TERO' alone misses this entity entirely - the generalisable lesson of the study. Two-tier ownership assertion: 'PREFERENCE 1 = CSKT TRIBAL MEMBER', 'PREFERENCE 2 = MEMBER FROM A FEDERALLY RECOGNIZED TRIBE'. OWNER PERSONAL NAMES make this linkable. NO UEI/CAGE/EIN."),

    "TRBF-COLVLL-00": dict(
        verdict="LIST_FOUND_PDF",
        official_site="https://www.colvilletribes.com/",
        hosts="www.colvilletribes.com;static1.squarespace.com",
        list_url="https://www.colvilletribes.com/tero",
        list_type="TERO", list_format="PDF", entry_count_approx="37-40",
        identifiers_present="contractor name;contractor work-category code;primary and secondary contact;business type;address;city;state;zip;phone;cell;email;CERTIFIED TITLE 10 flag;INDIAN PERCENT OWNED (numeric);preference tier;re-cert date;SIC;on/near/off-reservation flags",
        update_frequency="NOT_STATED (file named ContractorListJune26)",
        source_terms_status="TERMS_STATED_RESTRICTIVE",
        source_terms_quote="All rights reserved, Colville Tribes. Copyright (c)",
        publisher_relationship="SELF",
        robots_note="Squarespace robots.txt NAMES anthropic-ai / ClaudeBot / GPTBot / CCBot but groups them with 'User-agent: *' with NO blanket Disallow; /tero and /s/*.pdf are permitted. The naming is an expressed preference, not a technical prohibition - treat it as a reason to ask before publishing, not as a licence to ignore.",
        wayback_priority="HIGH",
        searched="colvilletribes.com nav -> /tero; followed the PDF redirect to static1.squarespace.com and text-extracted it; fetched robots.txt in full",
        notes="RICHEST SCHEMA IN THE STUDY. Explicit numeric 'Indian % Owned' plus a four-level preference tier (Tribal Member / Colville Family Business Enterprise / Other Federally Recognized Tribal Member / Indian Business Enterprise) - a GRADED assertion, not a binary one. CRITICAL CAVEAT: firms with 0% Indian ownership still appear flagged 'Certified Title 10 = Yes', so PRESENCE ON A TERO LIST IS NOT BY ITSELF AN OWNERSHIP CLAIM - the percentage column must be read. Two trailing columns ('Aggrieved by Other Employment Actions?', 'Forwarded to EEOC?') suggest an internal administrative export; handle with care and do not republish those fields."),

    "TRBF-YAKAMA-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.yakama.com/",
        hosts="yakama.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="TERMS_STATED_RESTRICTIVE",
        source_terms_quote="(c)2021 Yakama Nation - All Rights Reserved",
        publisher_relationship="SELF",
        robots_note="robots.txt permissive; sitemap at /sitemap_index.xml",
        wayback_priority="MEDIUM",
        searched="yakama.com nav -> /employment/tero/; enumerated all six of its downloadable PDFs; on-site search ?s=certified+business -> '0 search results'",
        notes="A TERO office plainly exists and operates but PUBLISHES ONLY GOVERNING DOCUMENTS AND BLANK FORMS, never a roster: Indian Preference Application, TERO Job Application, How to Create a TERO File, the Ordinance, How to File a Complaint, FAQ - all dated 2020-09-09. The existence of an 'Indian Preference Application' confirms a certification process produces a list INTERNALLY; it is simply not published. This is the classic pattern."),

    "TRBF-UMATLL-00": dict(
        verdict="LIST_FOUND_MACHINE_READABLE",
        official_site="https://ctuir.org/",
        hosts="ctuir.org",
        list_url="https://ctuir.org/departments/workforce-development/tero/certified-indian-owned-business-directory/",
        list_type="TERO", list_format="MACHINE_READABLE", entry_count_approx="14",
        identifiers_present="business name and DBA;OWNER PERSONAL NAME AND TITLE;street address;city;state;zip;phone;email;certificate validity date range;services",
        update_frequency="NOT_STATED as a cadence; file labelled 'As Of 4.20.26'; certificates run 2-year terms",
        source_terms_status="TERMS_STATED_RESTRICTIVE",
        source_terms_quote="Copyright (c) CTUIR 2020",
        publisher_relationship="SELF",
        robots_note="robots.txt is EMPTY (zero bytes) - no directives",
        wayback_priority="MEDIUM",
        searched="ctuir.org nav; /top-menu/contracting-opportunities/ (solicitations only); /?s=TERO (zero results, site search unreliable); /government/departments/ (TERO absent at department level); /departments/workforce-development/tero/ -> the directory; downloaded and XML-parsed the DOCX",
        notes="DOCX, so machine-readable in format - but the records are PROSE PARAGRAPHS, not a table, so extraction needs regex, not a table reader. Say that rather than claiming a clean structured feed. Ownership assertion quotable from the document preamble: businesses 'have been certified by the ... TERO Manager to have met the requirements to be certified as an Indian Owned Business as identified in Chapter 5 of the CTUIR TERO Code.' Small N but very clean, with owner names. One entry is an Alaska Native entity in Anchorage - relevant to the lower-48 scope rule."),

    "TRBF-MHATAT-00": dict(
        verdict="LIST_FOUND_MACHINE_READABLE",
        official_site="https://www.mhanation.com",
        hosts="mhatero.com;mhanation.com",
        list_url="https://mhatero.com/contractor-lists/",
        list_type="TERO", list_format="MACHINE_READABLE", entry_count_approx="136",
        identifiers_present="company name;phone;email;TIER LEVEL",
        update_frequency="NOT_STATED, but filenames are date-stamped and current (06.17.2026 / 07.17.2026 / 08.11.2026 / 08.14.2026) - de facto monthly or better",
        source_terms_status="SILENT",
        source_terms_quote="(c) 2025 MHA TERO. All Rights Reserved.",
        publisher_relationship="SELF",
        robots_note="robots.txt disallows only /wp-admin/",
        wayback_priority="HIGH",
        searched="site:mhanation.com TERO; fetched mhatero.com, /contractor-lists/, /search-contractors/, robots.txt, and the Certified Indian Contractors PDF",
        notes="ONLY XLSX IN THE STUDY (Preference-Level-1-Self-Performers). EIGHT lists on one page and THEY ARE NOT THE SAME THING: Certified Indian Contractors is TERO/ownership; Approved Oilfield Vendors, General Contractors, Prime General, Prime Oilfield, Consultants, Subs w/ DOT Exemption and Suppliers are VENDOR-type and must never be read as ownership. Four 'Preference Level' lists encode an ownership gradient: L1 self-performing certified Indian contractors, L2 certified with mentorship agreements, L3 CERTIFIED INDIAN CONTRACTORS ACTING AS BROKERS, L4 other federally recognised tribes. L3 is a tribal government publicly flagging its own pass-through firms - directly relevant to attribution. NO street address, NO owner name, NO UEI/CAGE/EIN."),

    "TRBF-STNDRK-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.standingrock.org",
        hosts="standingrock.org",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched="standingrock.org homepage; /programs/ (full department directory); on-site search ?s=TERO and ?s=vendor",
        notes="TERO EXISTS but as a phone number: listed in the programme directory as 'TERO (Tribal Employment Rights Office), 701-854-7295' with no dedicated page. The TERO ordinance IS published as Title XXX of the tribal code, and a 2024 TERO public hearing notice is posted. No certified-firm list, vendor list or licence registry anywhere. Publication capacity, not TERO adoption, is what is missing."),

    "TRBF-OGLALA-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.oglala.gov",
        hosts="oglala.gov",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched="oglala.gov/programs (63-department directory); on-site search ?s=TERO",
        notes="TERO exists as a listed programme with a phone number only (605-867-5167). The programmes page gives phone numbers, not URLs. WARNING FOR ANY SWEEP: 'oglalalakotanation.net' is currently serving an OFFSHORE ONLINE-CASINO SITE IMPERSONATING THE TRIBE, resolving through a Cloudflare Workers subdomain. Do not include that host in any host list and never cite it as tribal. The legitimate host is oglala.gov."),

    "TRBF-ONDAWI-00": dict(
        verdict="LIST_FOUND_HTML",
        official_site="https://oneida-nsn.gov",
        hosts="oneida-nsn.gov",
        list_url="https://oneida-nsn.gov/business/indian-preference/indian-preference-vendor-list/",
        list_type="TERO", list_format="PORTAL_SEARCH_ONLY",
        entry_count_approx="UNKNOWN - NOT VERIFIED",
        identifiers_present="business name;NAICS CODE;contact information (per the page description; NOT individually verified)",
        update_frequency="WEEKLY - stated verbatim: 'This list is updated on Friday Evenings.' The most explicit cadence in the study.",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="robots.txt blocks only calendar views and /wp-content/uploads/formidable/; the list path is permitted",
        wayback_priority="MEDIUM",
        searched="oneida-nsn.gov homepage; /business/indian-preference/; /business/purchasing-department/; the vendor-list page twice; robots.txt; ?s=indian+preference+vendor+list",
        notes="HONEST LIMIT: the page renders its rows in JavaScript, so a plain fetch sees only the loading shell. THE ENTRY COUNT AND FIELD SET ARE UNVERIFIED and a headless render is needed. No login is required. The public WP REST search route answered HTTP 401 and was NOT worked around. Despite its name this is an Indian Preference CERTIFICATION list (annual re-certification via an IP Vendor Application), not a do-business-with list. The tribe separately runs Vendor LICENSING, which is a distinct LICENSE-type registry."),

    "TRBF-LCORLS-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.lco-nsn.gov",
        hosts="lco-nsn.gov;law.lco-nsn.gov",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched="lco-nsn.gov homepage; ?s=TERO (2 hits, BOTH FALSE POSITIVES - 'Honor the Earth' pageant pages matching the letter string); ?s=Indian preference (zero); ?s=RFP; /request-for-proposals/; site:lco-nsn.gov TERO via Bing",
        notes="CLEAN NEGATIVE on an entity we hold nothing for. No TERO office, no certified-firm list, no vendor list, no business licence registry anywhere on the LCO web presence. The only procurement surface is an RFP page with two active elder-rehab solicitations - no bidders list, no awardee list. law.lco-nsn.gov (the tribal law library) is the one host worth a Wayback sweep for an ordinance that may exist in code without being surfaced."),

    "TRBF-MSBCTW-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.choctaw.org",
        hosts="choctaw.org",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched="choctaw.org homepage; ?s=TERO (No Results Found); ?s=vendor (No Results Found); ?s=Indian preference (no results); /choctaw-tribal-code/ and reviewed all 38 code titles",
        notes="STRONG NEGATIVE. The tribal code is fully published as PDFs, 38 titles, and CONTAINS NO TERO TITLE AND NO INDIAN-PREFERENCE CONTRACTING TITLE. Three independent on-site searches returned zero. If MBCI operates a preference programme it is neither codified nor published. Note the tribe's commercial arm (Chahta Enterprise) is a separate brand not covered by choctaw.org search."),

    "TRBF-POARCH-00": dict(
        verdict="LIST_FOUND_PDF",
        official_site="https://pci-nsn.gov",
        hosts="pci-nsn.gov",
        list_url="https://pci-nsn.gov/our-government/regulatory-affairs/",
        list_type="TERO", list_format="PDF", entry_count_approx="40-55 (35 pages; density read on pages 1-4 only)",
        identifiers_present="business name;mailing address;physical street address;contact person;phone;cell;fax;email;website;registration categories keyed to TERO Regulation sections;BID LIMIT",
        update_frequency="NOT_STATED as a cadence; the PDF states 'The date of the Certification List is listed at the bottom of the page and the most current date shall be used'; current file 2026-07-21",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="robots.txt fully permissive with a sitemap",
        wayback_priority="HIGH",
        searched="pci-nsn.gov homepage; ?s=vendor (pow-wow CRAFT vendors only - 'vendor' is a false-friend term here) and ?s=TERO; the Regulatory Affairs page; the list PDF",
        notes="BEST OWNERSHIP SEMANTICS IN THE STUDY. The PDF is explicitly segmented into 'TRIBAL BUSINESSES' (tribally owned: PCI Manufacturing, PCI Printing, PCI Support Services) versus '100% TRIBAL MEMBER OWNED BUSINESSES' (individual member-owned) - a published distinction between ENTITY ownership and INDIVIDUAL Native ownership, which is exactly the line Cedar Press's own entity classes draw and which no other source in the study draws this cleanly. Certification under TERO Ordinance Title 33 with an active re-certification application, so it is a renewed status rather than a stale roster."),

    "TRBF-ESTCHK-00": dict(
        verdict="LIST_FOUND_PDF",
        official_site="https://ebci.gov",
        hosts="ebci-tero.com;ebci.gov",
        list_url="https://ebci-tero.com/vendor-list/",
        list_type="TERO", list_format="PDF", entry_count_approx="80",
        identifiers_present="business name;OWNER/PRINCIPAL NAME;street address;PO box;city;state;zip;business phone;mobile;email;TRIBAL VENDOR NUMBER;service category;PRIORITY LEVEL P1/P2;services scope",
        update_frequency="Bimonthly issue ('July-August 2026'); the document carries a running 'New 2026 Certified TERO Vendors' log by month",
        source_terms_status="SILENT",
        source_terms_quote="Certified TERO vendors are TRIBAL MEMBER owned businesses that are vetted by the TERO office and have met the qualification requirements as an Indian-owned business.",
        publisher_relationship="SELF",
        robots_note="robots.txt permissive (only /wp-admin/ disallowed), sitemap published",
        wayback_priority="HIGH",
        searched="site: search surfacing ebci-tero.com; fetched ebci-tero.com, /vendor-list/, robots.txt, the list PDF pages 1-9; ebci.com -> ebci.gov",
        notes="HIGHEST-QUALITY SINGLE DOCUMENT. Unambiguous ownership assertion, names the human owner of each firm, and carries a STABLE TRIBAL VENDOR ID that supports linkage ACROSS VINTAGES - the one identifier in the study that makes a time series joinable to itself. The month-by-month 'new vendors' log gives certification ENTRY DATES, i.e. close to a certification event history. TERO is on its own domain and is NOT linked from the ebci.gov homepage. Underlying Tribal Business Preference Law is public on Municode."),

    "TRBF-SNCNAT-00": dict(
        verdict="LIST_REFERENCED_NOT_PUBLISHED",
        official_site="https://sni.org/",
        hosts="sni.org",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        source_terms_quote="2026 (c) Seneca Nation of Indians. All Rights Reserved.",
        publisher_relationship="SELF",
        wayback_priority="MEDIUM",
        searched="sni.org nav; /community-services/tribal-employment/; ?s=vendor; ?s=TERO+certified (0 results); ?s=Request+for+Proposals; /about-our-government/rfp-rfq/; read the TERO Ordinance PDF pages 1-6",
        notes="THE CRISPEST 'CERTIFICATION EXISTS BUT IS NOT PUBLISHED' CASE. The Seneca TERO Ordinance defines an 'Indian-Owned Firm' at Sec. 2.J as 51%+ Indian-owned with significant Indian management, and Sec. 4A.A orders preference among 'qualified entities, which are certified by the Commission as 51% or more Indian-owned and controlled', with graded certifications '100% Seneca', '100% Indian-Majority Seneca', 'Majority Seneca'. So a certified-firm register with ownership-percentage tiers demonstrably exists. NONE of it is on the website. The only TERO downloads are the Ordinance, a 2025 amendment, a 2025 Compliance Plan and a Skill Bank Form for INDIVIDUALS. A records request to the Commission is the realistic route."),

    "TRBF-SRMHWK-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.srmt-nsn.gov/",
        hosts="srmt-nsn.gov",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="robots.txt disallows only /cpresources/, /vendor/ (a Composer directory, NOT a vendor list), /.env, /cache/",
        wayback_priority="LOW",
        searched="srmt-nsn.gov nav; /support-services/compliance-department; /programs/economic-development; /programs/economic-development/small-business-support; /enterprises; sitemap index and sitemaps-2-sitemap.xml grepped for tero/vendor/procure/bid/rfp/licen/business/contract/compliance - ZERO HITS FOR 'tero'",
        notes="NO TERO OFFICE AT ALL - no page, no sitemap entry, no mention. The Compliance Department does license regulated business activity, so a LICENSE registry almost certainly exists internally; nothing is published. The only published ownership assertion is the Enterprises page: TWO entities (Akwesasne Mohawk Casino Resort, Mohawk Networks LLC) under the Tewathahon:ni Corporation holding company - useful for naming the holding structure, far too thin for attribution. CAUTION: much 'Akwesasne business directory' material online belongs to the MOHAWK COUNCIL OF AKWESASNE (Canada), a DIFFERENT GOVERNMENT. Do not conflate."),

    "TRBF-PCHNGA-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.pechanga-nsn.gov/",
        hosts="pechanga-nsn.gov",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched="pechanga-nsn.gov nav; /tribal-government/services/purchasing-department; /tribal-economy; Joomla site search for 'vendor' (1 irrelevant hit), 'Indian preference' (1 irrelevant hit - a BASKETRY article), 'business license' (1 irrelevant hit)",
        notes="THE HYPOTHESIS HELD. A tribe with among the largest gaming revenues in the country and no federal contracting has a real Purchasing Department and ZERO Indian-preference or Indian-owned-business apparatus published. Procurement was outsourced in June 2026 to a third-party SaaS portal (Beacon Bid) holding SOLICITATIONS and per-solicitation interest lists; suppliers must register to bid. Registration was NOT attempted and there is no evidence a certified-ownership list sits behind it, so this is NO_LIST_FOUND, not LIST_BEHIND_LOGIN. The informative null."),

    "TRBF-ELYTNV-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://elyshoshonetribe.com/",
        hosts="elyshoshonetribe.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="ROBOTS_DISALLOW",
        source_terms_quote="robots.txt explicitly names and disallows 'ClaudeBot', 'anthropic-ai', 'GPTBot', 'Amazonbot' and others",
        publisher_relationship="SELF",
        robots_note="ROBOTS_DISALLOW naming this agent. Crawling STOPPED on discovery; two pages had been fetched before robots.txt was read and no further requests were made.",
        wayback_priority="EXCLUDED",
        wayback_excluded_reason="The origin explicitly refuses ClaudeBot and anthropic-ai. Fetching the same content from an archive would honour the letter of robots.txt and defeat its purpose. Manual research only.",
        searched="elyshoshonetribe.com homepage; /departments/; robots.txt (which ended the crawl)",
        notes="THE FLOOR CASE, and it answered. Within what was legitimately retrieved: 10 departments (Law Enforcement, Judicial, Administration, Finance, Health, Housing, Medical Clinic, Education, Environmental, Maintenance) - NO TERO, no economic development, no planning, no business licensing. Two tribal businesses named. A very small self-governance tribe with no published business apparatus of any kind."),

    # ---------------------------------------------- ANC REGIONAL CORPORATIONS
    "ANRC-ARCSLO-00": dict(
        verdict="LIST_FOUND_HTML",
        official_site="https://www.asrc.com/",
        hosts="asrcfederal.com;asrcindustrial.com;asrc.com",
        list_url="https://www.asrcfederal.com/contract-vehicles/",
        list_type="SUBSIDIARY_DIRECTORY", list_format="HTML",
        entry_count_approx="46 (21 federal + 25 industrial) against 57 operating companies in Cedar's own ranking",
        identifiers_present="UEI;CAGE;DUNS;federal contract numbers;small-business set-aside status;PARENT UEI/CAGE/DUNS",
        update_frequency="NOT_STATED",
        source_terms_status="NOT_CHECKED",
        source_terms_quote="an https://www.asrc.com/terms/ page exists in the sitemap but its HTML is unreachable",
        publisher_relationship="SELF",
        robots_note="asrc.com serves XML fine but returns HTTP 307 on EVERY HTML page - a bot/WAF gate. The full page list was enumerated from page-sitemap.xml but none of it could be read.",
        wayback_priority="HIGH",
        searched="asrc.com root and /operations/* (all HTTP 307); asrc.com/sitemap.xml and page-sitemap.xml (32 URLs enumerated); asrcfederal.com sitemaps; /contract-vehicles/; asrcindustrial.com",
        notes="THE PARENT ASSERTS BOTH SIDES OF THE OWNERSHIP LINK WITH UEIs. /asrc-federal-netcentric-oasis-small-business/ publishes prime CAGE 1R5E0, UEI T65LCYKJCW58, DUNS 113807676 ALONGSIDE parent CAGE 3JA23, UEI VYN3SB8H8BL7, DUNS 135908783. That is the third-party ownership assertion the study wants, directly joinable, with no name matching. ~21 federal entities each paired with a GSA/agency contract number. NO shareholder-owned vendor registry was found - but asrc.com's HTML is unreadable, so that is NOT_CHECKED on the parent, not absent."),

    "ANRC-NANARC-00": dict(
        verdict="LIST_FOUND_HTML",
        official_site="https://www.nana.com/",
        hosts="akima.com;nana.com",
        list_url="https://www.akima.com/opco-sitemap.xml",
        list_type="SUBSIDIARY_DIRECTORY", list_format="MACHINE_READABLE",
        entry_count_approx="55 operating companies at akima.com + 8 at nana.com",
        identifiers_present="CAGE;UEI;DUNS;primary NAICS;8(a) status;street address",
        update_frequency="NOT_STATED",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="akima.com robots.txt is WordPress boilerplate, sitemap declared. nana.com itself answered 403 to an automated client on /our-companies/ - a WAF, so nana.com's own terms are UNREAD.",
        wayback_priority="HIGH",
        searched="nana.com nav; /business/; /shareholders/; robots.txt; akima.com/sitemap.xml -> opco-sitemap.xml and operating_company-sitemap.xml; sampled /opcos/nakuuruq/",
        notes="MOST MACHINE-TRACTABLE FIND IN THE STUDY. ~55 operating companies fully ENUMERABLE FROM AN XML SITEMAP with no scraping of search pages. Sampled /opcos/nakuuruq/ publishes CAGE 3NCA0, UEI FZYKN78D9LJ2, DUNS 141090170, primary NAICS 517112, 8(a) Direct Award status and a street address. If that field template repeats across the ~55, this single host yields a UEI-keyed, PARENT-ASSERTED ANC subsidiary roster ready to join to federal award data. NO shareholder-owned business list is published; NANA offers shareholder HIRING preference, not a published shareholder-business list. NANAtkut is a login portal and was not attempted."),

    "ANRC-CALSTA-00": dict(
        verdict="LIST_FOUND_HTML",
        official_site="https://www.calistacorp.com/",
        hosts="calistashareholderbiz.com;calistacorp.com",
        list_url="https://calistashareholderbiz.com/",
        list_type="SHAREHOLDER_VENDOR", list_format="MACHINE_READABLE",
        entry_count_approx="150 shareholder-owned businesses + 40 named subsidiaries",
        identifiers_present="OWNER NAME;street address;city;state;zip;phone;email;website;business category",
        update_frequency="NOT_STATED (a self-service 'Submit Your Business' implies rolling additions)",
        source_terms_status="SILENT",
        source_terms_quote="Welcome to Calivika ('my workplace' in Yup'ik), a free directory of businesses owned by Calista Shareholders, Descendants and their spouses.",
        publisher_relationship="SELF",
        robots_note="WordPress boilerplate; two sitemaps declared; /shareholder/{slug}/ fully enumerable from shareholder-sitemap.xml",
        wayback_priority="HIGH",
        searched="calistacorp.com nav; /our-businesses/; /federal-contracting/; calistashareholderbiz.com root, robots.txt, sitemap.xml, shareholder-sitemap.xml; sampled /shareholder/arctic-accessible-homes-llc/",
        notes="THE ONLY PUBLIC SHAREHOLDER-OWNERSHIP DIRECTORY IN THE STUDY: 150 businesses, no login, enumerable from an XML sitemap, each with owner names, street address, phone, email and category. WEAKER AS AN ASSERTION THAN A TERO CERTIFICATION AND MUST BE TYPED AS SUCH: eligibility is shareholder / descendant / SPOUSE ownership with NO stated percentage threshold and NO described verification. Treat as CORROBORATING, never dispositive. Separately /our-businesses/ is a clean 40-entity subsidiary roster with live URLs, but /federal-contracting/ publishes NO UEI/CAGE/DUNS - Calista is identifier-POOR exactly where NANA and ASRC are identifier-rich."),

    "ANRC-DOYONL-00": dict(
        verdict="LIST_FOUND_HTML",
        official_site="https://www.doyon.com/",
        hosts="doyongovgrp.com;doyon.com",
        list_url="https://www.doyon.com/operations/",
        list_type="SUBSIDIARY_DIRECTORY", list_format="HTML",
        entry_count_approx="15 named entities via 7 business lines; 5 named construction subsidiaries on doyongovgrp.com",
        identifiers_present="company name;business line;parent-ownership statement; ON THE LINKED CAPABILITY-STATEMENT PDFs: UEI;CAGE;primary NAICS;office addresses;phone;named officers",
        update_frequency="NOT_STATED (capability-statement PDFs are date-stamped by upload path)",
        source_terms_status="SILENT",
        source_terms_quote="(c) 2026 Doyon, Limited",
        publisher_relationship="SELF",
        robots_note="robots.txt disallows only /wp-admin/ and publishes a sitemap",
        wayback_priority="HIGH",
        searched="doyon.com/robots.txt; sitemap.xml keyword-scanned across ~400 URLs; /subsidiaries/ and /our-companies/ and /shareholders/shareholder-owned-businesses/ all 404; /operations/; /operations/construction/; doyongovgrp.com/what-we-do/",
        notes="THE ARTEFACT CLASS WORTH GENERALISING. Per-company CAPABILITY STATEMENT PDFs carry exactly the evidence needed: Doyon-Project-Services-Capability-Statement.pdf gives 'Unique Entity ID: F9M5KXFBC8N3 | CAGE Code: 3Q5W1 | Primary NAICS: 236220' plus the explicit sentence 'Doyon Project Services, LLC (DPS) is a Minority-Owned, Small Disadvantaged Business and a subsidiary of Doyon, Limited, an Alaska Native Corporation (ANC).' A parent naming its subsidiary AND supplying the UEI is a direct machine-linkable ownership record. NO shareholder-owned business list exists; /shareholders/ covers registry, distributions, records and meetings only."),

    "ANRC-SEALSK-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.sealaska.com/",
        hosts="sealaska.com;woocheen.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="robots.txt disallows only /wp-admin/ and one plugin JSON",
        wayback_priority="LOW",
        searched="sealaska.com/robots.txt; sealaska.com/sitemap.xml keyword-scanned for subsidiar/compan/business/enterprise/vendor/supplier/procure/directory/shareholder/government/contract/operations - ONLY ANNUAL-MEETING NOTICES MATCHED; homepage nav; /about/; woocheen.com homepage and /about/",
        notes="CONFIRMS THE HYPOTHESIS THE ROSTER WAS BUILT TO TEST. The ANCSA regional with the largest shareholder base and near-zero federal contracting publishes NO subsidiary directory and NO shareholder business directory. Its whole public nav is culture, people, sustainability, land and advocacy. Operating businesses sit under a separately branded arm (woocheen.com) which also has no portfolio page and names businesses only incidentally in news items. THE FINDING: publication of a subsidiary directory tracks FEDERAL-CONTRACTING INTENSITY, not shareholder size or corporate scale. Shareholder content sits behind mySealaska, a login portal, which was not probed."),

    # ------------------------------------------------- ALASKA NATIVE VILLAGES
    "AKNF-CHNEGA-00-CHGCCO-CHGCMT": dict(
        verdict="NO_LIST_FOUND",
        official_site="NOT_FOUND",
        hosts="chenega.com;chenegamios.com;chenegaehf.com;chenegaps.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="NOT_CHECKED",
        publisher_relationship="AFFILIATED_CORPORATION",
        affiliated_publisher="Chenega Corporation (chenega.com)",
        affiliated_publisher_verdict="LIST_FOUND_HTML / SUBSIDIARY_DIRECTORY / ~50 operating companies",
        wayback_priority="HIGH",
        searched="chenega.org and chenegairacouncil.org both NXDOMAIN; chugachmiut.org (the regional tribal consortium) enumerates no member villages with URLs; then chenega.com/robots.txt, sitemaps, /strategic-business-units/, /about/native-8a-program/, and the four SBU microsites",
        notes="THE VILLAGE GOVERNMENT HAS NO DISCOVERABLE WEBSITE; THE CORPORATION PUBLISHES A LOT. The verdict above is about the ROSTER ENTITY (the IRA Council) and must not be read as a corporate finding. Chenega Corporation distributes its subsidiary directory across FOUR SBU microsites rather than one page - a crawl must follow chenega.com -> /strategic-business-units/ -> four hosts -> /companies/<slug>/ or it silently misses most entries. Each company page is structured: primary and secondary NAICS, full street addresses, SBA 8(a) SDB and HUBZone status, and the parent relationship stated in prose. NO capability-statement PDFs with UEI/CAGE were found, unlike Doyon - so linkage here needs name+address+NAICS matching, not a key join."),

    "AKNF-INPTBW-00-ARCSLO": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://nvb-nsn.gov/",
        hosts="nvb-nsn.gov;uicalaska.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="AFFILIATED_CORPORATION",
        affiliated_publisher="Ukpeagvik Inupiat Corporation (uicalaska.com)",
        affiliated_publisher_verdict="LIST_FOUND_HTML / SUBSIDIARY_DIRECTORY / 23 displayed against 'over 70' claimed",
        wayback_priority="MEDIUM",
        searched="nvb-nsn.gov homepage; sitemap.xml; FULL ENUMERATION of wp-sitemap-posts-page-1.xml (all 22 pages of the site); direct fetch of /workforce-development/; nvb-nsn.org, nativevillageofbarrow.com/.org, nvbarrow.org, nvb.org all NXDOMAIN",
        notes="THE VILLAGE GOVERNMENT HAS A REAL, WELL-MAINTAINED SITE - contra the expectation that most do not - and NONE of its 22 pages is a vendor list, TERO registry, licence registry or Indian-owned business directory. /workforce-development/ is social services with no TERO, no contractor certification and no Native-hire preference content. A clean negative on an EXHAUSTIVELY ENUMERATED page inventory. UIC's directory shows 23 companies while the site claims 'over 70 subsidiaries', so EVEN A SUCCESSFUL SCRAPE OF A PUBLISHED DIRECTORY MAY CAPTURE ONLY ABOUT A THIRD OF A CORPORATE FAMILY - budget for systematic under-coverage rather than assuming directories are exhaustive."),

    "AKNF-WAINWT-00-ARCSLO": dict(
        verdict="NO_LIST_FOUND",
        official_site="NOT_FOUND",
        hosts="olgoonik.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="NOT_CHECKED",
        publisher_relationship="AFFILIATED_CORPORATION",
        affiliated_publisher="Olgoonik Corporation (olgoonik.com)",
        affiliated_publisher_verdict="NOT_CHECKED - HTTP 403 WAF on every path including robots.txt",
        wayback_priority="HIGH",
        searched="wainwrighttribe.org, nvwainwright.org, wainwright-nsn.gov all NXDOMAIN; the sibling North Slope village Barrow DOES use the -nsn.gov convention so that pattern was tested specifically; north-slope.org/our-communities/wainwright/ lists only a municipal phone and gives no tribal council website",
        notes="THE EXPECTED AND USEFUL NEGATIVE: the village government appears to have no web presence at all and the borough's own community page cannot supply one. OLGOONIK CORPORATION MUST BE RECORDED NOT_CHECKED, NOT ABSENT - olgoonik.com returns HTTP 403 to an automated client on every path tried, with and without www. That is a WAF, not a robots disallow and not a login. No evasion was attempted. Olgoonik is rank 25 in Cedar's own contractor ranking, so this is real unread value."),

    "AKNF-KTZBUE-00-NANARC-MANLLQ": dict(
        verdict="SITE_UNREACHABLE",
        official_site="https://kotzebueira.org/",
        hosts="kotzebueira.org",
        list_type="NONE", list_format="NONE",
        source_terms_status="NOT_CHECKED",
        source_terms_quote="terms unreadable - the terms page sits behind the same 403 filter",
        publisher_relationship="NONE",
        robots_note="HTTP 403 on every path INCLUDING /robots.txt. A WAF/bot filter, NOT a robots disallow and NOT a login wall.",
        wayback_priority="HIGH",
        searched="https://www.kotzebueira.org/ -> 403; /robots.txt -> 403; kotzebueira.com and nativevillageofkotzebue.org -> NXDOMAIN; regional context nana.com/our-companies/ -> 403 (same signature)",
        notes="THE HOST EXISTS AND ANSWERS; it refuses this automated client on every path. That is NOT evidence of absence and must never be recorded as one. An unreadable term is not an absent term, so terms status is NOT_CHECKED rather than SILENT. Both kotzebueira.org and nana.com behave identically, suggesting a shared hosting/CDN filter across the region. Wayback is the appropriate route here precisely because no stated refusal was readable - unlike Ely Shoshone, where a refusal WAS readable and the archive route is therefore closed."),

    "AKNF-EKLTNA-00-CKINLT": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://eklutna-nsn.gov/",
        hosts="eklutna-nsn.gov;eklutnainc.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched="eklutna-nsn.gov homepage; /sitemap.xml; FULL ENUMERATION of page-sitemap.xml (all 34 pages) scanned for TERO/vendor/procurement/business-license/directory slugs - no matches; direct fetch of /economic-development/",
        notes="A working tribal government site of 34 pages whose /economic-development/ section is EXCLUSIVELY the Chin'an Gaming Hall project - no business directory of any kind. The site has a /members/ area behind /login/ which was NOT probed; nothing in the public structure suggests a business list lives there rather than member services. Eklutna, Inc. names operating divisions inline (Eklutna Construction & Maintenance, power generation, sand & gravel, real estate) but publishes NO dedicated subsidiary directory and directs enquirers to phone or email. Small corporation, negligible federal contracting - consistent with the Sealaska pattern."),
}


# --------------------------------------------------------------------------
# PRODUCTS 2 AND 3, TYPED SEPARATELY.
#
# READ THIS BEFORE QUOTING ANY COUNT FROM THESE TWO COLUMNS. The 2026-08-26
# pass searched for OWNERSHIP certifications. Everything below was observed
# INCIDENTALLY while looking for something else. So:
#
#   * a LIST_FOUND_* here is a real find, verified in the same pass;
#   * a NO_LIST_FOUND here is recorded ONLY where the discovery pass actually
#     enumerated the site's procurement or licensing surface and came up
#     empty;
#   * everything else stays NOT_CHECKED, and NOT_CHECKED is most of it.
#
# **The counts for products 2 and 3 are therefore a LOWER BOUND, and the
# coordinator's expectation - that general vendor lists are MORE common than
# TERO certifications - is NOT tested by this pass.** It needs a dedicated
# sweep with its own query set ("bidders list", "small works roster",
# "approved supplier", "business licence registry", "licensed vendors").
# Reporting these numbers as a measured rate would be our own scope limit
# published as a fact about the source, which is defect class 2.
# --------------------------------------------------------------------------
VT = {
    "TRBF-MHATAT-00": dict(
        verdict_vendor_relationship="LIST_FOUND_MACHINE_READABLE",
        vendor_relationship_url="https://mhatero.com/contractor-lists/",
        vendor_relationship_note=(
            "SEVEN vendor-type lists published beside the certified list, on "
            "the same page and NOT the same thing: Approved Oilfield Vendors, "
            "General Contractors, Prime General, Prime Oilfield, Consultants, "
            "Subs with MHA DOT Exemption, Suppliers. This is the single best "
            "'does business with a tribe' source found - a Bakken-scale "
            "procurement surface with named counterparties, which is exactly "
            "what mobility data cannot give. It is NOT ownership evidence."),
        verdict_business_licence="NOT_CHECKED"),
    "TRBF-COLVLL-00": dict(
        verdict_vendor_relationship="LIST_REFERENCED_NOT_PUBLISHED",
        vendor_relationship_url="https://www.colvilletribes.com/tero",
        vendor_relationship_note=(
            "The TERO page carries a SMALL WORKS ROSTER among 16+ downloads. "
            "A small works roster is a bidders list - product 2, not product "
            "1. It was seen on the page and its contents were not opened, so "
            "this is REFERENCED, not FOUND."),
        verdict_business_licence="NOT_CHECKED"),
    "TRBF-ONDAWI-00": dict(
        verdict_vendor_relationship="NOT_CHECKED",
        verdict_business_licence="LIST_REFERENCED_NOT_PUBLISHED",
        business_licence_url=(
            "https://oneida-nsn.gov/resources/licensing/vendor-licensing/"),
        business_licence_note=(
            "The tribe runs Vendor Licensing as a function DISTINCT from its "
            "Indian Preference certification. Whether a roster of licensed "
            "vendors is published was not established - the function is "
            "referenced, the registry was not seen.")),
    "TRBF-GILARV-00": dict(
        verdict_vendor_relationship="NO_LIST_FOUND",
        vendor_relationship_note=(
            "RFPs moved to a third-party portal (bonfirehub). That is vendor "
            "REGISTRATION, not a published vendor list. The full site map was "
            "enumerated."),
        verdict_business_licence="LIST_REFERENCED_NOT_PUBLISHED",
        business_licence_url=(
            "https://www.gilariver.org/index.php/opportunities/"
            "business-lictax-forms"),
        business_licence_note=(
            "A Business License regime plainly exists - application form, "
            "Transaction Privilege Tax form and Title 13 ordinance are all "
            "published - but NO REGISTRY OF LICENSED BUSINESSES is. The "
            "cleanest product-3 'exists but unpublished' case in the study.")),
    "TRBF-SRMHWK-00": dict(
        verdict_vendor_relationship="NOT_CHECKED",
        verdict_business_licence="LIST_REFERENCED_NOT_PUBLISHED",
        business_licence_url=(
            "https://www.srmt-nsn.gov/support-services/compliance-department"),
        business_licence_note=(
            "The Compliance Department's own description covers 'the levying, "
            "collection and maintenance of all fees associated with licensing "
            "regulated business activity', so a licence registry almost "
            "certainly exists internally. Nothing is published.")),
    "TRBF-CHKNAT-00": dict(
        verdict_vendor_relationship="NO_LIST_FOUND",
        vendor_relationship_url="https://www.cherokeebids.org",
        vendor_relationship_note=(
            "cherokeebids.org is a SOLICITATION board and a supplier "
            "REGISTRATION funnel. Open solicitations are not a vendor list "
            "and registration is not publication."),
        verdict_business_licence="NOT_CHECKED"),
    "TRBF-PCHNGA-00": dict(
        verdict_vendor_relationship="NO_LIST_FOUND",
        vendor_relationship_note=(
            "Procurement outsourced June 2026 to Beacon Bid, a third-party "
            "SaaS portal holding solicitations and per-solicitation interest "
            "lists behind supplier registration. Registration was NOT "
            "attempted. No published vendor roster."),
        verdict_business_licence="NO_LIST_FOUND",
        business_licence_note=(
            "On-site search for 'business license' returned one irrelevant "
            "hit.")),
    "TRBF-UMATLL-00": dict(
        verdict_vendor_relationship="NO_LIST_FOUND",
        vendor_relationship_url=(
            "https://ctuir.org/top-menu/contracting-opportunities/"),
        vendor_relationship_note=(
            "Open solicitations only, with no ownership data and no bidders "
            "or awardees roster."),
        verdict_business_licence="NOT_CHECKED"),
    "TRBF-SNCNAT-00": dict(
        verdict_vendor_relationship="NO_LIST_FOUND",
        vendor_relationship_url="https://sni.org/about-our-government/rfp-rfq/",
        vendor_relationship_note=(
            "An open-solicitations announcement board with no bidders list."),
        verdict_business_licence="NOT_CHECKED"),
    "TRBF-LCORLS-00": dict(
        verdict_vendor_relationship="NO_LIST_FOUND",
        vendor_relationship_url="https://lco-nsn.gov/request-for-proposals/",
        vendor_relationship_note=(
            "Two active elder-rehab RFPs. No bidders list, no awardee list."),
        verdict_business_licence="NO_LIST_FOUND",
        business_licence_note=(
            "No business licence registry anywhere on the LCO web presence.")),
    "TRBF-CTWNAT-00": dict(
        verdict_vendor_relationship="LIST_REFERENCED_NOT_PUBLISHED",
        vendor_relationship_url="https://preferredsuppliers.choctawnation.com/",
        vendor_relationship_note=(
            "The dead preferred-supplier portal straddles products 1 and 2: "
            "its stated purpose is member-owned enterprises (ownership) but "
            "the artefact is a SUPPLIER programme (relationship). Because the "
            "host is NXDOMAIN neither can be confirmed, so it is recorded "
            "under both and resolved under neither."),
        verdict_business_licence="NOT_CHECKED"),
    "TRBF-NAVAJO-00": dict(
        verdict_vendor_relationship="NOT_CHECKED",
        verdict_business_licence="LIST_REFERENCED_NOT_PUBLISHED",
        business_licence_note=(
            "The NBOA source list carries a 'license no.' field per record, "
            "often blank. That implies a Navajo business licence regime whose "
            "own registry was not located in this pass.")),
}


# --------------------------------------------------------------------------
# TRANCHE 2 verdicts, 2026-08-26. Same method and the same bound: the
# WebSearch budget was exhausted before the first query in BOTH passes and
# every general search engine refused (CAPTCHA / 429 / 403), so discovery ran
# by robots.txt and sitemap enumeration, each site's own search box, and
# separate-domain guessing. A NO_LIST_FOUND here is "not published on the
# entity's own site, as at 2026-08-26" - weaker than "does not exist".
#
# THE METHOD FINDING THAT NOW HAS THREE INDEPENDENT CONFIRMATIONS: separate
# domains carry the lists. tulaliptero.com, btero.com, wstero.com,
# chickasawbusinessnetwork.com, shop.fcpotawatomi.com and fortpecktero.org
# join cherokeetero.com, ebci-tero.com and mhatero.com. Treat the
# `<tribe>tero.com` guess as a PRIMARY step, not a fallback.
# --------------------------------------------------------------------------
V2 = {
    "TRBF-TULALP-00": dict(
        verdict="LIST_FOUND_MACHINE_READABLE",
        official_site="https://www.tulaliptribes-nsn.gov/",
        hosts="tulaliptero.com;tulaliptribes-nsn.gov",
        list_url="https://www.tulaliptero.com/TEROReports/NAOBRegistryAllAll",
        list_type="TERO", list_format="MACHINE_READABLE",
        entry_count_approx=(
            "UNKNOWN - certification numbers observed run #143 to #5196 and "
            "the visible records covered only the start of the alphabet, so "
            "the true figure is in the hundreds. DO NOT QUOTE A NUMBER "
            "without re-running the CSV export."),
        identifiers_present=(
            "business name;TERO CERTIFICATION NUMBER;address;phone;cell;fax;"
            "email;website;applicant/owner name;business type;years of "
            "experience;TRIBE AFFILIATION;TULALIP OWNERSHIP PERCENTAGE;"
            "small-business status;business summary"),
        update_frequency="NOT_STATED",
        source_terms_status="NOT_CHECKED",
        source_terms_quote=(
            "tulaliptero.com publishes /Home/TermsOfUse and "
            "/Home/PrivacyPolicy which were NOT opened - hence NOT_CHECKED "
            "rather than an asserted SILENT. READ THEM BEFORE ANY BULK "
            "EXPORT."),
        publisher_relationship="SELF",
        robots_note="tulaliptribes-nsn.gov/robots.txt returns 404",
        wayback_priority="HIGH",
        searched="",
        notes=(
            "THE SINGLE MOST VALUABLE FIND IN THE WHOLE STUDY. The only true "
            "machine-readable ownership registry - 'Download as .csv' and "
            "'Download as .txt' controls with construction / non-construction "
            "filters - AND the only source anywhere carrying an EXPLICIT "
            "OWNERSHIP PERCENTAGE beside a stable certification number. It "
            "records tribe affiliation for non-Tulalip Natives, so it "
            "distinguishes Tulalip-owned from generally-Indian-owned, which "
            "is exactly the distinction the rule table exists to preserve. "
            "Reachable only via one link on /GeneralServices/TERO."),
        rule_url=""),

    "TRBF-MSENAT-00": dict(
        verdict="LIST_FOUND_MACHINE_READABLE",
        official_site="https://www.muscogeenation.com/",
        hosts="muscogeenation.com;mcn-nsn.gov",
        list_url=("https://www.muscogeenation.com/wp-content/uploads/2026/08/"
                  "MCN-CESO-Vendor-List-260817.xlsx"),
        list_type="TERO", list_format="MACHINE_READABLE",
        entry_count_approx=(
            "~380, extrapolated from 7 PDF pages at ~55 rows - NOT an exact "
            "count; the XLSX would give one"),
        identifiers_present=(
            "business name;OWNER PERSONAL NAME;address;city;state;zip;phone;"
            "business details;email column present but 'N/A' throughout"),
        update_frequency=(
            "NOT_STATED as policy, but the filename is date-stamped 260817 - "
            "nine days before this check - on a predictable "
            "MCN-CESO-Vendor-List-YYMMDD.xlsx pattern, implying at least "
            "monthly republication"),
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="disallows /wp-admin only; no crawl-delay",
        wayback_priority="HIGH",
        searched="",
        notes=(
            "NATIVE XLSX WITH PER-ROW OWNER NAMES, and the codified rule to "
            "go with it: NCA 18-199 (Contracting and Employment Support Act "
            "2019) s.9-105(I) requires 'Documented evidence proving fifty-one "
            "percent (51%) or more Native ownership and proof of Native "
            "control and management'. TWO CAUTIONS. (1) The file is titled "
            "'Vendor List' and a naive keyword rule would MISFILE IT AS "
            "VENDOR - only the Act proves it is the certified roster. (2) The "
            "Act defines both 'Muscogee Owned Vendor' (51% Muscogee citizen) "
            "and 'Indian Owned Vendor' (51% other federally recognised "
            "tribe), but THE LIST DOES NOT DISTINGUISH THEM, so the owning "
            "tribe is not recoverable from the file. The word 'TERO' appears "
            "nowhere on this tribe's site."),
        rule_url=("https://www.muscogeenation.com/wp-content/uploads/2023/04/"
                  "2019-Law-final.pdf")),

    "TRBF-THNODM-00": dict(
        verdict="LIST_FOUND_PDF",
        official_site="https://www.tonation-nsn.gov/",
        hosts="tonation-nsn.gov;toua.net",
        list_url=("https://www.tonation-nsn.gov/wp-content/uploads/2026/07/"
                  "July-2026-Updated-Certified-Firms-Listing-V2.pdf"),
        list_type="TERO", list_format="PDF",
        entry_count_approx="19 (16 FIRST PREFERENCE, 3 SECOND PREFERENCE)",
        identifiers_present=(
            "company name;address;OWNER NAME AND TITLE;type of business;"
            "phone;email;fax;DATE CERTIFIED;certification status Full vs "
            "Probationary"),
        update_frequency="'Updated as of 07/21/2026' printed on every page",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="fully permissive; sitemap_index.xml declared",
        wayback_priority="HIGH",
        searched="",
        notes=(
            "AN ENTITY WE HOLD ZERO TIER-A UEI LINKS FOR, AND IT PUBLISHES. "
            "Rule quoted from TERO Ordinance 01-85 / Regulations Part 3.1: "
            "'First preference shall be given to Indian preference certified "
            "firms, 51% or more of which are owned by O'odham and other local "
            "Indians.' THE LIST SITS ON A THIRD-LEVEL PAGE NOT LINKED FROM "
            "THE TERO LANDING PAGE BODY - only sitemap enumeration found it."),
        rule_url=("https://www.tonation-nsn.gov/departments/public-safety/"
                  "tero/tero-information/")),

    "TRBF-STHUTE-00": dict(
        verdict="LIST_FOUND_PDF",
        official_site="https://www.southernute-nsn.gov/",
        hosts="southernute-nsn.gov;sugf.com",
        list_url=("https://www.southernute-nsn.gov/wp-content/uploads/sites/"
                  "15/2026/03/2026-Indian-Own-Business-List.pdf"),
        list_type="TERO", list_format="PDF",
        entry_count_approx="27",
        identifiers_present=(
            "business name;OWNER/CONTACT NAME;address;phone;email;services. "
            "No certification number, expiry, NAICS or ownership %"),
        update_frequency=(
            "ANNUAL - year-titled file under a 2026/03 upload path, with a "
            "companion 'Indian Owned Business Annual Update' form"),
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="Crawl-delay: 10 - HONOUR IT. Multisite (/sites/15/).",
        wayback_priority="HIGH",
        searched="",
        notes=(
            "ANSWERS THE GROWTH-FUND QUESTION DIRECTLY: the energy arm's "
            "operating companies - RED WILLOW PRODUCTION COMPANY and RED "
            "CEDAR GATHERING COMPANY - appear ON THE TERO INDIAN-OWNED LIST "
            "ITSELF, alongside small local contractors, rather than in a "
            "separate subsidiary directory. Certification is mandatory: firms "
            "'must be certified through the Southern Ute Indian Tribe's TERO "
            "Office as an Indian-Owned Business... regardless of any other "
            "registration or certification'. Live Adobe Sign intake - the "
            "most modern application process seen. NOTE the published "
            "preference ladder on the TERO page is about HIRING order, not "
            "business ownership; do not conflate them."),
        rule_url="https://www.southernute-nsn.gov/business/purchasing-vendors/"),

    "TRBF-LUMMIT-00": dict(
        verdict="LIST_FOUND_PDF",
        official_site="https://www.lummi-nsn.gov/",
        hosts="lummi-nsn.gov",
        list_url="https://www.lummi-nsn.gov/widgets/LummiOwnedBusinesses.php",
        list_type="TERO", list_format="PDF",
        entry_count_approx="~143 across 9 categories",
        identifiers_present=(
            "business name;description;phone;email;LICENCE EXPIRY DATE;"
            "category. No address, no owner name, no ownership %"),
        update_frequency=(
            "EFFECTIVELY LIVE - the cover page rendered 'Current as of "
            "Wednesday August 26th, 2026', the fetch date, and every footer "
            "carries it"),
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note=(
            "CONSEQUENTIAL. robots.txt disallows /apps, and the tribe's own "
            "Business Directory page links the file at "
            "/apps/BusLicenses/LummiOwnedBusinesses.php - THAT PATH WAS NOT "
            "FETCHED. The identical report is served from /widgets/, which is "
            "NOT disallowed, and that is the copy retrieved. ANY RE-RUN MUST "
            "USE /widgets/."),
        wayback_priority="MEDIUM",
        searched="",
        notes=(
            "A DYNAMICALLY GENERATED PDF - a .php endpoint rendering a fresh "
            "14-page document per request, which is why it is always current. "
            "TWO REPORTS EXIST AND MUST NOT BE CONFLATED: 'Lummi Owned "
            "Businesses' (ownership-filtered, the valuable one) and the "
            "broader 'Lummi Nation Business Phonebook'. PROVENANCE CAVEAT: "
            "the final page reads 'This has been provided by the Lummi "
            "Chamber of Commerce' - a Chamber compilation published on and "
            "served by the tribal government's own system, carrying LIBC "
            "licence-expiry data. The tribe's own directory page renders 'no "
            "documents currently available', so navigating by it alone "
            "produces a FALSE NEGATIVE."),
        rule_url=""),

    "TRBF-BLCKFT-00": dict(
        verdict="LIST_FOUND_PDF",
        official_site="https://blackfeetnation.com/",
        hosts="btero.com;blackfeetnation.com",
        list_url=("https://img1.wsimg.com/blobby/go/"
                  "2bd82483-43d9-461a-984e-7cc3cd7b3cad/downloads/"
                  "25a94857-0206-4fad-a938-543ab3713502/"
                  "doc20250610134440.pdf"),
        list_type="TERO", list_format="PDF",
        entry_count_approx="25 across 6 pages",
        identifiers_present=(
            "firm name;OWNER NAME;address;phone;email;services;TRIBAL "
            "BUSINESS LICENCE NUMBER (2025-BL-nnnn);insurance effective and "
            "expiry dates"),
        update_frequency="NOT_STATED; PDF stamped 2025-06-04, titled '2024 "
                         "Certified'",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="blackfeetnation.com sets Crawl-delay: 10 - HONOUR IT",
        wayback_priority="HIGH",
        searched="",
        notes=(
            "THE HARDEST FIND IN THE STUDY AND THE STRONGEST PROOF OF THE "
            "SEPARATE-DOMAIN RULE. The word 'TERO' appears NOWHERE in "
            "blackfeetnation.com's sitemap; neither the Economic Development "
            "nor the Employment page mentions it. The only pointer to "
            "btero.com was a PLAIN-TEXT PHONE-BOOK ENTRY in the Tribal "
            "Directory staff listing, reachable only through the WordPress "
            "?s= search. The PDF is SCANNED, so it needs OCR, not text "
            "extraction. An advertised companion 'TERO Catalog 2026' .xlsx is "
            "linked from btero.com and returns HTTP 404 - if that link is "
            "ever repaired this becomes MACHINE_READABLE. It is also the only "
            "list carrying a TRIBAL BUSINESS LICENCE NUMBER, which bridges "
            "products 1 and 3."),
        rule_url="https://www.btero.com/"),

    "TRBF-CHKSWN-00": dict(
        verdict="LIST_FOUND_HTML",
        official_site="https://www.chickasaw.net/",
        hosts="chickasawbusinessnetwork.com;chickasaw.net",
        list_url=("http://www.chickasawbusinessnetwork.com/"
                  "Chickasaw-Business-Directory.aspx"),
        list_type="TERO", list_format="HTML",
        entry_count_approx=(
            "UNKNOWN total across 17 categories; counted Construction 250 and "
            "Retail 23. Plausibly 500-900, NOT enumerated."),
        identifiers_present=(
            "business name;city;state;phone. Owner name, email and NAICS are "
            "NOT on the category listing; each name links to an unopened "
            "detail page"),
        update_frequency="NOT_STATED",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note=("chickasaw.net permissive, blocks several SEO crawlers, "
                     "no ClaudeBot; chickasawbusinessnetwork.com robots 404"),
        wayback_priority="HIGH",
        searched="",
        notes=(
            "SEPARATE-DOMAIN CASE. Reachable only via "
            "chickasawbusinessnetwork.com, and every link that page emits "
            "points at chickasaw.net paths that now 404 - a stale migration, "
            "so requests must stay on the business-network host. Rule stated "
            "on the page: 'identifies existing businesses at least 51% owned, "
            "controlled and operated by Chickasaw citizens'. CAUTION: the "
            "companion Preferred Vendor Program page frames eligibility more "
            "broadly ('minority-owned enterprises, including those owned by "
            "Chickasaw citizens') and the Construction listing carries many "
            "non-Chickasaw-sounding Oklahoma firms - CONFIRM the directory "
            "and the Preferred Vendor Program are the same population before "
            "treating the 51% rule as binding on every row."),
        rule_url=("http://www.chickasawbusinessnetwork.com/"
                  "Chickasaw-Business-Directory.aspx")),

    "TRBF-FSTCTY-00": dict(
        verdict="LIST_FOUND_HTML",
        official_site="https://www.fcpotawatomi.com/",
        hosts="shop.fcpotawatomi.com;fcpotawatomi.com",
        list_url="https://shop.fcpotawatomi.com/businesses/",
        list_type="TERO", list_format="HTML",
        entry_count_approx="18",
        identifiers_present=(
            "business name 18/18;OWNER NAME 18/18;email 14/18;phone 14/18;"
            "website 9/18;address 1/18"),
        update_frequency="NOT_STATED",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="shop.fcpotawatomi.com sets Crawl-delay: 15 - unusually "
                    "strict for a tribal host, HONOUR IT",
        wayback_priority="MEDIUM",
        searched="",
        notes=(
            "'FCP Tribal Member Owned Businesses', on the tribe's SHOP "
            "subdomain rather than the government site, and not reachable "
            "from government-site search. FCP has no TERO. Value is real but "
            "MODEST AND MUST BE TYPED DOWN: small, self-asserted, NO stated "
            "verification and NO ownership threshold published anywhere. "
            "Owner names are the useful field."),
        rule_url=""),

    "TRBF-MNMNEE-00": dict(
        verdict="LIST_FOUND_HTML",
        official_site="https://www.menominee-nsn.gov/",
        hosts="menominee-nsn.gov",
        list_url=("https://www.menominee-nsn.gov/BusinessPages/"
                  "ContractorsListing.aspx"),
        list_type="VENDOR", list_format="HTML",
        entry_count_approx="23 - the tribe's own stated count",
        identifiers_present=(
            "business name;type of business;OWNER/PRINCIPAL NAME. No address, "
            "phone, email, licence number, certification number, expiry or "
            "ownership %"),
        update_frequency="NOT_STATED",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="no Sitemap directive; ASP.NET, so sitemap enumeration "
                    "was unavailable and it was found by nav-walking",
        wayback_priority="LOW",
        searched="",
        notes=(
            "DELIBERATELY SCORED DOWN TO VENDOR, AND THE REASONING IS THE "
            "POINT. FOR ownership: the application collects an ENROLMENT "
            "NUMBER and AFFILIATION, the listing is branded 'Menominee "
            "Contractors', it is reviewed and approved before publication "
            "rather than self-serve, and it names individual principals. "
            "AGAINST: no TERO branding anywhere, no stated ownership "
            "threshold, no certification number or expiry, no published "
            "eligibility rule. It is a vetted tribal-member contractor "
            "referral directory - weaker than a TERO certification, stronger "
            "than a bidder list. CONFIRM THE ELIGIBILITY RULE BY PHONE before "
            "counting it either way. When a row is genuinely ambiguous the "
            "honest move is to type it DOWN and say why."),
        rule_url=("https://www.menominee-nsn.gov/BusinessPages/"
                  "ContractorsApplication.aspx")),

    "TRBF-LAGUNA-00": dict(
        verdict="LIST_REFERENCED_NOT_PUBLISHED",
        official_site="https://www.lagunapueblo-nsn.gov/",
        hosts="lagunapueblo-nsn.gov",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="HIGH",
        searched="",
        notes=(
            "HIGHEST-VALUE NEAR-MISS OF THE TRANCHE. The machinery is fully "
            "codified in the Indian Preference Code Chapter 8-3: 'Indian "
            "Owned and Controlled means ownership of a business by an Indian "
            "or Indian Tribe demonstrated by entitlement to fifty-one percent "
            "(51%) or greater share in the profits and losses of the business "
            "and the power to direct or cause the direction of the "
            "management, day-to-day operations, and major decisions', and "
            "s.8-3-4(E) imposes a STATUTORY DUTY to certify. The roster is "
            "not published. THE TERO IS FILED UNDER TAX ADMINISTRATION, which "
            "no employment- or business-oriented navigation would reach - add "
            "department-agnostic sitemap keyword grep as a standard step. "
            "Records request to pol.ipeco@pol-nsn.gov is the route."),
        rule_url=("https://www.lagunapueblo-nsn.gov/wp-content/uploads/2021/"
                  "02/Indian-Preference-Code-amended-May-4-2013-FINAL.pdf")),

    "TRBF-PNBSCT-00": dict(
        verdict="LIST_REFERENCED_NOT_PUBLISHED",
        official_site="https://www.penobscotnation.org/",
        hosts="penobscotnation.org",
        list_type="NONE", list_format="NONE",
        source_terms_status="ROBOTS_DISALLOW",
        source_terms_quote=(
            "'User-agent: ClaudeBot / Disallow: /', plus a Cloudflare "
            "content-signal line 'Content-Signal: search=yes,ai-train=no,"
            "use=reference' prefaced by 'As a condition of accessing this "
            "website, you agree to abide by the following content signals'"),
        publisher_relationship="SELF",
        robots_note=(
            "NAMES ClaudeBot UNDER Disallow: / alongside Amazonbot, "
            "Applebot-Extended, Bytespider, CCBot, Google-Extended, GPTBot "
            "and meta-externalagent. A later 'User-agent: *' block is "
            "permissive, but THE NAMED-AGENT RULE IS MORE SPECIFIC AND "
            "THEREFORE GOVERNS US. Collection stopped on discovery."),
        wayback_priority="EXCLUDED",
        wayback_excluded_reason=(
            "The origin explicitly refuses ClaudeBot. No archive workaround - "
            "the same rule Ely Shoshone earned."),
        searched="",
        notes=(
            "DISCLOSURE, RECORDED RATHER THAN TIDIED AWAY: a handful of pages "
            "were fetched BEFORE the robots sweep revealed the ClaudeBot "
            "disallow, and collection stopped immediately on discovery. What "
            "had already been gathered is reported; nothing further was "
            "requested and no archive fallback was used. SUBSTANTIVELY THIS "
            "IS A LIVE LEAD: the Penobscot Nation Business & Services "
            "Directory was announced 2026-06-08, is explicitly "
            "ownership-scoped ('goods and services offered by Penobscot owned "
            "enterprises') and is explicitly promised as 'public-facing'. IT "
            "DOES NOT EXIST YET. Intake is a Microsoft Forms link, so the "
            "data sits in a tenant, not on the web. Given the robots "
            "position, ANY FUTURE ACQUISITION MUST GO THROUGH DIRECT CONTACT "
            "WITH THE NATION, not crawling."),
        rule_url=""),

    "TRBF-UTEMTN-00": dict(
        verdict="LIST_REFERENCED_NOT_PUBLISHED",
        official_site="https://www.utemountainutetribe.com/",
        hosts="utemountainutetribe.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note="no robots.txt, no sitemap - flat static site, "
                    "'Copyright (c) 2020'",
        wayback_priority="MEDIUM",
        searched="",
        notes=(
            "TERO explicitly performs 'CERTIFICATION OF INDIAN-OWN BUSINESS' "
            "[sic] and publishes no roster. Rule as stated: 'Gives Indian "
            "Owned Business 51% the opportunity to acquire preference in "
            "contracting'. The Economic Development page lists the five "
            "tribal enterprises only - SUBSIDIARY content, not an ownership "
            "certification list, and must not be counted as one."),
        rule_url="https://www.utemountainutetribe.com/tero.html"),

    "TRBF-WRMSPR-00": dict(
        verdict="LIST_REFERENCED_NOT_PUBLISHED",
        official_site="https://warmsprings-nsn.gov/",
        hosts="wstero.com;warmsprings-nsn.gov",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="HIGH",
        searched="",
        notes=(
            "SEPARATE-DOMAIN CASE AGAIN: wstero.com is reachable via ONE "
            "outbound link on the tribal_programs TERO page and appears in NO "
            "warmsprings-nsn.gov sitemap. 'The TERO Commission certifies "
            "Native-owned companies that meet specific ownership and "
            "operational criteria.' The certification REGISTRATION FORM is "
            "published; the resulting register is not - employers are told to "
            "phone."),
        rule_url="https://wstero.com/for-employers/"),

    "TRBF-QUINLT-00": dict(
        verdict="LIST_REFERENCED_NOT_PUBLISHED",
        official_site="https://www.quinaultindiannation.com/",
        hosts="quinaultindiannation.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note=(
            "Names Baiduspider and Yandex under Disallow: / and gives "
            "Siteimprove a 20s crawl-delay. ClaudeBot and anthropic-ai are "
            "NOT named, so no stop condition."),
        wayback_priority="MEDIUM",
        searched="",
        notes=(
            "THE CLEANEST 'REFERENCED BUT WITHHELD' EVIDENCE ANYWHERE IN THE "
            "STUDY. The tribe's own construction bid packets state verbatim: "
            "'A list of Quinault Native American Owned Businesses is "
            "available from TERO.' The blank certification application is "
            "published; the resulting list is distributed ONLY ON REQUEST. "
            "/BusinessDirectoryii.aspx exists but returns 'No results were "
            "found' - an empty shell, not a list. TERO established 1987 under "
            "Title 97."),
        rule_url=("https://www.quinaultindiannation.com/234/"
                  "Tribal-Employment-Rights-Ordinance-TERO")),

    "TRBF-SMARIE-00": dict(
        verdict="LIST_REFERENCED_NOT_PUBLISHED",
        official_site="https://www.saulttribe.com/",
        hosts="saulttribe.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="MEDIUM",
        searched="",
        notes=(
            "A PUBLISHED RULE WITH NO PUBLISHED ROSTER, and the rule is "
            "unusually precise: 'The tribe's bid policy offers Native "
            "preference from one to five percent on goods and services "
            "procured from businesses at least 51 percent owned by members of "
            "a federally recognized by an Indian tribe.' [sic] A GRADUATED "
            "1-5% PRICE PREFERENCE on a 51% threshold. The tribe keeps an "
            "internal vendor database and asks Native-owned firms to phone "
            "for a packet. A 747-URL sitemap with zero TERO pages is a solid "
            "negative on the list itself. NOTE: no TERO office - this runs "
            "through PURCHASING."),
        rule_url=("https://www.saulttribe.com/about-us/purchasing-department/"
                  "245-about-us/purchasing-department/"
                  "5783-attention-native-owned-companies")),

    "TRBF-ABSXFP-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.fortpecktribes.org/",
        hosts="fortpecktero.org;fortpecktribes.org",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="HIGH",
        searched=(
            "fortpecktribes.org nav; /departments.html (404); ?s=TERO; "
            "/sitemap.xml -> wp-sitemap-posts-page-1.xml full 21-page "
            "enumeration; /government/departments/ (revealed the separate "
            "domain); fortpecktero.org homepage and sitemap"),
        notes=(
            "THE SEPARATE-DOMAIN GUESS PAID OFF AND THE DOMAIN IS NEARLY "
            "EMPTY. fortpecktero.org is linked from NOWHERE in site "
            "navigation - only the departments page reveals it. Its sitemap "
            "contains exactly ONE URL (lastmod 2025-03-25): a single-page "
            "GoDaddy brochure with a contact form, no certified-firm list, no "
            "covered-employer list, no ordinance. Given Fort Peck's "
            "long-standing and well-regarded TERO a certified-firm list "
            "almost certainly exists ON PAPER. THE ONE-PAGE SITE IS RECENT "
            "(Mar 2025), SO A WAYBACK SWEEP MAY SURFACE A RICHER EARLIER "
            "VERSION - the single best archive lead in the tranche."),
        rule_url=""),

    "TRBF-OSAGEN-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.osagenation-nsn.gov/",
        hosts="osagenation-nsn.gov;osagenationsmallbusiness.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched=("osagenation-nsn.gov nav; /business; /business-license; "
                  "osagenationsmallbusiness.com homepage"),
        notes=(
            "A LICENCE REGIME WITH NO PUBLIC REGISTRY - product 3, not "
            "product 1. All vendors register with the Tax Commission via a "
            "MAILED Business Application Packet, so a licensee roster "
            "certainly exists administratively and nothing is published. THE "
            "'SMALL BUSINESS PROGRAM' IS A LENDING PROGRAMME, not a "
            "certification: 'Osage Tribal Members located anywhere in the "
            "U.S. as well as any small business owner in Osage County' is a "
            "LOAN-ELIGIBILITY statement and must never be read as an "
            "ownership rule."),
        rule_url=""),

    "TRBF-SRPMCP-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.srpmic-nsn.gov/",
        hosts="srpmic-nsn.gov;businesslicense.srpmic-nsn.gov",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched=("srpmic-nsn.gov nav; ?s=TERO; sitemap_index.xml -> "
                  "page-sitemap1-3.xml, all page URLs regex-filtered for "
                  "tero|employ|vendor|business|procure|bid|licens|commerce|"
                  "contract|economic; /economic/business/; "
                  "/government/cra/licensing/; the licence portal"),
        notes=(
            "A LARGE, SOPHISTICATED GOVERNMENT WITH SUBSTANTIAL LICENSING "
            "INFRASTRUCTURE THAT EXPOSES NONE OF IT. The tribe's own claim "
            "for the GAMING licence population is 'approximately 3,500 active "
            "gaming licenses' - that is employees and gaming vendors, "
            "TERO_EMPLOYER-adjacent at best, NOT Indian-owned firms, and it "
            "is not published either. The business-licence portal requires "
            "login for 'Manage My Account', but that gates a licensee's OWN "
            "record with no public search behind it, so this is NOT "
            "LIST_BEHIND_LOGIN and no credentialed access was attempted."),
        rule_url=""),

    "TRBF-SMNLFL-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.semtribe.com/",
        hosts="semtribe.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched=("semtribe.com nav; /helpful-linksmain/vendor-application; "
                  "/services/solicitations-to-bid (raw HTML grepped for "
                  "indian|native|seminole|prefer|owned|certif|tero|list - "
                  "ZERO hits); robots.txt, sitemap.xml, sitemap_index.xml all "
                  "absent"),
        notes=(
            "THE LARGEST TRIBAL GAMING OPERATOR IN THE COUNTRY PUBLISHES NO "
            "OWNERSHIP APPARATUS. Vendor onboarding is a SINGLE EMAIL ADDRESS "
            "with a line card - no form, no certification, no roster. Bids "
            "are outsourced entirely to BidNet Direct, a commercial third "
            "party requiring registration, so nothing there is a tribal "
            "publication. Consistent with Pechanga in tranche 1: gaming "
            "wealth does not produce a certification list."),
        rule_url=""),

    "TRBF-REDLKE-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.redlakenation.org/",
        hosts="redlakenation.org",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched=("apex redlakenation.org serves an IIS7 default page and "
                  "404s robots/sitemap - THE LIVE SITE IS ON www.; "
                  "www.redlakenation.org/sitemap_index.xml -> page-sitemap "
                  "with ALL 61 URLs enumerated; "
                  "/planning-and-economic-development/"),
        notes=(
            "HOST SELECTION MATTERS HERE - the apex and www. behave "
            "differently and querying the apex alone would produce a false "
            "SITE_UNREACHABLE. Full 61-URL sitemap has no TERO, "
            "Indian-preference, procurement, vendor or business registry. "
            "Licensing exists only as BLANK APPLICATION FORMS with no "
            "register of holders. NOTABLY the site DOES publish other "
            "registries (sex-offender registry, active removal-order list), "
            "so registry publication per se is not foreign to them - the "
            "decision not to publish this one is a choice, not a capability "
            "gap."),
        rule_url=""),

    "TRBF-CHYNRV-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.cheyenneriversioux.com/",
        hosts="cheyenneriversioux.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="MEDIUM",
        searched=("cheyenneriversiouxtribe.org is DEAD and 301s to "
                  "laurenscounty.us - do not use; cheyenneriversioux.com "
                  "homepage; sitemap.xml; pages-sitemap.xml all 93 URLs; "
                  "/tribal-employment-rights-office-ter; /community-resources"),
        notes=(
            "TERO publishes four PDFs - two SDDOT compliance plans, Ordinance "
            "No. 42A, and a Council motion - but no certified-firm roster. "
            "TRAP AVOIDED AND WORTH RECORDING: /community-resources links a "
            "'business directory' PDF that is actually the CRST TELEPHONE "
            "AUTHORITY LOCAL EXCHANGE DIRECTORY - a residential phone book. "
            "Two genuine business directories are linked but are THIRD-PARTY "
            "(fourbands.org CDFI, oyateinfo.com), not sovereign publications, "
            "and are out of scope as such."),
        rule_url=("https://www.cheyenneriversioux.com/_files/ugd/"
                  "17ce4a_2454f4e3c34546359ad6a1435a256d65.pdf")),

    "TRBF-HOPIAZ-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.hopi-nsn.gov/",
        hosts="hopi-nsn.gov",
        list_type="NONE", list_format="NONE",
        source_terms_status="NOT_CHECKED",
        source_terms_quote=("the site publishes /terms-of-services/ and "
                            "/disclaimer/ which were not opened - hence "
                            "NOT_CHECKED rather than an asserted SILENT"),
        publisher_relationship="SELF",
        robots_note="Crawl-delay: 10 - honoured",
        wayback_priority="LOW",
        searched=("robots.txt; sitemap_index.xml (11 children); "
                  "page-sitemap.xml all 100 URLs; ?s=TERO (1 irrelevant hit); "
                  "/tero/ (404); /tribal-services/office-of-revenue-"
                  "commission/"),
        notes=(
            "A GENUINE NEGATIVE ON A FULLY ENUMERABLE SITE. The Revenue "
            "Commission is an APPLICATION PORTAL ONLY - business, "
            "construction, tour, peddler and special-event licences - with no "
            "public register of holders. 'Any Business/Construction services "
            "conducted on the Hopi Reservation MUST submit an application for "
            "approval prior to the start date' is a LICENSING requirement, "
            "not an ownership criterion. Worth one targeted re-check with a "
            "real search engine given Hopi's size."),
        rule_url=""),

    "TRBF-WNNBGO-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.winnebagotribe.com/",
        hosts="winnebagotribe.com;hochunkinc.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="MEDIUM",
        searched=("winnebagotribe.com nav; ?s=TERO (1 irrelevant hit); "
                  "?s=Indian+preference+business (no match); ?s=business (10 "
                  "government-service results); hochunkinc.com homepage; "
                  "/companies/ (404); sitemap.xml -> page-sitemap.xml full "
                  "38-page enumeration"),
        notes=(
            "HO-CHUNK INC. WAS CHECKED AND PUBLISHES NO SUBSIDIARY "
            "DIRECTORY - its full 38-page sitemap holds only /expertise/* "
            "narrative pages and /contact/submit-an-rfp/. A Tribal Tax "
            "Commission exists with no published licence registry. Rank 15 at "
            "$3.13B with no published ownership apparatus of any kind: the "
            "clearest lower-48 counterpart to the Sealaska finding."),
        rule_url=""),

    "TRBF-HLTNML-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://maliseets.net/",
        hosts="maliseets.net",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note=("maliseets.com serves a TLS certificate valid only for "
                     "*.townsquareinteractive.com - a cert misconfiguration, "
                     "NOT a block; it 301s to maliseets.net which is valid"),
        wayback_priority="MEDIUM",
        searched=("maliseets.com (cert mismatch, 301 -> maliseets.net); "
                  "maliseets.net nav; /wp-sitemap.xml full ~35-page "
                  "enumeration; ?s=TERO (no results); /our-businesses/"),
        notes=(
            "THE WHOLE SITE IS ~35 PAGES AND ALL WERE ENUMERATED. No TERO, "
            "no Indian-preference, no procurement, no vendor or "
            "business-licence page. NOTABLE GIVEN RANK 17 / $2.48B: the "
            "contracting is evidently run through entities not documented on "
            "the tribal government site at all, SO THE TRIBAL DOMAIN IS THE "
            "WRONG PLACE TO LOOK FOR THIS ONE. 'Our Businesses' lists three "
            "tribal enterprises with addresses only."),
        rule_url=""),

    "TRBF-PSKNML-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://paskenta-nsn.gov/",
        hosts="paskenta-nsn.gov",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched=("paskenta.org resolves to 127.0.0.1 and paskentaband.com / "
                  "paskentatribe.com are NXDOMAIN; paskenta-nsn.gov nav; "
                  "sitemap.xml -> page-sitemap.xml full 58-page enumeration"),
        notes=(
            "ALL 58 PAGES ENUMERATED. No TERO, no Indian-preference, no "
            "vendor, contractor or business-licence page. The tribe's "
            "ordinances sit at /members/government/policy-ordinances/ behind "
            "a MemberPress login which was NOT attempted; that gate covers "
            "member services and ordinances generally, and there is no "
            "evidence a certified-business list exists at all - hence "
            "NO_LIST_FOUND rather than LIST_BEHIND_LOGIN. The tribe operates "
            "TEPA Companies, a substantial federal contractor, listed only as "
            "an enterprise."),
        rule_url=""),

    "TRBF-OKYOWG-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://ohkay.org/",
        hosts="ohkay.org",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        robots_note=("ohkay.org serves an EXPIRED TLS CERTIFICATE - reachable "
                     "with a cert-ignoring client, HTTP 200. A cert-hygiene "
                     "problem, NOT a block, so this is a real negative and "
                     "not SITE_UNREACHABLE."),
        wayback_priority="LOW",
        searched=("ohkay.org homepage with full href extraction (~60 links, "
                  "complete 31-department inventory); ?s=TERO -> 'Nothing "
                  "Found'"),
        notes=(
            "THE RIO GRANDE PUEBLO STRATUM TRANCHE 1 COULD NOT COVER, AND THE "
            "NEGATIVE IS INFORMATIVE. The full department inventory contains "
            "no TERO, no employment-rights office, no procurement, no "
            "business-licence and no vendor function. The only "
            "contracting-adjacent artefact is a one-off RFP-Subs.pdf from "
            "2024. CONTRAST WITH LAGUNA, which has the full machinery - SO "
            "THIS IS NOT A UNIFORM PUEBLO PATTERN, which is exactly why two "
            "Pueblos were sampled rather than one."),
        rule_url=""),

    "TRBF-ONDANY-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.oneidaindiannation.com/",
        hosts="oneidaindiannation.com",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched=("oneidaindiannation.com nav (confirmed Oneida NY 13421, NOT "
                  "Wisconsin); /ordinances-and-regulations (category headers "
                  "only, no document links exposed); sitemap.xml full "
                  "download then regex-filtered ~1,000+ URLs for tero|"
                  "employment-right|indian-preference|vendor|procure|supplier|"
                  "contractor|business-direct|certif|licens|bid"),
        notes=(
            "CONFLATION RISK HANDLED EXPLICITLY: this is the NEW YORK nation "
            "only; oneida-nsn.gov (Wisconsin) was not touched. The sitemap "
            "keyword filter returned only press releases - 'increased "
            "regional vendor spending by 34% in 2022', 'vendor and team "
            "member investments exceeded $700 million in 2024' - and a vendor "
            "conference event page. So the Nation actively convenes vendors "
            "and publicises vendor spend while publishing NO roster and NO "
            "certification. Codes exist but are not exposed as individual "
            "URLs."),
        rule_url=""),

    "TRBF-JMSTSK-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://jamestowntribe.org/",
        hosts="jamestowntribe.org",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched=("jamestowntribe.org nav; ?s=TERO -> 'No relevant search "
                  "results found'; wp-sitemap.xml -> page-sitemap.xml full "
                  "37-page enumeration"),
        notes=(
            "ALL 37 PAGES ENUMERATED. The complete programme inventory holds "
            "no TERO, Indian-preference, procurement, vendor or "
            "business-licence function. /tribal-documents/ exists and was not "
            "opened - the only residual place a preference code could hide, "
            "and no list is indexed anywhere. Genuine negative at rank 68 / "
            "$218M."),
        rule_url=""),

    "TRBF-COQLLE-00": dict(
        verdict="NO_LIST_FOUND",
        official_site="https://www.coquilletribe.org/",
        hosts="coquilletribe.org",
        list_type="NONE", list_format="NONE",
        source_terms_status="SILENT",
        publisher_relationship="SELF",
        wayback_priority="LOW",
        searched=("coquilletribe.org nav; ?s=TERO -> 'No search results'; "
                  "wp-sitemap.xml -> wp-sitemap-posts-page-1.xml full ~180 "
                  "page enumeration"),
        notes=(
            "Full page-sitemap enumerated; most of the site is Coquille "
            "Indian Housing Authority board-meeting archives. "
            "Contracting-adjacent pages are only /bidding/ and "
            "/construction-project-bidding/ - SOLICITATION POSTINGS, NOT "
            "ROSTERS. mytribe.coquilletribe.org is a member portal, not "
            "attempted, with no indication it holds a business list."),
        rule_url=""),

    "TRBF-TURTLM-00": dict(
        verdict="SITE_UNREACHABLE",
        official_site="https://tmchippewa.com/",
        hosts="tmchippewa.com;tmbci.org",
        list_type="NONE", list_format="NONE",
        source_terms_status="NOT_CHECKED",
        publisher_relationship="NONE",
        robots_note=("HTTP 403 on EVERY path attempted INCLUDING robots.txt - "
                     "a WAF/bot block, not a readable refusal"),
        wayback_priority="HIGH",
        searched=("tmbci.org robots.txt (ECONNREFUSED on :443); "
                  "http://tmbci.org/ 301 -> tmchippewa.com; tmchippewa.com "
                  "and www. over both schemes, /robots.txt, /sitemap.xml, "
                  "/sitemap_index.xml - all 403; tmtero.com NXDOMAIN"),
        notes=(
            "A FALSE UNKNOWN, NOT A FALSE NEGATIVE - must never be scored as "
            "absence. Needs a re-check from a different egress path. The "
            "domain migration tmbci.org -> tmchippewa.com means HISTORICAL "
            "CAPTURES LIVE UNDER THE OLD HOST, so a Wayback sweep must cover "
            "both."),
        rule_url=""),

    "TRBF-SNCRLS-00": dict(
        verdict="SITE_UNREACHABLE",
        official_site="https://www.scat-nsn.gov/",
        hosts="scat-nsn.gov",
        list_type="NONE", list_format="NONE",
        source_terms_status="NOT_CHECKED",
        publisher_relationship="NONE",
        robots_note=(
            "ASYMMETRIC BLOCK: robots.txt and all sitemap XML serve 200, but "
            "EVERY HTML page including the homepage returns HTTP 307. Edge "
            "filtering, not a stated refusal. robots.txt itself is permissive "
            "and names no ClaudeBot or anthropic-ai."),
        wayback_priority="HIGH",
        searched=("robots.txt 200; sitemap_index.xml 14 children; "
                  "page-sitemap.xml 177 URLs 200; wpdmpro-sitemap.xml; "
                  "/tribal-employment-rights-office/ 307; /tero-2/ 307; "
                  "/licensing-and-permits-2/ 307; homepage 307; "
                  "/wp-json/wp/v2/pages?search=TERO 307"),
        notes=(
            "HIGH-PRIORITY RE-CHECK: THE SITEMAP PROVES TWO DISTINCT TERO "
            "PAGES EXIST - /tribal-employment-rights-office/ AND /tero-2/ - "
            "and the duplicate is the same URL-MIGRATION SIGNATURE seen at "
            "CTUIR in tranche 1. Only the WAF stopped this. DO NOT SCORE AS A "
            "NEGATIVE. Also worth checking wpdmpro download-manager IDs, "
            "which is where a certified-firm file would sit on this stack."),
        rule_url=""),

    "TRBF-WMTNAZ-00": dict(
        verdict="SITE_UNREACHABLE",
        official_site="https://www.wmat.us/",
        hosts="wmat.us",
        list_type="NONE", list_format="NONE",
        source_terms_status="NOT_CHECKED",
        publisher_relationship="NONE",
        robots_note=("TLS certificate EXPIRED on every host tried, so no "
                     "connection could be established at all"),
        wayback_priority="HIGH",
        searched=("https and http on www.wmat.us/robots.txt, wmat.us, "
                  "wmat.nsn.us - all cert-expired; whitemountainapache.org "
                  "301s to sticksushi.es, an EXPIRED/HIJACKED DOMAIN - DO NOT "
                  "USE AND DO NOT CITE AS TRIBAL"),
        notes=(
            "NOT A FINDING EITHER WAY. Needs a plain-HTTP fetch or a "
            "cert-ignoring client. THE HIJACKED whitemountainapache.org IS "
            "THE LOAD-BEARING WARNING HERE - it is the third such domain "
            "found in this study, after oglalalakotanation.net (offshore "
            "casino impersonating Oglala) and cheyenneriversiouxtribe.org "
            "(301s to laurenscounty.us)."),
        rule_url=""),
}

def main():
    if not REGISTRY.exists():
        raise SystemExit(f"{REGISTRY} absent - run 316 first")
    with REGISTRY.open(encoding="utf-8-sig", newline="") as fh:
        rdr = csv.DictReader(fh)
        cols = list(rdr.fieldnames or [])
        rows = list(rdr)
    if not cols:
        raise SystemExit("registry has no header")

    V.update(V2)
    unknown_fields = sorted(
        ({k for d in V.values() for k in d}
         | {k for d in VT.values() for k in d}) - set(cols))
    if unknown_fields:
        raise KeyError(
            f"319 writes field(s) the registry has no column for: "
            f"{unknown_fields}. Add them to 316's FIELD_COLUMNS first - "
            f"a value written to a column that does not exist is silently "
            f"lost, which is how a defect becomes a fact about the source.")

    ids_in_registry = {r["tribe_id"] for r in rows}
    # Defect class 2c: a count is not actionable, a NAME is a task.
    missing = sorted(set(V) - ids_in_registry)
    if missing:
        raise SystemExit("verdicts written for ids absent from the registry:\n"
                         "  " + "\n  ".join(missing))
    unverdicted = sorted(ids_in_registry - set(V))
    if unverdicted:
        print("  entities left NOT_CHECKED (named, not counted):")
        for t in unverdicted:
            print(f"    {t}")

    written = 0
    for r in rows:
        d = V.get(r["tribe_id"])
        if not d:
            continue
        for k, val in d.items():
            r[k] = val
        r["assertion_class"] = ASSERTION_BY_LIST_TYPE.get(
            r.get("list_type", ""), "NONE")
        # Products 2 and 3. `verdict` IS the certification verdict.
        r["verdict_certification"] = r["verdict"]
        for k, val in (VT.get(r["tribe_id"]) or {}).items():
            r[k] = val
        r["verdict_vendor_relationship"] = (
            r.get("verdict_vendor_relationship") or "NOT_CHECKED")
        r["verdict_business_licence"] = (
            r.get("verdict_business_licence") or "NOT_CHECKED")
        r["types_published"] = ";".join(
            p for p, v in (
                ("CERTIFICATION", r["verdict_certification"]),
                ("VENDOR_RELATIONSHIP", r["verdict_vendor_relationship"]),
                ("BUSINESS_LICENCE", r["verdict_business_licence"]))
            if v.startswith("LIST_FOUND")) or "NONE_FOUND"
        r["checked_date"] = CHECKED_DATE
        r["checked_by"] = CHECKED_BY
        # Consent is NOT inferred from silence.  Nothing here flips to OPT_IN.
        r["consent_status"] = r.get("consent_status") or "UNRESOLVED"
        # A row is publishable only if consent is resolved.  It never is yet.
        r["publishable"] = "Y" if r["consent_status"] == "OPT_IN" else "N"
        written += 1

    bak = REGISTRY.with_suffix(
        REGISTRY.suffix + f".bak_{CHECKED_DATE}_pre_{SCRIPT}")
    bak.write_bytes(REGISTRY.read_bytes())
    part = REGISTRY.with_suffix(REGISTRY.suffix + ".part")
    with part.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    part.replace(REGISTRY)

    with REGISTRY.open(encoding="utf-8-sig", newline="") as fh:
        back = list(csv.DictReader(fh))
    counts = {}
    for r in back:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    types = {}
    for r in back:
        types[r["list_type"]] = types.get(r["list_type"], 0) + 1
    print(f"\n{written} verdicts written; {len(back)} rows re-read")
    print("  verdicts:", dict(sorted(counts.items())))
    print("  list types:", dict(sorted(types.items())))
    print("  ownership assertions:",
          sum(1 for r in back if r["assertion_class"] == "OWNERSHIP"))
    print("  publishable rows:",
          sum(1 for r in back if r["publishable"] == "Y"),
          "(consent is UNRESOLVED everywhere; silence is not permission)")
    for label, col in (("1 CERTIFICATION     ", "verdict_certification"),
                       ("2 VENDOR_RELATIONSHIP", "verdict_vendor_relationship"),
                       ("3 BUSINESS_LICENCE  ", "verdict_business_licence")):
        c = {}
        for r in back:
            c[r[col]] = c.get(r[col], 0) + 1
        print(f"  product {label}: {dict(sorted(c.items()))}")
    print("  NOTE: products 2 and 3 were observed INCIDENTALLY while searching "
          "for product 1. Their counts are a LOWER BOUND and their rates are "
          "NOT measured. NOT_CHECKED is most of them, and that is honest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
