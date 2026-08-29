#!/usr/bin/env python3
"""
Cedar Press - 91: the NIGC declination-letter layer.

WHAT A DECLINATION LETTER IS EVIDENCE OF - AND WHAT IT IS NOT
-------------------------------------------------------------
NIGC's Office of General Counsel reviews UNEXECUTED agreements a tribe submits
voluntarily and issues an opinion on two questions: does the submission
constitute a MANAGEMENT CONTRACT requiring the Chair's approval under IGRA, and
does it violate IGRA's SOLE PROPRIETARY INTEREST requirement.

A declination letter is strong evidence that NIGC REVIEWED SUBMITTED DOCUMENTS
and reached a legal conclusion. It is NOT evidence that

  * the transaction closed or the agreement was ever executed,
  * the property opened, was built, or still operates,
  * the land was taken into trust or the site is gaming-eligible.

That is not an editorial caution; it is the agency's own description of the
programme, quoted from the index page and reproduced on every row of the output:

    "Documents should be submitted prior to their execution (unsigned) as the
     General Counsel will not provide a declination letter for executed
     documents."

    "This review is neither required by the Indian Gaming Regulatory Act nor
     the NIGC regulations and is offered by the OGC as a courtesy."

For land status and federal approval, cite the Federal Register or BIA. Never a
declination letter.

AND ABSENCE PROVES NOTHING. Review is voluntary, and NIGC posts an opinion only
after its FOIA Officer clears it and the tribe is consulted. A property with no
letter is not a property with no financing. Same rule as absence-under-a-filter
everywhere else in this project.

CLAIMS, NOT OVERWRITES
----------------------
Nothing here overwrites another source. Each claim a letter makes is stored as
its own row in `gaming_source_claims.csv`, linked to the canonical entity, so a
subscriber can see WHICH SOURCE ESTABLISHES WHICH FACT. `supporting_text` is
the verbatim language of the letter (whitespace collapsed, nothing else
altered). A claim that cannot be quoted is not written.

FIVE LEGAL PERSONS, NOT ONE
---------------------------
The tribe, the gaming authority, the gaming enterprise, the property-owning
subsidiary and the casino brand are five legal persons. The letters are often
the only source that distinguishes them, so they are never collapsed. That is
also why this build carries an `instrumentality_of` predicate alongside
`wholly_owned_by`: an unincorporated instrumentality of a tribe is not the same
legal form as a wholly owned subsidiary, and the letters say which one they
mean.

THE CONTAINMENT DEFECT (AGENTS.md)
----------------------------------
`resolve_entity`'s containment tier matches whenever one token set contains the
other, in both directions, and has cost real money five times. Here it would be
catastrophic: these letters are full of short generic names. So:

  * entity resolution uses script 33's `resolve_entity` and NOTHING ELSE - no
    second name matcher exists in this file;
  * PROPERTY matching never uses containment at all. It is exact on the
    normalised name, and a match must also agree on the tribe or the state.
    Everything else is staged UNRESOLVED for a human.

NEVER attach a letter to a specific property merely because the tribal
enterprise owns that property. Many financings cover several properties, the
whole enterprise, unrestricted assets, or projects that do not exist yet. The
letter-entity-property relation is many-to-many by construction.

Reads  data/raw/external/nigc_declinations/  (index csv + pdfs + manifest)
       data/spine/cedar_entity_spine.csv
       data/clean/gaming_facilities.csv        READ ONLY - another agent owns it
       data/clean/deals_*.csv
Writes data/clean/nigc_declination_letters.csv
       data/clean/gaming_source_claims.csv
       data/clean/gaming_financing_events.csv
       review/nigc_declination_property_matches_<date>.csv
       review/nigc_declination_traces_<date>.csv
       review/nigc_declination_vs_deals_<date>.csv
       review/nigc_declination_entities_held_<date>.csv
"""

import sys as _sys_cd
from pathlib import Path as _Path_cd
_sys_cd.path.insert(0, str(_Path_cd(__file__).resolve().parent))
import cedar_domain as DOM   # noqa: E402  - DEALS_TRUTH, PROMOTED_TABLES

import csv
import hashlib
import importlib.util
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import fitz  # PyMuPDF

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
RAW = CEDAR / "data" / "raw" / "external" / "nigc_declinations"
TODAY = date.today().isoformat()
FETCHED = "2026-08-06"

INDEX_URL = ("https://www.nigc.gov/office-of-general-counsel/legal-opinions/"
             "declination-letters/")

# ---------------------------------------------------------------- resolver
# Script 33 holds the ONE resolver. Never write another name matcher.
_spec = importlib.util.spec_from_file_location(
    "cedar33", CEDAR / "code" / "33_apply_party_rulings.py")
_m33 = importlib.util.module_from_spec(_spec)
sys.modules["cedar33"] = _m33
_spec.loader.exec_module(_m33)
resolve_entity, norm, core = _m33.resolve_entity, _m33.norm, _m33.core


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


# ------------------------------------------------------------ text handling
def page_texts(pdf_path):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        return [], f"open_failed:{e}"
    pages = []
    for pg in doc:
        try:
            pages.append(pg.get_text("text"))
        except Exception:
            pages.append("")
    doc.close()
    return pages, ""


# RUNNING HEADERS BREAK NEGATION, WHICH INVERTS THE FINDING
# ---------------------------------------------------------
# Every page after the first repeats a header block - "Letter to Eric Dorsky /
# Re: Review of Credit Agreement for Seminole Tribe of Florida / May 5, 2022 /
# Page 2 of 2". A conclusion sentence that straddles the page break comes out
# of the extractor as
#
#   "it is my opinion that the 2022 Loan Documents do not  Letter to Eric
#    Dorsky Re: ... Page 2 of 2  constitute a management contract"
#
# and a negation test looking for "do not constitute a management contract"
# fails while a positive test for "constitute a management contract" succeeds.
# That single defect published TWO letters as finding that the agreement IS a
# management contract when both say the opposite. Header lines are therefore
# removed before any sentence is read.
HEADER_LINE = re.compile(
    r"^\s*(?:Page\s+\d+\s+of\s+\d+"
    r"|Letter\s+to\b.*"
    r"|Re:\s.*"
    r"|VIA\s+(?:EMAIL|E-MAIL|FACSIMILE|U\.?S\.?\s+MAIL).*"
    r"|NATIONAL\s+HEADQUARTERS.*"
    r"|REGIONAL\s+OFFICES.*"
    r"|MAILING\s+ADRESS.*|MAILING\s+ADDRESS.*"
    r"|Tel:\s*202.*|Fax:\s*202.*"
    r"|WWW\.NIGC\.GOV.*"
    r"|NIGC/DEPARTMENT\s+OF\s+THE\s+INTERIOR.*"
    r"|[A-Z][a-z]+\s+\d{1,2},\s+\d{4})\s*$", re.I)


def strip_running_matter(pages):
    """Drop letterhead and running headers/footers, keep everything else."""
    out = []
    for i, pg in enumerate(pages):
        keep = []
        for ln in (pg or "").split("\n"):
            if HEADER_LINE.match(ln):
                # The Re: line and the date on PAGE 1 are content, not running
                # matter, and are needed for the subject and the letter date.
                if i == 0 and re.match(r"^\s*(?:Re:|[A-Z][a-z]+\s+\d{1,2},)", ln):
                    keep.append(ln)
                continue
            keep.append(ln)
        out.append("\n".join(keep))
    return out


def flat(s):
    """Collapse whitespace. The ONLY transformation applied to quoted text."""
    s = (s or "").replace("\u00ad", "")
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", s).strip()


COMMON = set("""the of and to in a is for that this it my be as or not are with by on
any an shall have has was were which such other from will you your we our their its
all more may than been if no so at can under review letter opinion tribe gaming
contract management agreement documents approval interest proprietary sole national
indian commission general counsel chair federal act regulatory""".split())


def common_word_ratio(t):
    toks = [x.lower() for x in re.findall(r"[A-Za-z']{2,}", t)]
    if not toks:
        return 0.0
    return round(sum(1 for x in toks if x in COMMON) / len(toks), 3)


# ------------------------------------------------------- finding detection
#
# THE MISTAKE THIS SECTION EXISTS TO AVOID
# ----------------------------------------
# A first pass matched the phrase "management contract" anywhere in the letter
# and produced 86 AMBIGUOUS and 11 "YES, it IS a management contract" findings.
# Every one of the eleven was false, and they were false in the same way - the
# match was on the letter's QUESTION, not its ANSWER:
#
#     "Specifically, you have asked for my opinion whether the Agreement is a
#      management contract requiring the NIGC Chair's approval..."
#
# or on the footnoted legal standard:
#
#     "If a contract requires or permits the performance of any management
#      activity ... the contract is a management contract within the meaning of
#      IGRA and requires the Chair's approval."
#
# Both sentences say "is a management contract" and neither is a finding. So
# findings are read ONLY from a sentence that carries an explicit opinion marker
# and does NOT carry a question marker. A letter whose conclusion sentence
# cannot be recovered - a degraded scan, an unusual construction - is recorded
# as NOT_STATED_IN_TEXT_LAYER and NOTHING is claimed about it.

ABBREV = re.compile(
    r"(?:\b(?:Mr|Mrs|Ms|Dr|Jr|Sr|St|No|Inc|Corp|Co|Ltd|Nos|Esq|Cir|Supp|Ave|"
    r"Blvd|Rd|Ste|Fed|Reg|Stat|Op|Att|Assn|Dept|Div|et al|e\.g|i\.e|cf|vs|v)\.|"
    r"\b[A-Z]\.|\bU\.S\.|\bC\.F\.R\.|\bL\.P\.|\bN\.A\.|\bL\.L\.C\.|\bU\.S\.C\.)$")


def sentences(t):
    """Split on sentence ends, rejoining where the period is an abbreviation."""
    parts = re.split(r"(?<=[.;])\s+", t)
    out = []
    for p in parts:
        if out and ABBREV.search(out[-1]):
            out[-1] = out[-1] + " " + p
        else:
            out.append(p)
    return out


OPINION_MARK = re.compile(
    r"\b(?:it is (?:also |further |my |our )*opinion|it is (?:my|our) opinion|"
    r"in (?:my|our) opinion|(?:i|we) (?:therefore |thus )?conclude|"
    r"(?:i|we) have concluded|(?:i|we) find that|"
    r"it is the opinion of|(?:my|our) opinion is|OGC concludes)\b", re.I)
