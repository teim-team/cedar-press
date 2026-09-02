"""1070_anc_nho_business_sweep.py — WORKSTREAM NBOA-EXPAND, read-only on the web.

WHY THIS EXISTS
---------------
The owner, 2026-09-02:

    "I wanna make sure for gaming and the business dataset that you're
     scraping like every tribal website and ANC and NHO that could have
     stuff. The native business dataset should be the easiest to do."

    "This should be easier for NHOs and ANCs and individual native
     businesses — we should get more use out of our master list."

`data/clean/native_owned_businesses.csv` carries 2,393 firms from 18 certifying
authorities. `docs/methodology/native-owned-businesses.md` §B6 measures the
coverage that produced them:

    NHOs 0 of 210 · village corporations 0 of 173 · BIE schools 0 of 185

Script 701 swept 279 hosts and it swept ONE class: the 349 federally
recognized tribes of `review/tribal_vendor_list_registry_2026-08-26.csv`.
Shard E reached 22 ANC parents through ANCSA audited filings and shard H
reached 30 NHOs through a single Wayback capture of the NHOA member page.
Nobody has ever opened an Alaska Native Village Corporation's own website, a
Native Hawaiian Organization's own website, or an Alaska Native Village
government's own website looking for a business list.

That is what this does.

SELECTION DECLARATION
---------------------
Leg used         KNOWN_IDENTIFIER. The population is the spine
                 (`data/spine/cedar_entity_spine.csv`, 1,555 rows) filtered to
                 the classes named below, joined to
                 `data/staging/cedar_web_map.csv` for a host. There is no
                 register of "Native entities that publish a business list" to
                 filter on, so the identifier leg IS the population, not a
                 sample of one.
Leg missing      none available.
population_basis `spine_entity_class` on every row emitted.

TARGET CLASSES, and why each is in scope
  anc              Alaska Native Regional Corporation · Alaska Native Village
                   Corporation · ANCSA Group Corporation. They publish
                   operating-company lists; that is parent-asserted ownership.
  nho              Native Hawaiian Organization. 13 CFR 124.3 NHOs hold 8(a)
                   subsidiaries and publish member/affiliate directories.
  tribal_government
                   Federally recognized Alaska Native Village (228 — the class
                   701 never touched) · Federally recognized tribe not probed
                   by 701 · State-recognized tribe.
  intertribal      Intertribal Organization. Tribal chambers of commerce and
                   buy-Native directories live here and the mandate names them.

WHAT IS REUSED AND WHY IT IS IMPORTED, NOT COPIED
-------------------------------------------------
`excluded_hosts()`, `is_excluded()`, `fetch()`, `robots_ok()`, `reach()` and
the terms patterns are IMPORTED from `701_enterprise_and_business_list_sweep`.
Shard M re-probed a restricted host four hours after refusing it, because its
`--deep` path consulted a hard-coded constant instead of the verdict the same
script had written. The rule that came out of that incident —

    a refusal recorded in one code path must be enforced from a single place
    every other path reads

— is why this file contains no second copy of the exclusion set. If 701's set
grows, this script's does too, in the same process.

WHAT IS NEW HERE
----------------
1. CLASS-AWARE VOCABULARY. 701's vocabulary is a tribal government's. An ANC
   says "operating companies", "family of companies", "lines of business",
   "8(a) subsidiaries"; an NHO says "member directory", "our affiliates".
   Searching a corporation with a nation's vocabulary is the same defect
   `docs/HIDDEN_DATA_TECHNIQUES.md` records for searching a business list with
   TERO vocabulary: the negatives measure the wrong noun.
2. A NAME CHECK THAT SURVIVES AN ʻOKINA. 701's `names_entity` splits on
   [^a-z]; `Kaʻala Farm` and `Hawaiʻi Maoli` tokenise into fragments and every
   NHO would have been recorded as "does not name the entity" — a false
   negative that silently deletes 210 entities from the study. Unicode is
   folded, and the corporate stopwords (Incorporated, Corporation, Foundation,
   Association) are dropped the way 701 drops Tribe/Band/Nation.
3. TABLE-AWARE EXTRACTION. 701 scrapes <h2>/<a>/<strong>. A vendor directory
   is usually a <table> or a repeating card, and the table carries the city,
   the state and the category in named columns. selectolax reads it properly.
   PDF and XLSX documents found in the media index are parsed, not just filed.
4. AUTONOMOUS RULING, RECORDED AS SUCH. 701 waits for a human to write
   ENTERPRISE_REGISTER into `enterprise_pages.csv`. This one rules
   automatically with `hit_strength()` and writes `auto_ruled = Y` on every
   row it harvested that way, so a reviewer can find them.

WHAT IT WRITES — and it writes NOTHING that already exists
----------------------------------------------------------
data/staging/native_business_sweep_1070/
    host_log.jsonl        one record per entity probed, flushed per entity
    verdicts.csv          one row per entity in the population, rebuilt from
                          host_log at the end of every stage
    business_rows.jsonl   the harvested firms, flushed per source page
    staged_native_owned_businesses_2026-09-02.csv
                          the 58-column `native_owned_businesses.csv` schema,
                          de-duplicated against the live file. THIS IS THE
                          MERGE CANDIDATE. The live file is never opened for
                          writing by this script.
    raw/                  every body that produced a row

It MINTS NOTHING, resolves no identity, touches no file in data/clean/, and
appends to no shared registry.

STAGES
------
  targets   no network. Prints the population and where the hosts came from.
  sweep     the per-entity probe. Resumable; flushes per entity.
  harvest   fetch + parse every STRONG hit into business_rows.jsonl.
  stage     build the 58-column staging CSV, de-duplicated.
  verify    the invariants. Exits 1 when one breaks.
  selftest  proves each verify invariant FIRES on an injected violation.

INVARIANTS (`verify`)
---------------------
  V1  no excluded host appears anywhere in any output
  V2  every staged row carries a source_url on a host we actually reached
  V3  no staged business_name duplicates an existing (authority, name) pair in
      data/clean/native_owned_businesses.csv
  V4  identity_scope is from the declared vocabulary and is never invented
  V5  every entity in the population has a verdict, and every verdict that
      says NO_LIST_FOUND names the machine-readable routes that were run
  V6  the staged file has exactly the 58 columns of the live schema
  V7  no staged row carries a person-held field (email, phone, street address)
  V8  no staged row comes from an authority whose site was never established
      as its own, or whose publisher refused
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import threading
import time
import unicodedata
import urllib.parse as up
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
WEBMAP = ROOT / "data" / "staging" / "cedar_web_map.csv"
LIVE_NOB = ROOT / "data" / "clean" / "native_owned_businesses.csv"
E701_VERDICTS = ROOT / "data" / "staging" / "tribal_enterprises" / "verdicts.csv"

OUT = ROOT / "data" / "staging" / "native_business_sweep_1070"
OUT.mkdir(parents=True, exist_ok=True)
RAW = OUT / "raw"
HOSTLOG = OUT / "host_log.jsonl"
VERDICTS = OUT / "verdicts.csv"
BIZ = OUT / "business_rows.jsonl"
ANCSA_BIZ = OUT / "business_rows_ancsa.jsonl"      # written by code/1073
DOCLOG_1073 = OUT / "ancsa_document_log.csv"       # written by code/1073
SHARD_E = ROOT / "data" / "staging" / "anc_subsidiaries" / "shard_e.jsonl"
STAGED = OUT / "staged_native_owned_businesses_2026-09-02.csv"
STATE = OUT / "_state.json"

TODAY = "2026-09-02"
THIS = "1070_anc_nho_business_sweep.py"


# ---------------------------------------------------------------------------
# 701 is imported, never copied. See the docstring.
# ---------------------------------------------------------------------------
def _load701():
    path = CODE / "701_enterprise_and_business_list_sweep.py"
    spec = importlib.util.spec_from_file_location("cedar701", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cedar701"] = mod
    spec.loader.exec_module(mod)
    mod.RAW = RAW                      # keep 701's raw dir out of our run
    return mod


E = _load701()
fetch = E.fetch
is_excluded = E.is_excluded
excluded_hosts = E.excluded_hosts
robots_ok = E.robots_ok
_bare = E._bare
BROWSER_HEADERS = E.BROWSER_HEADERS
HEADERS = E.HEADERS
TERMS_FORBID_PAT = E.TERMS_FORBID_PAT
MARK_CONTEXT_PAT = E.MARK_CONTEXT_PAT
TERMS_PATHS = E.TERMS_PATHS
CPT_SKIP = E.CPT_SKIP
HIJACK_PAT = E.HIJACK_PAT
NOTALIST_PAT = E.NOTALIST_PAT
NEWSISH_PATH = E.NEWSISH_PATH
BOILERPLATE_PATH = E.BOILERPLATE_PATH
CMS_TEMPLATE_PATH = E.CMS_TEMPLATE_PATH
DOCUMENT_MIME = E.DOCUMENT_MIME
NOT_A_FIRM = E.NOT_A_FIRM
NOT_A_NAME = E.NOT_A_NAME
GOV_ORGAN = E.GOV_ORGAN
looks_like_a_firm = E.looks_like_a_firm

MEDIA_PAGE_CAP = 25
# 10 workers, but PER_HOST_DELAY is enforced PER HOST inside 701's `_pace`,
# so no single tribal server ever sees more than one request per 1.2 s no
# matter how wide the pool is. The politeness bound is per host, not global.
WORKERS = 16
DEFAULT_HOURS = 2.5


# ---------------------------------------------------------------------------
# CLASS-AWARE VOCABULARY
#
# 701's ENTERPRISE_PAT/MEMBERLIST_PAT are a tribal GOVERNMENT's words. An ANC
# is a corporation and says corporation things; an NHO is a 13 CFR 124.3
# non-profit and says member things. Searching either with the other's
# vocabulary reproduces the defect HIDDEN_DATA_TECHNIQUES records for TERO
# terms: the negative measures the vocabulary, not the object.
# ---------------------------------------------------------------------------
ANC_PAT = re.compile(
    r"operating[\s\-_]*compan|family[\s\-_]*of[\s\-_]*compan|"
    r"our[\s\-_]*(compan|subsidiar|business|famil|team[\s\-_]*of)|"
    r"lines?[\s\-_]*of[\s\-_]*business|business[\s\-_]*(unit|line|segment)|"
    r"subsidiar|\bholding[s]?\b|portfolio[\s\-_]*compan|"
    r"8\s*\(\s*a\s*\)|\bsba\b[\s\-_]*8|"
    r"shareholder[\s\-_]*(owned|business|director|enterprise)|"
    r"village[\s\-_]*corporation[\s\-_]*(compan|subsidiar)|"
    r"group[\s\-_]*of[\s\-_]*compan|corporate[\s\-_]*famil|"
    r"what[\s\-_]*we[\s\-_]*do[\s\-_]*compan",
    re.I)

NHO_PAT = re.compile(
    r"member[\s\-_]*(director|list|roster|organi)|our[\s\-_]*member|"
    r"affiliate[sd]?[\s\-_]*(compan|organi|list|director)?|"
    r"subsidiar|our[\s\-_]*(compan|business|enterprise|organi)|"
    r"social[\s\-_]*enterprise|"
    r"(hawaiian|native)[\s\-_]*owned[\s\-_]*business|"
    r"business[\s\-_]*(director|listing|roster|network)|"
    r"partner[\s\-_]*organi|"
    r"\boihana\b|\bhui\b",
    re.I)

# Words that mean a LIST of firms, whatever the entity class. Unioned with
# 701's LIST_SHAPED at use, never replacing it.
LIST_SHAPED_EXT = re.compile(
    r"operating[\s\-_]*compan|family[\s\-_]*of[\s\-_]*compan|"
    r"our[\s\-_]*(compan|subsidiar)|group[\s\-_]*of[\s\-_]*compan|"
    r"portfolio[\s\-_]*compan|member[\s\-_]*(director|list|roster)|"
    r"affiliate[sd]?[\s\-_]*(list|director|compan)|"
    r"business[\s\-_]*network|vendor[\s\-_]*(list|director|regist)|"
    r"(supplier|contractor)[\s\-_]*(list|director|regist)|"
    r"lines?[\s\-_]*of[\s\-_]*business|"
    r"buy[\s\-_]*(native|indian|hawaiian)",
    re.I)

PATH_PAT_EXT = re.compile(
    r"/(operating-?compan|our-?compan|our-?subsidiar|subsidiar|"
    r"family-?of-?compan|group-?of-?compan|portfolio|holdings?|"
    r"member-?director|our-?members?|affiliates?|business-?network|"
    r"vendor-?(list|director)|supplier-?(list|director)|lines?-?of-?business|"
    r"business-?units?|what-?we-?do|buy-?(native|indian|hawaiian))", re.I)

# A COLLECTION NOUN STANDING ALONE IS A LIST.
# The canary measured the cost of not having this. CIRI publishes its
# operating companies at `/enterprise/` and Sealaska at `/our-businesses/`;
# both were scored WEAK because 701's LIST_SHAPED wants a list WORD next to
# the noun ("enterprise directory", "enterprise portfolio") and a corporation
# does not write that — it just says "Enterprise". The slug that IS the noun,
# with nothing after it, is the index page of the collection.
PATH_IS_A_COLLECTION = re.compile(
    r"^/?(our-?)?(enterprises?|compan(y|ies)|businesses|subsidiar(y|ies)|"
    r"affiliates?|portfolio|holdings?|operating-?compan(y|ies)|"
    r"family-?of-?compan(y|ies)|group-?of-?compan(y|ies)|"
    r"business-?(registry|director[y|ies]*|network|listings?)|"
    r"member-?(director[y|ies]*|list|organizations?)|members?|"
    r"shareholder-?business-?director[y|ies]*|"
    r"lines?-?of-?business|business-?units?|what-?we-?do|"
    r"vendor-?(list|director[y|ies]*)|buy-?(native|indian|hawaiian))/?$",
    re.I)

# A REPEATING FIRST PATH SEGMENT IS A COLLECTION.
# Bristol Bay publishes 200+ sitemap URLs under `/affiliate/<company>/` and
# scored MENTION_ONLY, because each individual company page's slug is a long
# sentence and every rule here judges one URL at a time. The site's own
# sitemap is telling us the shape of its data: HIDDEN_DATA_TECHNIQUES #4.
# Judge the SET, not the member.
COLLECTION_SEGMENT = re.compile(
    r"^(affiliates?|subsidiar(y|ies)|compan(y|ies)|enterprises?|businesses|"
    r"business|portfolio|holdings?|operating-?compan(y|ies)|members?|"
    r"member-?organizations?|our-?compan(y|ies)|directory|listings?|"
    r"wpbdp_listing|vendors?|suppliers?)$", re.I)
COLLECTION_MIN = 4

SEARCH_TERMS_BY_CLASS = {
    "anc": ["subsidiaries", "operating companies", "our companies",
            "lines of business", "shareholder", "8(a)"],
    "nho": ["members", "member directory", "affiliates", "subsidiaries",
            "our companies", "business directory"],
    "tribal_government": ["enterprise", "subsidiaries", "business directory",
                          "economic development", "chamber", "vendor"],
    "intertribal": ["members", "member directory", "business directory",
                    "chamber", "buy native", "vendor"],
}

# identity_scope — the gradient the methodology forbids flattening. A key here
# is a claim the SOURCE made; nothing else may be written into the column.
SCOPE_BY_KIND = {
    "enterprise_register": "tribally_owned_entity",
    "anc_operating_companies": "parent_asserted_subsidiary",
    "nho_subsidiaries": "parent_asserted_subsidiary",
    # An ANC's own directory of businesses owned by its SHAREHOLDERS is the
    # same fact Calista's 98 live rows carry, and the live file already has
    # the right word for it: `shareholder_descendant_or_spouse`, with
    # directory_type `shareholder_vendor`. Bering Straits' 58-row
    # `wpbdp_listing` was going out as `any_native`, which is a STRONGER
    # claim than the source makes — an ANC shareholder may be a descendant
    # or an heir. Match the convention that is already in the table.
    "anc_shareholder_directory": "shareholder_descendant_or_spouse",
    # An NHO association's member list is a list of ORGANISATIONS that joined
    # it. That is not an ownership claim of any strength, and none of the 14
    # existing scopes says it, so it gets its own declared value rather than
    # being flattened into `any_native`.
    "nho_member_directory": "association_member",
    # AN INTERTRIBAL BODY'S AGGREGATED DIRECTORY DOES NOT MAKE IT THE OWNER.
    # USET's Tribal Enterprise Directory lists Choctaw Fresh Produce and
    # Passamaquoddy Maple Syrup. Those ARE tribally owned — by the Mississippi
    # Band of Choctaw and the Passamaquoddy Tribe, not by USET. Writing
    # `tribally_owned_entity` against a keyed authority of USET would assert
    # an ownership the source never asserted, which is the one thing the
    # affiliation rule exists to prevent. The claim the source actually makes
    # is: this is a tribal enterprise of one of my member nations.
    "intertribal_member_enterprise": "tribally_owned_entity_of_a_member_nation",
    "intertribal_member_directory": "association_member",
    "member_business_list": "any_native",
    "licence_register": "unknown",
    "vendor_list": "vendor_relationship",
}
DECLARED_SCOPES = set(SCOPE_BY_KIND.values())

ASSERTION_BY_KIND = {
    "enterprise_register": "OWNERSHIP",
    "anc_operating_companies": "OWNERSHIP",
    "nho_subsidiaries": "OWNERSHIP",
    "anc_shareholder_directory": "OWNERSHIP",
    # RELATIONSHIP relative to the KEYED entity: USET is not the owner. The
    # ownership fact is real and belongs to a member nation Cedar has not
    # resolved on this row.
    "intertribal_member_enterprise": "RELATIONSHIP",
    "intertribal_member_directory": "RELATIONSHIP",
    "nho_member_directory": "RELATIONSHIP",
    "member_business_list": "OWNERSHIP",
    "licence_register": "RELATIONSHIP",
    "vendor_list": "RELATIONSHIP",
}

DIRECTORY_TYPE_BY_KIND = {
    "enterprise_register": "enterprise_register",
    "anc_operating_companies": "enterprise_register",
    "nho_subsidiaries": "enterprise_register",
    "anc_shareholder_directory": "shareholder_vendor",
    "intertribal_member_enterprise": "aggregated_member_enterprise_directory",
    "intertribal_member_directory": "member_directory",
    "nho_member_directory": "member_directory",
    "member_business_list": "member_business_list",
    "licence_register": "business_licence_register",
    "vendor_list": "vendor_list",
}


# ---------------------------------------------------------------------------
# name check that survives an ʻokina
# ---------------------------------------------------------------------------
CORP_STOP = {
    "tribe", "tribes", "band", "nation", "indian", "indians", "pueblo",
    "community", "rancheria", "reservation", "confederated", "village",
    "council", "peoples", "people", "native", "natives", "alaska", "alaskan",
    "hawaii", "hawaiian", "hawaiians", "incorporated", "corporation", "corp",
    "company", "limited", "association", "foundation", "organization",
    "institute", "center", "centre", "group", "services", "service",
    "society", "trust", "fund", "inc", "llc", "ltd", "the", "and", "for",
    "of", "traditional", "regional", "cultural", "culture", "affairs",
}


def _fold(s: str) -> str:
    """ʻ, ā, ē, ʼ, ‘ → plain ascii. An NHO name without this tokenises to dust."""
    s = (s or "").replace("ʻ", "").replace("ʼ", "").replace("‘", "")
    s = s.replace("’", "").replace("`", "").replace("'", "")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def names_entity(html: str, canonical: str) -> str:
    """'YES: tok' / 'NO' / 'HIJACK'. Unicode-folded on both sides.

    Whole document, no cap — 701 records a 200,000-char cap reading
    menominee-nsn.gov as not naming the Menominee.
    """
    low = _fold(html or "")
    if HIJACK_PAT.search(low):
        return "HIJACK"
    toks = [t for t in re.split(r"[^a-z]+", _fold(canonical))
            if len(t) >= 4 and t not in CORP_STOP]
    for t in toks:
        if t in low:
            return "YES: " + t
    flat = re.sub(r"[^a-z]", "", low)
    for t in toks:
        if len(t) >= 5 and t in flat:
            return "YES(flattened): " + t
    joined = "".join(toks[:3])
    if len(joined) >= 6 and joined in flat:
        return "YES(flattened): " + joined
    ph = re.sub(r"[^a-z ]+", " ", _fold(canonical)).strip()
    if ph and len(ph) >= 4 and ph in low:
        return "YES: " + ph
    # short single-token names (Kaw, Hui) — allow the 3-letter fallback last
    short = [t for t in re.split(r"[^a-z]+", _fold(canonical))
             if 3 <= len(t) < 4 and t not in CORP_STOP]
    for t in short:
        if re.search(r"\b" + t + r"\b", low):
            return "YES(short): " + t
    return "NO"


def distinctive_tokens(canonical: str) -> list[str]:
    return [t for t in re.split(r"[^a-z]+", _fold(canonical))
            if len(t) >= 4 and t not in CORP_STOP]


def host_corroborates(host: str, canonical: str) -> bool:
    """Does the DOMAIN carry the entity's name?

    Needed for the 14 entities whose canonical name is nothing but stopwords
    once tribal and corporate furniture is removed: `Council`, `Eek`, `Ute`,
    `Koi`. For those the page-text name check degenerates — the word
    "council" appears on every tribal website ever built, and it passed
    kawerak.org (the Bering Strait regional consortium) as the village of
    Council's own site, which then produced six rows of navigation furniture
    filed under a tribal government. A name that carries no information
    cannot establish identity from page text alone; the domain has to say it
    too.
    """
    h = re.sub(r"[^a-z0-9]", "", _bare(host).rsplit(".", 1)[0])
    flat = re.sub(r"[^a-z0-9]", "", _fold(canonical))
    if flat and flat in h:
        return True
    # and the other direction: `councilnative.com` for "Council Native
    # Corporation". Every token of that name is a stopword, so the token
    # test below cannot fire, and the domain is plainly the entity's.
    if len(h) >= 5 and h in flat:
        return True
    toks = [t for t in re.split(r"[^a-z]+", _fold(canonical))
            if len(t) >= 3 and t not in CORP_STOP]
    return bool(toks) and all(t in h for t in toks)


def classify(blob: str, klass: str) -> tuple[str | None, str]:
    """(kind, matched_term). NOTALIST vetoes. Class vocabulary runs FIRST."""
    text = blob or ""
    if NOTALIST_PAT.search(text):
        return None, ""
    if klass == "anc":
        m = ANC_PAT.search(text)
        if m:
            return "anc_operating_companies", m.group(0)
    if klass == "nho":
        m = NHO_PAT.search(text)
        if m:
            term = m.group(0).lower()
            kind = ("nho_member_directory"
                    if "member" in term or "affiliate" in term
                    else "nho_subsidiaries")
            return kind, m.group(0)
    k, t = E.classify(text)
    return k, t


def hit_strength(h: dict) -> str:
    """STRONG (a published list) / WEAK. 701's judgement, plus our vocabulary."""
    route = h.get("route", "")
    title = re.sub(r"^\[[^\]]{1,40}\]\s*", "", h.get("title", "") or "")
    url = h.get("url", "") or ""
    path = up.urlparse(url).path

    if route == "custom_post_type":
        return "STRONG" if int(h.get("n_items") or 0) >= 2 else "WEAK"
    if route == "sitemap_collection":
        return "STRONG" if int(h.get("n_items") or 0) >= COLLECTION_MIN \
            else "WEAK"
    if route == "wp_media":
        mime = h.get("mime", "") or ""
        if not mime.startswith(DOCUMENT_MIME):
            return "WEAK"
        blob = f"{url} {title}"
        return ("STRONG" if (E.LIST_SHAPED.search(blob)
                             or LIST_SHAPED_EXT.search(blob)) else "WEAK")
    if NEWSISH_PATH.search(path) or BOILERPLATE_PATH.search(path):
        return "WEAK"
    if CMS_TEMPLATE_PATH.search(path):
        return "WEAK"
    if PATH_IS_A_COLLECTION.search(path):
        return "STRONG"
    if not (E.LIST_SHAPED.search(path) or LIST_SHAPED_EXT.search(path)):
        return "WEAK"
    last = [seg for seg in path.strip("/").split("/") if seg][-1:]
    if last and len(re.split(r"[-_+.]",
                             re.sub(r"\.[a-z]{2,5}$", "", last[0]))) > 5:
        return "WEAK"
    return "STRONG"


