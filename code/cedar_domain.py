#!/usr/bin/env python3
"""
Cedar Press - shared domain vocabulary. SPEC v2, Section 13.1.

    "Every finite concept defined once and imported everywhere. No re-declared
     lists in dataset modules; no enums remapped onto identical values."

WHY THIS FILE EXISTS
--------------------
Today the same concepts are spelled differently in a dozen scripts: tiers as
"A"/"tier_A"/"confidence_tier", methods as free text, relationship types as
whatever the author typed. Every re-declaration is a place where two scripts
can silently disagree, and the project has already lost money to exactly that
class of bug.

This module is the single source. Import from it; never re-declare.

DESIGN RULES
------------
1. **Values are the strings already in the data.** This is a migration, not a
   rename. `Tier.A.value == "A"` because the ledger says "A". Changing values
   would orphan 20,559 rows to make an enum prettier.
2. **Membership is checked, never assumed.** `Tier.parse()` returns None for an
   unknown value rather than guessing, so a typo surfaces instead of silently
   becoming something plausible.
3. **Publishability is a property of the value, not of the caller.** `Tier.A`
   knows it publishes; `Tier.B` knows it does not. A serializer asks the enum.
"""

from enum import Enum

# ---------------------------------------------------------------------------
# TIER - what may be done with a record. Spec 8.1.
# ---------------------------------------------------------------------------


class Tier(str, Enum):
    """A/B/C/X as stored in `confidence_tier`."""
    A = "A"   # Publishable. Verified or human-ruled.
    B = "B"   # Visible internally and to analysis; NEVER publishes.
    C = "C"   # Unattributed. In the corpus, not linked.
    X = "X"   # Ruled out. Negative rule. Never resurfaces.

    @property
    def publishes(self) -> bool:
        return self is Tier.A

    @property
    def description(self) -> str:
        return {
            "A": "Publishable. Verified or human-ruled.",
            "B": "Visible internally; never publishes.",
            "C": "Unattributed. In the corpus, not linked.",
            "X": "Ruled out. Never resurfaces.",
        }[self.value]

    @classmethod
    def parse(cls, v):
        """None for anything unrecognised - a typo must not become a tier."""
        v = (v or "").strip().upper()
        return cls(v) if v in cls._value2member_map_ else None


# ---------------------------------------------------------------------------
# ATTRIBUTION METHOD - how the link was made, and whether a human made it.
# Values are the strings already in `attribution_method`.
# ---------------------------------------------------------------------------

# A RULING is permanent and only a new ruling reverses it (spec hard
# constraint 3). Everything else is provisional and MAY be demoted when its
# evidence is re-checked - which is why the regression guard watches
# `tier_A_ruled` and not `tier_A`.
RULED_METHODS = frozenset({
    "hand",
    "bgov_manual",
    "elijah_ruling",
    "elijah_ruling_redirect",
    "ruling",
    "web_verified",
})

# Two independent legs of evidence = Tier A. One leg = Tier B. Measured
# 2026-08-06: 49 single-leg rows were correctly demoted A -> B.
TWO_LEG_METHODS = frozenset({"agent_research_two_leg"})

ALGORITHMIC_METHODS = frozenset({
    "need_v6",              # 6.5% accurate against rulings - never publishes alone
    "cluster_v3",           # 43/44 against rulings
    "subsidiary_lookup",
    "sam_namematch_2026_05_06",
    "cross_dataset_propagation",
    "agent_research_one_leg",
    "unmatched",
})

METHOD_ACCURACY = {           # measured against Elijah's rulings
    "need_v6": 0.065,
    "cluster_v3": 0.977,
}


def is_ruling(method) -> bool:
    return (method or "").strip() in RULED_METHODS


# ---------------------------------------------------------------------------
# IDENTIFIER TYPES - spec 5.2.
# ---------------------------------------------------------------------------


class IdentifierType(str, Enum):
    UEI = "UEI"
    CAGE = "CAGE"
    EIN = "EIN"
    DUNS = "DUNS"
    SAM = "SAM"
    IRS = "IRS"
    STATE_CORP = "STATE_CORP"
    TRIBAL_CHARTER = "TRIBAL_CHARTER"
    SEC = "SEC"
    LDA_REGISTRANT = "LDA_REGISTRANT"
    LDA_CLIENT = "LDA_CLIENT"
    SOURCE_NATIVE = "SOURCE_NATIVE"
    CEDAR_INTERNAL = "CEDAR_INTERNAL"

    @property
    def is_official(self) -> bool:
        """A Cedar-generated ID is never presented as an official identifier."""
        return self is not IdentifierType.CEDAR_INTERNAL

    @property
    def licensed(self) -> bool:
        """Third-party licensed. Join on it internally; NEVER publish it."""
        return self is IdentifierType.DUNS


# Hard constraint 4: DUNS is D&B-licensed. Internal use only, suppressed from
# every published output at every tier. The publish-path serializer asserts on
# this set, so the rule is enforced by code rather than by memory.
LICENSED_IDENTIFIER_TYPES = frozenset({IdentifierType.DUNS})
LICENSED_SOURCE_FILES = frozenset({
    "gaming_property_capacity_history.csv",   # 100% Casino City panel
    "gaming_facility_metrics.csv",
})


def may_publish_identifier(identifier_type) -> bool:
    t = identifier_type if isinstance(identifier_type, IdentifierType) else None
    if t is None:
        v = (identifier_type or "").strip().upper()
        t = IdentifierType(v) if v in IdentifierType._value2member_map_ else None
    return bool(t) and not t.licensed


# ---------------------------------------------------------------------------
# RELATIONSHIP TYPES - spec 5.4. Grouped by family; never a generic related_to.
# ---------------------------------------------------------------------------

CORPORATE_RELATIONSHIPS = frozenset({
    "owned_by", "wholly_owned_by", "majority_owned_by", "controlled_by",
    "subsidiary_of", "indirect_subsidiary_of", "enterprise_of",
    "holding_company_for", "section_17_entity_of", "chartered_by",
    "instrumentality_of", "brand_of", "operating_group_of", "division_of",
    "doing_business_as", "joint_venture_of", "acquired_by",
    "formerly_owned_by",
})

GOVERNMENTAL_RELATIONSHIPS = frozenset({
    "constituent_band_of", "constituent_tribe_of", "member_government_of",
    "component_government_of", "federated_with",
    "governed_under_constitution_of", "legislative_body_of", "department_of",
    "agency_of", "authority_of", "commission_of", "program_of",
    "governmental_unit_of",
})

ALASKA_GEOGRAPHIC_RELATIONSHIPS = frozenset({
    "associated_with_village", "village_corporation_for",
    "regional_corporation_for", "serves_shareholders_from",
    "associated_with_region", "located_in_region", "serves_region",
    # Added 2026-08-26 with the ANCSA ownership ruling. These name the tie
    # BETWEEN an ANCSA corporation and the village whose people hold its
    # shares, so that a matcher has a correct edge to write instead of
    # inventing an ownership one. See ANCSA_ASSOCIATION_NOT_OWNERSHIP.
    "shares_ancestral_base_with", "shareholder_base_overlaps_with",
})

INSTITUTIONAL_RELATIONSHIPS = frozenset({
    "member_of", "membership_organization_for", "affiliated_with",
    "partner_of", "serves_native_entities", "fiscally_sponsored_by",
    "operated_by",
})

HISTORICAL_RELATIONSHIPS = frozenset({
    "formerly_known_as", "successor_to", "predecessor_of", "merged_into",
    "spun_out_of", "reorganized_as",
})

# ---------------------------------------------------------------------------
# INDIVIDUAL NATIVE OWNERSHIP - added 2026-08-26 with the individually
# Native-owned FIRM class (code/241). Exactly ONE type, and it is here rather
# than in INSTITUTIONAL_RELATIONSHIPS so that nothing can reach it by iterating
# a family that also contains ownership-bearing edges.
#
# `owner_self_identifies_with` records that the PERSON who owns a firm says
# they are of a tribe. It is:
#     * an attribute of a PERSON, never an edge of the FIRM;
#     * never keyed to a `tribe_id` - see INDIVIDUAL_NATIVE_* below;
#     * never in CORPORATE_RELATIONSHIPS and never in OWNERSHIP_BEARING;
#     * a member of NEVER_OWNERSHIP, so `bears_ownership()` refuses it.
#
# Thirty-eight of the owner's 45 individual-Native rulings read "owned by
# individual Cherokees". Writing `tribe_id = TRBF-CHRKEE-00` on those rows is
# wrong twice over: the Cherokee Nation does not own the firm, and the string
# "Cherokee" does not resolve - there are three federally recognised Cherokee
# tribes and a long tail of unrecognised groups using the name. $27.59B was
# once booked wrong on exactly this confusion between an association and an
# ownership edge.
# ---------------------------------------------------------------------------
INDIVIDUAL_NATIVE_RELATIONSHIPS = frozenset({
    "owner_self_identifies_with",     # person -> tribe. Carries NO money. Ever.
})

ALL_RELATIONSHIPS = (CORPORATE_RELATIONSHIPS | GOVERNMENTAL_RELATIONSHIPS
                     | ALASKA_GEOGRAPHIC_RELATIONSHIPS
                     | INSTITUTIONAL_RELATIONSHIPS | HISTORICAL_RELATIONSHIPS
                     | INDIVIDUAL_NATIVE_RELATIONSHIPS)

# These carry MONEY upward in a roll-up. Governmental and geographic ties do
# not: a constituent band's contracts are not the umbrella's, and an ANCSA
# region is a place, not an owner. $27.59B was booked wrong on that confusion.
OWNERSHIP_BEARING = frozenset({
    "owned_by", "wholly_owned_by", "majority_owned_by", "controlled_by",
    "subsidiary_of", "indirect_subsidiary_of", "enterprise_of",
    "holding_company_for", "section_17_entity_of", "instrumentality_of",
})

# ---------------------------------------------------------------------------
# ANCSA: SHARED SHAREHOLDERS ARE NOT AN OWNERSHIP EDGE.
# Elijah's ruling, 2026-08-26 - docs/ANCSA_OWNERSHIP_RULING.md - with his
# rule-4 correction the same day. Applied to 334 defects worth $24.52B by
# code/191_apply_ancsa_ownership_ruling.py.
#
# WHAT THE RULING SAYS
#   1. An ANCSA operating company is owned by the VILLAGE CORPORATION. That is
#      the presumption.
#   2. **A village GOVERNMENT never owns an ANC.** In either direction.
#   3. A village government CAN directly own an enterprise - and then it is
#      simply a tribal enterprise attributed to a federally recognized tribe
#      that happens to be an Alaska Native village. It is NOT an ANC. This is
#      an exception that must be EVIDENCED, never assumed.
#   4. Village corporation <-> village government is ASSOCIATION, never
#      ownership - and **the association is ANCESTRAL, not membership**.
#   5. The regional corporation relationship is SHAREHOLDING, not ownership.
#      Two separate corporations with an overlapping shareholder base.
#
# THE PRECISION THAT MATTERS, IN THE OWNER'S OWN CORRECTION
#   "Shareholders are not necessarily enrolled in the tribe, but they
#    necessarily have ancestry. Enrollment for villages has been closed for a
#    while."
#   ANCSA shares descend by inheritance and by gift; village tribal enrollment
#   closed long ago. So the ANC shareholder roll and the village government's
#   enrollment roll are **two different populations that overlap**, not two
#   views of one list. Never use one as a proxy for the other. The looser
#   phrasing - "a shared membership base" - is wrong, and it is wrong in the
#   direction that invites a matcher to treat the two rolls as one list and
#   then to treat one list as one owner.
#
# WHY IT IS ENCODED HERE RATHER THAN LEFT IN A DOC
#   The spine holds 173 Alaska Native Village Corporations against 228
#   federally recognized Alaska Native Villages, **and the two populations name
#   each other**: "Chenega" the village government and "Chenega Corporation"
#   the ANC; "Elim" and "Elim Native Corporation". Any matcher that scores on a
#   shared name plus a shared place will re-derive this defect, which is the
#   containment defect's direction-2 case already in AGENTS.md
#   ("NATIVE VILLAGE OF ELIM -> Elim Native CORPORATION"). Leaving the rule in
#   prose guarantees the next matcher rediscovers it. Two names being alike
#   here is not weak evidence of one owner - **it is no evidence at all,
#   because the names are alike BY CONSTRUCTION**: both are named for the same
#   village, by statute.
#
# The share-transfer rules bearing on who may hold shares at all - adopted
# persons, gifts to non-Natives, gifts to spouses - are an OPEN QUESTION
# recorded in the ruling doc. Nothing in this module answers them and no
# predicate here depends on an answer.
# ---------------------------------------------------------------------------

ANCSA_CORPORATION_CLASSES = frozenset({
    "Alaska Native Village Corporation",
    "Alaska Native Regional Corporation",
    "ANCSA Group Corporation",
})
ALASKA_VILLAGE_GOVERNMENT_CLASSES = frozenset({
    "Federally recognized Alaska Native Village",
})