QUESTION_MARK = re.compile(
    r"\b(?:whether|you (?:have )?(?:asked|ask)|you requested|the request asks|"
    r"has requested|requesting|you also asked)\b", re.I)
STANDARD_MARK = re.compile(
    r"\bwithin the meaning of IGRA\b|\bC\.F\.R\.|\bif a contract requires or "
    r"permits\b|\bIGRA defines\b|\bis defined as\b", re.I)

# Negation is tested as "a negation word within 90 characters before the phrase",
# because the letters negate in several shapes: "do not constitute a management
# contract", "are not management contracts", "neither X nor Y are management
# contracts", "would not cause a loan facility to be a management contract".
RE_MC_NEG = re.compile(
    r"\b(?:not|nor|neither)\b[^.]{0,90}?management\s+contracts?"
    r"|\bno\w{0,3}\W{0,2}\s+(?:constitut|managem)", re.I)
RE_MC_POS = re.compile(
    r"\b(?:is|are)\s+(?:a\s+)?management\s+contracts?"
    r"|\bconstitutes?\s+(?:a\s+)?management\s+contracts?", re.I)

# OCR-TOLERANT NEGATION - the defect this exists to stop
# -------------------------------------------------------
# The 2013-12-23 Shingle Springs letter is a scan and its OCR reads
# "it does noi: violate IGRA's sole proprietary interest requirement".
# A negation test spelling out "not" misses "noi:", the affirmative test then
# fires, and the row publishes as VIOLATION_FOUND - the exact inverse of what
# the agency wrote. Likewise "do not requit\"c the approval" (Poarch 2013) and
# "dues no! rcquir~ the approval" (Mohegan 2013).
#
# So negation is matched as "a token beginning `no` immediately before the
# verb", and as "any negation word within 90 characters before the operative
# noun". The second rule would misread a hypothetical "is not a management
# contract but requires the Chair's approval"; that construction does not occur
# in this archive, because an arrangement that is not a management contract
# needs no approval by definition.
RE_APPROVAL_NEG = re.compile(
    r"\b(?:not|nor|neither)\b[^.]{0,90}?(?:approv|requir)"
    r"|\bno\w{0,3}\W{0,2}\s+requi"
    r"|\bno\s+approval\s+(?:is|by)\b", re.I)
RE_APPROVAL_POS = re.compile(
    r"\brequires?\s+(?:the\s+)?(?:NIGC\s+)?"
    r"(?:Chair(?:man|woman|person)?'?s?\s+)?approval", re.I)
RE_APPROVAL_ANY = re.compile(r"\bapprov\w+|\bChair", re.I)

# "Nor, in my opinion, do they violate IGRA's sole proprietary interest mandate."
# is the agency's own way of writing a NEGATIVE finding, and a naive test for
# "violates" read six of these as violations. It is not one.
RE_SPI_NEG = re.compile(
    r"\b(?:not|nor|neither)\b[^.]{0,90}?violat"
    r"|\bno\w{0,3}\W{0,2}\s+violat", re.I)
RE_CONDITIONAL = re.compile(
    r"\bif\b|\bunless\b|\bto the extent\b|\bprovided that\b|\bshould\b", re.I)
RE_SPI_POS = re.compile(r"\bviolates?\b|\bviolation\s+of\b", re.I)
RE_SPI_ANY = re.compile(r"sole\s+proprietary", re.I)


def conclusion_sentences(t):
    """Sentences that state the agency's own conclusion, and only those."""
    out = []
    for s in sentences(t):
        if not OPINION_MARK.search(s):
            continue
        if QUESTION_MARK.search(s) or STANDARD_MARK.search(s):
            continue
        out.append(s.strip())
    return out


def read_finding(concs, topic_any, neg, pos):
    """(value, quote) from the conclusion sentences alone. Never from elsewhere."""
    rel = [s for s in concs if topic_any.search(s)]
    if not rel:
        return "", ""
    neg_hits = [s for s in rel if neg.search(s)]
    if neg_hits:
        return "NO", flat(neg_hits[0])
    pos_hits = [s for s in rel if pos.search(s)]
    if pos_hits:
        return "YES", flat(pos_hits[0])
    return "STATED_BUT_DIRECTION_NOT_PARSED", flat(rel[0])


RE_MC_ANY = re.compile(r"management\s+contracts?", re.I)

RE_MATERIAL = re.compile(
    r"[^.]{0,400}?in\s+any\s+material\s+(?:way|respect)[^.]{0,300}?\.", re.I)
RE_SCOPE_LIMIT = re.compile(
    r"[^.]{0,200}?(?:this\s+opinion\s+is\s+limited\s+to|does\s+not\s+include\s+or\s+"
    r"extend\s+to)[^.]{0,300}?\.", re.I)
RE_UNEXECUTED = re.compile(
    r"[^.]{0,300}?(?:unexecuted|not\s+been\s+executed|substantially\s+final\s+form|"
    r"prior\s+to\s+(?:their\s+)?execution)[^.]{0,300}?\.", re.I)


def first(rx, t):
    m = rx.search(t)
    return flat(m.group(0)) if m else ""


# ------------------------------------------------------- agreement typology
AGREEMENT_TYPES = [
    ("loan_or_credit_agreement",
     r"credit agreement|loan agreement|loan documents|term loan|revolving|"
     r"promissory note|financing agreement"),
    ("note_indenture_or_bond",
     r"indenture|senior notes|bond|note purchase agreement|trust indenture"),
    ("security_or_collateral_agreement",
     r"security agreement|pledge agreement|deposit account control|"
     r"blocked account|collateral agreement|mortgage|leasehold deed of trust"),
    ("lease",
     r"\blease\b|leasing|ground lease|sublease"),
    ("equipment_or_gaming_machine_agreement",
     r"gaming machine|slot machine|equipment lease|participation agreement|"
     r"placement agreement"),
    ("technology_or_systems_agreement",
     r"technology|systems agreement|software|player tracking|kiosk|"
     r"internet sports|sportsbook|sports betting|sports wagering"),
    ("development_or_construction_agreement",
     r"development agreement|construction|design[- ]build|architect"),
    ("consulting_or_services_agreement",
     r"consulting|consultant|marketing agreement|services agreement|"
     r"advisory agreement|employment agreement|independent contractor"),
    ("amendment_or_restatement",
     r"amendment|amended and restated|first amendment|second amendment|"
     r"third amendment|fourth amendment"),
]

RE_AMEND_NUM = re.compile(
    r"\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
    r"eleventh|twelfth)\s+amendment", re.I)
RE_AMEND_ORD = re.compile(r"\bamendment\s+no\.?\s*(\d+)", re.I)
ORD = {w: i for i, w in enumerate(
    "first second third fourth fifth sixth seventh eighth ninth tenth "
    "eleventh twelfth".split(), start=1)}

RE_PRIOR = re.compile(
    r"[^.]{0,250}?(?:our\s+(?:prior\s+)?letters?\s+(?:of|dated)|"
    r"(?:my|our)\s+(?:previous|prior|earlier)\s+(?:opinion|letter)|"
    r"declination\s+letter\s+(?:of|dated)|previously\s+reviewed|"
    r"the\s+Office\s+of\s+General\s+Counsel\s+has\s+already\s+reviewed)"
    r"[^.]{0,250}?\.", re.I)
RE_REFI = re.compile(r"refinanc\w*", re.I)
RE_RESTATE = re.compile(r"amended\s+and\s+restated", re.I)
RE_EXTEND = re.compile(r"extend\w*\s+the\s+(?:maturity|term)", re.I)
RE_SUPERSEDE = re.compile(r"supersed\w+", re.I)


# ------------------------------------------------------------ party parsing
ROLE_TO_PREDICATE = {
    "administrative agent": "administrative_agent_for",
    "collateral agent": "collateral_agent_for",
    "disbursement agent": "administrative_agent_for",
    "lender": "lender_in",
    "lenders": "lender_in",
    "borrower": "borrower_in",
    "borrowers": "borrower_in",
    "guarantor": "guarantor_of",
    "guarantors": "guarantor_of",
    "developer": "developer_of",
    "trustee": "trustee_for",
    "senior notes trustee": "trustee_for",
    "indenture trustee": "trustee_for",
}

# "<Name>, as <Role>" - the defined-role construction financing letters use.
RE_AS_ROLE = re.compile(
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,70}?)\s*,?\s+as\s+"
    r"(Administrative Agent|Collateral Agent|Disbursement Agent|Senior Notes Trustee|"
    r"Indenture Trustee|Trustee|Lenders?|Borrowers?|Guarantors?|Developer)\b")