# ---------------------------------------------------------------------------
# reach() — 701's ladder, with OUR name check
# ---------------------------------------------------------------------------
def reach(host: str, canonical: str):
    return E.reach(host, accept=lambda b: names_entity(b, canonical) != "NO")


# ---------------------------------------------------------------------------
# population
# ---------------------------------------------------------------------------
CLASS_OF = {
    "Alaska Native Regional Corporation": "anc",
    "Alaska Native Village Corporation": "anc",
    "ANCSA Group Corporation": "anc",
    "Native Hawaiian Organization": "nho",
    "Federally recognized Alaska Native Village": "tribal_government",
    "Federally recognized tribe": "tribal_government",
    "State-recognized tribe": "tribal_government",
    "Intertribal Organization": "intertribal",
}
GOOD_URL_TYPE = {"government", "corporate", "organization", "institution",
                 "tribal_council", "consortium", "tero", "subsidiary_list",
                 "business_directory", "chamber"}

# A PLATFORM IS NOT THE ENTITY'S HOST.
# The web map carries `web.archive.org/.../malamamolokai.org` and Facebook
# pages as an entity's "organization" URL. Probing those would run the terms
# check, the robots check and the name check against ARCHIVE.ORG or META —
# whose terms are not the nation's and whose robots file says nothing about
# the nation's data. The Wayback route is a legitimate LATER rung when an
# origin is gone; it is not the origin, and treating it as one would file a
# platform's verdict under a Native entity's name.
NOT_THE_ENTITYS_HOST = {
    "web.archive.org", "archive.org", "archive.ph", "facebook.com",
    "m.facebook.com", "twitter.com", "x.com", "instagram.com",
    "linkedin.com", "youtube.com", "wixsite.com", "google.com",
    "docs.google.com", "drive.google.com",
}