#: Ties between an ANCSA corporation and the village whose people hold its
#: shares. Every one of these is a fact about PEOPLE and their ANCESTRY. Not
#: one of them is a fact about corporate control, and none may carry a dollar.
ANCSA_ASSOCIATION_NOT_OWNERSHIP = frozenset({
    "village_corporation_for",        # ANVC -> the village it was chartered for
    "regional_corporation_for",       # ANRC -> the region
    "associated_with_village",
    "associated_with_region",
    "located_in_region",
    "serves_region",
    "serves_shareholders_from",
    "shares_ancestral_base_with",
    "shareholder_base_overlaps_with",
})

# Association is never upgraded to ownership without evidence (spec 3).
NEVER_OWNERSHIP = frozenset({
    "associated_with_village", "associated_with_region", "located_in_region",
    "serves_region", "serves_shareholders_from", "serves_native_entities",
    "member_of", "affiliated_with", "partner_of", "operated_by",
} | GOVERNMENTAL_RELATIONSHIPS | ANCSA_ASSOCIATION_NOT_OWNERSHIP
  | INDIVIDUAL_NATIVE_RELATIONSHIPS)


def village_government_owns_an_anc(owner_class, owned_class) -> bool:
    """Rule 2. Always False, and it is a function so callers must ASK.

    Measured cost of the edge existing implicitly: 334 one-to-many defects on
    $24.52B, 3,883 individual attributions repointed on 2026-08-26.
    """
    return False


def ancsa_refusal_reason(rel, owner_class=None, owned_class=None):
    """Why this edge may not carry a dollar - or None if it may.

    Returns a sentence fit to paste into a review row, because a refusal that
    does not say why gets re-litigated by the next agent.
    """
    r = (rel or "").strip()
    if (owner_class in ALASKA_VILLAGE_GOVERNMENT_CLASSES
            and owned_class in ANCSA_CORPORATION_CLASSES):
        return ("RULE 2: a village GOVERNMENT never owns an ANC. If an "
                "attribution asserts it, the attribution is wrong. "
                "docs/ANCSA_OWNERSHIP_RULING.md, 2026-08-26.")
    if (owner_class in ANCSA_CORPORATION_CLASSES
            and owned_class in ALASKA_VILLAGE_GOVERNMENT_CLASSES):
        return ("RULE 4: an ANCSA corporation does not own the village "
                "government either. The two are ASSOCIATED because the people "
                "are - and the association is ANCESTRAL, not membership: a "
                "shareholder is not necessarily enrolled in the tribe but "
                "necessarily has ancestry. Shares descend by inheritance and "
                "gift; village enrollment closed long ago. Two overlapping "
                "populations, not one list. "
                "docs/ANCSA_OWNERSHIP_RULING.md, 2026-08-26.")
    if r in ANCSA_ASSOCIATION_NOT_OWNERSHIP:
        return (f"{r!r} is an ANCSA association edge, not a corporate "
                "ownership edge. Shared shareholders and shared ancestry are "
                "not corporate control (rules 4 and 5). A regional "
                "corporation does not own a village corporation. "
                "docs/ANCSA_OWNERSHIP_RULING.md, 2026-08-26.")
    return None


def bears_ownership(rel, owner_class=None, owned_class=None) -> bool:
    """True only where a roll-up may carry dollars through this edge.

    The two class arguments are optional and default to the pre-2026-08-26
    behaviour, so every existing caller keeps working. Pass them where the
    classes are known: they are what stops a village government and its
    village corporation - which share a name and a place BY CONSTRUCTION -
    being joined by an ownership edge in either direction.
    """
    r = (rel or "").strip()
    if ancsa_refusal_reason(r, owner_class, owned_class) is not None:
        return False
    if individual_native_refusal_reason(r, owner_class, owned_class) is not None:
        return False
    if r in NEVER_OWNERSHIP:
        return False
    return r in OWNERSHIP_BEARING


# ===========================================================================
# INDIVIDUALLY NATIVE-OWNED BUSINESS - the class, and the four rules that stop
# it corrupting tribal attribution. Owner ruling 2026-08-07 (AGENTS.md, on
# Hidden Water Inc); schema from docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md;
# encoded here 2026-08-26 by code/241_promote_individual_native_firms_in_place.py.
#
#   Elijah, 2026-08-07: "individual Native American owned - to the extent we
#   identify individual native owned businesses might as well add them as a
#   category, and if people want to be added gives them a centralized source
#   to do so."
#
# THE CLASS IS THE FIRM, NEVER THE PERSON.
# A person has no federal identifier and their name is not one. The stable key
# is the firm's UEI/CAGE or a Cedar-internal surrogate id - never a slug built
# from a name, because a mnemonic built from a person's name IS the disclosure,
# minted into the primary key of every downstream join.
#
# READ THIS BEFORE YOU READ ANY RULING IN THIS CLASS
# --------------------------------------------------
# **Five of the owner's 45 rulings read, verbatim:
#   "Not a Native entity - individually Native-owned firm".**
# That sentence refuses the TRIBAL LINK. It does NOT say the firm is not
# Native-owned - the second half of the sentence says the opposite. Read
# literally as "not Native" it inverts his meaning and deletes five firms from
# the register.
#
# It has already been read literally once, and the damage is on disk:
# `code/09_import_rulings.py`'s NOT_NATIVE_RE matched the leading clause, and
# CAGE 9DVK5 (SAN JUAN SERVICES LLC) now sits in
# `cedar_identifier_ledger_final.csv` as
#     confidence_tier  = X
#     tribe_id         = TRBF-SNJUAN-00      <- a tribe that does not own it
#     entity_class     = FEDERAL_TRIBE_LOWER48
#     tier_rationale   = "Ruled by Elijah 2026-08-12: not a Native entity"
# - the refusal recorded as its own opposite, ON a tribal binding the ruling
# was refusing. CAGE 9H8M8 is the same defect against TRBF-TEMOAK-00.
# `INDIVIDUAL_NATIVE_NOT_TRIBAL` is the ruling_class that keeps the DIRECTION
# of the refusal visible, and `is_tribal_link_refusal_not_native_refusal()`
# below is the predicate to ask instead of matching the string.
# ===========================================================================

#: The spine `entity_class` value. One string, imported, never re-typed.
INDIVIDUAL_NATIVE_CLASS = "Individually Native-owned business"

#: `ownership_basis` on every row of the class. The blank
#: `parent_native_entity` is a RULING, not unfinished research - the same
#: distinction the 56 federally operated BIE schools needed.
INDIVIDUAL_NATIVE_OWNERSHIP_BASIS = "INDIVIDUAL_NATIVE_OWNER_NOT_A_TRIBAL_ENTITY"

#: The two ruling_class values carried by `individual_native_prior_rulings.csv`.
INDIVIDUAL_NATIVE_RULING_CLASSES = frozenset({
    "INDIVIDUAL_NATIVE",
    "INDIVIDUAL_NATIVE_NOT_TRIBAL",   # "Not a Native entity - individually
                                      # Native-owned firm" - see the block above
})


def is_tribal_link_refusal_not_native_refusal(ruling_class, ruling_text="") -> bool:
    """True where a ruling refuses the TRIBAL LINK and affirms Native ownership.

    Ask this instead of matching on the words "not a Native entity". The whole
    sentence is "Not a Native entity - individually Native-owned firm"; the
    first clause read alone says the opposite of what the owner decided.
    """
    rc = (ruling_class or "").strip().upper()
    if rc in INDIVIDUAL_NATIVE_RULING_CLASSES:
        return True
    t = (ruling_text or "").lower()
    return "individually native-owned" in t or "individually native owned" in t


def individual_native_refusal_reason(rel, owner_class=None, owned_class=None):
    """Why this edge may not carry a dollar - or None if it may.

    A refusal that does not say why gets re-litigated by the next agent, so
    this returns a sentence fit to paste straight into a review row.
    """
    r = (rel or "").strip()
    if r in INDIVIDUAL_NATIVE_RELATIONSHIPS:
        return ("'owner_self_identifies_with' is a fact about a PERSON's "
                "self-stated ancestry, not an edge of the FIRM. It may never "
                "key a tribe_id and it carries no money. 38 of the owner's 45 "
                "individual-Native rulings read 'owned by individual "
                "Cherokees'; 'Cherokee' resolves to three federally recognised "
                "tribes and a long tail of unrecognised groups, so it does not "
                "resolve at all. "
                "docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md, 2026-08-26.")
    if INDIVIDUAL_NATIVE_CLASS in (owner_class, owned_class):
        return (f"{INDIVIDUAL_NATIVE_CLASS!r} is self-parented and has NO "
                f"ownership edge in either direction. It never rolls up to a "
                f"tribe, an ANC or an NHO, and no tribal total includes it - "
                f"these firms were never in one. Counting it as tribal "
                f"overstates tribal economic activity, which is the single "
                f"easiest way to discredit this dataset. "
                f"docs/INDIVIDUAL_NATIVE_CLASS_PROPOSAL.md, 2026-08-26.")
    return None


# ---------------------------------------------------------------------------
# ABSENCE VOCABULARY. There is no NOT_NATIVE value in this schema and there
# never will be one.
#
# Plenty of small contractors never mention ownership on their website. A
# budget-exhausted search session returns the same string as a completed one.
# `SITE_UNREACHABLE` is a fact about the moment; only 404 and 403 are facts
# about the object. None of those is a finding about a firm's owners, and
# Cedar Press is in no position to adjudicate anyone's Native identity.
# ---------------------------------------------------------------------------
ABSENCE_VALUES = frozenset({
    "NO_CLAIM_FOUND",     # swept the firm's own site; it says nothing either way
    "NO_SITE_FOUND",      # no site located - a CEILING on absence, not a measure
    "SITE_UNREACHABLE",   # transport/TLS/5xx - retryable, never a finding
    "NOT_CHECKED",        # nobody looked
    "UNDETERMINED",       # nobody said
})

#: Values that must never appear anywhere in this class. Each asserts a
#: negative about a private individual's ancestry that no source establishes.
FORBIDDEN_ABSENCE_VALUES = frozenset({
    "NOT_NATIVE", "NON_NATIVE", "NOT_INDIAN", "FALSE_CLAIM", "NOT_VERIFIED_NATIVE",
})


def absence_value_ok(value) -> bool:
    """False for any value that turns 'nobody said' into 'the answer is no'.

    Coerces rather than assuming a string: a guard that raises on an int is a
    guard that gets removed, and this one has to survive being pointed at every
    cell of a heterogeneous row.
    """
    v = str(value if value is not None else "").strip().upper()
    return v not in FORBIDDEN_ABSENCE_VALUES


# ---------------------------------------------------------------------------
# SELF-CERTIFICATION IS A CHANNEL, NEVER A VERDICT.
#
# It lives in its own column (`sam_self_certification`) and is never folded
# into a tier or an ownership class. Two measurements, both from the FY2000-07
# SAM extract, and they cut in OPPOSITE directions:
#
#   * `americanIndianOwned = YES` on **2,846 of 8,273 rows of the TRIBAL
#     extract** - rows that are tribal enterprises (Chugach, ASRC, Chickasaw
#     Nation Industries). The flag does NOT separate individual from entity
#     ownership. Goldbelt Raven, an ANC subsidiary, certifies
#     `alaskanNativeCorporationOwnedFirm = NO`.
#   * **$140.00B of the $244.77B attributed (57.2%) carries no Native
#     set-aside at all.** 22 of the owner's 40 prior-ruled firms carry ZERO
#     native flags across every one of their contract rows - the largest,
#     Frontier Electronic Systems, on 998 rows and $204,225,019.
#
# So the flag over-includes entities and under-includes firms simultaneously.
# **Absence of a flag is not evidence against.** Presence of one is not
# evidence for. It is a discovery channel with a documented blind spot, and a
# headline of the form "N individually Native-owned firms" built from it is a
# floor whose gap is unmeasured.
# ---------------------------------------------------------------------------
SELF_CERTIFICATION_IS_NOT_A_VERDICT = (
    "SAM socio-economic flags are the filer's own self-certification. They are "
    "recorded in `sam_self_certification` and are never a tier, a class or a "
    "leg of evidence. Measured: americanIndianOwned = YES on 2,846 of 8,273 "
    "rows of the TRIBAL extract, so the flag does not separate individual from "
    "entity ownership; and 57.2% of attributed prime dollars carry no Native "
    "set-aside at all, so its absence is not evidence against.")


# ---------------------------------------------------------------------------
# PRIVACY. A SECOND RESTRICTION, INDEPENDENT OF D&B LICENSING, THAT SURVIVES
# ANY ANSWER TO THE LICENSING QUESTION.
#
# Naming a private individual in a shipping dataset is an exposure a tribal
# government's name is not. Publishing "The Chickasaw Nation owns Chickasaw
# Nation Industries" discloses a sovereign government's commercial activity.
# Publishing a sole proprietor's legal name does three things and only the
# first is ordinary: it states contract facts; it names a private individual
# and their address; and it asserts that individual's ancestry.
#
# Measured, and not hypothetical: **even in the TRIBAL extract - the ENTITY
# class, where this was not supposed to appear - 8 of 402 distinct UEIs carry
# a legal business name that is unambiguously a person's name**, each with a
# street address in the same row.
#
# CEDAR PRESS'S OWN WRITTEN POLICY IS INHERITED HERE, NOT RESTATED:
#   `nrc_meeting_participants` - "Cedar Press names an individual only where a
#      public professional capacity is established"
#   `ferc_ex_parte_parties`    - "Cedar Press does not publish datasets about
#      private individuals."
# ---------------------------------------------------------------------------