# '<Name> (the "Term")' - the defined-term construction.
RE_DEFTERM = re.compile(
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s*\(\s*(?:the\s+|collectively,?\s+the\s+)?"
    r'"([A-Za-z][A-Za-z ]{1,40}?)"\s*\)')

# Ownership / legal-form statements. Kept narrow on purpose: each requires the
# letter to state the form in words.
# NOTE: these are deliberately NOT re.I. An earlier version carried re.I, which
# makes `[A-Z]` match any letter, and the capture then began mid-word - it
# produced the subject "pdated - Review of 2025 Loan Documents for the River
# Rock Entertainment Authority" from the word "Updated". Case is load-bearing
# here because a party name starts with a capital and a sentence fragment does
# not. Keyword alternatives carry both cases explicitly.
RE_WHOLLY = re.compile(
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s*,\s*an?\s+[Ww]holly[\s\-][Oo]wned\s+"
    r"([Ss]ubsidiary|[Ii]nstrumentality|[Cc]orporation|[Ee]ntity|[Ee]nterprise|"
    r"[Cc]ompany)\s+(?:and\s+\w+\s+)?of\s+(?:the\s+)?"
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s*[,.(]")
RE_INSTRUMENTALITY = re.compile(
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s*,\s*an?\s+"
    r"(?:[Uu]nincorporated\s+|[Tt]ribal\s+|[Pp]olitical\s+)?"
    r"([Ii]nstrumentality|[Pp]olitical subdivision|"
    r"[Ss]ubordinate economic organization|[Ss]ubordinate economic entity)\s+"
    r"(?:and\s+\w+\s+)?of\s+(?:the\s+)?"
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s*[,.(]")
RE_SUBSIDIARY = re.compile(
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s*,\s*an?\s+"
    r"([Ss]ubsidiary|[Aa]ffiliate)\s+of\s+(?:the\s+)?"
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s*[,.(]")
# Parties to the reviewed documents, from the Re: line and the opening
# paragraph. "between A and B" / "among A, B and C".
RE_BETWEEN = re.compile(
    r"\b(?:between|among|by and among)\s+"
    r"((?:[A-Z][A-Za-z0-9&.,'\-/ ]{2,70}?)(?:\s+and\s+[A-Z][A-Za-z0-9&.,'\-/ ]{2,70}?)+)"
    r"\s*[,.(:;]")
# "<Property> (ACRONYM), wholly owned by <Tribe>" - the form the letters
# actually use most often. The earlier pattern only caught "a wholly owned
# subsidiary of", which is a different and rarer construction.
# The commonest form in this archive is NOT "X, wholly owned by Y" but
# "X, a federally chartered tribal business corporation wholly owned by Y" -
# a descriptor clause sits between the name and the ownership phrase. Measured:
# 21 "wholly owned" mentions in the corpus, of which the tight pattern caught
# one. The descriptor is allowed for, and it is worth keeping in the quote
# because "chartered under 25 U.S.C. 477" is itself a legal-form fact.
RE_WHOLLY_BY = re.compile(
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s*(?:\([A-Z][A-Za-z]{1,9}\)\s*)?,?\s*"
    r"(?:\((?:the\s+)?\"[^\"]{2,40}\"\)\s*)?,?\s*"
    r"(?:a|an|which is a|dba)?\s*[a-zA-Z0-9\-.,'§ ]{0,95}?"
    r"[Ww]holly[\s\-][Oo]wned\s+by\s+(?:the\s+)?"
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s*[,.(]")
# "X, a wholly-owned enterprise and economic arm of the Pueblo of Acoma"
RE_WHOLLY_ARM = re.compile(
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s*,\s*(?:a|an)\s+"
    r"[Ww]holly[\s\-][Oo]wned\s+"
    r"(enterprise|instrumentality|subsidiary|entity|corporation|company|arm)"
    r"(?:\s+and\s+[a-z ]{0,25})?\s+of\s+(?:the\s+)?"
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s*[,.(]")
RE_OWNED_OPERATED_BY = re.compile(
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s*(?:\([A-Z][A-Za-z]{1,9}\)\s*)?,\s*"
    r"(?:which is\s+)?(?:owned and operated|operated)\s+by\s+(?:the\s+)?"
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s*[,.(]")
# "<Vendor> will lease/provide/supply ... to <Customer>"
RE_VENDOR = re.compile(
    r"([A-Z][A-Za-z0-9&.,'\-/ ]{2,60}?)\s+(?:will|shall|agrees to|is to)\s+"
    r"(?:lease|provide|supply|install|furnish|license|deliver|operate)\s+"
    r"[^.]{0,90}?\bto\s+(?:the\s+)?([A-Z][A-Za-z0-9&.,'\-/ ]{2,60}?)\s*[,.(]")
# "COLLATERAL" IS A HOMONYM IN THIS ARCHIVE AND THE WRONG SENSE IS THE COMMON ONE
# ------------------------------------------------------------------------------
# 25 C.F.R. 502.5 defines a "COLLATERAL AGREEMENT" as a contract related to a
# gaming operation - nothing to do with security for a loan - and that
# definition is quoted in the letters that analyse whether an arrangement is a
# management contract. A bare search for "collateral" therefore produced two
# collateral_for claims out of the *regulatory definition*, attaching Harrah's
# Cherokee Casino and Harrah's Cherokee Valley River Casino to a financing that
# the sentence never mentions. The sense that matters here is security for
# borrowing, so the test names that sense and rules the regulatory sense out.
RE_COLLATERAL_SENT = re.compile(
    r"secured\s+by|pledge[ds]?\b|pledging|mortgage|"
    r"leasehold\s+deed\s+of\s+trust|security\s+interest\s+in|"
    r"as\s+collateral\s+for", re.I)
RE_COLLATERAL_REGULATORY = re.compile(
    r"collateral\s+agreement|defines?\b|definition|25\s*C\.?F\.?R|"
    r"within\s+the\s+meaning", re.I)

RE_OPERATES = re.compile(
    r"(?:the\s+)?([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?)\s+(?:owns\s+and\s+)?operates?\s+"
    r"(?:the\s+)?([A-Z][A-Za-z0-9&.,'\-/ ]{2,80}?(?:Casino|Resort|Hotel|Bingo|"
    r"Gaming Center|Gaming Facility|Travel Plaza|Lodge|Card Room)"
    r"[A-Za-z0-9&.,'\-/ ]{0,30}?)\s*[,.(]")

# Property-name shapes. Detection only - a hit is a CANDIDATE, never a match.
PROP_TAIL = (r"(?:Casino(?:\s+Resort)?|Resort(?:\s+&?\s*Casino)?|Hotel(?:\s+&?\s*Casino)?"
             r"|Bingo(?:\s+Hall)?|Gaming\s+Center|Gaming\s+Facility|Travel\s+Plaza"
             r"|Card\s+Room|Lodge|Gaming\s+Hall)")
RE_PROPERTY = re.compile(
    r"\b((?:[A-Z][A-Za-z'\-]{1,20}\s+){0,5}" + PROP_TAIL + r")\b")

ENTERPRISE_WORDS = re.compile(
    r"gaming authority|gaming enterprise|gaming commission|development authority|"
    r"entertainment authority|gaming corporation|economic development|"
    r"tribal gaming agency|gaming board", re.I)
NON_GAMING_WORDS = re.compile(
    r"golf|water park|spa\b|convention center|arena|amphitheater|gas station|"
    r"marina|rv park|campground|smoke shop(?!.*gaming)", re.I)
PROPOSED_WORDS = re.compile(
    r"proposed|to be (?:built|constructed|developed)|future|planned|"
    r"under construction|will be constructed|new casino to be", re.I)

STOP_PROPERTY = {
    "casino", "resort", "hotel", "bingo", "lodge", "gaming center",
    "gaming facility", "the casino", "a casino", "casino resort",
    "gaming hall", "card room", "travel plaza", "hotel casino",
}


def party_id(name):
    """Stable id for a party that is not (or not yet) a spine entity."""
    return "NIGCP-" + hashlib.md5(norm(name).encode()).hexdigest()[:10].upper()


CLEAN_TAIL = re.compile(
    r"^(?:and|the|among|between|by|to|of|with|for|a|an|its|their|our|from|"
    r"submitted|dated|including|collectively)\s+", re.I)


BOUNDARY = re.compile(
    r"^.*?\b(?:on behalf of|by and among|among|between|in favor of|"
    r"request(?:ed)?(?:,)? (?:for|to)|responds to)\s+", re.I)
CORP_TOKEN = re.compile(
    r"\b(?:Bank|N\.A\.|LLC|L\.L\.C\.|Inc\.?|Incorporated|Corporation|Corp\.?|"
    r"Company|Co\.|Association|L\.?P\.?|Trust|Capital|Partners|Holdings|Group|"
    r"Financial|Securities|Fund|Systems|Technologies|Technology|Gaming|"
    r"Enterprises?|Authority|Development)\b")
# A captured span that contains any of these is a sentence fragment, not a
# party name. Rejected outright rather than salvaged - precision over recall.
JUNK_IN_NAME = re.compile(
    r"\b(?:request|behalf|letter|review of|dated|considered|submitted|"
    r"following|response|opinion|pursuant|provides that|states that|"
    r"January|February|March|April|May|"
    r"June|July|August|September|October|November|December)\b", re.I)

# A bare common noun is a sentence fragment, never a party. "Indians" arrived as
# a borrower_in subject from "...Band of Mission Indians, as Borrower", and a
# claim whose subject is the word "Indians" is worse than no claim.
GENERIC_FRAGMENT = {
    "indians", "tribe", "tribes", "nation", "nations", "band", "bands",
    "pueblo", "community", "rancheria", "authority", "enterprise",
    "corporation", "company", "commission", "council", "borrower", "lender",
    "agent", "guarantor", "grantor", "trustee", "casino", "resort",
    "gaming authority", "gaming enterprise", "the tribe", "tribal council",
}


# A letter's address block has no sentence-ending period, so the sentence
# splitter returns the whole letterhead as one "sentence" and a party pattern
# run over it produces things like "Bank of America President Joaquin" and
# "Churchill Downs Interactive Gaming Dear Mr". These tokens never appear in a
# party name and always appear in an address block or a salutation.
ADDRESS_JUNK = re.compile(
    r"\b(?:Esq|President|Partner|Chairman|Chairperson|Chairwoman|Attorney|"
    r"Suite|Ste|Street|Avenue|Ave|Blvd|Boulevard|Highway|Road|Drive|Floor|"
    r"P\.?\s?O\.?\s+Box|Dear|VIA|General Counsel|Legal Counsel|Council)\b"
    r"|\d{4}", re.I)
# A prior role designation inside the span: "..., as the Borrower, U.S. Bank
# National Association, as Administrative Agent" - keep only the last party.
ROLE_PREFIX = re.compile(
    r"^.*\bas\s+(?:the\s+|a\s+)?"
    r"(?:Borrower|Grantor|Lender|Guarantor|Agent|Trustee|Issuer|Pledgor)s?"
    r"(?:\s+and\s+a\s+\w+)?\s*,\s*", re.I)
ROLE_ONLY = re.compile(
    r"^(?:as\s+)?(?:the\s+)?(?:Borrower|Grantor|Lender|Guarantor|Agent|Trustee|"
    r"Issuer|Pledgor|Developer|Manager|Tribe|Authority|Enterprise|Lenders|"
    r"Other\s+\w+)s?$", re.I)


def narrow_party(s):
    """Cut a captured span down to the party, or return '' and claim nothing."""
    s = flat(s)
    m = ROLE_PREFIX.match(s)
    if m:
        s = s[m.end():]
    m = BOUNDARY.match(s)
    if m:
        s = s[m.end():]
    s = re.sub(r"^\s*as\s+(?:the\s+|a\s+)?", "", s, flags=re.I)
    if ADDRESS_JUNK.search(s) or ROLE_ONLY.match(s.strip()):
        return ""
    # "<Tribe> and <Commercial party>" - keep the right side only when it is
    # plainly a distinct commercial party. "Wichita and Affiliated Tribes" has
    # no corporate token on the right and is left whole.
    if " and " in s:
        right = s.rsplit(" and ", 1)[1].strip()
        if CORP_TOKEN.search(right) and len(right.split()) >= 2:
            s = right
    s = re.sub(r"^[\W_]+", "", s).strip()
    if JUNK_IN_NAME.search(s):
        return ""
    if len(s.split()) > 9:
        return ""
    if norm(s) in GENERIC_FRAGMENT:
        return ""
    if len(s.split()) == 1 and not CORP_TOKEN.search(s):
        return ""
    return s


def clean_name(s):
    """Light cleanup only. Used for names that are ALREADY names - NIGC's own
    index strings, ledger party fields - where narrowing would do damage."""
    s = flat(s)
    prev = None
    while prev != s:
        prev = s
        s = CLEAN_TAIL.sub("", s).strip()
    return re.sub(r"\s*[,;:]\s*$", "", s).strip()


def tidy_party(s):
    """Cleanup for a span CAPTURED out of running prose, which may be a
    sentence fragment. Narrows first, and returns '' rather than guess."""
    s = narrow_party(s)
    if not s:
        return ""
    prev = None
    while prev != s:
        prev = s
        s = CLEAN_TAIL.sub("", s).strip()
    s = re.sub(r"\s*[,;:]\s*$", "", s)
    s = re.sub(r"\s*\(\s*$", "", s)
    return s.strip()


# ================================================================== build
def main():
    print("=== Cedar Press 91: NIGC declination-letter layer ===\n")
    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    print(f"spine entities: {len(spine):,}")

    index = read_csv(RAW / "_index" / "declination_letters_index.csv")
    manifest = {m["cedar_opinion_id"]: m
                for m in read_csv(RAW / "_SOURCE_MANIFEST.csv")}
    print(f"index rows: {len(index):,}   PDFs retrieved: {len(manifest):,}")

    # ---------------------------------------------------------------------
    # TWO INDEX ROWS, ONE PDF - a defect in the published archive, not in us.
    #
    # The 2021-04-12 Yavapai-Apache/BOKF row and the 2021-04-13 Tunica
    # Biloxi/First Guaranty Bank row carry DIFFERENT `wpdmdl=` values (3173 and
    # 3175) but the SAME `ind=3176`, and both 302-redirect to the identical
    # object `20210412Yavapai-Apache-BOKFNA.pdf`. So one of those two links
    # serves the other letter's document.
    #
    # This is the download trap of docs/NIGC_REGION_BUILD_LOG.md §15 in a new
    # form - there the collision was on `wpdmdl`, here it is on `ind` - and it
    # is exactly why the fetcher verifies md5s instead of trusting distinct
    # URLs. Reading findings out of that PDF for BOTH rows would attribute a
    # Yavapai-Apache opinion to the Tunica-Biloxi Tribe.
    #
    # The rule, stated so it generalises: where n index rows resolve to one
    # md5, the PDF is attributed to the row whose OWN index date appears in the
    # resolved filename, and to no row at all if that test is not decisive.
    # The losers are recorded, not deleted, and nothing is read out of them.
    by_md5 = defaultdict(list)
    for o, m in manifest.items():
        if m.get("md5"):
            by_md5[m["md5"]].append(o)
    idx_date = {r["cedar_opinion_id"]: r["index_date"] for r in index}
    pdf_owner = {}
    for digest, oids in by_md5.items():
        if len(oids) < 2:
            continue
        winner = None
        for o in oids:
            digits = re.sub(r"[^0-9]", "", manifest[o].get("local_name", ""))
            if idx_date.get(o, "").replace("-", "") in digits:
                winner = o if winner is None else "AMBIGUOUS"
        for o in oids:
            pdf_owner[o] = (winner if winner not in (None, "AMBIGUOUS") else "",
                            [x for x in oids if x != o])
    if pdf_owner:
        print(f"  shared-PDF index rows: {len(pdf_owner)} "
              f"(in {len([1 for v in by_md5.values() if len(v) > 1])} md5 group(s))")

    # HTTP failures, from the fetch log, so a 404 is published as a 404 and not
    # as a silent blank.
    http_fail = {}
    for lg in sorted((CEDAR / "logs").glob("90_nigc_declinations_fetch_*.log")):
        for ln in lg.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.search(r"(NIGC-DL-\S+): FAILED status=(\d+)", ln)
            if m:
                http_fail[m.group(1)] = m.group(2)

    facilities = read_csv(CLEAN / "gaming_facilities.csv")
    fac_by_name = defaultdict(list)
    fac_by_tribe = defaultdict(list)
    for f in facilities:
        for key in (f.get("facility_name"), f.get("company")):
            if key and key.strip():
                fac_by_name[norm(key)].append(f)
        if f.get("tribe_id"):
            fac_by_tribe[f["tribe_id"]].append(f)
    print(f"gaming_facilities rows (READ ONLY): {len(facilities):,}")

    # resolution cache so an entity name is resolved once, identically
    rescache = {}

    # ------------------------------------------------------------------
    # CONTAINMENT GUARDS AT THE CALL SITE
    #
    # AGENTS.md: "containment may be used only to resolve an owner already
    # named in evidence - never to detect a match, and never to key a dollar."
    # Script 33 is shared and is NOT modified here; the guards live where the
    # call is made. Measured on this archive before the guards existed:
    #
    #   "Keweenaw Bay Indian Community" -> Keweenaw Bay Ojibwa Community
    #       COLLEGE (class: Tribal College or University)
    #   "N/A"                           -> Native American BANK, N.A.
    #       (class: Native CDFI) - the literal string "N/A" resolved to a bank
    #       because core("N/A") = {n, a} is contained in that name's tokens
    #   "San Carlos Apache Tribe"       -> ambiguous between San Carlos Apache
    #       College and a relending enterprise (correctly refused by script 33)
    #
    # Two different guards, because the two call sites need opposite things.
    #
    # TRIBE guard: NIGC's index_tribe column is a tribal GOVERNMENT by
    # construction, so a containment hit is accepted only when the matched
    # spine row is a government class AND the spine name's tokens are a subset
    # of the record's - the direction in which containment is defensible,
    # because the spine stores short canonical names ("Ione", "Scotts Valley")
    # and NIGC writes the long official one.
    #
    # PARTY guard: containment is REFUSED OUTRIGHT. A claim subject is often an
    # enterprise, authority or property-owning subsidiary, and containment
    # would resolve "Twenty-Nine Palms Enterprises Corporation" onto the tribe
    # "Twenty-Nine Palms" - collapsing two legal persons into one, which is the
    # exact flattening this build exists to prevent. Only exact, core and alias
    # resolutions are accepted for a party; everything else is HELD.
    # The constituency classes belong here. White Earth and Leech Lake are
    # constituent bands of the Minnesota Chippewa Tribe and Viejas is a band of
    # the Capitan Grande Band; the spine classes them "Federal-level
    # constituency entity" because that IS their federal status, and they are
    # the correct answer for "White Earth Band of Chippewa". Excluding them
    # threw away three right answers. The direction guard still applies, and it
    # is what stops the class from being a loophole - it is also what caught
    # "Cherokee Nation of Oklahoma" -> United Keetoowah Band of Cherokee
    # Indians in Oklahoma, a different federally recognised tribe, which
    # containment offered and this build refuses.
    GOV_CLASSES = {"Federally recognized tribe",
                   "Federally recognized Alaska Native Village",
                   "State-recognized tribe",
                   "Federal-level constituency entity",
                   "State-level constituency entity"}
    by_id = {r["tribe_id"]: r for r in spine}

    def resolve(nm, mode="party"):
        nm = clean_name(nm)
        if not nm or len(nm) < 4 or norm(nm) in ("n a", "na", "none", "various"):
            return None, None, "too_short_or_placeholder"
        key = (nm, mode)
        if key in rescache:
            return rescache[key]
        tid, cname, how = resolve_entity(nm, spine)
        if how == "containment":
            if mode != "tribe":
                tid, cname, how = (
                    None, None,
                    "containment_refused_for_a_party: a party may be a distinct "
                    "legal person (enterprise, authority, subsidiary) from the "
                    "entity it contains")
            else:
                ent = by_id.get(tid, {})
                if ent.get("entity_class") not in GOV_CLASSES:
                    tid, cname, how = (
                        None, None,
                        "containment_refused_non_government_class:"
                        + str(ent.get("entity_class")))
                elif not core(cname) <= core(nm):
                    tid, cname, how = (
                        None, None,
                        "containment_refused_record_not_more_specific")
        rescache[key] = (tid, cname, how)
        return rescache[key]

    letters, claims, fin_events, prop_rows, held = [], [], [], [], []
    claim_seq = 0

    for row in index:
        oid = row["cedar_opinion_id"]
        man = manifest.get(oid)
        rec = {
            "cedar_opinion_id": oid,
            "opinion_date": row["index_date"],
            "opinion_date_basis": "nigc_published_index_table",
            "index_tribe_string": row["index_tribe"],
            "index_company_string": row["index_company"],
            "source_url": row["wpdm_url"],
            "index_url": INDEX_URL,
            "pdf_path": (man or {}).get("local_path", ""),
            "pdf_md5": (man or {}).get("md5", ""),
            "resolved_pdf_url": (man or {}).get("resolved_url", ""),
            "fetched_date": FETCHED,
        }
        own, twins = pdf_owner.get(oid, (None, []))
        rec["pdf_shared_with_opinion_ids"] = "|".join(twins)
        if not man:
            rec["retrieval_status"] = (
                f"not_retrieved_http_{http_fail[oid]}" if oid in http_fail
                else "not_retrieved")
            rec["retrieval_note"] = (
                "NIGC's published download link for this row returned HTTP "
                f"{http_fail[oid]}. The letter is listed in the agency's own "
                "index and its PDF is not served. Recorded, not dropped."
                if oid in http_fail else "no PDF retrieved")
        elif twins and own != oid:
            rec["retrieval_status"] = "pdf_link_serves_another_letters_document"
            rec["retrieval_note"] = (
                "This row's link resolves to the SAME object as "
                f"{'|'.join(twins)} (identical md5), and the resolved filename "
                f"carries that other row's date, not this one's. NIGC's index "
                "and its file store disagree here. NOTHING is read out of the "
                "PDF for this row - doing so would attribute another tribe's "
                "opinion to this one.")
        else:
            rec["retrieval_status"] = "retrieved"
            rec["retrieval_note"] = (
                ("this PDF is also served by " + "|".join(twins) +
                 "; attributed here because the resolved filename carries this "
                 "row's date") if twins else "")

        # ---- tribe resolution, from NIGC's own index string
        tid, cname, how = resolve(row["index_tribe"], mode="tribe")
        rec["tribe_entity_id"] = tid or ""
        rec["tribe_canonical_name"] = cname or ""
        rec["tribe_resolve_how"] = how
        rec["tribe_resolve_status"] = "RESOLVED" if tid else "HELD"
        if not tid:
            held.append({"cedar_opinion_id": oid, "name": row["index_tribe"],
                         "role": "index_tribe", "reason": how,
                         "source_url": row["wpdm_url"], "YOUR_RULING": ""})

        pages_raw, err = ([], "no_pdf")
        if man and rec["retrieval_status"] == "retrieved":
            pages_raw, err = page_texts(CEDAR / man["local_path"])
        pages = strip_running_matter(pages_raw)
        raw = "\n".join(pages)
        t = flat(raw)
        rec["n_pages"] = len(pages)
        rec["text_chars"] = len(raw)
        rec["common_word_ratio"] = common_word_ratio(raw)

        # ---- findings, read ONLY from the agency's own conclusion sentences
        concs = conclusion_sentences(t)
        rec["n_conclusion_sentences"] = len(concs)
        no_text = len(raw) < 400

        v, q = read_finding(concs, RE_MC_ANY, RE_MC_NEG, RE_MC_POS)
        rec["is_management_contract"] = {
            "NO": "NO_NOT_A_MANAGEMENT_CONTRACT",
            "YES": "YES_IS_A_MANAGEMENT_CONTRACT",
            "STATED_BUT_DIRECTION_NOT_PARSED": "STATED_BUT_DIRECTION_NOT_PARSED",
            "": "NOT_EXTRACTABLE" if no_text else "NOT_STATED_IN_TEXT_LAYER",
        }[v]
        rec["finding_quote"] = q

        v, q = read_finding(concs, RE_APPROVAL_ANY, RE_APPROVAL_NEG,
                            RE_APPROVAL_POS)
        rec["chair_approval_required"] = {
            "NO": "NO", "YES": "YES",
            "STATED_BUT_DIRECTION_NOT_PARSED": "STATED_BUT_DIRECTION_NOT_PARSED",
            "": "NOT_EXTRACTABLE" if no_text else "NOT_STATED_IN_TEXT_LAYER",
        }[v]
        rec["chair_approval_quote"] = q

        v, q = read_finding(concs, RE_SPI_ANY, RE_SPI_NEG, RE_SPI_POS)
        rec["sole_proprietary_interest_analysis"] = {
            "NO": "NO_VIOLATION_FOUND",
            "YES": "VIOLATION_FOUND",
            "STATED_BUT_DIRECTION_NOT_PARSED": "STATED_BUT_DIRECTION_NOT_PARSED",
            "": ("NOT_EXTRACTABLE" if no_text else
                 ("ADDRESSED_BUT_NOT_IN_A_CONCLUSION_SENTENCE"
                  if RE_SPI_ANY.search(t) else "NOT_ADDRESSED_IN_TEXT_LAYER")),
        }[v]
        rec["sole_proprietary_interest_quote"] = q

        # A conditional conclusion is a different asset from an unconditional
        # one. Mashantucket 2020-10-20 concludes the agreement violates the sole
        # proprietary interest requirement *if* gaming occurs on Indian lands.
        allq = " ".join([rec["finding_quote"], rec["chair_approval_quote"],
                         rec["sole_proprietary_interest_quote"]])
        rec["finding_is_conditional"] = 1 if RE_CONDITIONAL.search(allq) else 0

        mat = first(RE_MATERIAL, t)
        rec["material_change_warning"] = 1 if mat else 0
        rec["material_change_quote"] = mat
        rec["scope_limitation_quote"] = first(RE_SCOPE_LIMIT, t)
        rec["documents_unexecuted_quote"] = first(RE_UNEXECUTED, t)

        # text-layer grade, defined by what was RECOVERABLE, not by a guess
        if len(raw) < 400:
            rec["text_layer_quality"] = "no_text_layer"
        elif rec["finding_quote"] or rec["chair_approval_quote"]:
            rec["text_layer_quality"] = "standard_language_recovered"
        else:
            rec["text_layer_quality"] = "text_present_standard_language_not_recovered"

        # ---- Re: line, addressee, signer
        m = re.search(r"\bRe:?\s*(.{5,400}?)\s+Dear\b", t)
        rec["re_line"] = flat(m.group(1)) if m else ""
        m = re.search(r"\bDear\s+([^:]{2,60}):", t)
        rec["addressee"] = flat(m.group(1)) if m else ""
        m = re.search(r"Sincerely,?\s+([A-Z][A-Za-z.'\- ]{3,40}?)\s+"
                      r"((?:Acting\s+|Associate\s+|Deputy\s+)?General Counsel)", t)
        rec["signer"] = flat(m.group(1)) if m else ""
        rec["signer_title"] = flat(m.group(2)) if m else ""

        # ---- agreement typology
        hay = " ".join([rec["re_line"], t[:6000]]).lower()
        types, bases = [], []
        for label, pat in AGREEMENT_TYPES:
            mm = re.search(pat, hay, re.I)
            if mm:
                types.append(label)
                bases.append(f"{label}<-'{mm.group(0)}'")
        rec["agreement_type"] = "|".join(types)
        rec["agreement_type_basis"] = "; ".join(bases)[:600]

        am = RE_AMEND_NUM.search(t) or RE_AMEND_ORD.search(t)
        if am:
            g = am.group(1)
            rec["amendment_number"] = str(ORD.get(g.lower(), g))
            rec["amendment_quote"] = flat(am.group(0))
        else:
            rec["amendment_number"] = ""
            rec["amendment_quote"] = ""

        rec["prior_financing_reference"] = first(RE_PRIOR, t)
        lin = []
        if rec["amendment_number"] or re.search(r"\bamendment\b", t, re.I):
            lin.append("AMENDS")
        if RE_RESTATE.search(t):
            lin.append("RESTATES")
        if RE_REFI.search(t):
            lin.append("REFINANCES")
        if RE_EXTEND.search(t):
            lin.append("EXTENDS")
        if RE_SUPERSEDE.search(t):
            lin.append("SUPERSEDES")
        rec["lineage_relations_in_text"] = "|".join(lin)

        # NIGC's own evidentiary limit, carried on every row.
        rec["evidence_meaning"] = (
            "NIGC OGC reviewed the SUBMITTED, UNEXECUTED documents named in this "
            "letter and reached the legal conclusion recorded here. This is NOT "
            "evidence that the transaction closed, that any agreement was "
            "executed, that a property opened or operates, or that land is in "
            "trust or gaming-eligible. NIGC states the review is voluntary and "
            "that it will not opine on executed documents.")
        rec["absence_meaning"] = (
            "NIGC review is voluntary and posting is subject to a FOIA release "
            "review, so this archive is not a census of tribal gaming "
            "agreements. A property or tribe with no letter is not a property "
            "or tribe with no financing.")
        rec["built_date"] = TODAY
        letters.append(rec)

        # ================================================== claims
        def page_of(quote):
            if not quote:
                return ""
            k = flat(quote)[:60]
            for i, pg in enumerate(pages, 1):
                if k and k in flat(pg):
                    return str(i)
            return ""

        def add_claim(subject, predicate, obj, quote, conf, note="",
                      tidy_object=True):
            nonlocal claim_seq
            subject = tidy_party(subject)
            obj = (tidy_party(obj) if tidy_object else flat(obj)) if obj else ""
            if not subject or len(subject) < 3 or not quote:
                return
            if norm(subject) in STOP_PROPERTY or (obj and norm(obj) in STOP_PROPERTY):
                return
            claim_seq += 1
            sid, sname, show = resolve(subject)
            oid_e, oname, ohow = ((resolve(obj) if (obj and tidy_object)
                                   else (None, None, "")))
            if not sid:
                held.append({"cedar_opinion_id": oid, "name": subject,
                             "role": f"claim_subject:{predicate}", "reason": show,
                             "source_url": row["wpdm_url"], "YOUR_RULING": ""})
            if obj and tidy_object and not oid_e:
                held.append({"cedar_opinion_id": oid, "name": obj,
                             "role": f"claim_object:{predicate}", "reason": ohow,
                             "source_url": row["wpdm_url"], "YOUR_RULING": ""})
            claims.append({
                "source_claim_id": f"NIGCDL-CLM-{claim_seq:05d}",
                "source_record_id": oid,
                "source_type": "nigc_ogc_declination_letter",
                "subject_entity_id": sid or party_id(subject),
                "subject_value": subject,
                "subject_entity_resolved": 1 if sid else 0,
                "subject_resolve_how": show,
                "predicate": predicate,
                "object_entity_id": (oid_e or (party_id(obj) if obj else "")),
                "object_entity_resolved": 1 if oid_e else 0,
                "object_value": obj,
                "claim_date": row["index_date"],
                "effective_date": "",
                "effective_date_basis": (
                    "NOT CLAIMED. A declination letter dates the OPINION, not the "
                    "transaction. The documents reviewed are unexecuted, so no "
                    "effective date is established by this source."),
                "source_page": page_of(quote),
                "supporting_text": flat(quote),
                "confidence": conf,
                "verification_status": (
                    "NIGC_DOCUMENT_QUOTED_ENTITY_RESOLVED" if sid
                    else "NIGC_DOCUMENT_QUOTED_ENTITY_HELD"),
                "claim_note": note,
                "source_url": row["wpdm_url"],
                "fetched_date": FETCHED,
                "built_date": TODAY,
            })

        # Claims are read SENTENCE BY SENTENCE. Running the patterns over the
        # whole letter let a capture span a sentence boundary and produced
        # subjects like "March 6, 2026 request, on behalf of Twenty-Nine Palms
        # Enterprises Corporation". A sentence is the natural bound.
        sents = sentences(t) if rec["text_layer_quality"] != "no_text_layer" else []
        seen_role = set()
        for sent in sents:
            t = sent
            for mm in RE_WHOLLY.finditer(t):
                add_claim(mm.group(1), "wholly_owned_by", mm.group(3),
                          mm.group(0), "high",
                          f"legal form stated: wholly owned {mm.group(2).lower()}")
            for mm in RE_INSTRUMENTALITY.finditer(t):
                add_claim(mm.group(1), "instrumentality_of", mm.group(3),
                          mm.group(0), "high",
                          "an instrumentality is NOT a wholly owned subsidiary; "
                          "the distinct predicate preserves the legal form the "
                          "letter states")
            for mm in RE_SUBSIDIARY.finditer(t):
                add_claim(mm.group(1), "subsidiary_of", mm.group(3),
                          mm.group(0), "high",
                          f"legal form stated: {mm.group(2).lower()}")
            for mm in RE_WHOLLY_BY.finditer(t):
                add_claim(mm.group(1), "wholly_owned_by", mm.group(2),
                          mm.group(0), "high",
                          "the letter states the ownership in words: "
                          "'wholly owned by'")
            for mm in RE_WHOLLY_ARM.finditer(t):
                add_claim(mm.group(1), "wholly_owned_by", mm.group(3),
                          mm.group(0), "high",
                          f"legal form stated: wholly owned {mm.group(2).lower()}")
            for mm in RE_OWNED_OPERATED_BY.finditer(t):
                add_claim(mm.group(1), "operated_by", mm.group(2), mm.group(0),
                          "high", "operation stated in the letter")
            for mm in RE_OPERATES.finditer(t):
                add_claim(mm.group(2), "operated_by", mm.group(1), mm.group(0),
                          "medium",
                          "the named property is operated by the subject per the "
                          "letter; the property is NOT thereby matched to a "
                          "Cedar facility")
            for mm in RE_VENDOR.finditer(t):
                add_claim(mm.group(1), "vendor_to", mm.group(2), mm.group(0),
                          "medium",
                          "the letter describes the subject supplying goods or "
                          "services to the object under the reviewed agreement")
            if RE_COLLATERAL_SENT.search(t) and not RE_COLLATERAL_REGULATORY.search(t):
                for pm in RE_PROPERTY.finditer(t):
                    pn = tidy_party(pm.group(1))
                    if len(pn) < 6 or norm(pn) in STOP_PROPERTY:
                        continue
                    if len(norm(pn).split()) < 2:
                        continue
                    add_claim(pn, "collateral_for", row["index_tribe"], t,
                              "medium",
                              "the property is named in a sentence about "
                              "collateral, pledge, mortgage or security; this "
                              "does NOT establish that this property, and only "
                              "this property, secures the financing")
            # Parties NAMED in the documents NIGC reviewed. This predicate makes
            # no ownership, service or transaction claim - it records only that
            # the party appears as a party to the submitted documents, which is
            # exactly what this archive can establish and often the only public
            # source that does.
            # Only from a sentence short enough to BE a sentence and naming an
            # agreement. The address block extracts as one long pseudo-sentence
            # and produced parties that are really addressees.
            agree_sent = (len(t) < 400 and re.search(
                r"\b(?:Agreement|Note|Indenture|Lease|Guaranty|Mortgage|"
                r"Contract|Documents)\b", t))
            for mm in (RE_BETWEEN.finditer(t) if agree_sent else []):
                for part in re.split(r"\s+and\s+|,\s+", mm.group(1)):
                    nm = tidy_party(part)
                    if not nm or len(nm.split()) < 2:
                        continue
                    if (norm(nm), "party") in seen_role:
                        continue
                    seen_role.add((norm(nm), "party"))
                    add_claim(nm, "party_to_reviewed_agreement",
                              rec["re_line"] or row["index_company"],
                              t, "medium",
                              "named as a party to the documents submitted for "
                              "NIGC review; NOT evidence the documents were "
                              "executed", tidy_object=False)
            for mm in RE_AS_ROLE.finditer(t):
                nm, role = tidy_party(mm.group(1)), mm.group(2).lower()
                pred = ROLE_TO_PREDICATE.get(role)
                if not pred or (norm(nm), pred) in seen_role:
                    continue
                seen_role.add((norm(nm), pred))
                add_claim(nm, pred, "", mm.group(0), "high",
                          f"role defined in the reviewed documents: {role}")
            for mm in RE_DEFTERM.finditer(t):
                nm, term = tidy_party(mm.group(1)), mm.group(2).strip().lower()
                pred = ROLE_TO_PREDICATE.get(term)
                if not pred or (norm(nm), pred) in seen_role:
                    continue
                seen_role.add((norm(nm), pred))
                add_claim(nm, pred, "", mm.group(0), "high",
                          f'defined term in the reviewed documents: "{term}"')
        t = flat(raw)          # restore; the loop above rebinds it per sentence

        # ================================================== financing event
        is_fin = any(x in rec["agreement_type"] for x in (
            "loan_or_credit_agreement", "note_indenture_or_bond",
            "security_or_collateral_agreement"))
        if is_fin:
            def parties(pred):
                return " | ".join(sorted({c["subject_value"] for c in claims
                                          if c["source_record_id"] == oid
                                          and c["predicate"] == pred}))
            fin_events.append({
                "financing_event_id": f"NIGCDL-FIN-{oid}",
                "cedar_opinion_id": oid,
                "opinion_date": row["index_date"],
                "tribe_entity_id": rec["tribe_entity_id"],
                "tribe_canonical_name": rec["tribe_canonical_name"],
                "index_tribe_string": row["index_tribe"],
                "index_company_string": row["index_company"],
                "re_line": rec["re_line"],
                "agreement_type": rec["agreement_type"],
                "borrower": parties("borrower_in"),
                "lender": parties("lender_in"),
                "administrative_agent": parties("administrative_agent_for"),
                "collateral_agent": parties("collateral_agent_for"),
                "trustee": parties("trustee_for"),
                "guarantor": parties("guarantor_of"),
                "developer": parties("developer_of"),
                "collateral_properties": "",     # filled after property matching
                "amendment_number": rec["amendment_number"],
                "amendment_quote": rec["amendment_quote"],
                "prior_financing_reference": rec["prior_financing_reference"],
                "lineage_relations_in_text": rec["lineage_relations_in_text"],
                "lineage_related_opinion_ids": "",
                "lineage_basis": "",
                "principal_amount_usd": "",
                "principal_amount_basis": (
                    "NOT EXTRACTED. Loan amounts appear in the reviewed drafts, "
                    "not reliably in the opinion letter, and the drafts are "
                    "unexecuted. No dollar figure is claimed from this source."),
                "execution_status": "UNEXECUTED_DRAFTS_REVIEWED",
                "execution_status_basis": rec["documents_unexecuted_quote"] or (
                    "NIGC index page: 'Documents should be submitted prior to "
                    "their execution (unsigned) as the General Counsel will not "
                    "provide a declination letter for executed documents.'"),
                "source_url": row["wpdm_url"],
                "pdf_path": rec["pdf_path"],
                "fetched_date": FETCHED,
                "built_date": TODAY,
            })

        # ================================================== property matching
        if rec["text_layer_quality"] != "no_text_layer":
            cands = {}
            for mm in RE_PROPERTY.finditer(flat(raw)):
                nm = tidy_party(mm.group(1))
                if len(nm) < 6 or norm(nm) in STOP_PROPERTY:
                    continue
                if len(norm(nm).split()) < 2:
                    continue
                ctx = flat(raw)[max(0, mm.start() - 180): mm.end() + 180]
                cands.setdefault(norm(nm), (nm, ctx))
            for key, (nm, ctx) in sorted(cands.items()):
                # "the Tribal Casino", "the Tribe's Casino", "Operator's
                # Casino" are how a letter refers to a property it has already
                # named; they are not property names and creating a property
                # from one is precisely the containment-defect failure mode in
                # a different guise.
                head = key.split()[0]
                if head in ("tribal", "tribe", "tribes", "operator",
                            "operators", "company", "facility", "gaming",
                            "existing", "new", "current"):
                    continue
                if re.search(r"manager|statement|department|division",
                             nm, re.I):
                    continue
                hits = fac_by_name.get(key, [])
                # tribe / state agreement is REQUIRED. Never match on name alone.
                same_tribe = [f for f in hits
                              if rec["tribe_entity_id"]
                              and f.get("tribe_id") == rec["tribe_entity_id"]]
                outcome, matched, basis = "", "", ""
                if same_tribe:
                    f = same_tribe[0]
                    outcome = ("EXISTING_PROPERTY_CONFIRMED"
                               if norm(f.get("facility_name", "")) == key
                               else "EXISTING_PROPERTY_ALIAS_FOUND")
                    matched = f["facility_id"]
                    basis = ("exact normalised name equals the facility "
                             f"{'name' if outcome.endswith('CONFIRMED') else 'operating-company alias'}"
                             " AND the letter's tribe resolves to that facility's tribe")
                elif hits and not rec["tribe_entity_id"]:
                    outcome = "UNRESOLVED_PROPERTY_REFERENCE"
                    basis = ("name matches a Cedar facility but the letter's tribe "
                             "did not resolve, so the tribe agreement required by "
                             "this build could not be tested")
                elif hits:
                    outcome = "UNRESOLVED_PROPERTY_REFERENCE"
                    basis = ("name matches a Cedar facility belonging to a DIFFERENT "
                             "tribe; refused rather than matched")
                elif ENTERPRISE_WORDS.search(nm):
                    outcome = "GAMING_ENTERPRISE_ONLY"
                    basis = "the name is an authority/enterprise/commission, not a property"
                elif NON_GAMING_WORDS.search(nm) or NON_GAMING_WORDS.search(ctx[:200]):
                    outcome = "NON_GAMING_RELATED_ASSET"
                    basis = "surrounding language describes a non-gaming asset"
                elif PROPOSED_WORDS.search(ctx):
                    outcome = "PROPOSED_PROPERTY"
                    basis = "surrounding language describes a proposed or future project"
                elif rec["tribe_entity_id"] and fac_by_tribe.get(
                        rec["tribe_entity_id"]):
                    # The tribe HAS properties in Cedar and none carries this
                    # exact name. That is far more likely an alias of one of
                    # them than a property Cedar has never heard of - "Sky City
                    # Casino" against "Sky City Casino Hotel". Fuzzy matching is
                    # forbidden here, so the row goes to a human with the
                    # tribe's own facility list attached, which is a one-glance
                    # ruling.
                    outcome = "UNRESOLVED_PROPERTY_REFERENCE"
                    basis = ("no exact name match, but this tribe has "
                             f"{len(fac_by_tribe[rec['tribe_entity_id']])} "
                             "Cedar facilities; likely an alias of one of them. "
                             "Not resolved here - fuzzy property matching is "
                             "forbidden by the containment defect.")
                elif rec["tribe_entity_id"]:
                    outcome = "POTENTIAL_NEW_PROPERTY"
                    basis = ("reads as a property name, the letter's tribe "
                             "resolves, and that tribe has NO facility in "
                             "gaming_facilities.csv at all")
                else:
                    outcome = "UNRESOLVED_PROPERTY_REFERENCE"
                    basis = "no Cedar facility match and the letter's tribe did not resolve"
                prop_rows.append({
                    "cedar_opinion_id": oid,
                    "opinion_date": row["index_date"],
                    "property_name_in_letter": nm,
                    "match_outcome": outcome,
                    "matched_facility_id": matched,
                    "matched_facility_name": (same_tribe[0]["facility_name"]
                                              if same_tribe else ""),
                    "match_basis": basis,
                    "tribe_entity_id": rec["tribe_entity_id"],
                    "tribe_canonical_name": rec["tribe_canonical_name"],
                    "index_tribe_string": row["index_tribe"],
                    "n_cedar_name_hits": len(hits),
                    "tribe_facilities_in_cedar": " | ".join(
                        sorted({f"{f['facility_id']}:{f['facility_name']}"
                                for f in fac_by_tribe.get(
                                    rec["tribe_entity_id"], [])})[:12]),
                    "context_quote": flat(ctx),
                    "attachment_caution": (
                        "A financing may cover several properties, the whole "
                        "enterprise, unrestricted assets or future projects. This "
                        "row does NOT assert the letter is about this property "
                        "alone, and a property is never attached to a letter "
                        "merely because the tribal enterprise owns it."),
                    "source_url": row["wpdm_url"],
                    "YOUR_RULING": "",
                    "built_date": TODAY,
                })

    # ------------------------------------------------ collateral properties
    conf_props = defaultdict(list)
    for p in prop_rows:
        if p["match_outcome"] in ("EXISTING_PROPERTY_CONFIRMED",
                                  "EXISTING_PROPERTY_ALIAS_FOUND"):
            conf_props[p["cedar_opinion_id"]].append(
                f"{p['matched_facility_id']}:{p['property_name_in_letter']}")
    for e in fin_events:
        e["collateral_properties"] = " | ".join(
            sorted(set(conf_props.get(e["cedar_opinion_id"], []))))
        e["collateral_properties_basis"] = (
            "Properties NAMED in the letter and matched to a Cedar facility on "
            "exact name plus tribe agreement. This is not a statement that these "
            "properties, and only these, secure the financing."
            if e["collateral_properties"] else
            "No property in this letter met the exact-name-plus-tribe test. "
            "Absence here is a matching outcome, not a statement about collateral.")

    # ------------------------------------------------ transaction lineage
    # One long-running financing relationship must not be counted as several
    # unrelated deals. Chain letters that share a tribe AND a counterparty
    # string; that is a CANDIDATE chain, and it is labelled as one.
    # Grouping on the whole counterparty string under-detects badly: NIGC's own
    # index writes the same lender as "PNC" on one row and "PNC Bank" on
    # another. Group instead on (tribe, any SIGNIFICANT token of the
    # counterparty string), unioning groups that share an event, and drop the
    # tokens that are generic across the whole banking industry - otherwise
    # "First Guaranty Bank" and "First National Bank of Santa Fe" merge on
    # "first" and two unrelated tribes' financings become one deal.
    GENERIC_CP = {"bank", "banks", "national", "association", "capital", "llc",
                  "inc", "incorporated", "the", "of", "and", "na", "n", "a",
                  "lp", "first", "trust", "company", "co", "corp", "group",
                  "financial", "gaming", "corporation", "usa", "us", "u", "s",
                  "holdings", "partners", "fund", "lender", "lenders"}
    tok_groups = defaultdict(list)
    for e in fin_events:
        tribe = e["tribe_entity_id"] or e["index_tribe_string"]
        for tk in set(norm(e["index_company_string"]).split()) - GENERIC_CP:
            if len(tk) > 2:
                tok_groups[(tribe, tk)].append(e["financing_event_id"])
    parent = {e["financing_event_id"]: e["financing_event_id"] for e in fin_events}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for members in tok_groups.values():
        for m in members[1:]:
            parent[find(m)] = find(members[0])
    fin_by_id = {e["financing_event_id"]: e for e in fin_events}
    chains = defaultdict(list)
    for e in fin_events:
        chains[find(e["financing_event_id"])].append(e)
    for k, group in chains.items():
        if len(group) < 2:
            continue
        group.sort(key=lambda x: x["opinion_date"])
        for i, e in enumerate(group):
            others = [g["cedar_opinion_id"] for g in group
                      if g is not e]
            e["lineage_related_opinion_ids"] = "|".join(others)
            rel = e["lineage_relations_in_text"] or "FINANCING_FOR"
            e["lineage_relation"] = rel.split("|")[0]
            e["lineage_basis"] = (
                f"POSSIBLE_SAME_TRANSACTION: {len(group)} letters share this "
                f"tribe and the counterparty string "
                f"'{e['index_company_string']}' ({group[0]['opinion_date']} .. "
                f"{group[-1]['opinion_date']}). Treat as ONE financing "
                f"relationship unless ruled otherwise; counting them as "
                f"separate deals double-counts.")
    for e in fin_events:
        e.setdefault("lineage_relation", "")
        if not e["lineage_basis"]:
            e["lineage_basis"] = ("single letter for this tribe-counterparty pair "
                                  "in this archive")

    # ------------------------------------------------ deals-ledger comparison
    # THE TRUTH: data/clean/deals_classified.csv (cedar_domain.DEALS_TRUTH).
    # Assembled the parts by hand until 2026-08-26. The parts union to 936
    # Deal_IDs against the promoted table's 935 because they do not honour
    # `review/deals_withdrawn_duplicates.csv`, and they carry none of the
    # classification or `native_party_*` attribution columns that make this
    # comparison keyable. See `cedar_domain.PROMOTED_TABLES`.
    deal_rows = []
    for d in read_csv(CEDAR / DOM.DEALS_TRUTH):
        d["_src"] = Path(DOM.DEALS_TRUTH).name
        deal_rows.append(d)

    # index letters by resolved tribe and by counterparty token
    letters_by_tribe = defaultdict(list)
    for L in letters:
        if L["tribe_entity_id"]:
            letters_by_tribe[L["tribe_entity_id"]].append(L)

    MANAGER_WORDS = re.compile(
        r"casino manag\w+|manages the casino|management (?:company|agreement|"
        r"contract) for|will manage the", re.I)

    cmp_rows = []
    for d in deal_rows:
        party = d.get("Native_Party", "")
        if not party:
            continue
        # A ledger Native_Party is a tribe, so it gets the TRIBE guard, not the
        # party guard - otherwise every containment-resolved tribe drops out of
        # the comparison and the ledger looks unrelated to the archive.
        tid, cname, how = resolve(party, mode="tribe")
        cands = letters_by_tribe.get(tid or "", [])
        if not cands:
            continue
        cp = norm(d.get("Counterparty_or_Funder", ""))
        text_blob = " ".join([d.get("Deal_Title", ""), d.get("Description", ""),
                              d.get("Notes", "")])
        for L in cands:
            comp = norm(L["index_company_string"])
            shared = bool(comp) and bool(cp) and (
                set(comp.split()) & set(cp.split()) - {"bank", "capital", "llc",
                                                       "inc", "national",
                                                       "association", "the",
                                                       "of", "and", "lp", "na"})
            if not shared:
                continue
            outcome = "POSSIBLE_SAME_TRANSACTION"
            note = ("counterparty token overlap plus the same resolved tribe; "
                    "not a confirmed identity")
            cand, assess = 0, ""
            # A CONTRADICTED ruling is the most valuable thing this layer can
            # produce and therefore the one it must be most careful about. The
            # detector below finds CANDIDATES; it cannot rule them, because
            # CONTRADICTED requires that the ledger row and the letter describe
            # THE SAME arrangement, and neither name overlap nor date proximity
            # can establish that.
            #
            # The single candidate this build found demonstrates the point.
            # ND-2013-003 records Shingle Springs paying $57.1M to end the Red
            # Hawk Casino MANAGEMENT AGREEMENT with Lakes Entertainment, and
            # NIGC-DL-20130801-01 finds the Tribe's amended agreement with Lakes
            # KAR-Shingle Springs is NOT a management contract. Those are
            # consistent, not contradictory: the letter is about the AMENDED
            # agreement that replaced the management contract, and it is dated
            # four weeks BEFORE the payoff. Publishing it as CONTRADICTED would
            # have been a false and very quotable claim.
            if MANAGER_WORDS.search(text_blob) and \
                    L["is_management_contract"] == "NO_NOT_A_MANAGEMENT_CONTRACT":
                cand = 1
                assess = (
                    "CANDIDATE ONLY. The ledger row describes the counterparty "
                    "in management terms while NIGC OGC found the reviewed "
                    "arrangement is NOT a management contract requiring Chair "
                    "approval. Before this can be ruled CONTRADICTED it must be "
                    "shown that both describe the SAME agreement - a tribe can "
                    "have had an approved management contract AND a later "
                    "amended agreement that is not one, which is the ordinary "
                    "way such relationships wind down.")
            cmp_rows.append({
                "deal_id": d.get("Deal_ID", ""),
                "deal_source_file": d["_src"],
                "deal_date": d.get("Event_Date", ""),
                "deal_title": d.get("Deal_Title", ""),
                "deal_native_party": party,
                "deal_counterparty": d.get("Counterparty_or_Funder", ""),
                "cedar_opinion_id": L["cedar_opinion_id"],
                "opinion_date": L["opinion_date"],
                "opinion_company_string": L["index_company_string"],
                "tribe_entity_id": tid or "",
                "comparison_outcome": outcome,
                "comparison_note": note,
                "contradiction_candidate": cand,
                "contradiction_assessment": assess,
                "comparison_vocabulary": (
                    "CONFIRMED_BY_NIGC_DOCUMENT | PARTIALLY_CONFIRMED | "
                    "CONSISTENT_BUT_EXECUTION_UNCONFIRMED | CONTRADICTED | "
                    "NOT_ESTABLISHED | POSSIBLE_SAME_TRANSACTION"),
                "nigc_finding": L["is_management_contract"],
                "nigc_finding_quote": L["finding_quote"],
                "source_url": L["source_url"],
                "YOUR_RULING": "",
                "built_date": TODAY,
            })

    # ------------------------------------------------ per-property traces
    trace = defaultdict(list)
    for p in prop_rows:
        if p["matched_facility_id"]:
            trace[p["matched_facility_id"]].append(p["opinion_date"])
    trace_rows = []
    for fid, dates in sorted(trace.items()):
        opinions = {p["cedar_opinion_id"] for p in prop_rows
                    if p["matched_facility_id"] == fid}
        trace_rows.append({
            "facility_id": fid,
            "trace_nigc_declination_letter": 1,
            "nigc_declination_opinion_count": len(opinions),
            "nigc_declination_first_opinion_date": min(dates),
            "nigc_declination_latest_opinion_date": max(dates),
            "nigc_declination_opinion_ids": "|".join(sorted(opinions)),
            "match_rule": ("property named in the letter, exact normalised name "
                           "equal to the facility name or operating company, AND "
                           "the letter's tribe resolves to that facility's tribe"),
            "trace_meaning": (
                "A declination letter is an independent federal trace that NIGC "
                "OGC reviewed submitted documents naming this property. It is "
                "NOT evidence the property opened, operates, or that any "
                "agreement was executed."),
            "source_dataset": "data/clean/nigc_declination_letters.csv",
            "built_date": TODAY,
        })

    # ------------------------------------------------------------- write
    print()
    write_csv(CLEAN / "nigc_declination_letters.csv", letters,
              list(letters[0].keys()) if letters else [])
    write_csv(CLEAN / "gaming_source_claims.csv", claims,
              list(claims[0].keys()) if claims else [])
    fin_fields = ["financing_event_id", "cedar_opinion_id", "opinion_date",
                  "tribe_entity_id", "tribe_canonical_name", "index_tribe_string",
                  "index_company_string", "re_line", "agreement_type", "borrower",
                  "lender", "administrative_agent", "collateral_agent", "trustee",
                  "guarantor", "developer", "collateral_properties",
                  "collateral_properties_basis", "amendment_number",
                  "amendment_quote", "prior_financing_reference",
                  "lineage_relation", "lineage_relations_in_text",
                  "lineage_related_opinion_ids", "lineage_basis",
                  "principal_amount_usd", "principal_amount_basis",
                  "execution_status", "execution_status_basis", "source_url",
                  "pdf_path", "fetched_date", "built_date"]
    write_csv(CLEAN / "gaming_financing_events.csv", fin_events, fin_fields)
    write_csv(REVIEW / f"nigc_declination_property_matches_{TODAY}.csv", prop_rows,
              list(prop_rows[0].keys()) if prop_rows else [])
    write_csv(REVIEW / f"nigc_declination_traces_{TODAY}.csv", trace_rows,
              list(trace_rows[0].keys()) if trace_rows else [])
    write_csv(REVIEW / f"nigc_declination_vs_deals_{TODAY}.csv", cmp_rows,
              list(cmp_rows[0].keys()) if cmp_rows else
              ["deal_id", "cedar_opinion_id", "comparison_outcome"])
    # ------------------------------------------------ tribe roster diff
    # docs/CROSS_SOURCE_VERIFICATION.md: a COUNT comparison says a gap exists,
    # a ROSTER diff says which row. A tribe that appears in NIGC's own
    # declination archive is a tribe NIGC OGC reviewed gaming-related documents
    # for. Where Cedar holds no gaming facility for that tribe, that is a lead.
    #
    # The ceiling travels with it: OGC review is voluntary and its archive is
    # not a gaming census, so a tribe ABSENT from these letters is not a tribe
    # without gaming or without financing.
    roster = []
    seen_t = set()
    for L in letters:
        tid = L["tribe_entity_id"]
        key = tid or ("UNRESOLVED:" + L["index_tribe_string"])
        if key in seen_t:
            continue
        seen_t.add(key)
        mine = fac_by_tribe.get(tid, []) if tid else []
        ls = [x for x in letters
              if (x["tribe_entity_id"] or "UNRESOLVED:" +
                  x["index_tribe_string"]) == key]
        roster.append({
            "tribe_entity_id": tid,
            "tribe_canonical_name": L["tribe_canonical_name"],
            "index_tribe_string": L["index_tribe_string"],
            "n_declination_letters": len(ls),
            "first_opinion_date": min(x["opinion_date"] for x in ls),
            "latest_opinion_date": max(x["opinion_date"] for x in ls),
            "n_cedar_gaming_facilities": len(mine),
            "outcome": ("MATCHED" if mine else
                        ("IN_SOURCE_NOT_IN_CEDAR" if tid else
                         "TRIBE_NOT_RESOLVED_TO_SPINE")),
            "cedar_facilities": " | ".join(
                sorted({f["facility_name"] for f in mine})[:10]),
            "ceiling_note": (
                "NIGC OGC declination review is VOLUNTARY and its published "
                "archive is subject to a FOIA release review. Absence of a "
                "tribe here is a property of that process, not evidence the "
                "tribe has no gaming or no financing."),
            "YOUR_RULING": "",
            "built_date": TODAY,
        })
    write_csv(REVIEW / f"nigc_declination_tribe_roster_diff_{TODAY}.csv",
              sorted(roster, key=lambda r: (-r["n_declination_letters"],
                                            r["index_tribe_string"])),
              list(roster[0].keys()) if roster else ["tribe_entity_id"])

    # An AFFIRMATIVE finding - "this IS a management contract", "this DOES
    # violate the sole proprietary interest requirement" - is rare and
    # consequential, and it is the finding an OCR defect produces by accident
    # when it eats a negation. Every one is staged for a human, with its quote,
    # rather than published unexamined. Same jurisprudence as the per-UEI
    # ownership drops.
    aff = [{"cedar_opinion_id": L["cedar_opinion_id"],
            "opinion_date": L["opinion_date"],
            "index_tribe_string": L["index_tribe_string"],
            "tribe_canonical_name": L["tribe_canonical_name"],
            "is_management_contract": L["is_management_contract"],
            "finding_quote": L["finding_quote"],
            "chair_approval_required": L["chair_approval_required"],
            "chair_approval_quote": L["chair_approval_quote"],
            "sole_proprietary_interest_analysis":
                L["sole_proprietary_interest_analysis"],
            "sole_proprietary_interest_quote":
                L["sole_proprietary_interest_quote"],
            "finding_is_conditional": L["finding_is_conditional"],
            "text_layer_quality": L["text_layer_quality"],
            "common_word_ratio": L["common_word_ratio"],
            "why_queued": why,
            "source_url": L["source_url"],
            "pdf_path": L["pdf_path"],
            "YOUR_RULING": ""}
           for L, why in (
               (x, "affirmative or unparsed finding - confirm against the PDF")
               for x in letters
               if x["is_management_contract"] in (
                   "YES_IS_A_MANAGEMENT_CONTRACT",
                   "STATED_BUT_DIRECTION_NOT_PARSED")
               or x["sole_proprietary_interest_analysis"] in (
                   "VIOLATION_FOUND", "STATED_BUT_DIRECTION_NOT_PARSED")
               or x["chair_approval_required"] in (
                   "YES", "STATED_BUT_DIRECTION_NOT_PARSED"))]
    write_csv(REVIEW / f"nigc_declination_affirmative_findings_{TODAY}.csv", aff,
              list(aff[0].keys()) if aff else ["cedar_opinion_id"])

    # dedupe held names
    seen, held2 = set(), []
    for h in held:
        k = (h["name"], h["role"])
        if k in seen:
            continue
        seen.add(k)
        held2.append(h)
    write_csv(REVIEW / f"nigc_declination_entities_held_{TODAY}.csv", held2,
              ["cedar_opinion_id", "name", "role", "reason", "source_url",
               "YOUR_RULING"])

    # ------------------------------------------------------------- report
    print("\n--- letters ---")
    print(f"  rows {len(letters)}  dates "
          f"{min(l['opinion_date'] for l in letters)} .. "
          f"{max(l['opinion_date'] for l in letters)}")
    for c in ("retrieval_status", "text_layer_quality", "is_management_contract",
              "chair_approval_required", "sole_proprietary_interest_analysis",
              "tribe_resolve_status"):
        print(f"  {c}: {dict(Counter(l[c] for l in letters))}")
    print(f"  material_change_warning=1: "
          f"{sum(1 for l in letters if l['material_change_warning'] == 1)}")
    print(f"  distinct tribes resolved: "
          f"{len({l['tribe_entity_id'] for l in letters if l['tribe_entity_id']})}")
    print("\n--- claims ---")
    print(f"  rows {len(claims)}")
    print(f"  predicates: {dict(Counter(c['predicate'] for c in claims))}")
    print(f"  subject resolved: "
          f"{sum(1 for c in claims if c['subject_entity_resolved'] == 1)} / {len(claims)}")
    print("\n--- financing ---")
    print(f"  events {len(fin_events)}")
    lenders = {x for e in fin_events for x in e["lender"].split(" | ") if x}
    lenders |= {e["index_company_string"] for e in fin_events
                if e["index_company_string"]}
    print(f"  distinct lender/counterparty strings: {len(lenders)}")
    print(f"  with a lineage chain: "
          f"{sum(1 for e in fin_events if e['lineage_related_opinion_ids'])}")
    print("\n--- property matching ---")
    print(f"  rows {len(prop_rows)}: "
          f"{dict(Counter(p['match_outcome'] for p in prop_rows))}")
    print(f"  facilities traced: {len(trace_rows)}")
    print("\n--- deals comparison ---")
    print(f"  rows {len(cmp_rows)}: "
          f"{dict(Counter(c['comparison_outcome'] for c in cmp_rows))}")
    print("\n--- tribe roster diff ---")
    print(f"  {len(roster)} tribes: "
          f"{dict(Counter(r['outcome'] for r in roster))}")
    print(f"\n  entities held for a ruling: {len(held2)}")
    print(f"  affirmative/unparsed findings staged: {len(aff)}")


if __name__ == "__main__":
    main()