def spine_rows() -> list[dict]:
    with open(SPINE, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def probed_by_701() -> set[str]:
    if not E701_VERDICTS.exists():
        return set()
    with open(E701_VERDICTS, encoding="utf-8-sig", newline="") as fh:
        return {r["tribe_id"] for r in csv.DictReader(fh)
                if (r.get("probed") or "") == "Y"}


def targets() -> list[dict]:
    """The population. Never a sample — see the SELECTION DECLARATION."""
    prior = probed_by_701()
    hosts: dict[str, list[str]] = {}
    with open(WEBMAP, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["url_type"] not in GOOD_URL_TYPE:
                continue
            h = _bare(up.urlparse(r["url"]).netloc)
            if not h or h in NOT_THE_ENTITYS_HOST:
                continue
            live = r["http_status"].startswith(("2", "3"))
            b = hosts.setdefault(r["cedar_uid"], [])
            # a live host first; a dead-recorded one is still tried, because
            # `reach` fixes www/TLS/UA failures that produced those statuses
            (b.insert(0, h) if live else b.append(h))
    out = []
    for s in spine_rows():
        k = CLASS_OF.get(s["entity_class"])
        if not k:
            continue
        if k == "tribal_government" and s["tribe_id"] in prior:
            continue                       # 701 owns it; do not re-probe
        hh = [x for x in dict.fromkeys(hosts.get(s["cedar_uid"], [])) if x]
        out.append({
            "tribe_id": s["tribe_id"],
            "cedar_uid": s["cedar_uid"],
            "canonical_name": s["canonical_name"],
            "entity_class": s["entity_class"],
            "klass": k,
            "state": s.get("state", ""),
            "host": hh[0] if hh else "",
            "all_hosts": hh,
        })
    return out


# ---------------------------------------------------------------------------
# the per-entity probe
# ---------------------------------------------------------------------------
_wlock = threading.Lock()


def _flush(path: Path, obj) -> None:
    """FLUSH PER ENTITY. A buffered shard map nearly lost 1,159 rows once and
    three agents were killed mid-run on 2026-09-02."""
    with _wlock:
        with open(path, "a", encoding="utf-8", newline="") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())


def sweep_entity(t: dict) -> dict:
    host = t["host"]
    log = {
        "tribe_id": t["tribe_id"], "cedar_uid": t["cedar_uid"],
        "canonical_name": t["canonical_name"],
        "entity_class": t["entity_class"], "klass": t["klass"],
        "host": host, "checked_date": TODAY,
        "excluded_reason": "", "robots_note": "", "robots_allowed": None,
        "reached": "N", "reach_route": "", "names_entity": "",
        "terms_status": "NOT_CHECKED", "terms_url": "", "terms_quote": "",
        "wp": "N", "cpts": [], "media_total": 0, "media_scanned": 0,
        "sitemap_urls": 0, "hits": [],
        "routes": {"types": False, "search": False, "media": False,
                   "sitemap": False},
        "machine_readable_basis": "", "requests": 0, "errors": [],
    }
    r0 = E._nreq[0]
    if not host:
        log["errors"].append("NO_HOST_IN_WEB_MAP")
        log["machine_readable_basis"] = ("no URL of any usable type in "
                                         "cedar_web_map.csv for this entity")
        return log

    why = is_excluded(host)
    if why:
        log["excluded_reason"] = why
        log["terms_status"] = "TERMS_STATED_RESTRICTIVE"
        return log

    root = how = body = None
    for h in t["all_hosts"][:3]:
        if is_excluded(h):
            log["excluded_reason"] = is_excluded(h)
            log["terms_status"] = "TERMS_STATED_RESTRICTIVE"
            return log
        root, how, body = reach(h, t["canonical_name"])
        if root:
            log["host"] = h
            break
    log["reach_route"] = how or ""
    if not root:
        log["requests"] = E._nreq[0] - r0
        return log
    log["reached"] = "Y"

    ok, note = robots_ok(root)
    log["robots_allowed"], log["robots_note"] = ok, note
    if not ok:
        log["errors"].append("robots Disallow on /")
        log["requests"] = E._nreq[0] - r0
        return log

    log["names_entity"] = names_entity(body, t["canonical_name"])
    if (log["names_entity"].startswith("YES")
            and not distinctive_tokens(t["canonical_name"])
            and not host_corroborates(log["host"], t["canonical_name"])):
        log["names_entity"] = "INDETERMINATE"
        log["errors"].append(
            "canonical name carries no distinctive token once tribal and "
            "corporate stopwords are removed, and the domain does not carry "
            "it either - identity cannot be established from page text")
    if not log["names_entity"].startswith("YES"):
        log["errors"].append(
            "served page does not name the entity — not treated as this "
            "entity's site")
        log["requests"] = E._nreq[0] - r0
        return log

    # TERMS, BEFORE any enumeration
    for p in TERMS_PATHS:
        r = fetch(root + p, headers=BROWSER_HEADERS, verify=False)
        if not (r["ok"] and r["status"] == 200 and len(r["text"]) > 400):
            continue
        txt = re.sub(r"<[^>]+>", " ", r["text"])
        m = TERMS_FORBID_PAT.search(txt)
        log["terms_url"] = r["url"]
        if m:
            s = max(0, m.start() - 130)
            quote = re.sub(r"\s+", " ", txt[s:m.end() + 130]).strip()
            log["terms_quote"] = quote
            if MARK_CONTEXT_PAT.search(quote):
                log["terms_status"] = "TERMS_STATED_COPYRIGHT_ONLY"
            else:
                log["terms_status"] = "TERMS_STATED_RESTRICTIVE"
                log["requests"] = E._nreq[0] - r0
                return log
        else:
            log["terms_status"] = "TERMS_READ_PERMISSIVE"
        break
    else:
        log["terms_status"] = "NO_TERMS_PAGE_SERVED"

    kl = t["klass"]

    def note_hit(route, url, title, extra=""):
        kind, term = classify(f"{url} {title} {extra}", kl)
        if kind:
            log["hits"].append({"route": route, "url": url,
                                "title": title.strip()[:200], "kind": kind,
                                "matched": term})

    # 1 — WordPress probe gates the three REST routes
    probe = fetch(f"{root}/wp-json/", headers=BROWSER_HEADERS, verify=False)
    has_wp = bool(probe["ok"] and probe["status"] == 200
                  and probe["text"].lstrip().startswith("{"))
    log["machine_readable_basis"] = (
        "WordPress REST answered; types/search/media all attempted"
        if has_wp else
        "not WordPress — /wp-json returns nothing, so the media index, custom "
        "post types and REST search DO NOT EXIST on this host; the only "
        "machine-readable route is the sitemap")

    # 2 — CUSTOM POST TYPES: the highest-yield signal in this project
    if has_wp:
        r = fetch(f"{root}/wp-json/wp/v2/types", headers=BROWSER_HEADERS,
                  verify=False)
        if r["ok"] and r["status"] == 200:
            try:
                types = json.loads(r["text"])
            except ValueError:
                types = {}
            if isinstance(types, dict) and types:
                log["wp"] = "Y"
                log["routes"]["types"] = True
                for slug, meta in types.items():
                    if slug in CPT_SKIP or not isinstance(meta, dict):
                        continue
                    log["cpts"].append(slug)
                    label = f"{meta.get('name','')} {slug}".replace("_", " ")
                    kind, term = classify(label, kl)
                    if not kind:
                        continue
                    base = meta.get("rest_base") or slug
                    ep = f"{root}/wp-json/wp/v2/{base}?per_page=100"
                    hit = {"route": "custom_post_type", "url": ep,
                           "title": f"CPT `{slug}` ({meta.get('name','')})",
                           "kind": kind, "matched": term}
                    rr = fetch(ep, headers=BROWSER_HEADERS, verify=False)
                    if rr["ok"] and rr["status"] == 200:
                        try:
                            items = json.loads(rr["text"])
                        except ValueError:
                            items = []
                        if isinstance(items, list):
                            hit["n_items"] = len(items)
                    log["hits"].append(hit)

    # 3 — REST search, class vocabulary
    for term in (SEARCH_TERMS_BY_CLASS[kl] if has_wp else []):
        r = fetch(f"{root}/wp-json/wp/v2/search?search={up.quote(term)}"
                  f"&per_page=100", headers=BROWSER_HEADERS, verify=False)
        if not (r["ok"] and r["status"] == 200):
            continue
        log["routes"]["search"] = True
        log["wp"] = "Y"
        try:
            items = json.loads(r["text"])
        except ValueError:
            continue
        for it in items if isinstance(items, list) else []:
            note_hit("rest_search", str(it.get("url", "")),
                     f"[{term}] {it.get('title','')}")

    # 4 — MEDIA, unfiltered by mime (shard M's best find was a .docx)
    page, total_pages, seen = 1, 1, 0
    while has_wp and page <= total_pages and page <= MEDIA_PAGE_CAP:
        r = fetch(f"{root}/wp-json/wp/v2/media?per_page=100&page={page}"
                  f"&_fields=source_url,title,date,modified,mime_type",
                  headers=BROWSER_HEADERS, verify=False)
        if not (r["ok"] and r["status"] == 200):
            break
        try:
            items = json.loads(r["text"])
        except ValueError:
            break
        if not isinstance(items, list) or not items:
            break
        log["wp"] = "Y"
        log["routes"]["media"] = True
        log["media_total"] = int(r["headers"].get("x-wp-total", 0) or 0)
        total_pages = int(r["headers"].get("x-wp-totalpages", 1) or 1)
        for it in items:
            seen += 1
            title = re.sub(r"<[^>]+>", "",
                           (it.get("title") or {}).get("rendered", ""))
            u = it.get("source_url", "") or ""
            mime = it.get("mime_type", "") or ""
            kind, term = classify(f"{u} {title}", kl)
            if kind and not mime.startswith(("image/", "video/", "audio/")):
                log["hits"].append({
                    "route": "wp_media", "url": u,
                    "title": title.strip()[:200], "kind": kind,
                    "matched": term,
                    "edition_date": (it.get("date") or "")[:10],
                    "modified": (it.get("modified") or "")[:10],
                    "mime": mime})
        page += 1
    log["media_scanned"] = seen

    # 5 — sitemaps
    locs = []
    for sm in ("/sitemap_index.xml", "/sitemap.xml", "/wp-sitemap.xml"):
        r = fetch(root + sm, headers=BROWSER_HEADERS, verify=False)
        if not (r["ok"] and r["status"] == 200 and "<" in r["text"]):
            continue
        log["routes"]["sitemap"] = True
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r["text"])
        for sub in [l for l in locs if l.endswith(".xml")][:6]:
            r2 = fetch(sub, headers=BROWSER_HEADERS, verify=False)
            if r2["ok"] and r2["status"] == 200:
                locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", r2["text"])
        break
    pages = [l for l in dict.fromkeys(locs) if not l.endswith(".xml")]
    log["sitemap_urls"] = len(pages)
    for l in pages:
        p = up.urlparse(l).path
        if E.PATH_PAT.search(p) or PATH_PAT_EXT.search(p):
            kind, term = classify(p.replace("/", " ").replace("-", " "), kl)
            if kind:
                log["hits"].append({"route": "sitemap", "url": l, "title": "",
                                    "kind": kind, "matched": term})

    # 5b — the sitemap's own SHAPE. A repeating first segment is a collection;
    #      see COLLECTION_SEGMENT. Judge the set, not the member.
    import collections as _c
    seg = _c.defaultdict(list)
    for l in pages:
        parts = [x for x in up.urlparse(l).path.strip("/").split("/") if x]
        if len(parts) == 2:
            seg[parts[0].lower()].append(l)
    for s, members in seg.items():
        if len(members) < COLLECTION_MIN or not COLLECTION_SEGMENT.match(s):
            continue
        kind, term = classify(s.replace("-", " ") + " listing", kl)
        if not kind:
            kind, term = (("anc_operating_companies" if kl == "anc"
                           else "nho_subsidiaries" if kl == "nho"
                           else "enterprise_register"),
                          s)
        idx = up.urlunparse(up.urlparse(members[0])._replace(
            path=f"/{s}/", query="", fragment=""))
        log["hits"].append({
            "route": "sitemap_collection", "url": idx,
            "title": f"sitemap segment /{s}/ carries {len(members)} member "
                     f"pages", "kind": kind, "matched": term,
            "n_items": len(members), "members": members[:200]})

    # 6 — NAV FALLBACK. Not every site is WordPress and not every site ships a
    #     sitemap; 38 of 173 village-corp hosts answered at all on the last
    #     web map. The homepage's own links are a machine-readable route too,
    #     and for a corporation the "Our Companies" nav item IS the list.
    if not (log["routes"]["sitemap"] or log["routes"]["types"]):
        for href, txt in re.findall(r'<a\b[^>]*href="([^"#]+)"[^>]*>(.*?)</a>',
                                    body or "", re.S | re.I)[:400]:
            u = up.urljoin(root + "/", href)
            if _bare(up.urlparse(u).netloc) != _bare(up.urlparse(root).netloc):
                continue
            label = re.sub(r"<[^>]+>", " ", txt)
            label = re.sub(r"\s+", " ", label).strip()
            p = up.urlparse(u).path
            if not (E.PATH_PAT.search(p) or PATH_PAT_EXT.search(p)
                    or E.LIST_SHAPED.search(label)
                    or LIST_SHAPED_EXT.search(label)):
                continue
            kind, term = classify(f"{p.replace('/',' ')} {label}", kl)
            if kind:
                log["hits"].append({"route": "nav_link", "url": u,
                                    "title": label[:200], "kind": kind,
                                    "matched": term})
        log["machine_readable_basis"] += (
            " || nav-link fallback run: the homepage's own <a href> set")

    log["requests"] = E._nreq[0] - r0
    return log