#: Fields that publish for this class. Facts about a contract or a segment,
#: with no natural person in them.
INDIVIDUAL_NATIVE_PUBLISHABLE_FIELDS = frozenset({
    "surrogate_entity_id", "entity_class", "fiscal_year", "n_contract_rows",
    "total_obligations_usd", "naics", "psc", "funding_agency", "setaside",
    "extent_competed", "sector", "supersector", "defense",
    "evidence_tier", "evidence_grade", "ownership_class",
    "sam_self_certification", "n_firms", "value_suppressed_small_cell",
})

#: Fields that do NOT publish - in bulk OR singly - absent recorded consent.
INDIVIDUAL_NATIVE_WITHHELD_FIELDS = frozenset({
    "canonical_name", "legal_business_name", "awardee_name", "dba_name",
    "owner_name", "owner_tribal_affiliation_named",
    "street", "recipient_city_name", "place_of_perform_city",
    "self_description_sentence", "researcher_note",
    # THE CARVE-OUT. SAM's own public entity search resolves a UEI to a name
    # and an address, so for a firm whose legal name is a person's name the
    # UEI is a pointer to that person's front door: publishing it publishes
    # the name by ONE HOP. Withheld wherever firm_legal_name_is_person is
    # 1 or UNKNOWN; publishable where the firm is demonstrably incorporated.
    "awardee_uei", "cage_code",
})

#: Any published aggregate cell resolving to fewer than this many FIRMS is
#: suppressed. "Individually Native-owned firms in Wyoming, NAICS 236220,
#: FY2004 - 1 firm, $412,000" is a person's name written in another alphabet.
#: Report the suppression; never silently drop the row (the CGCC precedent).
INDIVIDUAL_NATIVE_MIN_CELL_FIRMS = 3


def may_publish_individual_native_field(field, name_is_person=None,
                                        consent_status="NOT_ASKED") -> bool:
    """Per-FIELD answer, never per-dataset. Defaults to withholding.

    `consent_status = OPTED_IN` is the ONLY thing that releases a name, and it
    must be recorded with a date and a source. **A firm's own website
    statement is our EVIDENCE, never their PERMISSION.** A firm writing "Being
    Of Cherokee Indian descent..." on its homepage has consented to that
    sentence being on its homepage. It has not consented to being enumerated,
    ranked by federal obligations, and distributed in a subscription dataset.
    Conflating the two is the fastest route from a good product to a complaint.
    """
    f = (field or "").strip()
    if f in INDIVIDUAL_NATIVE_PUBLISHABLE_FIELDS:
        return True
    if f not in INDIVIDUAL_NATIVE_WITHHELD_FIELDS:
        return False          # unknown field: withhold. Fail closed.
    if (consent_status or "").strip().upper() == "OPTED_IN":
        return True
    if f in {"awardee_uei", "cage_code"}:
        # An identifier for an incorporated firm; a pointer to a person
        # otherwise. UNKNOWN counts as a person.
        return str(name_is_person).strip().upper() in {"0", "FALSE", "NO"}
    return False


def suppress_small_cell(n_firms) -> bool:
    try:
        return int(n_firms) < INDIVIDUAL_NATIVE_MIN_CELL_FIRMS
    except (TypeError, ValueError):
        return True


# ---------------------------------------------------------------------------
# ALIAS TYPES - spec 5.3.
# ---------------------------------------------------------------------------

ALIAS_TYPES = frozenset({
    "legal", "former_legal", "common", "abbreviation", "acronym", "brand",
    "operating_name", "dba", "governmental_unit_variation", "historical",
    "translated", "source_specific", "shortened",
    "full_form_federal_filing",   # "Village of Sleetmute" for spine "Sleetmute"
    "diacritic_folded",           # Ukpeaġvik -> ukpeagvik
    "known_typo", "informal",
})

# ---------------------------------------------------------------------------
# MEASUREMENT TYPE - spec 9.4. PROJECTED never silently becomes ACTIVE.
# ---------------------------------------------------------------------------


class MeasurementType(str, Enum):
    ACTIVE_FLOOR_COUNT = "ACTIVE_FLOOR_COUNT"
    REGULATORY_REPORTED_COUNT = "REGULATORY_REPORTED_COUNT"
    AUTHORIZED_MAXIMUM = "AUTHORIZED_MAXIMUM"
    OPENING_INVENTORY = "OPENING_INVENTORY"
    COMPACT_REPORTED_COUNT = "COMPACT_REPORTED_COUNT"
    ENVIRONMENTAL_REVIEW_COUNT = "ENVIRONMENTAL_REVIEW_COUNT"
    PROPERTY_REPORTED_COUNT = "PROPERTY_REPORTED_COUNT"
    MANUFACTURER_PLACEMENT = "MANUFACTURER_PLACEMENT"
    OSHA_ESTABLISHMENT_REPORTED = "OSHA_ESTABLISHMENT_REPORTED"
    LODES_BLOCK_WORKPLACE_JOBS = "LODES_BLOCK_WORKPLACE_JOBS"
    PROJECTED = "PROJECTED"
    DERIVED_BOUND = "DERIVED_BOUND"
    # A public "find your game" listing. Measured on the operator platform that
    # serves WinStar / Riverwind / Newcastle: the same title and manufacturer is
    # listed once PER DENOMINATION, each with its own map id. A row is therefore
    # a (title x denomination x venue) SKU, not a cabinet, and the row count is
    # never a device count. Added 2026-08-12 by script 142.
    GAME_FINDER_OBSERVATION = "GAME_FINDER_OBSERVATION"
    # A DOL Form 5500 `TOT_ACTIVE_PARTCP_CNT`. A row is the number of people
    # ENROLLED IN A BENEFIT PLAN sponsored by a tribal employer in a gaming
    # NAICS, for one plan year. It is NOT a headcount and it is NOT employment:
    # it INCLUDES separated employees who still hold a balance, and it EXCLUDES
    # employees who never enrolled or who sit below the plan's age/service
    # threshold. The two errors do not cancel and their net sign is not stable -
    # measured on 13 SEC-overlapping tribe-years the ratio to full-time
    # headcount is 1.65 for the largest retirement plan and 1.19 for the largest
    # welfare plan, and 0.79 against a study's total employment. NONE of those
    # is a calibration factor; only CHANGES are usable (slope ~0.63, R2 0.86,
    # 11 pairs, 2 entities). A sponsor's several plans are NEVER summed - the
    # largest is taken - because summing counts the same people twice.
    # Added 2026-08-26 by script 156.
    FORM5500_ACTIVE_PARTICIPANTS = "FORM5500_ACTIVE_PARTICIPANTS"
    # An OSHA ITA Form 300A `annual_average_employees`, rolled from the
    # ESTABLISHMENT that filed it up to the TRIBE that owns the establishment.
    # A row is a real employer-filed headcount, which is why - unlike
    # FORM5500_ACTIVE_PARTICIPANTS - it is not barred from promotion. What it is
    # NOT is a census: electronic submission is required only above size
    # thresholds in covered industries, compliance is uneven, and the set of
    # establishments filing under one tribe CHANGES YEAR TO YEAR. So a tribe-year
    # SUM of these rows is not a consistent panel and must never be differenced
    # as though it were. An establishment absent from ITA did not file; it does
    # not have zero employees and it does not have zero injuries.
    # Added 2026-08-26 by script 157.
    OSHA_TRIBE_LEVEL_REPORTED = "OSHA_TRIBE_LEVEL_REPORTED"
    # A CAPACITY figure a property states about ITSELF, in MARKETING COPY, on
    # its own website. A row is one sentence of promotional prose containing a
    # number - "With over 1,500 slots and 40 table games" - captured verbatim
    # beside the number, with the page URL and the capture date.
    #
    # WHAT IT IS: the operator's own public assertion about its own property,
    # on a date we observed it. The operator does know its floor, which is why
    # this is `is_observed` and why it is a PRIMARY, NON-VENDOR source - the
    # thing Casino City is not. It is publishable where the vendor panel is not.
    #
    # WHAT IT IS NOT: an audited count. It is written to sell, so it carries
    # three defects a regulator's filing does not:
    #   1. PUFFERY - "over 1,500" is a floor, not a value, and the true figure
    #      may be 1,501 or 2,400. `value_is_bounded` / `bound_direction` record
    #      which, per row, from the qualifier in the sentence itself.
    #   2. ROUNDING - "2,000 slot machines" is almost never exactly 2,000.
    #   3. STALENESS WITHOUT A DATE - marketing copy is rarely re-dated when
    #      the floor changes, so `as_of_date` is the RETRIEVAL date and its
    #      precision is `observed_on_retrieval_date`, never a count date.
    # It is therefore in NEVER_PROMOTES_TO_ACTIVE. A regulator's count and a
    # website's boast are different measurements of different things and must
    # never be summed, averaged, or silently preferred one over the other.
    # A row with no verbatim `source_quote` is unusable and is refused at write.
    # Added 2026-08-26 by script 382.
    SELF_PUBLISHED_MARKETING_CLAIM = "SELF_PUBLISHED_MARKETING_CLAIM"
    # An EMPLOYMENT figure a property or its tribe states about itself in
    # marketing or "about us" copy - "we employ more than 1,200 team members",
    # "the largest employer in the county".
    #
    # It is kept SEPARATE from SELF_PUBLISHED_MARKETING_CLAIM because the
    # population it counts is undeclared in a way a slot count is not. A
    # casino's own employment sentence may mean any of: full-time only, FT+PT
    # headcount, the whole tribal enterprise portfolio rather than this one
    # property, or the tribal government plus the enterprise. The sentence
    # almost never says which, so `population_stated` records what the quote
    # actually declares and is blank on most rows - blank meaning UNDECLARED,
    # not "all employees".
    #
    # WHY IT MATTERS ANYWAY: 100% of the 10,122 facility-level `employees` rows
    # in `gaming_facility_metrics.csv` are the Casino City panel, which is
    # QA-reference-only and may never publish. Measured 2026-08-26. This type is
    # the only per-property employment evidence Cedar holds that CAN ship.
    # NEVER_PROMOTES_TO_ACTIVE for the same reason as the capacity type, and it
    # must never be differenced against OSHA_ESTABLISHMENT_REPORTED or
    # LODES_BLOCK_WORKPLACE_JOBS as though the three counted one population.
    # Added 2026-08-26 by script 382.
    SELF_PUBLISHED_EMPLOYMENT_CLAIM = "SELF_PUBLISHED_EMPLOYMENT_CLAIM"

    @property
    def is_observed(self) -> bool:
        """Did somebody count the thing, or is this a plan or a ceiling?"""
        return self in {
            MeasurementType.ACTIVE_FLOOR_COUNT,
            MeasurementType.REGULATORY_REPORTED_COUNT,
            MeasurementType.OPENING_INVENTORY,
            MeasurementType.COMPACT_REPORTED_COUNT,
            MeasurementType.PROPERTY_REPORTED_COUNT,
            MeasurementType.OSHA_ESTABLISHMENT_REPORTED,
            MeasurementType.LODES_BLOCK_WORKPLACE_JOBS,
            # Somebody counted these. A plan administrator counted enrollees and
            # an employer counted its own people - both are counts of a real
            # population on a real date, which is what `is_observed` asserts.
            # It does NOT assert that the population is "employees at a casino";
            # that is what the measurement type itself is for.
            MeasurementType.FORM5500_ACTIVE_PARTICIPANTS,
            MeasurementType.OSHA_TRIBE_LEVEL_REPORTED,
            # The operator counted its own floor and its own payroll. That is a
            # real population on a real date and it is what `is_observed`
            # asserts - it does NOT assert the figure is exact, audited, or
            # current, which is what the measurement type and the bound columns
            # are for. Added 2026-08-26 by script 382.
            MeasurementType.SELF_PUBLISHED_MARKETING_CLAIM,
            MeasurementType.SELF_PUBLISHED_EMPLOYMENT_CLAIM,
        }


# An authorised maximum is never the number operating; a projection is never a
# count. Promotion requires a NEW observation from a source that supports it -
# it is never an in-place relabel.
NEVER_PROMOTES_TO_ACTIVE = frozenset({
    MeasurementType.AUTHORIZED_MAXIMUM,
    MeasurementType.PROJECTED,
    MeasurementType.ENVIRONMENTAL_REVIEW_COUNT,
    MeasurementType.DERIVED_BOUND,
    MeasurementType.GAME_FINDER_OBSERVATION,
    # Plan enrollees are not employees. The population overlaps employment
    # without being it - separated employees with a balance are in, unenrolled
    # employees are out - so relabelling one as a headcount would invent a
    # measurement nobody made. Same shape as the rule this set already encodes:
    # an authorised maximum is never the number operating, a projection is never
    # a count, and an enrollment is never a payroll. Added 2026-08-26.
    MeasurementType.FORM5500_ACTIVE_PARTICIPANTS,
    # A REGULATOR'S COUNT AND A WEBSITE'S BOAST ARE NOT THE SAME MEASUREMENT.
    # Relabelling promotional copy as an active floor count would launder
    # puffery ("over 1,500"), rounding ("2,000 slot machines") and an undated
    # page into an audited figure, and it would do it with a correct citation -
    # which is the shape this project keeps paying for (the marginal-rate
    # inversion, the receipts-as-obligation bound). Promotion requires a NEW
    # observation from a source that supports it, never an in-place relabel.
    # Note the deliberate ASYMMETRY with PROPERTY_REPORTED_COUNT, which sits in
    # neither set: see the block below. Added 2026-08-26 by script 382.
    MeasurementType.SELF_PUBLISHED_MARKETING_CLAIM,
    MeasurementType.SELF_PUBLISHED_EMPLOYMENT_CLAIM,
})