def stage_sweep(limit=None, only=None, hours=DEFAULT_HOURS,
                redo=None) -> None:
    E._deadline[0] = time.time() + hours * 3600
    RAW.mkdir(parents=True, exist_ok=True)
    done = set()
    if HOSTLOG.exists():
        for l in HOSTLOG.read_text(encoding="utf-8").splitlines():
            if l.strip():
                try:
                    done.add(json.loads(l)["tribe_id"])
                except Exception:
                    pass
    pop = targets()
    done -= (redo or set())
    todo = [t for t in pop if t["tribe_id"] not in done]
    if only:
        todo = [t for t in todo if t["klass"] in only]
    # The owner named ANCs and NHOs the easy class and the one never touched.
    # If this run is killed mid-way — three agents were today — the classes
    # with zero prior coverage are the ones already done.
    order = {"anc": 0, "nho": 1, "intertribal": 2, "tribal_government": 3}
    todo.sort(key=lambda t: (order.get(t["klass"], 9), t["canonical_name"]))
    if limit:
        todo = todo[:limit]
    print(f"[sweep] population {len(pop)} · already logged {len(done)} · "
          f"probing {len(todo)} · deadline {hours}h")
    n = [0]

    def run(t):
        try:
            log = sweep_entity(t)
        except Exception as exc:                       # never lose the entity
            log = {"tribe_id": t["tribe_id"], "cedar_uid": t["cedar_uid"],
                   "canonical_name": t["canonical_name"],
                   "entity_class": t["entity_class"], "klass": t["klass"],
                   "host": t["host"], "checked_date": TODAY,
                   "errors": [f"EXCEPTION {type(exc).__name__}: {exc}"],
                   "hits": [], "reached": "N", "requests": 0,
                   "machine_readable_basis": "aborted by exception"}
        _flush(HOSTLOG, log)                            # PER ENTITY
        with _wlock:
            n[0] += 1
            s = sum(1 for h in log.get("hits", [])
                    if hit_strength(h) == "STRONG")
            # cp1252 CANNOT ENCODE THIS CORPUS. `Ukpeaġvik Iñupiat
            # Corporation` raised UnicodeEncodeError inside the worker, the
            # exception propagated out of ex.map, and a 290-entity run died
            # at the PRINT — not at the fetch. Every record was already on
            # disk because the flush is per entity, which is the only reason
            # this cost minutes instead of hours. Progress output is now
            # ascii-safe and can never kill a run again.
            line = (f"  [{n[0]:4d}/{len(todo)}] {log['klass'][:4]:4s} "
                    f"{log['canonical_name'][:34]:34s} "
                    f"{log.get('reached','N')} "
                    f"hits={len(log.get('hits', [])):3d} strong={s:2d} "
                    f"{log.get('host','')[:34]}")
            sys.stdout.write(
                line.encode("ascii", "replace").decode("ascii") + chr(10))
            sys.stdout.flush()

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(run, todo))
    write_verdicts()


# ---------------------------------------------------------------------------
# verdicts
# ---------------------------------------------------------------------------
VERDICT_COLS = ["tribe_id", "cedar_uid", "canonical_name", "entity_class",
                "klass", "host", "probed", "reached", "reach_route",
                "names_entity", "robots_note", "terms_status", "verdict",
                "n_strong", "n_weak", "kinds", "routes",
                "machine_readable_basis", "media_total", "media_scanned",
                "sitemap_urls", "requests", "errors", "top_urls",
                "checked_date"]


def load_logs() -> dict[str, dict]:
    """LAST record per entity. host_log is append-only; a retry exists because
    the first attempt was wrong, and counting both double-counts the entity."""
    logs = {}
    if not HOSTLOG.exists():
        return logs
    for l in HOSTLOG.read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        try:
            d = json.loads(l)
        except ValueError:
            continue
        logs[d.get("tribe_id") or d.get("host")] = d
    return logs


def verdict_for(d: dict) -> str:
    if d.get("excluded_reason"):
        return "EXCLUDED_TERMS"
    if not d.get("host"):
        return "NO_HOST_KNOWN"
    if d.get("reached") != "Y":
        return "UNREACHABLE"
    if d.get("names_entity", "") and not d["names_entity"].startswith("YES"):
        if d["names_entity"] == "HIJACK":
            return "HIJACKED_OR_WRONG_DOMAIN"
        if d["names_entity"] == "INDETERMINATE":
            return "NAME_CHECK_INDETERMINATE"
        return "DOMAIN_NOT_THE_ENTITY"
    if d.get("robots_allowed") is False:
        return "ROBOTS_DISALLOW"
    if d.get("terms_status") == "TERMS_STATED_RESTRICTIVE":
        return "TERMS_STATED_RESTRICTIVE"
    hits = d.get("hits", [])
    strong = [h for h in hits if hit_strength(h) == "STRONG"]
    if strong:
        return "LIST_FOUND"
    if hits:
        return "MENTION_ONLY"
    routes = d.get("routes", {})
    if not any(routes.values()):
        return "NOT_SEARCHED_MACHINE_READABLE"
    return "NO_LIST_FOUND"


def write_verdicts() -> None:
    logs = load_logs()
    pop = {t["tribe_id"]: t for t in targets()}
    rows = []
    for tid, t in pop.items():
        d = logs.get(tid)
        if not d:
            rows.append({**{c: "" for c in VERDICT_COLS},
                         "tribe_id": tid, "cedar_uid": t["cedar_uid"],
                         "canonical_name": t["canonical_name"],
                         "entity_class": t["entity_class"],
                         "klass": t["klass"], "host": t["host"],
                         "probed": "N", "verdict": "NEVER_CHECKED",
                         "machine_readable_basis": "not attempted in this run",
                         "checked_date": ""})
            continue
        hits = d.get("hits", [])
        strong = [h for h in hits if hit_strength(h) == "STRONG"]
        rows.append({
            "tribe_id": tid, "cedar_uid": d.get("cedar_uid", ""),
            "canonical_name": d.get("canonical_name", ""),
            "entity_class": d.get("entity_class", ""),
            "klass": d.get("klass", ""), "host": d.get("host", ""),
            # `probed` MUST mean a request was made. An excluded host is
            # returned from before the first fetch, and writing Y here made
            # V1 report "excluded host probed: akima.com" — the check was
            # right and the label was the lie. NANA was never contacted.
            "probed": ("N" if d.get("excluded_reason") else "Y"),
            "reached": d.get("reached", ""),
            "reach_route": d.get("reach_route", ""),
            "names_entity": d.get("names_entity", ""),
            "robots_note": (d.get("robots_note", "") or "")[:200],
            "terms_status": d.get("terms_status", ""),
            "verdict": verdict_for(d),
            "n_strong": len(strong), "n_weak": len(hits) - len(strong),
            "kinds": ";".join(sorted({h["kind"] for h in hits})),
            "routes": ";".join(k for k, v in (d.get("routes") or {}).items()
                               if v),
            "machine_readable_basis": d.get("machine_readable_basis", ""),
            "media_total": d.get("media_total", 0),
            "media_scanned": d.get("media_scanned", 0),
            "sitemap_urls": d.get("sitemap_urls", 0),
            "requests": d.get("requests", 0),
            "errors": " | ".join(d.get("errors", []))[:300],
            "top_urls": " | ".join(h["url"] for h in strong[:5]),
            "checked_date": d.get("checked_date", ""),
        })
    rows.sort(key=lambda r: (r["klass"], r["canonical_name"]))
    with open(VERDICTS, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=VERDICT_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in VERDICT_COLS})
    print(f"[verdicts] {len(rows)} rows -> {VERDICTS}")


# ---------------------------------------------------------------------------
# EXTRACTION
# ---------------------------------------------------------------------------
def _clean(t: str) -> str:
    t = re.sub(r"&(nbsp|amp|#8217|#8211|#039|rsquo|lsquo|quot|gt|lt);", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" –—-|·,:;")
    return t


def _firmish(t: str) -> bool:
    if not (3 <= len(t) <= 90):
        return False
    if NOT_A_FIRM.match(t):
        return False
    return looks_like_a_firm(t)


def extract_html(html: str) -> tuple[list[dict], str]:
    """(rows, how). A TABLE is read as a table; otherwise headings/anchors.

    701 scrapes <h2>/<a>/<strong> only. A vendor directory is usually a table
    and the table carries city, state and category in NAMED columns — dropping
    them for a heading scrape throws away the columns the methodology says are
    the thinnest in the live file (naics 1.4% filled).
    """
    from selectolax.parser import HTMLParser
    tree = HTMLParser(html)
    for sel in ("script", "style", "nav", "header", "footer", "form",
                "aside", "noscript"):
        for nd in tree.css(sel):
            nd.decompose()

    # --- table route -------------------------------------------------------
    best, best_rows = None, []
    for tb in tree.css("table"):
        trs = tb.css("tr")
        if len(trs) < 4:
            continue
        head = [_clean(c.text()) .lower() for c in trs[0].css("th,td")]
        body = []
        for tr in trs[1:]:
            cells = [_clean(c.text()) for c in tr.css("td,th")]
            if any(cells):
                body.append(cells)
        if len(body) < 3:
            continue
        namecol = 0
        for i, h in enumerate(head):
            if re.search(r"business|company|firm|vendor|name|entit|"
                         r"contractor|organi", h):
                namecol = i
                break
        got = []
        for cells in body:
            if namecol >= len(cells):
                continue
            nm = cells[namecol]
            if not _firmish(nm):
                continue
            rec = {"name": nm, "city": "", "state": "", "category": "",
                   "cert_no": "", "extra": " | ".join(
                       f"{head[i] if i < len(head) else 'col%d' % i}={c}"
                       for i, c in enumerate(cells) if c and i != namecol)[:400]}
            for i, c in enumerate(cells):
                h = head[i] if i < len(head) else ""
                if re.search(r"\bcity\b|town", h):
                    rec["city"] = c
                elif re.search(r"\bstate\b|province", h):
                    rec["state"] = c
                elif re.search(r"categor|type|industr|trade|service|naics", h):
                    rec["category"] = c
                elif re.search(r"cert|licen|number|\bid\b", h):
                    rec["cert_no"] = c
            got.append(rec)
        if len(got) > len(best_rows):
            best, best_rows = tb, got
    if len(best_rows) >= 3:
        return best_rows, ("HTML <table> read as a table; column headers "
                           "mapped to city/state/category/certification")

    # --- heading / anchor route -------------------------------------------
    body = tree.css_first("main") or tree.css_first("article") or tree.body
    if body is None:
        return [], "no body"
    got, seen = [], set()
    # selectolax rejects a child combinator inside a comma list
    # ("Bad CSS Selectors: h2,h3,h4,a,strong,dt,li>b") and the ValueError
    # killed every Goldbelt and Kijik page in the first harvest. One
    # selector per call, and the parser's limits are respected rather than
    # assumed.
    nodes = []
    for sel in ("h2", "h3", "h4", "a", "strong", "dt", "b"):
        nodes.extend(body.css(sel))
    for nd in nodes:
        t = _clean(nd.text())
        if not _firmish(t) or t.lower() in seen:
            continue
        seen.add(t.lower())
        got.append({"name": t, "city": "", "state": "", "category": "",
                    "cert_no": "", "extra": ""})
    return got, ("HTML heading/anchor scrape — not a table; review before "
                 "resolving")


def extract_cpt(text: str) -> tuple[list[dict], str]:
    try:
        items = json.loads(text)
    except ValueError:
        return [], "not JSON"
    out = []
    for it in items if isinstance(items, list) else []:
        if not isinstance(it, dict):
            continue
        nm = _clean(re.sub(r"<[^>]+>", "",
                           (it.get("title") or {}).get("rendered", "")))
        if not nm or len(nm) > 120:
            continue
        ex = _clean(re.sub(r"<[^>]+>", " ",
                           (it.get("excerpt") or {}).get("rendered", "")))
        out.append({"name": nm, "city": "", "state": "",
                    "category": "", "cert_no": "",
                    "extra": ex[:400], "link": it.get("link", ""),
                    "edition": (it.get("modified") or it.get("date")
                                or "")[:10]})
    return out, ("title.rendered from the WordPress custom post type "
                 "collection — one post per listing, the entity's own record")


def extract_pdf(blob: bytes) -> tuple[list[dict], str]:
    import pdfplumber
    rows, how = [], ""
    try:
        with pdfplumber.open(io.BytesIO(blob)) as pdf:
            tabs = 0
            for pg in pdf.pages[:40]:
                for tb in (pg.extract_tables() or []):
                    if len(tb) < 3:
                        continue
                    tabs += 1
                    head = [(c or "").strip().lower() for c in tb[0]]
                    namecol = 0
                    for i, h in enumerate(head):
                        if re.search(r"business|company|firm|vendor|name", h):
                            namecol = i
                            break
                    for r in tb[1:]:
                        if namecol >= len(r):
                            continue
                        nm = _clean(r[namecol] or "")
                        if not _firmish(nm):
                            continue
                        rec = {"name": nm, "city": "", "state": "",
                               "category": "", "cert_no": "",
                               "extra": " | ".join(
                                   f"{head[i] if i < len(head) else i}="
                                   f"{(c or '').strip()}"
                                   for i, c in enumerate(r)
                                   if c and i != namecol)[:400]}
                        for i, c in enumerate(r):
                            h = head[i] if i < len(head) else ""
                            if re.search(r"city|town", h):
                                rec["city"] = _clean(c or "")
                            elif re.search(r"state", h):
                                rec["state"] = _clean(c or "")
                            elif re.search(r"categor|type|trade|service", h):
                                rec["category"] = _clean(c or "")
                        rows.append(rec)
            if rows:
                how = f"pdfplumber extract_tables over {tabs} table(s)"
            else:
                # no ruled table: read lines that look like firm names
                txt = "\n".join((p.extract_text() or "")
                                for p in pdf.pages[:40])
                for ln in txt.splitlines():
                    t = _clean(ln)
                    if _firmish(t) and re.search(
                            r"\b(llc|inc|corp|company|construction|services|"
                            r"enterprises?|contracting|group|consulting|"
                            r"trucking|excavat|electric|plumbing|ltd|l\.l\.c)"
                            r"\b", t, re.I):
                        rows.append({"name": t, "city": "", "state": "",
                                     "category": "", "cert_no": "",
                                     "extra": ""})
                how = ("pdfplumber text lines carrying a corporate suffix — "
                       "no ruled table in the PDF")
    except Exception as exc:
        return [], f"pdf failed: {type(exc).__name__}"
    return rows, how


def extract_xlsx(blob: bytes) -> tuple[list[dict], str]:
    import openpyxl
    try:
        wb = openpyxl.load_workbook(io.BytesIO(blob), read_only=True,
                                    data_only=True)
    except Exception as exc:
        return [], f"xlsx failed: {type(exc).__name__}"
    out = []
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))[:5000]
        if len(rows) < 4:
            continue
        head = [str(c or "").strip().lower() for c in rows[0]]
        namecol = 0
        for i, h in enumerate(head):
            if re.search(r"business|company|firm|vendor|name", h):
                namecol = i
                break
        for r in rows[1:]:
            if namecol >= len(r):
                continue
            nm = _clean(str(r[namecol] or ""))
            if not _firmish(nm):
                continue
            rec = {"name": nm, "city": "", "state": "", "category": "",
                   "cert_no": "",
                   "extra": " | ".join(
                       f"{head[i] if i < len(head) else i}={c}"
                       for i, c in enumerate(r) if c and i != namecol)[:400]}
            for i, c in enumerate(r):
                h = head[i] if i < len(head) else ""
                if re.search(r"city|town", h):
                    rec["city"] = _clean(str(c or ""))
                elif re.search(r"state", h):
                    rec["state"] = _clean(str(c or ""))
                elif re.search(r"categor|type|trade|service|naics", h):
                    rec["category"] = _clean(str(c or ""))
            out.append(rec)
    return out, "openpyxl worksheet read; header row mapped to columns"


# ---------------------------------------------------------------------------
# harvest
# ---------------------------------------------------------------------------
TITLE_TAIL = re.compile(
    r"\s*[|\-–—:·]\s*[^|\-–—:·]{2,45}$")


def member_page_name(url: str) -> tuple[str, str]:
    """The firm's own page states its own name. (name, how)."""
    r = fetch(url, headers=BROWSER_HEADERS, verify=False)
    if not (r["ok"] and r["status"] == 200 and r["text"]):
        return "", ""
    from selectolax.parser import HTMLParser
    tree = HTMLParser(r["text"])
    h1 = tree.css_first("h1")
    if h1:
        t = _clean(h1.text())
        if _firmish(t):
            return t, "<h1> of the member page the sitemap listed"
    ttl = tree.css_first("title")
    if ttl:
        t = _clean(TITLE_TAIL.sub("", _clean(ttl.text())))
        if _firmish(t):
            return t, "<title> of the member page, site name trimmed"
    return "", ""


def harvest_collection(d: dict, h: dict) -> tuple[list[dict], str]:
    """Index page first; member pages only if the index yields nothing.

    A slug is NOT read as a name. `bristol-bay-construction-holdings-llc`
    title-cases to "Llc" and would put a manufactured spelling of a real
    company into an ownership table. The member page states the name itself.
    """
    r = fetch(h["url"], headers=BROWSER_HEADERS, verify=False)
    if r["ok"] and r["status"] == 200 and r["text"]:
        rows, how = extract_html(r["text"])
        if len(rows) >= 3:
            return rows, ("index page of the sitemap collection /"
                          + up.urlparse(h["url"]).path.strip("/") + "/ :: "
                          + how)
    out = []
    for m in (h.get("members") or [])[:80]:
        nm, how1 = member_page_name(m)
        if nm:
            out.append({"name": nm, "city": "", "state": "", "category": "",
                        "cert_no": "", "extra": "", "link": m})
    return out, ("member pages enumerated from the site's own sitemap "
                 "segment; each name read from that page's <h1>/<title>, "
                 "never from the URL slug")


def harvest_hit(d: dict, h: dict) -> list[dict]:
    url = h["url"]
    if is_excluded(up.urlparse(url).netloc):
        return []
    if h.get("route") == "sitemap_collection":
        rows, how = harvest_collection(d, h)
        r = {"text": "", "headers": {}}
    else:
        r = fetch(url, headers=BROWSER_HEADERS, verify=False)
        if not (r["ok"] and r["status"] == 200):
            return []
        rows = how = None
    RAW.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", url)[-80:]
    mime = (r["headers"].get("content-type", "") or h.get("mime", "")).lower()

    if rows is not None:
        pass                                   # sitemap_collection, done above
    elif "/wp-json/" in url:
        text = r["text"]
        rows, how = extract_cpt(text)
        # PAGINATE. per_page=100 is the ceiling; a 100-row answer is a
        # truncation, not a total. `X-WP-TotalPages` says how many there are.
        tp = int(r["headers"].get("x-wp-totalpages", 1) or 1)
        for pg in range(2, min(tp, 20) + 1):
            rr = fetch(url + f"&page={pg}", headers=BROWSER_HEADERS,
                       verify=False)
            if not (rr["ok"] and rr["status"] == 200):
                break
            more, _ = extract_cpt(rr["text"])
            rows += more
            text += rr["text"]
        if tp > 1:
            how += f" (paginated: {min(tp,20)} of {tp} REST pages)"
        (RAW / f"{d['tribe_id']}_{slug}.json").write_text(
            text[:8_000_000], encoding="utf-8")
    elif "pdf" in mime or url.lower().endswith(".pdf"):
        blob = fetch_bytes(url)
        if blob is None:
            return []
        (RAW / f"{d['tribe_id']}_{slug}.pdf").write_bytes(blob[:20_000_000])
        rows, how = extract_pdf(blob)
    elif (url.lower().endswith((".xlsx", ".xlsm", ".xls"))
          or "spreadsheet" in mime or "excel" in mime):
        blob = fetch_bytes(url)
        if blob is None:
            return []
        (RAW / f"{d['tribe_id']}_{slug}.xlsx").write_bytes(blob[:20_000_000])
        rows, how = extract_xlsx(blob)
    else:
        rows, how = extract_html(r["text"])
        (RAW / f"{d['tribe_id']}_{slug}.html").write_text(
            r["text"][:3_000_000], encoding="utf-8")

    edition = h.get("edition_date") or h.get("modified") or ""
    if not edition:
        m = re.search(r'"date(Modified|Published)"\s*:\s*"([\d\-T:+]{10,})',
                      r["text"][:200_000] if isinstance(r["text"], str) else "")
        if m:
            edition = m.group(2)[:10]

    kind = h["kind"]
    if d["klass"] == "anc" and kind == "member_business_list":
        kind = "anc_shareholder_directory"
    out = []
    for rec in rows:
        out.append({
            "authority_tribe_id": d["tribe_id"],
            "authority_cedar_uid": d["cedar_uid"],
            "authority_name": d["canonical_name"],
            "authority_entity_class": d["entity_class"],
            "klass": d["klass"],
            "business_name_raw": rec["name"],
            "city": rec.get("city", ""),
            "state_province": rec.get("state", ""),
            "service_category_raw": rec.get("category", ""),
            "certification_number": rec.get("cert_no", ""),
            "extra_columns": rec.get("extra", ""),
            "kind": kind,
            "identity_scope": SCOPE_BY_KIND[kind],
            "assertion_class": ASSERTION_BY_KIND[kind],
            "directory_type": DIRECTORY_TYPE_BY_KIND[kind],
            "identity_claim_text": h.get("title", "") or h.get("matched", ""),
            "source_url": rec.get("link") or url,
            "source_page_url": url,
            "source_edition": rec.get("edition") or edition,
            "route": h["route"],
            "extraction_note": how,
            "auto_ruled": "Y",
            "harvest_date": TODAY,
            "terms_status": d.get("terms_status", ""),
            "built_by_script": THIS,
        })
    return out