# LATENT, FOUND 2026-08-26 BY SCRIPT 382 AND DELIBERATELY NOT CHANGED HERE.
# `PROPERTY_REPORTED_COUNT` is `is_observed` and is NOT in
# NEVER_PROMOTES_TO_ACTIVE, so `may_promote(PROPERTY_REPORTED_COUNT,
# ACTIVE_FLOOR_COUNT)` returns True today. Script 142 writes that type on all
# 262 rows of `gaming_property_site_observations.csv`, which are marketing
# sentences off operator websites - exactly the material the two types above
# are barred from promoting. Nothing promotes anything today (no promoter
# exists), so this is a latent hole, not a live defect, and closing it would
# change the meaning of an existing shipped column written by another build.
# The correct fix is for 142's rows to be re-typed to
# SELF_PUBLISHED_MARKETING_CLAIM by whoever owns 142, at which point
# PROPERTY_REPORTED_COUNT can go back to meaning what its name says: a count a
# property REPORTED to somebody who asked, on a stated date. Recorded here
# rather than patched silently, per the project's own rule that a defect fixed
# in one place leaves no trace in the other nine.


def may_promote(frm, to) -> bool:
    return not (frm in NEVER_PROMOTES_TO_ACTIVE
                and to is MeasurementType.ACTIVE_FLOOR_COUNT)


# ---------------------------------------------------------------------------
# REVENUE EVIDENCE HIERARCHY - spec 9.4. Ordered best to worst.
# ---------------------------------------------------------------------------

REVENUE_EVIDENCE = (
    "REPORTED_PROPERTY_REVENUE",
    "EXACT_DERIVED_PROPERTY_REVENUE",   # payment / rate, exact arithmetic
    "BOUNDED_DERIVED_REVENUE",
    "TRIBE_LEVEL_REVENUE",
    "REGIONAL_GGR_CONTEXT",
    "REGIONAL_GGR_CEILING",             # a ceiling, never an allocation
    "NO_REVENUE_OBSERVATION",           # states so explicitly; never blank
)

# ---------------------------------------------------------------------------
# INSTRUMENT FAMILIES - spec 9.1, mirroring instrument_taxonomy.csv.
# ---------------------------------------------------------------------------


class InstrumentFamily(str, Enum):
    PROCUREMENT = "PROCUREMENT"
    ASSISTANCE = "ASSISTANCE"
    CREDIT = "CREDIT"
    SELF_DETERMINATION = "SELF_DETERMINATION"

    @property
    def obligations_are_summable(self) -> bool:
        """CREDIT reports $0 obligation BY DESIGN - the money is face value
        plus subsidy cost, and a loan guarantee is not federal outlay."""
        return self is not InstrumentFamily.CREDIT


# `total_obligations` is transactional and SUMS. `total_award_value` is
# restated on every transaction of the same award and must be MAXed - summing
# it double-counts. Enforced in shared helpers, never per-analysis.
SUM_COLUMNS = frozenset({"total_obligations", "obligated_usd",
                         "subaward_amount"})
MAX_PER_AWARD_COLUMNS = frozenset({"total_award_value",
                                   "total_face_value_of_loan"})

# ---------------------------------------------------------------------------
# ADVOCACY CHANNELS - spec 9.5. Consultation is NOT lobbying.
# ---------------------------------------------------------------------------


class EventClass(str, Enum):
    """The three-way split, added 2026-08-12.

    The single biggest methodological risk in this dataset is inferring
    lobbying from PROXIMITY - concluding that because two people were in a
    building together, influence was exercised. These classes exist to make
    that inference impossible to write by accident.
    """

    #: Someone affirmatively tried to influence a government decision.
    ADVOCACY = "ADVOCACY"
    #: A government-to-government or institutional interaction. NOT lobbying.
    GOVERNMENT_ENGAGEMENT = "GOVERNMENT_ENGAGEMENT"
    #: Evidence two actors had an OPPORTUNITY to interact. Nothing more.
    ACCESS = "ACCESS"


class AdvocacyChannel(str, Enum):
    # --- ADVOCACY -------------------------------------------------------
    LDA_FILING = "LDA_FILING"
    STATE_FILING = "STATE_FILING"
    OIRA_MEETING = "OIRA_MEETING"
    CONGRESSIONAL_CORRESPONDENCE = "CONGRESSIONAL_CORRESPONDENCE"
    REGULATORY_EX_PARTE = "REGULATORY_EX_PARTE"
    ADMINISTRATIVE_COMMENT = "ADMINISTRATIVE_COMMENT"
    ADMINISTRATIVE_APPEAL = "ADMINISTRATIVE_APPEAL"
    LITIGATION_BRIEF = "LITIGATION_BRIEF"

    # --- GOVERNMENT ENGAGEMENT ------------------------------------------
    CONSULTATION = "CONSULTATION"
    SECTION_106_CONSULTATION = "SECTION_106_CONSULTATION"
    HEARING_TESTIMONY = "HEARING_TESTIMONY"
    FACA = "FACA"

    # --- ACCESS ---------------------------------------------------------
    AGENCY_CALENDAR = "AGENCY_CALENDAR"
    VISITOR_RECORD = "VISITOR_RECORD"
    SPONSORED_TRAVEL = "SPONSORED_TRAVEL"

    @property
    def event_class(self) -> "EventClass":
        if self in _ACCESS_CHANNELS:
            return EventClass.ACCESS
        if self in _ENGAGEMENT_CHANNELS:
            return EventClass.GOVERNMENT_ENGAGEMENT
        return EventClass.ADVOCACY

    @property
    def is_lobbying(self) -> bool:
        """Tribal consultation is a statutory government-to-government
        obligation. Filing it under lobbying would characterise a sovereign
        relationship as influence-buying.

        NOTE this is NARROWER than EventClass.ADVOCACY. An administrative
        comment or an amicus brief is advocacy but is not LOBBYING, and calling
        it lobbying would be wrong in a way that matters legally.
        """
        return self in {AdvocacyChannel.LDA_FILING,
                        AdvocacyChannel.STATE_FILING}


_ACCESS_CHANNELS = frozenset({
    AdvocacyChannel.AGENCY_CALENDAR,
    AdvocacyChannel.VISITOR_RECORD,
    AdvocacyChannel.SPONSORED_TRAVEL,
})
_ENGAGEMENT_CHANNELS = frozenset({
    AdvocacyChannel.CONSULTATION,
    AdvocacyChannel.SECTION_106_CONSULTATION,
    AdvocacyChannel.HEARING_TESTIMONY,
    AdvocacyChannel.FACA,
})


def may_promote_event_class(frm: EventClass, to: EventClass) -> bool:
    """An ACCESS event NEVER becomes an ADVOCACY event.

    Same shape as the measurement rule that AUTHORIZED_MAXIMUM never becomes
    ACTIVE_FLOOR_COUNT, and for the same reason: the two are different facts,
    and the weaker one looks like the stronger one once the type is lost.

    A visitor log says a person entered a building. It does not say a meeting
    happened, that it concerned the matter we care about, or that anyone was
    influenced. Corroboration by a SEPARATE source of the stronger class is
    what upgrades the claim - and then the stronger source is the evidence,
    not the access record.
    """
    if frm == to:
        return True
    return False


# ---------------------------------------------------------------------------
# NAME TRAPS - spec 7.3. A hit on one of these NEVER links on its own.
# Every term here cost a real misattribution.
# ---------------------------------------------------------------------------

NAME_TRAPS = frozenset({
    # the original list
    "creek", "cherokee", "colorado", "ojibwe", "shawnee", "oneida", "apache",
    "central", "eagle", "river", "mountain", "santa",
    # added 2026-08-06/07 from measured failures
    "indian",      # may mean India - "Indian Aerospace, Inc."
    "united", "san", "little",     # United Tribes Technical College -> United Auburn
    "rancheria",   # generic term for California tribal land
    "minnesota", "three", "wind", "bristol",   # brand-match false positives
    "advantage", "alliance", "pacific", "summit", "frontier",
    # added 2026-08-12: a tribe name that is also a US place name. Measured on
    # the review page - "Boys & Girls Clubs of Wichita Falls" matched the
    # Wichita Tribe at 85%. Wichita Falls is a city in Texas.
    "wichita", "cheyenne", "omaha", "peoria", "miami", "wyandotte", "kiowa",
    "seminole", "pontiac", "tacoma", "yuma", "modoc", "ottawa",
    # added 2026-08-12 by code/140_build_grantmaker_funding_flows.py. Each
    # count is the number of organisations in the FULL IRS EO BMF (1,957,340
    # rows, data/raw/external/irs990/bmf_full_2026-08-12/) whose name contains
    # the word. A single one of them is the organisation being looked for.
    "mason",      # 697 - Mason City, Mason County, George Mason Bank
    "bradley",    # 262 - BRADLEY UNIVERSITY (Peoria IL); 31 other "Bradley Foundation"
    "spencer",    # 261 - Spencer, IA/WV/MA; Spencer Foundation (a different funder)
    "hoover",     # 127 - HOOVER-FOSTER RAC (Oakland); Herbert Hoover Presidential Fdn
    "stanford",   # 105 - Stanford Health Care; Stanford CT; Stanford KY
    "kirby",      #  74 - A P Kirby Foundation is NOT F M Kirby Foundation
    "koch",       #  52 - KOCH FOUNDATION INC (Evansville IN) is a Catholic funder
    "templeton",  #  51 - Templeton MA/CA/IA; Franklin Templeton
    "cato",       #  17 - Cato NY
    "coors",      #   7 - Coors Western Art Exhibit and other Coors-named orgs
    "scaife",     #   6 - SCAIFE FAMILY FOUNDATION is a DIFFERENT foundation
    "goldwater",  #   5 - Goldwater Memorial Hospital NYC; Barry Goldwater HS
})

# A tribe name followed by one of these is a PLACE, not the tribe. Fires only
# on the containment path, where a single shared token carries the whole match.
PLACE_SUFFIXES = frozenset({
    "falls", "city", "county", "springs", "heights", "valley", "park",
    "beach", "ridge", "lake", "lakes", "river", "hills", "junction",
    "township", "borough", "village", "plains", "bay", "harbor", "island",
})

# Fire before any sweep match involving these names (spec 5.9).
STANDING_DISAMBIGUATIONS = (
    ("Oneida Nation (NY)", "Oneida Nation (WI)",
     "Two distinct federally recognised nations."),
    ("Shoshone-Paiute Tribes (Duck Valley)", "Paiute-Shoshone (Fallon)",
     "Word order is the only difference; different tribes."),
)



# ---------------------------------------------------------------------------
# SINGLE-PROPERTY ATTRIBUTION - Elijah, 2026-08-07:
#   "if we know how many properties a tribe has and they only have 1, we would
#    be able to say it's the property level right? of course we can add a note
#    about it that it's still an assumption"
#
# Correct, and it is worth a lot: 128 of 261 gaming tribes (49%) operate exactly
# ONE open property. For those, a tribe-level GAMING revenue figure and the
# property's gaming revenue are the same number.
#
# It is an INFERENCE, not an observation, and the three ways it breaks are all
# checkable BEFORE it is applied:
#
#   1. The base must be GAMING revenue. A whole-tribe revenue figure includes
#      non-gaming enterprises - fuel, retail, government receipts - and is not
#      the casino's.
#   2. Our property count must be complete FOR THAT TRIBE. A property we never
#      captured makes a one-property tribe look single when it is not. Check
#      the NIGC roster diff before trusting a count.
#   3. The period must have exactly one property OPEN. A tribe that opened its
#      second casino mid-series is single-property only up to that date.
#
# So it produces its own measurement status, never a silent upgrade to
# REPORTED_PROPERTY_REVENUE, and every row states the assumption.
# ---------------------------------------------------------------------------

SINGLE_PROPERTY_ATTRIBUTED = "SINGLE_PROPERTY_ATTRIBUTED"

SINGLE_PROPERTY_NOTE = (
    "Attributed to this property because the tribe operated exactly one gaming "
    "property in this period. The source reports at tribe level; the "
    "property-level reading is an inference from the property count, not a "
    "figure the source states."
)


def may_attribute_to_single_property(n_open_properties, base_is_gaming_revenue,
                                     property_count_verified):
    """All three must hold. Any one false and the row stays tribe-level."""
    return bool(n_open_properties == 1
                and base_is_gaming_revenue
                and property_count_verified)