def fetch_bytes(url: str) -> bytes | None:
    import requests
    host = _bare(up.urlparse(url).netloc)
    if is_excluded(host):
        return None
    E._pace(host)
    try:
        r = requests.get(url, headers=BROWSER_HEADERS, timeout=45,
                         verify=False, allow_redirects=True)
        E._nreq[0] += 1
        return r.content if r.status_code == 200 else None
    except Exception:
        return None


def stage_harvest(hours=DEFAULT_HOURS, limit=None) -> None:
    E._deadline[0] = time.time() + hours * 3600
    logs = load_logs()
    done_pages = set()
    if BIZ.exists():
        for l in BIZ.read_text(encoding="utf-8").splitlines():
            if l.strip():
                try:
                    done_pages.add(json.loads(l)["source_page_url"])
                except Exception:
                    pass
    jobs = []
    for d in logs.values():
        if verdict_for(d) != "LIST_FOUND":
            continue
        seen_urls = set()
        for h in d.get("hits", []):
            if hit_strength(h) != "STRONG":
                continue
            if h["url"] in seen_urls or h["url"] in done_pages:
                continue
            seen_urls.add(h["url"])
            jobs.append((d, h))
    if limit:
        jobs = jobs[:limit]
    print(f"[harvest] {len(jobs)} STRONG pages across "
          f"{len({j[0]['tribe_id'] for j in jobs})} entities")
    tot = [0]

    def run(j):
        d, h = j
        try:
            rows = harvest_hit(d, h)
        except Exception as exc:
            print(f"   !! {d['canonical_name']}: {type(exc).__name__}: {exc}")
            return
        for r in rows:
            _flush(BIZ, r)                             # PER PAGE, not per run
        with _wlock:
            tot[0] += len(rows)
            line = (f"  {d['canonical_name'][:30]:30s} {len(rows):4d} names "
                    f" {h['url'][:66]}")
            sys.stdout.write(
                line.encode("ascii", "replace").decode("ascii") + chr(10))
            sys.stdout.flush()

    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(run, jobs))
    print(f"[harvest] {tot[0]} rows appended -> {BIZ}")


# ---------------------------------------------------------------------------
# stage — the 58-column merge candidate
# ---------------------------------------------------------------------------
def live_schema() -> list[str]:
    with open(LIVE_NOB, encoding="utf-8-sig", newline="") as fh:
        return next(csv.reader(fh))


def _nk(s: str) -> str:
    s = _fold(s)
    s = re.sub(r"\b(llc|l\.l\.c|inc|incorporated|corp|corporation|co|company|"
               r"ltd|limited|lp|llp|pllc)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def existing_keys() -> tuple[set, set]:
    """(authority+name, name-only) as they stand in the LIVE clean file."""
    pair, nameonly = set(), set()
    with open(LIVE_NOB, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            n = _nk(r.get("business_name_raw", ""))
            if not n:
                continue
            nameonly.add(n)
            pair.add((r.get("certifying_authority_name", "").strip().lower(),
                      n))
    return pair, nameonly


ADDRESSISH = re.compile(
    r"\b\d{1,6}\s+[A-Za-z][^,;.]{0,30}?\b"
    r"(street|st\.|avenue|ave\.|road|rd\.|drive|dr\.|lane|ln\.|"
    r"boulevard|blvd)\b", re.I)
CONTACTISH = re.compile(
    r"[\w.+-]+@[\w-]+\.[\w.]+|\b\d{3}[-. ]\d{3}[-. ]\d{4}\b")


def redact_quote(q: str) -> tuple[str, bool]:
    """Strip address- and contact-shaped spans out of a verbatim quote.

    Measured need, not a hypothetical: two ANCSA quotes carried "2201 Buena
    Vista Drive" and "925 Park Avenue" — the street addresses of hotels the
    corporation owns, printed in a public audited filing. They are almost
    certainly not a natural person's home. But `identity_claim_text` ships,
    the cost of dropping the two spans is nil, and the policy line is that a
    STREET ADDRESS does not ship from this table at all. Keeping the
    invariant strict and redacting is cheaper than arguing the exception,
    and the unredacted quote survives in the staging JSONL.
    """
    a = ADDRESSISH.sub("[address withheld]", q or "")
    b = CONTACTISH.sub("[contact withheld]", a)
    return b, b != (q or "")


# ---------------------------------------------------------------------------
# TWO TIERS, AND THE SECOND ONE IS NOT DELETED.
#
# Measured on the first 761 harvested rows: the CPT route (99), the table
# route (5) and the sitemap-member route (13) were clean. The HTML
# heading/anchor scrape (638) returned real subsidiaries — "ASRC Federal
# Mission Services", "Aleut Patrick Mechanical" — mixed with
# "NAICS Code: Healthcare", "Press Release", "Fairbanks", "Spring 2026",
# "Shareholder Portal" and "What We Do". A heading on a marketing page is not
# a company, and no denylist of words separates the two reliably.
#
# So: a row STAGES if the source route is structured (the entity's own record
# of one listing per row), or the name itself carries a corporate signal.
# Everything else goes to `candidates_for_review_*.csv` — kept, counted, with
# its quote and URL, for a human to rule. "Flag, never delete."
CORP_SIGNAL = re.compile(
    r"\b(LLC|L\.L\.C|Inc|Incorporated|Corp|Corporation|Company|Co\.|Ltd|"
    r"Limited|LP|LLP|PLLC|Holdings?|Group|Enterprises?|Services|Solutions|"
    r"Systems|Technologies|Technology|Partners|Contracting|Contractors|"
    r"Construction|Consulting|Logistics|Aviation|Marine|Transport|"
    r"Industrial|Industries|Energy|Federal|Ventures?|Associates|"
    r"Manufacturing|Engineering|Environmental|Security|Staffing|Supply|"
    r"Trading|Fisheries|Seafoods?|Development)\b", re.I)

STRUCTURED_NOTE = ("title.rendered", "HTML <table>", "member pages",
                   "index page of the sitemap collection")


# A DIRECTORY INDEX THAT YIELDED A CROWD IS A LIST, SUFFIX OR NO SUFFIX.
# USET's `/departments/economic-development/tribal-enterprise-directory`
# returned 471 names — "Akwesasne Farmers Market", "Choctaw Fresh Produce",
# "Penobscot Indian Nation Fish and Game", "Passamaquoddy Maple Syrup". 425
# of them carry no LLC/Inc/Services token, and the corporate-signal tier
# would have thrown away the single richest directory found in this sweep on
# the grounds that a farmers market is not spelled like a defence contractor.
#
# The evidence that these ARE the list is structural and it is not the name:
# the page's own path says directory, and one page produced dozens of them.
# A nav bar does not have 471 items. Staged, and flagged so the flag can be
# filtered on — never silently mixed in with a CPT row.
DIRECTORY_INDEX_PATH = re.compile(
    r"/[^/]*(director(y|ies)|regist(er|ry)|listings?|roster|"
    r"member[s]?|compan(y|ies)|subsidiar(y|ies)|enterprises?|"
    r"businesses|affiliates?|portfolio)[^/]*/?$", re.I)
DIRECTORY_INDEX_MIN_NAMES = 8

# The price of the directory-index tier, paid honestly. Turning the suffix
# rule off on those pages lets marketing furniture through with the real
# enterprises: "Government", "Press Kit", "Seaport NxG Contract Vehicle",
# "Digital Ops & IT Modernization", "Capabilities". These are section
# headings and federal contract vehicles, not firms. They go to review.
NOT_A_FIRM_ON_AN_INDEX = re.compile(
    r"^(government|commercial|federal|state|local|press ?kit|media ?kit|"
    r"capabilit\w*|overview|our (mission|vision|values|history|leadership|"
    r"people|team|approach|impact)|leadership|history|mission|vision|"
    r"values|careers?|contact\b|locations?|newsroom|resources?|"
    r"testimonials?|partners?|clients?|customers?|awards?|certifications?|"
    r"past performance|quality|safety|sustainability|"
    r"contract vehicles?|gsa\b|idiq\b|naics ?code|sic ?code|"
    r"annual report|financials?|shareholders?|board of directors|"
    r"more info|read more|learn more|apply now|see all)\b"
    r"|contract vehicle\b|\bnaics\b", re.I)


def stages_or_reviews(r: dict) -> tuple[bool, str]:
    """(stage?, why not). An address-shaped NAME never stages.

    Bering Straits' shareholder directory publishes a firm called
    "10 Editing Lane". It is almost certainly a video-editing company having
    a joke, and it is also indistinguishable from a street address by any
    rule this script can apply. The policy line is that no street address
    ships from this table; the row is kept in the review file with its URL
    so a human can rule it in.
    """
    nm = r.get("business_name_raw", "")
    if ADDRESSISH.search(nm) or CONTACTISH.search(nm):
        return False, ("name is address- or contact-shaped; kept out of the "
                       "clean table by the no-street-address policy, not by "
                       "a judgement that it is not a firm")
    note = r.get("extraction_note", "") or ""
    if note.startswith(STRUCTURED_NOTE):
        return True, ""
    if CORP_SIGNAL.search(nm):
        return True, ""
    if r.get("_page_is_directory_index"):
        if NOT_A_FIRM_ON_AN_INDEX.search(nm):
            return False, ("on a directory index but the text is section "
                           "furniture or a federal contract vehicle, not a "
                           "firm")
        return True, ""
    return False, ("unstructured heading/anchor scrape and the name carries "
                   "no corporate signal")


# A verdict in this set means we never established that the site belongs to
# the entity, or that the publisher refused. Neither can produce a row.
# ...and it applies ONLY to rows harvested from that website. Measured
# immediately: the first version dropped 131 ANCSA rows because the web sweep
# could not reach The Kuskokwim Corporation's, Alaska Peninsula's and
# Toghotthele's websites. Their evidence is an audited state filing. A verdict
# about a corporation's WEBSITE says nothing about its AS 45.55.139 filing,
# and letting one route's failure delete another route's evidence is the same
# error as inheriting a tier from the wrong source row.
WEB_ROUTES = {"custom_post_type", "rest_search", "wp_media", "sitemap",
              "sitemap_collection", "nav_link"}

DISQUALIFYING_VERDICTS = {
    "NAME_CHECK_INDETERMINATE", "DOMAIN_NOT_THE_ENTITY",
    "HIJACKED_OR_WRONG_DOMAIN", "EXCLUDED_TERMS",
    "TERMS_STATED_RESTRICTIVE", "ROBOTS_DISALLOW",
}

# A RESTRICTED PUBLISHER'S NAME IS NOT THE SAME AS A RESTRICTED PUBLISHER'S
# CONTENT — but the integrator gets to see the difference rather than have it
# decided here. Two staged rows NAME a source Cedar refuses:
#   Kuukpik Corporation  -> "Kuukpik / NANA Management Services, LLC"
#                           (a joint venture named in KUUKPIK's own filing)
#   ANCSA Regional Assn  -> "NANA Regional Corporation (NANA)"
#                           (a member of the ASSOCIATION, on its page)
# Neither came from nana.com or akima.com, both of which were refused before
# a request was sent and appear nowhere in `raw/`. NANA is already a spine
# entity. The rows are flagged, not withheld and not silently shipped.
RESTRICTED_PUBLISHER_NAME = re.compile(
    r"\b(colville|ctuir|umatilla|yakama|chickasaw|nana|akima|southern ute|"
    r"forest county potawatomi|stillaguamish)\b", re.I)

REVIEW_CSV = OUT / "candidates_for_review_2026-09-02.csv"
REVIEW_COLS = ["authority_name", "authority_cedar_uid", "klass",
               "business_name_raw", "kind", "route", "extraction_note",
               "source_url", "source_page_url", "why_not_staged",
               "harvest_date"]


def stage_build() -> None:
    cols = live_schema()
    # TWO producers, ONE merge candidate. `business_rows.jsonl` is the web
    # sweep; `business_rows_ancsa.jsonl` is code/1073's offline mine of the
    # AS 45.55.139 audited annual reports. They share a record shape on
    # purpose so that a reviewer reads one staged CSV, not two.
    rows = []
    for src in (BIZ, ANCSA_BIZ):
        if src.exists():
            rows += [json.loads(l)
                     for l in src.read_text(encoding="utf-8").splitlines()
                     if l.strip()]
    if not rows:
        print("[stage] no harvested rows yet")
        return
    # mark every row whose SOURCE PAGE is a directory index that yielded a
    # crowd. Counted over the harvest, not guessed at per row.
    percount = collections.Counter(x["source_page_url"] for x in rows)
    for x in rows:
        pth = up.urlparse(x["source_page_url"]).path
        x["_page_is_directory_index"] = bool(
            DIRECTORY_INDEX_PATH.search(pth)
            and percount[x["source_page_url"]] >= DIRECTORY_INDEX_MIN_NAMES)
    # AN AUTHORITY WHOSE SITE WAS NEVER ESTABLISHED AS ITS OWN CANNOT CERTIFY
    # ANYTHING. Kawerak.org answered the name check for the village of
    # Council because "council" is on every tribal website, and six rows of
    # navigation furniture were harvested under a tribal government's name
    # before the indeterminate-name guard existed. The guard fixed the
    # VERDICT; this drops the ROWS the bad verdict produced.
    disqualified = {}
    if VERDICTS.exists():
        with open(VERDICTS, encoding="utf-8-sig", newline="") as fh:
            for v in csv.DictReader(fh):
                if v["verdict"] in DISQUALIFYING_VERDICTS and v["cedar_uid"]:
                    disqualified[v["cedar_uid"]] = v["verdict"]
    pair, nameonly = existing_keys()
    # ALSO de-duplicate against shard E's hand-adjudicated ANC edges. Shard E
    # is not in native_owned_businesses.csv, so the live-file check cannot
    # see it, and re-emitting 482 edges someone adjudicated by hand would be
    # the worst kind of duplicate: one that looks like corroboration.
    se = set()
    if SHARD_E.exists():
        for l in SHARD_E.read_text(encoding="utf-8").splitlines():
            if l.strip():
                d = json.loads(l)
                se.add((_nk(d.get("parent_name", "")),
                        _nk(d.get("child_name_raw", ""))))
    out, seen, dropped = [], set(), {"dup_live_pair": 0, "dup_within": 0,
                                     "no_name": 0, "dup_shard_e": 0,
                                     "to_review": 0,
                                     "authority_identity_not_established": 0}
    review = []
    for r in rows:
        nk = _nk(r["business_name_raw"])
        if not nk:
            dropped["no_name"] += 1
            continue
        if (r.get("route") in WEB_ROUTES
                and r["authority_cedar_uid"] in disqualified):
            dropped["authority_identity_not_established"] += 1
            continue
        keep, why_not = stages_or_reviews(r)
        if not keep:
            review.append({
                "authority_name": r["authority_name"],
                "authority_cedar_uid": r["authority_cedar_uid"],
                "klass": r.get("klass", ""),
                "business_name_raw": r["business_name_raw"],
                "kind": r["kind"], "route": r["route"],
                "extraction_note": r["extraction_note"],
                "source_url": r["source_url"],
                "source_page_url": r["source_page_url"],
                "why_not_staged": why_not,
                "harvest_date": r["harvest_date"]})
            dropped["to_review"] += 1
            continue
        auth = r["authority_name"].strip().lower()
        if (auth, nk) in pair:
            dropped["dup_live_pair"] += 1
            continue
        if (_nk(r["authority_name"]), nk) in se:
            dropped["dup_shard_e"] += 1
            continue
        key = (auth, nk, r["kind"])
        if key in seen:
            dropped["dup_within"] += 1
            continue
        seen.add(key)
        # RECOMPUTE the gradient here rather than trusting what the harvest
        # process wrote. The harvest runs for hours and the mapping was
        # corrected mid-run; a row written at 02:10 and a row written at
        # 03:40 must not carry two different scopes for the same fact. The
        # STAGE is the single authority on the vocabulary.
        kind = r["kind"]
        if r.get("klass") == "anc" and kind == "member_business_list":
            kind = "anc_shareholder_directory"
        if r.get("klass") == "intertribal":
            # `/members/` on an association lists its MEMBERS (AIGA lists
            # tribes, ANCSA Regional Association lists the twelve ANCs);
            # anything else it calls an enterprise directory lists its
            # members' FIRMS. Different claims, told apart by the path.
            pth = up.urlparse(r["source_page_url"]).path.lower()
            kind = ("intertribal_member_directory"
                    if re.search(r"/members?/?$", pth)
                    else "intertribal_member_enterprise")
        r["kind"] = kind
        r["identity_scope"] = SCOPE_BY_KIND[kind]
        r["assertion_class"] = ASSERTION_BY_KIND[kind]
        r["directory_type"] = DIRECTORY_TYPE_BY_KIND[kind]
        bid = hashlib.sha256(
            f"{r['authority_tribe_id']}|{nk}|{r['kind']}".encode()
        ).hexdigest()[:16]
        rec = {c: "" for c in cols}
        rec.update({
            "business_source_id": f"CE1070-{bid}",
            "source_id": f"CE1070-{r['authority_tribe_id']}",
            "source_business_key": nk[:80],
            "certifying_authority_entity_id": r["authority_cedar_uid"],
            "certifying_authority_name": r["authority_name"],
            "nation_id": r["authority_cedar_uid"],
            "business_name_raw": r["business_name_raw"],
            "business_name_normalized": nk,
            "business_name_is_person_name": "-1",
            "business_entity_id": "",
            "business_entity_name": "",
            "business_entity_class": "",
            "resolution_method": "none — 1070 resolves no identity",
            "record_scope": "unresolved",
            "assertion_class": r["assertion_class"],
            "directory_type": r["directory_type"],
            "identity_scope": r["identity_scope"],
            "identity_claim_text": redact_quote(
                r["identity_claim_text"])[0][:300],
            # `inclusion_basis` is a CONTROLLED VOCABULARY: every one of the
            # 2,393 live rows reads `program_authority`. A directory row is
            # that same thing. An ANCSA row is NOT — it is a statutory
            # filing, so it gets its own value and the merge is told a
            # second value now exists in a column that had one.
            "inclusion_basis": ("audited_filing_as_45_55_139"
                                if r.get("route") in
                                ("consolidation_note",
                                 "named_subsidiary_sentence",
                                 "is_a_subsidiary_of", "equity_interest")
                                else "program_authority"),
            "programme_name": (
                f"{r['authority_name']} {r['directory_type'].replace('_',' ')}"),
            "verification_basis": (
                f"{r['route']} :: {r['extraction_note']}"
                + (f" :: stated relation = {r['ownership_relation']}"
                   if r.get("ownership_relation") else "")),
            "ownership_percent": r.get("stated_ownership_pct", ""),
            # `certification_tier` is DELIBERATELY LEFT EMPTY on these rows.
            # In the live file it holds a TERO preference priority
            # ("Priority 1", "Preference Level 1", 693 rows). An ANCSA
            # ownership relation is a different fact in the same shape, and
            # putting it here would give one column two vocabularies — the
            # defect START_HERE.md §5 records for `extent_competed`, which
            # cost a whole crosswalk to undo. The relation rides in
            # `verification_basis` and in `validation_flags`, and the merge
            # should give it a column of its own.
            "certification_number": r.get("certification_number", ""),
            "service_category_raw": r.get("service_category_raw", ""),
            "city": r.get("city", ""),
            "state_province": r.get("state_province", ""),
            "owner_name_present": "0",
            "n_owners_named": "0",
            "withheld_fields": "",
            "source_url": r["source_url"],
            "source_edition": r.get("source_edition", ""),
            "harvest_date": r["harvest_date"],
            "first_seen": r["harvest_date"],
            "last_seen": r["harvest_date"],
            "is_current": "Y",
            "ingestion_method": r["route"] + "|" + r["extraction_note"][:60],
            "raw_snapshot_uri": str(RAW.relative_to(ROOT)).replace("\\", "/"),
            "source_terms_status": r.get("terms_status", ""),
            "consent_status": "UNRESOLVED",
            "publishable": "",
            "validation_flags": ";".join(x for x in [
                ("AUTO_RULED_NOT_HUMAN_REVIEWED"
                 if r.get("auto_ruled") == "Y" else ""),
                (f"RELATION={r['ownership_relation']}"
                 if r.get("ownership_relation") else ""),
                ("HEADING_SCRAPE_ON_A_DIRECTORY_INDEX"
                 if (r.get("_page_is_directory_index")
                     and not (r.get("extraction_note", "")
                              .startswith(STRUCTURED_NOTE))
                     and not CORP_SIGNAL.search(r["business_name_raw"]))
                 else ""),
                ("NAMES_A_RESTRICTED_PUBLISHER_BUT_SOURCED_ELSEWHERE"
                 if RESTRICTED_PUBLISHER_NAME.search(
                     r["business_name_raw"] + " " + r["authority_name"])
                 else ""),
                ("ADDRESS_OR_CONTACT_REDACTED_FROM_QUOTE"
                 if redact_quote(r["identity_claim_text"])[1] else ""),
            ] if x),
            "built_by_script": THIS,
            "publishable_basis": ("not decided by 1070 — 615 owns the "
                                  "publishing gate"),
            "federal_identifier_match_status": "NOT_ATTEMPTED",
        })
        rec["record_hash"] = hashlib.sha256(
            "|".join(str(rec[c]) for c in cols).encode()).hexdigest()[:32]
        rec["validation_flags"] = ";".join(
            x for x in [rec["validation_flags"],
                        ("NAME_ALSO_IN_LIVE_FILE_UNDER_ANOTHER_AUTHORITY"
                         if nk in nameonly else "")] if x)
        out.append(rec)
    with open(STAGED, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    seenr = set()
    uniq = []
    for r in review:
        k = (r["authority_name"].lower(), _nk(r["business_name_raw"]))
        if k in seenr:
            continue
        seenr.add(k)
        uniq.append(r)
    with open(REVIEW_CSV, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=REVIEW_COLS)
        w.writeheader()
        w.writerows(uniq)
    print(f"[stage] {len(out)} rows -> {STAGED}")
    print(f"[stage] {len(uniq)} candidates held for review -> {REVIEW_CSV}")
    print(f"        dropped: {dropped}")


# ---------------------------------------------------------------------------
# verify / selftest
# ---------------------------------------------------------------------------
def verify(staged: Path = STAGED, verdicts: Path = VERDICTS,
           quiet=False) -> list[str]:
    bad = []
    cols = live_schema()
    excl = set(excluded_hosts())

    rows = []
    if staged.exists():
        with open(staged, encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            got = rd.fieldnames or []
            rows = list(rd)
        if got != cols:                                              # V6
            bad.append(f"V6 staged schema is not the live 58-column schema: "
                       f"{len(got)} cols, "
                       f"{set(cols) ^ set(got) or 'order differs'}")

    reached = set()
    # code/1073's rows come from the Alaska DBS STAR portal, which is not a
    # host this script ever probed and so is not in `verdicts`. V2 asks "did
    # we actually retrieve this?", not "did the web sweep retrieve this?" —
    # the ANCSA document log is the equivalent evidence for that route.
    if DOCLOG_1073.exists():
        with open(DOCLOG_1073, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                h = _bare(up.urlparse(r.get("portal_url", "")).netloc)
                if h:
                    reached.add(h)
    if verdicts.exists():
        with open(verdicts, encoding="utf-8-sig", newline="") as fh:
            vs = list(csv.DictReader(fh))
        for v in vs:
            if v["reached"] == "Y":
                reached.add(_bare(v["host"]))
            if v["probed"] == "Y" and _bare(v["host"]) in excl:       # V1
                bad.append(f"V1 excluded host probed: {v['host']} "
                           f"({v['canonical_name']})")
            if (v["verdict"] == "NO_LIST_FOUND"
                    and not (v["routes"] or "").strip()):             # V5
                bad.append(f"V5 NO_LIST_FOUND with no machine-readable route "
                           f"run: {v['canonical_name']}")
        pop = {t["tribe_id"] for t in targets()}
        missing = pop - {v["tribe_id"] for v in vs}
        if missing:                                                   # V5
            bad.append(f"V5 {len(missing)} population entities have no "
                       f"verdict row, e.g. {sorted(missing)[:3]}")

    disq = {}
    if verdicts.exists():
        with open(verdicts, encoding="utf-8-sig", newline="") as fh:
            for v in csv.DictReader(fh):
                if v["verdict"] in DISQUALIFYING_VERDICTS and v["cedar_uid"]:
                    disq[v["cedar_uid"]] = v["verdict"]
    pair, _ = existing_keys()
    PERSON = re.compile(r"@|\b\d{3}[-. ]\d{3}[-. ]\d{4}\b|"
                        r"\b\d{1,6}\s+[A-Za-z].{0,30}\b"
                        r"(street|st\.|avenue|ave\.|road|rd\.|drive|dr\.|"
                        r"lane|ln\.|boulevard|blvd)\b", re.I)
    for r in rows:
        h = _bare(up.urlparse(r["source_url"]).netloc)
        if h in excl:                                                 # V1
            bad.append(f"V1 staged row on an excluded host: {r['source_url']}")
        if not r["source_url"]:                                       # V2
            bad.append(f"V2 staged row with no source_url: "
                       f"{r['business_name_raw']}")
        elif h not in reached and reached:                            # V2
            bad.append(f"V2 staged row on a host never recorded as reached: "
                       f"{h}")
        k = (r["certifying_authority_name"].strip().lower(),
             _nk(r["business_name_raw"]))
        if k in pair:                                                 # V3
            bad.append(f"V3 staged row duplicates the live file: {k}")
        if (r["certifying_authority_entity_id"] in disq
                and r["inclusion_basis"] != "audited_filing_as_45_55_139"):
                                                                      # V8
            bad.append(f"V8 staged row from an authority whose site was "
                       f"never established as its own "
                       f"({disq[r['certifying_authority_entity_id']]}): "
                       f"{r['certifying_authority_name']}")
        if r["identity_scope"] not in DECLARED_SCOPES:                # V4
            bad.append(f"V4 undeclared identity_scope "
                       f"{r['identity_scope']!r}")
        for c in ("business_name_raw", "city", "service_category_raw",
                  "identity_claim_text"):
            if PERSON.search(r.get(c, "") or ""):                     # V7
                bad.append(f"V7 person-held datum in {c}: "
                           f"{r[c][:60]!r}")
    if not quiet:
        seen = set()
        for b in bad:
            tag = b.split()[0]
            if tag in seen and len([x for x in bad
                                    if x.startswith(tag)]) > 6:
                continue
            seen.add(tag)
        for b in bad[:40]:
            print("  FAIL " + b)
        if len(bad) > 40:
            print(f"  ... and {len(bad)-40} more")
        print(f"[verify] {len(bad)} violations across {len(rows)} staged rows")
    return bad


def selftest() -> int:
    """Every invariant must FIRE on an injected violation. A check that has
    never failed on purpose is not known to work."""
    import tempfile
    cols = live_schema()
    tmp = Path(tempfile.mkdtemp(prefix="cedar1070_"))
    ok = True

    def mk(rows, vrows=None):
        s = tmp / "s.csv"
        with open(s, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for r in rows:
                w.writerow({c: r.get(c, "") for c in cols})
        v = tmp / "v.csv"
        with open(v, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=VERDICT_COLS)
            w.writeheader()
            for r in (vrows or []):
                w.writerow({c: r.get(c, "") for c in VERDICT_COLS})
        return s, v

    good = {"business_name_raw": "Kahuku Wholesale Partners LLC",
            "certifying_authority_name": "A Nation That Does Not Exist",
            "source_url": "https://example-nonexistent-cedar.test/list",
            "identity_scope": "any_native", "city": "Kahuku"}
    goodv = [{"tribe_id": "X", "host": "example-nonexistent-cedar.test",
              "probed": "Y", "reached": "Y", "verdict": "LIST_FOUND",
              "routes": "sitemap", "canonical_name": "X"}]

    cases = [
        ("V1", {**good, "source_url": "https://chickasaw.net/x"}, goodv),
        ("V2", {**good, "source_url": ""}, goodv),
        ("V4", {**good, "identity_scope": "definitely_native"}, goodv),
        ("V7", {**good, "city": "12 Elm Street"}, goodv),
    ]
    for tag, row, vr in cases:
        s, v = mk([row], vr)
        bad = verify(s, v, quiet=True)
        fired = [b for b in bad if b.startswith(tag)]
        # V5's population check always fires on a 1-row fixture; ignore it
        print(f"  {tag}: {'FIRES' if fired else 'DID NOT FIRE'}"
              + (f"  -> {fired[0][:90]}" if fired else ""))
        ok &= bool(fired)

    # V3 needs a real live-file pair
    with open(LIVE_NOB, encoding="utf-8-sig", newline="") as fh:
        first = next(csv.DictReader(fh))
    s, v = mk([{**good,
                "business_name_raw": first["business_name_raw"],
                "certifying_authority_name":
                    first["certifying_authority_name"]}], goodv)
    bad = verify(s, v, quiet=True)
    fired = [b for b in bad if b.startswith("V3")]
    print(f"  V3: {'FIRES' if fired else 'DID NOT FIRE'}")
    ok &= bool(fired)

    # V8 — a row from an authority whose site was never established as its own
    s8, v8 = mk([{**good, "certifying_authority_entity_id": "CE-TEST-1",
                  "inclusion_basis": "program_authority"}],
                [{"tribe_id": "X", "cedar_uid": "CE-TEST-1",
                  "host": "example-nonexistent-cedar.test", "probed": "Y",
                  "reached": "Y", "verdict": "NAME_CHECK_INDETERMINATE",
                  "routes": "sitemap", "canonical_name": "X"}])
    bad = verify(s8, v8, quiet=True)
    fired = [b for b in bad if b.startswith("V8")]
    print(f"  V8: {'FIRES' if fired else 'DID NOT FIRE'}")
    ok &= bool(fired)

    # V5 — a NO_LIST_FOUND verdict with no route run
    s, v = mk([], [{"tribe_id": "X", "host": "h.test", "probed": "Y",
                    "reached": "Y", "verdict": "NO_LIST_FOUND", "routes": "",
                    "canonical_name": "X"}])
    bad = verify(s, v, quiet=True)
    fired = [b for b in bad if b.startswith("V5") and "no machine" in b]
    print(f"  V5: {'FIRES' if fired else 'DID NOT FIRE'}")
    ok &= bool(fired)

    # V6 — a column dropped
    s = tmp / "s6.csv"
    with open(s, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols[:-1])
    bad = verify(s, tmp / "v.csv", quiet=True)
    fired = [b for b in bad if b.startswith("V6")]
    print(f"  V6: {'FIRES' if fired else 'DID NOT FIRE'}")
    ok &= bool(fired)

    # and the clean case must PASS
    s, v = mk([good], goodv)
    bad = [b for b in verify(s, v, quiet=True) if not b.startswith("V5")]
    print(f"  clean fixture: {'PASSES' if not bad else 'FAILS ' + str(bad)}")
    ok &= not bad
    print(f"[selftest] {'ALL INVARIANTS FIRE' if ok else 'A CHECK IS DEAD'}")
    return 0 if ok else 1


# ---------------------------------------------------------------------------
def report() -> None:
    if not VERDICTS.exists():
        print("no verdicts yet")
        return
    import collections
    with open(VERDICTS, encoding="utf-8-sig", newline="") as fh:
        vs = list(csv.DictReader(fh))
    by = collections.defaultdict(collections.Counter)
    for v in vs:
        by[v["klass"]][v["verdict"]] += 1
    verdicts_all = sorted({v["verdict"] for v in vs})
    print(f"\n{'verdict':34s}" + "".join(f"{k[:12]:>13s}" for k in sorted(by))
          + f"{'TOTAL':>8s}")
    for vd in verdicts_all:
        tot = sum(by[k][vd] for k in by)
        print(f"{vd:34s}" + "".join(f"{by[k][vd]:13d}" for k in sorted(by))
              + f"{tot:8d}")
    print(f"{'TOTAL':34s}"
          + "".join(f"{sum(by[k].values()):13d}" for k in sorted(by))
          + f"{len(vs):8d}")
    if STAGED.exists():
        with open(STAGED, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        print(f"\nstaged rows: {len(rows)}")
        # The class of the AUTHORITY, resolved from the spine first and the
        # sweep verdicts second. Reading it only out of `verdicts` reported
        # every ANCSA row as "?" — code/1073's authorities are keyed from
        # ancsa_filings_index.csv and were never sweep targets.
        cls = {}
        for x in spine_rows():
            cls[x["cedar_uid"]] = CLASS_OF.get(x["entity_class"],
                                               x["entity_class"])
        with open(VERDICTS, encoding="utf-8-sig", newline="") as fh:
            for v in csv.DictReader(fh):
                cls.setdefault(v["cedar_uid"], v["klass"])
        c = collections.Counter(
            cls.get(r["certifying_authority_entity_id"], "unkeyed_authority")
            for r in rows)
        print("  by class:", dict(c))
        print("  identity_scope:",
              dict(collections.Counter(r["identity_scope"] for r in rows)))
        print("  assertion_class:",
              dict(collections.Counter(r["assertion_class"] for r in rows)))
        print("  authorities:",
              len({r["certifying_authority_name"] for r in rows}))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["targets", "sweep", "harvest", "stage",
                                      "verdicts", "verify", "selftest",
                                      "report"])
    ap.add_argument("--limit", type=int)
    ap.add_argument("--only", help="comma list of anc,nho,tribal_government,"
                                   "intertribal")
    ap.add_argument("--hours", type=float, default=DEFAULT_HOURS)
    ap.add_argument("--redo", help="comma list of tribe_ids to re-probe even "
                                   "though they are already in host_log; the "
                                   "LAST record per entity wins")
    a = ap.parse_args()
    only = set(a.only.split(",")) if a.only else None

    if a.stage == "targets":
        import collections
        pop = targets()
        c = collections.Counter(t["klass"] for t in pop)
        ch = collections.Counter(t["klass"] for t in pop if t["host"])
        ce = collections.Counter(t["entity_class"] for t in pop)
        print("population by workstream class (total / with a host):")
        for k in sorted(c):
            print(f"  {k:20s} {c[k]:5d} / {ch[k]:5d}")
        print(f"  {'TOTAL':20s} {len(pop):5d} / {sum(ch.values()):5d}")
        print("\nby spine entity_class:")
        for k, n in ce.most_common():
            print(f"  {k:52s} {n:5d}")
        print(f"\nexcluded hosts in force: {len(excluded_hosts())}")
        return 0
    if a.stage == "sweep":
        stage_sweep(limit=a.limit, only=only, hours=a.hours,
                    redo=set((a.redo or "").split(",")) - {""})
        return 0
    if a.stage == "harvest":
        stage_harvest(hours=a.hours, limit=a.limit)
        return 0
    if a.stage == "stage":
        stage_build()
        return 0
    if a.stage == "verdicts":
        write_verdicts()
        return 0
    if a.stage == "report":
        report()
        return 0
    if a.stage == "selftest":
        return selftest()
    bad = verify()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