__all__ = [
    "Tier", "IdentifierType", "MeasurementType", "InstrumentFamily",
    "AdvocacyChannel", "RULED_METHODS", "TWO_LEG_METHODS",
    "ALGORITHMIC_METHODS", "METHOD_ACCURACY", "is_ruling",
    "LICENSED_IDENTIFIER_TYPES", "LICENSED_SOURCE_FILES",
    "may_publish_identifier", "CORPORATE_RELATIONSHIPS",
    "GOVERNMENTAL_RELATIONSHIPS", "ALASKA_GEOGRAPHIC_RELATIONSHIPS",
    "INSTITUTIONAL_RELATIONSHIPS", "HISTORICAL_RELATIONSHIPS",
    "ALL_RELATIONSHIPS", "OWNERSHIP_BEARING", "NEVER_OWNERSHIP",
    "ANCSA_ASSOCIATION_NOT_OWNERSHIP", "ANCSA_CORPORATION_CLASSES",
    "ALASKA_VILLAGE_GOVERNMENT_CLASSES", "ancsa_refusal_reason",
    "village_government_owns_an_anc",
    "bears_ownership", "ALIAS_TYPES", "NEVER_PROMOTES_TO_ACTIVE",
    "may_promote", "REVENUE_EVIDENCE", "SUM_COLUMNS", "SINGLE_PROPERTY_ATTRIBUTED",
    "SINGLE_PROPERTY_NOTE", "may_attribute_to_single_property",
    "MAX_PER_AWARD_COLUMNS", "NAME_TRAPS", "STANDING_DISAMBIGUATIONS",
    "Position", "POSITION_KEY", "position_is_addressable", "EvidenceClass",
]


# ---------------------------------------------------------------------------
# POSITION - Elijah, 2026-08-12:
#   "applying this nuance to other things i think will help us fill in
#    opposition and perhaps lobbying too"
#
# The nuance came from energy, where coalition lines genuinely cross: an
# environmental group opposing a pipeline may be opposing a TRIBAL sponsor's
# revenue; an operator may be opposing a tribal land claim; two tribes may sit
# on OPPOSITE sides of the same docket.
#
# Generalised: a position is a property of an OBSERVATION, never of an
# organisation. "Sierra Club is anti-Native" is not a fact the data can carry.
# "Sierra Club filed in opposition on docket X, which tribe Y sponsored" is.
# ---------------------------------------------------------------------------


class Position(str, Enum):
    SUPPORTS = "SUPPORTS"
    OPPOSES = "OPPOSES"
    MIXED = "MIXED"
    #: The document exists but its own words do not establish a direction.
    #: NOT the same as neutral, and never the same as absent.
    UNDETERMINED = "UNDETERMINED"


#: The key a position MUST be recorded against. Anything coarser is an
#: assertion about an organisation rather than an observation about a record.
POSITION_KEY = ("organisation_id", "matter_id", "native_entity_id")


def position_is_addressable(organisation_id, matter_id, native_entity_id):
    """A position needs all three legs. Two is a generalisation.

    Refusing here is what stops `position_on_native_issue` degenerating into an
    organisation-level label - which is both wrong (organisations are not
    monolithic across matters or across tribes) and, for a published product,
    the kind of claim that has to survive contact with a lawyer.
    """
    return all(bool(str(x or "").strip())
               for x in (organisation_id, matter_id, native_entity_id))


class EvidenceClass(str, Enum):
    """Whose act is being recorded. Only one of these is an institutional
    position; conflating them is how a good finding becomes a retraction.

    Measured need, 2026-08-12: testing whether policy institutions support
    Native causes in one channel and oppose them in another.
    """

    #: A donor to the institution also funds work adverse to Native interests.
    #: A fact about the DONOR. Says nothing about the institution's position.
    FUNDER_ACTIVITY = "FUNDER_ACTIVITY"
    #: A fellow, scholar or employee acted or wrote. A fact about a PERSON.
    #: Institutions host people who disagree with each other.
    AFFILIATED_INDIVIDUAL = "AFFILIATED_INDIVIDUAL"
    #: The institution itself filed, registered, commented or resolved.
    #: The ONLY class that carries an institutional position.
    INSTITUTIONAL_ACTION = "INSTITUTIONAL_ACTION"

    @property
    def carries_institutional_position(self) -> bool:
        return self is EvidenceClass.INSTITUTIONAL_ACTION



# ---------------------------------------------------------------------------
# PROMOTED TABLES - the additions/ledger defect, declared once so it cannot be
# rediscovered a fifth time.
#
# THE DEFECT, in four scripts across three sessions
# ------------------------------------------------
# `glob("data/clean/deals_*_additions.csv")` reads the ADDITIONS to the deals
# ledger and never the LEDGER ITSELF. That is why a 790-row deals master held
# exactly ONE row dated 2026 while 131 verified rows sat in two root CSVs.
# `docs/FACT_CHECK_2026-08-06.md` finding B-1 named the miscount on 2026-08-06;
# it was still live in `82_build_gaming_property_dataset.py`,
# `35_coverage_audit.py`, `33_apply_party_rulings.py`,
# `59_build_deal_source_index.py`, `73_add_tcu_and_cdfi.py`,
# `31_build_dataset5_linked.py` and `175_sync_published_property_view_entities.py`
# on 2026-08-26, because each session fixed only the instances it tripped over.
#
# THE RULE
# --------
#   1. A build that reads the ADDITIONS must also read the LEDGER.
#   2. A build must STATE which file it treats as the truth.
#
# A CONSUMER (counting, joining, auditing, profiling) reads the PROMOTED table
# and nothing else - it is the merged, deduplicated, withdrawal-honouring
# superset. Only a PRODUCER whose job is to BUILD the promoted table reads the
# parts, and it must read every part.
#
# Measured 2026-08-26:
#     9 x deals_*_additions.csv                       790 rows
#     deals_2026_ytd.csv                               90
#     deals_historical_2020_2025.csv                   56
#     union of distinct Deal_ID                       936
#     less MA2020-008, withdrawn as a duplicate of ANCSA2-2020-004
#     data/clean/deals_classified.csv  (THE TRUTH)    935
#
# Note the parts route ALSO needs `review/deals_withdrawn_duplicates.csv` to
# reach 935, because script 54 deliberately leaves a withdrawn row in its source
# file. The promoted table already honours it. That is a second reason a
# consumer should never assemble the universe itself.
# ---------------------------------------------------------------------------

#: promoted table (relative to the project root) -> the parts it was built from.
#: Add a family here the day it is created, not the day it is miscounted.
PROMOTED_TABLES = {
    "data/clean/deals_classified.csv": (
        "data/clean/deals_*_additions.csv",
        "deals_2026_ytd.csv",
        "deals_historical_2020_2025.csv",
    ),
}

#: Scripts allowed to read the PARTS without reading the promoted table,
#: because building or reconciling the promoted table is their whole job.
#: Anything not listed here that reads a part is a defect, by name.
PROMOTED_TABLE_PRODUCERS = frozenset({
    "88_build_deals_taxonomy.py",           # builds deals_classified.csv
    "153_merge_base_ledgers_into_classified.py",   # merged the 131 root rows
    "54_reconcile_deals_duplicates.py",     # dedupes ACROSS the parts
    "155_collect_deals_2026_08.py",         # appends to a part and the truth
    "38_fain_backfill.py",                  # patches ONE named additions file
    "build_federal_award_rows.py",          # writes that additions file
    # One-off ANCSA collection runs under code/ancsa_portal/ and code/ancsa_v2/.
    # Each MINTS Deal_IDs into a `deals_ancsa_*_additions.csv` and checks the
    # new ids for collisions against every existing part - which is the one
    # place the parts really are the right input, because a WITHDRAWN id must
    # still count as taken and the promoted table no longer holds it.
    "build_deals.py",
    "build_deals2.py",
    "build_v2.py",
    "build_skipped_v2.py",
    "build_log_doc.py",
})

#: The single truth for the deals universe. Import this; do not glob.
DEALS_TRUTH = "data/clean/deals_classified.csv"


def promoted_table_for(path) -> str:
    """The promoted table a part belongs to, or "" if the path is not a part.

    `path` may be a full path, a glob pattern or a bare filename - matching is
    on the basename, because the parts live in two different directories and
    that is exactly what hid this defect.
    """
    import fnmatch
    import os
    base = os.path.basename(str(path or "")).strip()
    if not base:
        return ""
    for promoted, parts in PROMOTED_TABLES.items():
        if base == os.path.basename(promoted):
            return ""
        for part in parts:
            if fnmatch.fnmatch(base, os.path.basename(part)):
                return promoted
    return ""


__all__ = __all__ + [
    "PROMOTED_TABLES", "PROMOTED_TABLE_PRODUCERS", "DEALS_TRUTH",
    "promoted_table_for",
]

# Added 2026-08-26 with the individually Native-owned FIRM class
# (code/241_promote_individual_native_firms_in_place.py). Appended rather than
# merged into the list above so a concurrent editor of this module cannot lose
# either block.
__all__ = __all__ + [
    "INDIVIDUAL_NATIVE_RELATIONSHIPS", "INDIVIDUAL_NATIVE_CLASS",
    "INDIVIDUAL_NATIVE_OWNERSHIP_BASIS", "INDIVIDUAL_NATIVE_RULING_CLASSES",
    "is_tribal_link_refusal_not_native_refusal",
    "individual_native_refusal_reason",
    "ABSENCE_VALUES", "FORBIDDEN_ABSENCE_VALUES", "absence_value_ok",
    "SELF_CERTIFICATION_IS_NOT_A_VERDICT",
    "INDIVIDUAL_NATIVE_PUBLISHABLE_FIELDS",
    "INDIVIDUAL_NATIVE_WITHHELD_FIELDS", "INDIVIDUAL_NATIVE_MIN_CELL_FIRMS",
    "may_publish_individual_native_field", "suppress_small_cell",
]

# ---------------------------------------------------------------------------
# NONPROFIT CLASSIFICATION RULINGS - AN ALLOW-LIST OF POSITIVES
#
# Added 2026-08-26 by the 293 lint-consolidation pass, after
# `169_build_identifier_graph.py` was found deciding "ruled Native" as
#
#     if classification_ruling not in ("", "UNRULED", "place_name_coincidence"):
#         np_ruled_native.add(ein)
#
# That is an ALLOW-LIST OF NEGATIVES, and its safety depends on somebody
# remembering to enumerate every future bad value. `not_a_native_entity` - the
# obvious next token - would have read as *ruled Native*; that is why
# `code/251_apply_np_ein_exclusions_to_np_orgs.py` had to reuse the existing
# `place_name_coincidence` token rather than write the honest one.
#
# The polarity is inverted here, once, for everyone: a ruling is Native only if
# it is NAMED as a positive outcome. A token nobody has classified is UNKNOWN,
# and UNKNOWN is not Native.
#
# Measured in data/clean/np_orgs.csv, 2026-08-26 (12,764 rows):
#     UNRULED                 12,366
#     place_name_coincidence     309
#     native_controlled           71
#     tribally_controlled         11
#     native_serving               7
# `34_apply_nonprofit_rulings.py` can additionally write CONFLICT, which is a
# deferral and decides nothing.
# ---------------------------------------------------------------------------

#: The ONLY values that mean "ruled Native". Same set as
#: `111_build_advocacy_passthrough.NP_ORGS_NATIVE_RULINGS` and the set
#: `132_build_schedule_i_layer.py` documents for `filer_is_ruled_native`.
NP_CLASSIFICATION_POSITIVE = frozenset({
    "native_controlled", "tribally_controlled", "native_serving",
})

#: Values that mean "ruled NOT Native". Kept for reporting; nothing should
#: branch on this set to decide the POSITIVE case - that is the defect.
NP_CLASSIFICATION_NEGATIVE = frozenset({
    "place_name_coincidence", "not_a_native_entity", "not_native",
})

#: Values that decide nothing: nobody has ruled, or the rulings disagree.
NP_CLASSIFICATION_UNDECIDED = frozenset({"", "UNRULED", "CONFLICT", "UNSURE"})


def np_ruling_is_native(ruling) -> bool:
    """True only for a NAMED positive nonprofit classification ruling.

    An unrecognised token is FALSE, deliberately. The alternative - treating
    anything that is not a known negative as a positive - is the polarity this
    function exists to remove, and it fails open in the direction that
    publishes an attribution nobody made.
    """
    return (ruling or "").strip().lower() in NP_CLASSIFICATION_POSITIVE


def np_ruling_is_unrecognised(ruling) -> bool:
    """A token that is in none of the three declared sets.

    Worth reporting rather than silently treating as undecided: a new ruling
    vocabulary landing upstream should be noticed the day it lands, not the day
    somebody wonders why a count moved.
    """
    v = (ruling or "").strip()
    return (v.lower() not in NP_CLASSIFICATION_POSITIVE
            and v.lower() not in {x.lower() for x in NP_CLASSIFICATION_NEGATIVE}
            and v not in NP_CLASSIFICATION_UNDECIDED)


__all__ = __all__ + [
    "NP_CLASSIFICATION_POSITIVE", "NP_CLASSIFICATION_NEGATIVE",
    "NP_CLASSIFICATION_UNDECIDED", "np_ruling_is_native",
    "np_ruling_is_unrecognised",
]


# ===========================================================================
# A LOBBYING ATTRIBUTION THAT HAS BEEN WITHDRAWN  (2026-08-26)
#
# `native_entity_lobbying_disclosures.csv` now carries TWO withdrawal marks,
# written by two different scripts for two different reasons:
#
#   `org_type_barred = 1`      65_lobbying_organization_type_guard.py
#       a LEGAL FORM a Native entity cannot be: CITY OF, MINES, a power
#       district, SALT RIVER PROJECT.  841 filings.
#
#   `attribution_withdrawn = 1`  350_withdraw_false_lobbying_attributions.py
#       a demonstrably different ORGANISATION with a similar name: SANTA ROSA
#       COUNTY FL, SANTA ROSA JUNIOR COLLEGE, COEUR D'ALENE MINING, BRISTOL
#       BAY ECONOMIC DEVELOPMENT CORPORATION, BRISTOL BAY AREA HEALTH
#       CORPORATION.  471 filings.
#
# BOTH mean "this filing is not this Native entity's". Consumers were reading
# `org_type_barred` alone, because on 2026-08-06 that was the only mark there
# was - so a second withdrawal, written correctly, would have been re-imported
# in full by the next `180_build_lobbying_registrant_hub.py` run.
#
# **That is this project's signature failure with the arrow reversed**: not a
# correction that failed to reach a consumer, but a consumer that cannot see a
# correction because it tests for one specific spelling of it. One predicate,
# declared once, is the fix. Add the next mark HERE, never at a call site.
# ===========================================================================

LOBBYING_WITHDRAWAL_MARKS = ("org_type_barred", "attribution_withdrawn")

LOBBYING_WITHDRAWN_CONFIDENCES = frozenset({
    "withdrawn_org_type",          # script 65
    "withdrawn_false_attribution", # script 350
})


def lobbying_attribution_withdrawn(row) -> bool:
    """True when a lobbying disclosure row's entity attribution was withdrawn.

    Reads every declared mark, not one of them. A row is withdrawn if any mark
    is set or its `match_confidence` is a withdrawal sentinel - three
    independent signals, because the whole point of this function is that a
    consumer testing ONE of them goes blind to the others.
    """
    for m in LOBBYING_WITHDRAWAL_MARKS:
        if (row.get(m) or "").strip():
            return True
    return (row.get("match_confidence") or "").strip() in \
        LOBBYING_WITHDRAWN_CONFIDENCES


__all__ = __all__ + [
    "LOBBYING_WITHDRAWAL_MARKS", "LOBBYING_WITHDRAWN_CONFIDENCES",
    "lobbying_attribution_withdrawn",
]


# ===========================================================================
# THE PROJECT ROOT, ENUMERATED  (added 2026-08-26 by
# `code/401_register_root_csv_parts.py`; measured by
# `code/399_inventory_stranded_data.py`)
#
# `160_ship_gap_report.py` prints, correctly:
#
#     "LEDGERS IN THE PROJECT ROOT, OUTSIDE data/clean: 8 files, 7,009 rows.
#      No registry enumerates the root. This is the shape of the deals defect."
#
# It was right about the shape and it stayed at eight files for as long as
# nobody said what those eight files ARE. Two of them - `deals_2026_ytd.csv`
# and `deals_historical_2020_2025.csv` - were ALREADY declared parts below and
# were still being printed as unenumerated, because 160 globs the root and the
# declaration it prints two sections later never reached the glob.
#
# APPENDED rather than merged into the dict literal above, so a concurrent
# editor of this module cannot lose either block - the same reason the `__all__`
# additions are appended.
#
# EVERY ONE OF THESE SIX WAS CHECKED FOR MEMBERSHIP ON A REAL KEY, NOT ASSUMED.
# The checks live in `399_inventory_stranded_data.py` and re-run on every
# invocation, because a ruling that is not re-derivable is a note:
#
#   entity_master.csv                751 of 815 Entity_IDs carried on the
#     -> cedar_entity_spine.csv      spine's `cedar_entity_id`; 28 more match a
#                                    canonical name or alias exactly. The
#                                    remaining 36 are NEEDS-A-RULING and are
#                                    listed in docs/STRANDED_DATA_DISPOSITION.md
#   entity_crosswalk_bgov.csv        878 of 878 CAGE codes present in the
#     -> cedar_identifier_ledger     ledger at tier A, attribution_method
#                                    `bgov_manual`
#   bgov.csv                         878 of 878 CAGE codes present, via the
#     -> cedar_identifier_ledger     crosswalk above. NOTE the ledger stores the
#                                    value in `identifier`, NOT in a `cage_code`
#                                    column - a check aimed at `cage_code`
#                                    returns 0 of 878 and reads as a total
#                                    stranding. That is defect 2b, and it cost
#                                    one wrong conclusion before it was caught.
#   contract-03-18-23-19-40-24.csv   named in 13_build_fpds_hierarchy.py's FILES
#     -> fpds_uei_cage_map.csv       list and cited by `source_file` on 28 rows
#                                    of the cage map and 27 of fpds_uei_edges.
#                                    EXACTLY 4,000 rows is the USAspending
#                                    Advanced Search download cap - it is a
#                                    TRUNCATED EXPORT and must never be summed
#                                    as a ledger.
#   Assistance_56G180126_...csv      92 of 92 rows present in
#     -> federal_funding_transactions  federal_funding_transactions.csv on
#                                    `assistance_transaction_unique_key`. A
#                                    single-FAIN drill-down export, a QA
#                                    artefact.
#
# The eighth root file, `reconcile_queue.csv`, is NOT a part of any promoted
# table - it is 326 unanswered review questions with an empty `YOUR_RULING`
# column - and 401 moved it to `review/`, where the review-backlog registry
# that 160 already runs enumerates it by name. Registering a queue as a
# dataset part would have been the wrong shape of honest.
# ===========================================================================

PROMOTED_TABLES.update({
    "data/spine/cedar_entity_spine.csv": (
        "entity_master.csv",
    ),
    "data/clean/cedar_identifier_ledger_final.csv": (
        "entity_crosswalk_bgov.csv",
        "bgov.csv",
    ),
    "data/clean/fpds_uei_cage_map.csv": (
        "contract-03-18-23-19-40-24.csv",
    ),
    "data/clean/federal_funding_transactions.csv": (
        "Assistance_56G180126_TransactionHistory_1.csv",
    ),
})

# Scripts whose job IS to read these parts. Each is named with the reason, the
# same way the deals producers are - "anything not listed here that reads a part
# is a defect, by name."
PROMOTED_TABLE_PRODUCERS = PROMOTED_TABLE_PRODUCERS | frozenset({
    "01_build_entity_spine.py",        # builds the spine FROM entity_master +
                                       # entity_crosswalk_bgov
    "03_apply_exclusions_and_tier.py", # names entity_crosswalk_bgov.csv in
                                       # AUTHORITY_FILES; it tiers the ledger
    "35_entity_harvest.py",            # harvests INTO the spine
    "36_build_nho_intertribal.py",     # reads entity_master only to check which
                                       # N- ids are TAKEN before minting new
                                       # ones - the same case the ANCSA builds
                                       # are exempted for: a WITHDRAWN id must
                                       # still count as taken, and the promoted
                                       # table no longer holds it
    "52_add_village_corporations.py",  # appends village corps to the spine
    "66_build_entity_hierarchy.py",    # builds the hierarchy over the spine
    "374_build_cedar_taxonomy_export.py",
    "13_build_fpds_hierarchy.py",      # builds fpds_uei_cage_map / _edges
    "399_inventory_stranded_data.py",  # the inventory: reading the parts IS the
                                       # job, and it reads the promoted table
                                       # too, on a real key
    "401_register_root_csv_parts.py",  # this declaration's own author
})


# ===========================================================================
# THE ALIAS LAYER IS FIRST-CLASS  (2026-08-26, scripts 415-419)
#
# Elijah: "Three Affiliated Tribes is also MHA is also Mandan, Hidatsa and
#          Arikara Nation."
#
# One entity, three names in daily use, and MEASURED 2026-08-26:
# `TRBF-MHATAT-00` carries seven alias rows and **not one of them is "MHA" or
# "Mandan, Hidatsa and Arikara Nation"** - neither the initialism nor the name
# the nation uses for itself. Four of the seven are machine-generated
# permutations of "Three Affiliated" at confidence 0.40.
#
# Nearly every matching defect this project has paid for was a name the
# resolver did not know was the same entity, or two names it wrongly thought
# were. The alias layer is where that is fixed, and it is DATA so a later pass
# can extend it without editing a matcher.
#
# APPENDED, AND ALIAS_TYPES IS REBOUND RATHER THAN EDITED IN PLACE, because
# this module was being written by another agent at 20:54 on 2026-08-26 and a
# rebind at the end of the file cannot collide with an edit earlier in it.
# There is still exactly ONE `ALIAS_TYPES` at import time - a SECOND alias
# vocabulary would be the defect this file exists to prevent.
# ===========================================================================

#: An alias produced by OCR of a scanned document. NOT a typo (`known_typo`)
#: and NOT a source's rendering choice (`source_specific`): it is an artefact
#: of the CAPTURE, so it is systematic, it recurs across every document from
#: the same scanner, and it must never be published as a name anyone uses.
#: The measured shape is letterhead spacing collapsing - `WyandotteNation`.
ALIAS_TYPES = ALIAS_TYPES | frozenset({"ocr_variant"})

#: How to say the owner's alias vocabulary in the vocabulary that already
#: exists. **Nothing parallel is declared.** A synonym for an existing type is
#: two vocabularies wearing one name, which is the `entity_class` seam in the
#: identifier ledger (docs/CEDAR_TAXONOMY.md Gap 7) arriving in a new place.
ALIAS_TYPE_SYNONYMS = {
    "legal_current": "legal",
    "legal_historical": "former_legal",
    "initialism": "acronym",          # MHA. An initialism IS an acronym here.
    "common_name": "common",
    "dba": "dba",
    "spelling_variant": "known_typo",
    "ocr_variant": "ocr_variant",
    "source_rendering": "source_specific",
    "retired_entity_id": "historical",
}

#: Does this alias name the entity NOW, or did it once?
#: `historical` is also what a RETIRED ENTITY ID becomes when a class change
#: mints a new one - `cedar_ids.reclassify`. A retired id always resolves and
#: is never reused.
ALIAS_ROLES = frozenset({"current", "historical", "unknown"})

#: alias_type -> role. `unknown` is the honest answer for a generated
#: permutation: nobody has established whether anyone uses that string.
ALIAS_TYPE_ROLE = {
    "legal": "current", "common": "current", "acronym": "current",
    "abbreviation": "current", "shortened": "current", "brand": "current",
    "operating_name": "current", "dba": "current",
    "governmental_unit_variation": "current", "translated": "current",
    "diacritic_folded": "current", "source_specific": "current",
    "full_form_federal_filing": "current", "informal": "current",
    "former_legal": "historical", "historical": "historical",
    "known_typo": "unknown", "ocr_variant": "unknown",
}


def alias_type_role(alias_type) -> str:
    """`current` / `historical` / `unknown` for an alias type.

    `unknown` for an unrecognised type, deliberately - the same polarity as
    `np_ruling_is_native`. A type nobody has classified must not silently
    become a name the entity currently uses.
    """
    return ALIAS_TYPE_ROLE.get((alias_type or "").strip(), "unknown")


def canonical_alias_type(name) -> str:
    """Map any accepted spelling of an alias type onto the ONE vocabulary.

    Returns "" for anything unrecognised, so a new type surfaces at the write
    instead of quietly becoming a category.
    """
    v = (name or "").strip()
    if v in ALIAS_TYPES:
        return v
    return ALIAS_TYPE_SYNONYMS.get(v, "") if ALIAS_TYPE_SYNONYMS.get(
        v, "") in ALIAS_TYPES else ""


__all__ = __all__ + [
    "ALIAS_TYPE_SYNONYMS", "ALIAS_ROLES", "ALIAS_TYPE_ROLE",
    "alias_type_role", "canonical_alias_type",
]


# ===========================================================================
# THE ENTITY-CLASS VOCABULARY, CANONICAL AND IMPORTABLE
# (2026-08-26, `code/441_make_ancsa_class_guard_load_bearing.py` and
#  `code/442_consolidate_entity_class_vocabulary.py`; gaps 1, 3, 4, 5, 6 and 8
#  of docs/CEDAR_TAXONOMY.md)
#
# THE DEFECT THIS BLOCK CLOSES IS NOT A MISSING GUARD. IT IS A GUARD THAT
# EXISTS AND IS NEVER CALLED.
#
# `ANCSA_CORPORATION_CLASSES` and `ALASKA_VILLAGE_GOVERNMENT_CLASSES` were
# declared above on 2026-08-26 to carry the owner's $24.52B ruling. Measured
# the same evening: **zero importers outside this module.** The ruling WAS
# applied - by `191_apply_ancsa_ownership_ruling.py`, using its OWN local copy
# of the same three strings (`CORPORATION_CLASSES`, line 135). So the ruling
# was enforced once, in one script, and the reusable guard protected nothing
# while reading, to the next author, exactly like protection.
#
# **A guard that silently no-ops on a missing argument is the same failure as
# `setdefault` on a pre-initialised dict** (defect class 2a): the call
# succeeds, the counter says it ran, and nothing was checked.
#
# `bears_ownership(rel)` with no classes CANNOT fire rule 2 or rule 4. That
# default is kept - four module-load assertions on constants depend on it and
# breaking them helps nobody - but it is no longer the only door:
#
#   bears_ownership_checked(rel, owner_class, owned_class)
#       RAISES `ClassesNotSupplied` when either class is missing. Use it
#       wherever the classes ARE knowable. A refusal to guess is not a
#       degraded mode; it is the guard.
#   bears_ownership_for_edge(rel, source_id, target_id)
#       Resolves both classes from the spine ITSELF and raises when it cannot.
#       This is the one a real edge table calls: the caller then has no
#       argument to forget.
#
# `441 --selftest` fails if either raising path stops raising, and if any
# caller that walks a real edge table calls `bears_ownership` with fewer than
# three arguments. A fixture that passes vacuously proves nothing - that is
# the lesson `284` and `cedar_match_guard` both taught on 2026-08-26.
#
# APPENDED, AND NOTHING ABOVE IS EDITED IN PLACE, because this module was
# being written by two other agents on 2026-08-26 (the root-CSV registration
# at 20:54 and the alias layer at 21:03). A rebind at the end of the file
# cannot collide with an edit earlier in it, and there is still exactly ONE
# binding of every name here at import time.
# ===========================================================================

#: Every `entity_class` value in `data/spine/cedar_entity_spine.csv`, quoted
#: VERBATIM including capitalisation. 1,534 rows, 17 classes, no blanks and no
#: spelling variants inside the file, measured 2026-08-26.
#:
#: **Retyping a class name with a different case is a guard that fails OPEN**,
#: and four scripts had already done it - see `DEAD_ENTITY_CLASS_STRINGS`.
ENTITY_CLASSES = frozenset({
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
    "Native Hawaiian Organization",
    "BIE School",
    "Alaska Native Village Corporation",
    "State-recognized tribe",
    "Native Community Development Financial Institution",
    "Intertribal Organization",
    "Individually Native-owned business",
    "Urban Indian Organization",
    "Tribal College or University",
    "Native Financial Institution",
    "Federal-level constituency entity",
    "Alaska Native Regional Corporation",
    "Federal-level self-governance consortium",
    "ANCSA Group Corporation",
    "State-level constituency entity",
})

#: Spine row counts as of 2026-08-26 21:15. Recorded so a membership test that
#: suddenly matches nothing can be recognised as such, and so the SIZE of what
#: a dead guard failed to filter is legible at the call site.
#:
#: **THE SET IS THE AUTHORITY; THESE COUNTS ARE A STAMP AND THEY MOVE.** The
#: spine grew 1,534 -> 1,536 rows in the eleven minutes this block was being
#: written, by another agent. The seventeen CLASSES did not change, and that
#: is the invariant a guard may rely on. Never assert a count from here;
#: recompute it from the spine and say when.
ENTITY_CLASS_COUNTS = {
    "Federally recognized tribe": 349,
    "Federally recognized Alaska Native Village": 228,
    "Native Hawaiian Organization": 210,
    "BIE School": 185,
    "Alaska Native Village Corporation": 173,
    "State-recognized tribe": 64,
    "Native Community Development Financial Institution": 64,
    "Intertribal Organization": 55,
    "Individually Native-owned business": 45,
    "Urban Indian Organization": 43,
    "Tribal College or University": 37,
    "Native Financial Institution": 29,
    "Federal-level constituency entity": 22,
    "Alaska Native Regional Corporation": 12,
    "Federal-level self-governance consortium": 9,
    "ANCSA Group Corporation": 6,
    "State-level constituency entity": 3,
}

# ---------------------------------------------------------------------------
# THE NAMED SUBSETS. One per QUESTION, never one per script.
#
# 37 set literals across 28 build scripts declared their own copy of some part
# of this vocabulary, under at least three names per concept
# (`GOVERNMENT_CLASSES` / `GOV_CLASSES` / `GOVERNMENT_ENTITY_CLASSES`). Most
# were identical and could simply be replaced. **Two genuinely disagreed, and
# both carried a written reason** - so both survive here, under names that say
# which question each answers. Silently unifying them would have deleted a
# decision somebody made on purpose; that is why divergence gets a NAME and a
# REASON rather than a merge.
# ---------------------------------------------------------------------------

#: The three classes that are a SOVEREIGN GOVERNMENT of a people. The most
#: re-typed set in the repo: ten identical local copies (104, 107, 111, 119,
#: 144, 168, 33, 53, 70, 98).
SOVEREIGN_GOVERNMENT_CLASSES = frozenset({
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
    "State-recognized tribe",
})

#: A constituent band or a state-level constituency is a GOVERNMENTAL BODY but
#: it is NOT a sovereign in its own right, and `111_build_advocacy_passthrough`
#: excludes both deliberately: a constituent band's contracts are not the
#: umbrella's. `100` and `91` include them because their question is "did a
#: governmental body appear in this record", not "who is the sovereign".
#: **Both readings are correct about different questions.**
GOVERNMENT_AND_CONSTITUENCY_CLASSES = SOVEREIGN_GOVERNMENT_CLASSES | frozenset({
    "Federal-level constituency entity",
    "State-level constituency entity",
})

#: `96_build_consultation_events.py`'s set, kept verbatim and named.
#: A federal agency consults government-to-government with tribes, Alaska
#: Native villages, ANCSA-region consortia, intertribal organisations AND
#: Native Hawaiian Organizations - the last by 54 U.S.C. 302706 rather than by
#: the trust relationship. It is a CONSULTATION-PARTY set, not a sovereignty
#: set, and collapsing it into `SOVEREIGN_GOVERNMENT_CLASSES` would drop NHOs
#: out of Section 106 consultation, which is a legal error, not a tidy-up.
CONSULTATION_PARTY_CLASSES = SOVEREIGN_GOVERNMENT_CLASSES | frozenset({
    "Federal-level constituency entity",
    "Federal-level self-governance consortium",
    "Intertribal Organization",
    "Native Hawaiian Organization",
})

#: Bodies whose members are OTHER Native entities, not persons.
MEMBERSHIP_CLASSES = frozenset({
    "Intertribal Organization",
    "Federal-level self-governance consortium",
})

#: A part of a larger government, not a government.
CONSTITUENCY_CLASSES = frozenset({
    "Federal-level constituency entity",
    "State-level constituency entity",
})

#: A SEPARATE LEGAL PERSON from the tribe it is named for, and therefore never
#: the payee of a gaming distribution, a compact allocation or a device count.
#: **This is the set the four dead guards were reaching for.** `107` and `92`
#: spell it correctly; `103` and `105` spelled two of its five members in a
#: vocabulary the spine does not use, so 93 spine entities (64 + 29) passed a
#: refusal that had never once matched. See `DEAD_ENTITY_CLASS_STRINGS`.
INSTITUTION_CLASSES = frozenset({
    "Tribal College or University",
    "BIE School",
    "Urban Indian Organization",
    "Native Community Development Financial Institution",
    "Native Financial Institution",
})

#: The two classes carried under the `CDFI-` prefix. They are DIFFERENT
#: classes - the prefix does not identify either - and a filter that wants
#: "the lenders" needs both.
NATIVE_FINANCIAL_INSTITUTION_CLASSES = frozenset({
    "Native Community Development Financial Institution",
    "Native Financial Institution",
})

#: Every class that can OWN another entity and carry a dollar upward. Sovereign
#: governments plus ANCSA corporations. `157_stage_osha_tribe_level_employment`
#: had this exact six-member set locally.
OWNER_BEARING_CLASSES = SOVEREIGN_GOVERNMENT_CLASSES | ANCSA_CORPORATION_CLASSES

#: Classes that NEVER roll up to anything. `Individually Native-owned business`
#: is self-parented by ruling and its blank `parent_native_entity` is that
#: ruling, not unfinished research.
NEVER_ROLLS_UP_CLASSES = frozenset({INDIVIDUAL_NATIVE_CLASS})

# ---------------------------------------------------------------------------
# CLASS STRINGS THAT ARE NOT IN THE SPINE - a guard written against a name that
# does not exist. Detected by `293_lint_bug_classes.py --class 8`.
#
# Each of these WAS a class name once, or is a plausible shortening of one, so
# the guard reads as live at the call site and filters nothing. The cost is
# measured, not hypothetical: `103_build_california_gaming.py` and
# `105_build_florida_gaming.py` each refused `"Native CDFI"` and
# `"Native financial institution"` while the spine says
# `"Native Community Development Financial Institution"` (64 rows) and
# `"Native Financial Institution"` (29) - **93 entities passing a filter that
# has never once matched**, on a table that keys gaming payments.
#
# Ask `canonical_entity_class()`; never type a class name into a comparison.
# ---------------------------------------------------------------------------
DEAD_ENTITY_CLASS_STRINGS = {
    "Native CDFI": "Native Community Development Financial Institution",
    "Native financial institution": "Native Financial Institution",
    "Native Financial institution": "Native Financial Institution",
    "Alaska Native Village Government": "Federally recognized Alaska Native Village",
    "Federally Recognized Tribe": "Federally recognized tribe",
    "Federally Recognized Alaska Native Village":
        "Federally recognized Alaska Native Village",
    "Tribal College": "Tribal College or University",
    "ANCSA Village Corporation": "Alaska Native Village Corporation",
    "ANCSA Regional Corporation": "Alaska Native Regional Corporation",
}


class UndeclaredEntityClass(ValueError):
    """A class string that is neither a spine class nor a known near-miss."""


def canonical_entity_class(value, strict=False):
    """The spine's spelling of `value`, or "" when it is not a class at all.

    A near-miss maps to the real class and is NOT silently accepted as-is:
    the point is that `"Native CDFI"` and
    `"Native Community Development Financial Institution"` must never be two
    live vocabularies at once.

    `strict=True` raises `UndeclaredEntityClass` instead of returning "".
    Use it at a WRITE - a class nobody declared must surface at the moment it
    is minted, not three tables downstream.
    """
    v = (value or "").strip()
    if v in ENTITY_CLASSES:
        return v
    real = DEAD_ENTITY_CLASS_STRINGS.get(v)
    if real:
        return real
    # Case-insensitive last resort, so a rename that only changed case is
    # recovered rather than becoming a nineteenth class.
    low = v.lower()
    for c in ENTITY_CLASSES:
        if c.lower() == low:
            return c
    if strict:
        raise UndeclaredEntityClass(
            f"{value!r} is not a Cedar entity class. The 17 declared classes "
            f"are in cedar_domain.ENTITY_CLASSES; known near-misses are in "
            f"DEAD_ENTITY_CLASS_STRINGS. docs/CEDAR_TAXONOMY.md Part I.")
    return ""


def entity_class_is_declared(value) -> bool:
    """True only for a string the spine actually carries.

    Deliberately FALSE for a near-miss: `"Native CDFI"` is not a class, it is
    a defect, and this predicate is what a linter asks.
    """
    return (value or "").strip() in ENTITY_CLASSES


# ===========================================================================
# GAP 5 - THE PREFIX IS NOT THE CLASS, AND THE FIX IS NOT TO STRIP THE PREFIX
#
# The owner has ruled that an id prefix SHOULD encode class, for agent
# legibility, and `cedar_ids.CLASS_PREFIX` implements that for every NEW
# entity. Nothing here argues with it. What is forbidden is the INVERSE:
# DERIVING a class from a prefix that is already minted.
#
#   ANVC -> Alaska Native Village Corporation 173 + ANCSA Group Corporation 6
#   CDFI -> Native CDFI 64 + Native Financial Institution 29
#   AKNF -> Alaska Native Village 228 + Federally recognized tribe 1
#           (Tlingit & Haida, a regional tribal government, documented)
#
# 272 entities sit under the two ambiguous prefixes. `cedar_ids.prefix_hint()`
# returns the observed classes AND `unambiguous: False`, which is the object to
# ask. `cedar_ids`' own rule states it: *type lives in a column and is read
# from the registry; it is never inferred from the prefix, because a prefix is
# history and an entity's class can change.*
#
# This constant is here rather than only in `cedar_ids` because a build script
# that branches on a class already imports `cedar_domain`, and the whole point
# of gap 3 is that a fact stored where nobody imports it protects nothing.
# ===========================================================================

#: Prefixes under which MORE THAN ONE entity_class is observed. Reading the
#: class off any of these is wrong for the number of entities shown.
AMBIGUOUS_ENTITY_PREFIXES = {
    "ANVC": ("Alaska Native Village Corporation",
             "ANCSA Group Corporation"),
    "CDFI": ("Native Community Development Financial Institution",
             "Native Financial Institution"),
    "AKNF": ("Federally recognized Alaska Native Village",
             "Federally recognized tribe"),
}


def prefix_identifies_class(entity_id_or_prefix) -> bool:
    """False wherever a class may NOT be read off the prefix.

    Ask this before writing `entity_class` from an id. Returns False for the
    three ambiguous prefixes and True otherwise - and True still means "the
    spine agrees TODAY", never "this is where class lives".
    """
    v = (entity_id_or_prefix or "").strip().upper()
    p = v.split("-", 1)[0] if "-" in v else v
    return bool(p) and p not in AMBIGUOUS_ENTITY_PREFIXES


# ===========================================================================
# GAP 6 - THE ANCSA STATUTORY FORM IS A COLUMN, NOT A CLASS
#
# 43 U.S.C. 1607(c) names "Village Corporations, Urban Corporations, and Group
# Corporations". Cedar has a class for two of the three, so the four ANCSA
# URBAN Corporations sit in `Alaska Native Village Corporation`.
#
# **This is a LABELLING defect and not an ownership one, and the distinction is
# load-bearing:** 1607(c) applies 1606(g), (h) and (o) IDENTICALLY to all
# three forms, so every conclusion in docs/ANCSA_OWNERSHIP_RULING.md holds
# unchanged for an Urban Corporation. Splitting the class would therefore fix
# a label and risk an ownership guard - a future `Alaska Native Urban
# Corporation` would not be in `ANCSA_CORPORATION_CLASSES` unless somebody
# remembered to add it, and rules 2 and 4 would fall open for those four.
#
# So the form is a COLUMN. The class governs the guard; the form is a
# statutory fact about the same row.
# ===========================================================================

#: `ancsa_corporation_form` - the statutory form under ANCSA.
ANCSA_CORPORATION_FORMS = frozenset({"VILLAGE", "URBAN", "GROUP", "REGIONAL"})

#: The four Urban Corporations, by spine id. Named rather than counted,
#: because a count is not a task (defect class 2c) and the next reader
#: filtering "village corporations" needs to know WHICH four are not.
ANCSA_URBAN_CORPORATIONS = {
    "ANVC-GLDBLT-00": "Goldbelt, Incorporated",            # Juneau
    "ANVC-SHEEAT-00": "Shee Atika, Incorporated",          # Sitka
    "ANVC-NTVSKD-00": "Natives of Kodiak, Inc.",           # Kodiak
    "ANVC-KNNTVS-00": "Kenai Natives Association, Inc.",   # Kenai
}


def ancsa_corporation_form(entity_id, entity_class):
    """`VILLAGE` / `URBAN` / `GROUP` / `REGIONAL`, or "" for a non-ANCSA row.

    The URBAN answer comes from the named-entity register above, because the
    class column cannot express it and inferring it from a place name would be
    the containment defect in a new coat.
    """
    eid = (entity_id or "").strip().upper()
    cls = canonical_entity_class(entity_class)
    if eid in ANCSA_URBAN_CORPORATIONS:
        return "URBAN"
    if cls == "Alaska Native Regional Corporation":
        return "REGIONAL"
    if cls == "ANCSA Group Corporation":
        return "GROUP"
    if cls == "Alaska Native Village Corporation":
        return "VILLAGE"
    return ""


# ===========================================================================
# GAP 1 - MAKING THE ANCSA GUARD LOAD-BEARING
#
# Three doors, and only the first one can no-op:
#
#   bears_ownership(rel)                    class-blind, kept for the four
#                                           module-load assertions on constants
#   bears_ownership_checked(rel, a, b)      RAISES if a class is missing
#   bears_ownership_for_edge(rel, src, tgt) resolves classes itself, RAISES if
#                                           it cannot
# ===========================================================================


class ClassesNotSupplied(ValueError):
    """`bears_ownership_checked` was called without both entity classes.

    Raised rather than defaulted, because defaulting is the whole defect: the
    ANCSA rule-2 / rule-4 branch cannot fire without classes, and a guard that
    returns an answer it did not check is worse than no guard - the next
    author reads the constant and believes they are protected.
    """


class UnknownEntityClass(LookupError):
    """An entity id whose class could not be resolved from the spine."""


_SPINE_CLASS_CACHE = {}


def entity_class_index(spine_path=None, refresh=False):
    """`{entity_id: entity_class}` read from the spine. Cached per path.

    Imported lazily so this module stays import-cheap and side-effect free:
    a domain vocabulary that touches the disk at import time is a domain
    vocabulary that cannot be imported by a linter.
    """
    import csv as _csv
    import pathlib as _pathlib
    p = _pathlib.Path(spine_path) if spine_path else (
        _pathlib.Path(__file__).resolve().parent.parent
        / "data" / "spine" / "cedar_entity_spine.csv")
    key = str(p)
    if refresh or key not in _SPINE_CLASS_CACHE:
        idx = {}
        with open(p, newline="", encoding="utf-8-sig") as fh:
            for row in _csv.DictReader(fh):
                eid = (row.get("tribe_id") or row.get("entity_id") or "").strip()
                cls = (row.get("entity_class") or "").strip()
                if eid:
                    idx[eid] = cls
        _SPINE_CLASS_CACHE[key] = idx
    return _SPINE_CLASS_CACHE[key]


def entity_class_for(entity_id, class_by_id=None, spine_path=None):
    """The spine's `entity_class` for `entity_id`. RAISES if it cannot.

    `UnknownEntityClass` rather than "" on purpose. An unresolved id returning
    a blank class turns `bears_ownership_checked` back into the class-blind
    version by the back door, which is the defect this whole block exists to
    close.
    """
    eid = (entity_id or "").strip()
    if not eid:
        raise UnknownEntityClass(
            "blank entity id - a blank endpoint is not an entity whose class "
            "can be checked. See docs/CEDAR_TAXONOMY.md Gap 2: type the blank "
            "(NO_SPINE_ENTITY_BY_RULING vs UNRESOLVED) before asking this.")
    idx = class_by_id if class_by_id is not None else entity_class_index(spine_path)
    if eid not in idx:
        raise UnknownEntityClass(
            f"{eid!r} is not in the entity spine, so its class is unknown and "
            f"no ownership guard can be evaluated on it.")
    cls = canonical_entity_class(idx[eid])
    if not cls:
        raise UnknownEntityClass(
            f"{eid!r} carries entity_class {idx[eid]!r}, which is not one of "
            f"the 17 declared classes.")
    return cls


def bears_ownership_checked(rel, owner_class, owned_class) -> bool:
    """`bears_ownership`, with the classes MANDATORY.

    Raises `ClassesNotSupplied` when either class is missing or is not a
    declared class. Call this anywhere the classes are knowable; the
    class-blind form is for module-load assertions on constants and nothing
    else.
    """
    a = canonical_entity_class(owner_class)
    b = canonical_entity_class(owned_class)
    if not a or not b:
        missing = []
        if not a:
            missing.append(f"owner_class={owner_class!r}")
        if not b:
            missing.append(f"owned_class={owned_class!r}")
        raise ClassesNotSupplied(
            "bears_ownership_checked requires BOTH entity classes; "
            + " and ".join(missing) + ". Without them ANCSA rule 2 (a village "
            "GOVERNMENT never owns an ANC) and rule 4 (nor the reverse) "
            "cannot fire, and the call would return an answer it did not "
            "check. docs/ANCSA_OWNERSHIP_RULING.md; docs/CEDAR_TAXONOMY.md "
            "Gap 1.")
    return bears_ownership(rel, a, b)


def bears_ownership_for_edge(rel, source_entity_id, target_entity_id,
                             class_by_id=None, spine_path=None) -> bool:
    """The form a real edge table calls. Resolves both classes itself.

    There is no argument to forget, which is the point: `97:829` walked 2,292
    relationship rows calling the class-blind form, so the ANCSA branch never
    evaluated a single edge. Raises `UnknownEntityClass` on an endpoint the
    spine does not carry - a blank endpoint is Gap 2 and must be TYPED, not
    silently skipped by a guard pretending it checked.
    """
    a = entity_class_for(source_entity_id, class_by_id, spine_path)
    b = entity_class_for(target_entity_id, class_by_id, spine_path)
    return bears_ownership_checked(rel, a, b)


# ===========================================================================
# GAP 8 - FOUR ABSENCE VOCABULARIES, TWO OF THEM DECLARED NOWHERE IN CODE
#
# **They are NOT merged, and that is the decision, not an omission.** The owner
# asked for one absence vocabulary so a reader can tell a genuine source
# absence from our own failure - and the way to answer that is to make each
# vocabulary say WHICH QUESTION it answers, because the four answer four
# different questions and a single merged list would answer none of them:
#
#   "we did not sweep this firm's website"      -> cedar_domain.ABSENCE_VALUES
#   "the source reported nothing"               -> 288's ABSENCE_VOCABULARY
#   "the AUTHORITY withholds it by statute"     -> SOURCE_COVERAGE_VALUES
#   "the list is behind a login"                -> TRIBAL_LIST_VERDICT_VALUES
#
# Collapsing the first two would let *"nobody looked"* be read as *"the source
# reported nothing"*, and `288_build_collection_descriptors.py` says so in its
# own source. That separation is correct and is preserved.
#
# What was actually wrong is that TWO of the four lived only in prose
# (AGENTS.md) and in a CSV column - **so nothing could validate a value and a
# typo became a new category.** They are declared here now, each with the
# question it answers, and `ABSENCE_VOCABULARIES` is the single index a reader
# consults to find out which of the four they are looking at.
#
# `NOT_CHECKED` is the only token common to all four, and it means the same
# thing in all four: nobody looked. It is never a finding.
# ===========================================================================

#: Whether a SOURCE publishes a fact. Declared in AGENTS.md prose since
#: 2026-08-07 and in no module until now.
#: `WITHHOLDS` is a fact about the AUTHORITY's policy - 2 CFR 200.512(b)(2)
#: is an auditee OPT-OUT, and generalising one auditee's election into a
#: property of the source is the error START_HERE.md records against the
#: tribal Single Audit "dead end".
SOURCE_COVERAGE_VALUES = frozenset({
    "PUBLISHES",     # the source publishes this fact
    "WITHHOLDS",     # the source holds it and does not publish it
    "NOT_FOUND",     # looked for, and the source does not hold it
    "NOT_CHECKED",   # nobody looked
})

#: Whether a tribal AUTHORITY publishes a contractor list. The vocabulary of
#: `review/tribal_vendor_list_registry_*.csv::verdict`, declared in a CSV and
#: in no module until now.
#: `SITE_UNREACHABLE` is a fact about the MOMENT, never a negative, and it must
#: not enter a denominator (AGENTS.md, 2026-08-26).
TRIBAL_LIST_VERDICT_VALUES = frozenset({
    "LIST_FOUND_MACHINE_READABLE",
    "LIST_FOUND_PDF",
    "LIST_FOUND_HTML",
    "LIST_BEHIND_LOGIN",
    "LIST_REFERENCED_NOT_PUBLISHED",
    "NO_LIST_FOUND",
    "SITE_UNREACHABLE",
    "NOT_CHECKED",
})

#: The single index. name -> (values, the question it answers, where it is
#: used). Four entries, deliberately - see the block above.
ABSENCE_VOCABULARIES = {
    "cedar_domain.ABSENCE_VALUES": (
        ABSENCE_VALUES,
        "Did WE find an ownership claim when we swept this firm's own site?",
        "individual-Native ownership evidence only"),
    "288_build_collection_descriptors.ABSENCE_VOCABULARY": (
        frozenset({"NOT_IN_SOURCE", "BELOW_REPORTING_THRESHOLD",
                   "OUT_OF_SCOPE_BY_CONSTRUCTION", "SUPPRESSED",
                   "REPORTED_EMPTY", "NOT_CHECKED"}),
        "Why is this cell empty in a SHIPPED collection?",
        "product-wide; every collection descriptor"),
    "cedar_domain.SOURCE_COVERAGE_VALUES": (
        SOURCE_COVERAGE_VALUES,
        "Does the SOURCE publish this fact at all?",
        "AGENTS.md source-coverage tables"),
    "cedar_domain.TRIBAL_LIST_VERDICT_VALUES": (
        TRIBAL_LIST_VERDICT_VALUES,
        "Does this tribal AUTHORITY publish a contractor list?",
        "review/tribal_vendor_list_registry_*.csv::verdict"),
}


def absence_vocabulary_for(value):
    """Which of the four vocabularies a token belongs to, by name.

    Returns a sorted list, because `NOT_CHECKED` is in all four and a function
    that returned one of them would be asserting a scope nobody established.
    Returns [] for a token in none - which is how a typo surfaces instead of
    becoming a new category.
    """
    v = str(value if value is not None else "").strip().upper()
    return sorted(k for k, (vals, _q, _w) in ABSENCE_VOCABULARIES.items()
                  if v in vals)


__all__ = __all__ + [
    "ENTITY_CLASSES", "ENTITY_CLASS_COUNTS",
    "SOVEREIGN_GOVERNMENT_CLASSES", "GOVERNMENT_AND_CONSTITUENCY_CLASSES",
    "CONSULTATION_PARTY_CLASSES", "MEMBERSHIP_CLASSES", "CONSTITUENCY_CLASSES",
    "INSTITUTION_CLASSES", "NATIVE_FINANCIAL_INSTITUTION_CLASSES",
    "OWNER_BEARING_CLASSES", "NEVER_ROLLS_UP_CLASSES",
    "DEAD_ENTITY_CLASS_STRINGS", "UndeclaredEntityClass",
    "canonical_entity_class", "entity_class_is_declared",
    "AMBIGUOUS_ENTITY_PREFIXES", "prefix_identifies_class",
    "ANCSA_CORPORATION_FORMS", "ANCSA_URBAN_CORPORATIONS",
    "ancsa_corporation_form",
    "ClassesNotSupplied", "UnknownEntityClass", "entity_class_index",
    "entity_class_for", "bears_ownership_checked", "bears_ownership_for_edge",
    "SOURCE_COVERAGE_VALUES", "TRIBAL_LIST_VERDICT_VALUES",
    "ABSENCE_VOCABULARIES", "absence_vocabulary_for",
]
