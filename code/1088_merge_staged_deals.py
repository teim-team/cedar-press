#!/usr/bin/env python3
"""1088 - merge the four staged deal channels into the deals ledger.

Three separate agents staged candidates and NONE were merged, because each
needs a READ rather than a blind append. This script is that read, expressed
as ordered gates so the refusals are auditable and reproducible.

    data/staging/deals_from_newsletters/deal_candidates_screened.csv
        258 tier-A promotable rows (286 minus 28 self-duplicates)
    review/deals_sec_edgar_1032_staged.csv          21 EDGAR transactions
    review/deals_ancsa_1031_staged.csv              24 ANCSA AS 45.55.139 rows
    review/deals_sec_edgar_1032_held_terms.csv       3 held on a terms question
    review/1071_identifier_deal_candidates.csv       6 identifier-driven changes

WHAT THIS SCRIPT REFUSES, AND WHY EACH REFUSAL IS A RULE AND NOT A TASTE
-----------------------------------------------------------------------
G0  NOT_INDIAN_COUNTRY
    A place name is not a nation. "FRIENDS OF SOUTH CONGAREE - PINE RIDGE
    LIBRARY" is a South Carolina library group that matched on `Pine Ridge`;
    "FRIENDS OF TEN MILE CREEK AND LITTLE SENECA RESERVOIR" is a Montgomery
    County, Maryland watershed group that matched on `Seneca`. START_HERE:
    "A place suffix makes a tribe name a place."

G1  DATE_NOT_IN_EVIDENCE
    docs/methodology/deals.md: "Never write a row whose DATE is not in
    retrieved evidence. Skip and log."

G2  PARENTAGE_STATEMENT_NOT_A_TRANSACTION
    "X is a wholly owned subsidiary of Y" is a standing corporate fact with no
    date and no consideration. The screen's own tier D is defined as exactly
    this class; 24 rows leaked past it into tier A because the phrase also
    appears inside sentences that carry a transaction verb. These belong in
    `nest_enterprise_relations.csv`, which already records them from audited
    filings under Alaska Statute 45.55.139.

G3  FEDERAL_AWARD_NOT_A_DEAL
    A federal contract award is `prime_contracts`, a Cedar dataset of
    1,217,768 rows. Re-publishing a press release about one as a "deal" makes
    a second, keyless copy of a transaction Cedar already holds, and it is how
    the $151B IDIQ CEILING entered this staging set. The owner's rule is
    thirteen clean datasets, each one the home of its own event class.

G4  MILESTONE_NOT_A_TRANSACTION
    A groundbreaking is a construction milestone. No counterparty, no
    consideration, no transfer.

G5  PARTY_IS_PUBLISHER_NOT_TRANSACTOR
    THE SHARPEST OF THE FOUR WARNINGS IN THE MERGE PROPOSAL. `Native_Party`
    in the staging file is the PUBLISHER of the page, which is a strong prior
    and not a fact. A tribal newspaper, an intertribal association and a
    regional nonprofit consortium all report on transactions they are not
    party to.

    The gate is TWO conditions, never one, because either alone misfires:
      (a) the host is a hand-classified third-party publisher, AND
      (b) no distinctive token of the assigned party appears in the source
          sentence.
    Condition (a) alone would refuse `oan.srpmic-nsn.gov` reporting the Salt
    River Pima-Maricopa Indian Community's own Pavilions acquisition, which is
    real. Condition (b) alone would refuse 105 rows on nothing but an
    ABBREVIATION - "ASRC Industrial Services Acquires Mavo Systems" shares no
    token with "Arctic Slope Regional Corporation", and that row is correct.
    A one-condition version of this gate was written, measured, and thrown
    away for that reason; it is the repo's signature defect (AGENT_FIELD_GUIDE
    section 3), a check that produces a plausible number about something else.

G6  INTRA_FAMILY_RELABELLING
    A move between two sub-hubs of one nation is a relabelling, not a
    transaction - the owner's own example is "All Native Group -> Ho-Chunk
    Inc". Re-run here against `nest_enterprise_relations.csv`, which did not
    exist when the newsletter screen ran its own intra-family test.

    TWO MEASURED CORRECTIONS TO THIS GATE, both made after the first version
    of it was run and its refusals were read one by one:

    (i)  `cedar_constellation_edges.csv` IS NOT AN OWNERSHIP SOURCE and is not
         used here. All 3,153 of its rows carry `is_ownership_claim = N`, and
         its five tiers are `registered_with` (2,365), `declares_service_to`
         (588), `managed_under_contract` (78), `located_within` (78) and
         `chartered_by` (44). None of those is ownership. A college
         `chartered_by` a nation is a separate legal person - the ledger's own
         instrumentality rule - and folding it into the nation's corporate
         family would refuse real transactions. Within
         `nest_enterprise_relations.csv` the same discipline applies: only
         `relation_class = ownership` counts, and `joint_venture` (157 edges)
         and `passive_investment` (10) are EXCLUDED from the family, because a
         joint venture between two families is exactly the transaction this
         dataset exists to record. The first version of this gate ingested
         both files wholesale and, through an `affiliation` edge reading
         "Doyon, Limited publishes these as its own operating companies", made
         HUNA TOTEM CORPORATION - an independent Hoonah village corporation -
         a member of Doyon's family, and refused five real Doyon rows on it.

    (ii) A PRESENT-TENSE OWNERSHIP MAP INVERTS THE TEST ON A PAST
         ACQUISITION. This is the trap, and it is general. Bering Straits
         acquired Alaska Gold Company from NovaGold in 2012; Alaska Gold is a
         BSNC subsidiary TODAY, so a naive shared-hub test calls the 2012
         purchase an intra-family relabelling and throws away the very event
         that created the relationship. A map built from today's ownership
         will refuse exactly the acquisitions that succeeded. So a shared hub
         is a NECESSARY condition here, never a sufficient one.

    (iii) THE FIX FOR (ii) THAT DID NOT WORK, RECORDED BECAUSE IT LOOKS
         CORRECT. The second version asked whether the sentence names an
         organisation OUTSIDE the family for the transaction to be with. That
         test is circular for the same reason (ii) is: the target of a
         successful acquisition is a family member by the time the map is
         built, so it is never "outside". It still refused UIC/Johansen
         Construction, Choggiung/Bristol Industries, Shee Atika/Eikon Research
         and eleven ASRC Industrial acquisitions.
         What finally works is not topology at all but what the passage DOES -
         a transfer verb means a transaction and overrules the topology, a
         reorganisation verb means a relabelling and confirms it, and an
         identifier flip with no sentence has only the topology to go on. The
         gate went 34 -> 24 -> 2 refusals across those three versions, and the
         32 rows it stopped refusing are real transactions. See
         `intra_family()`.

G7  DUPLICATE_OF_LEDGER / DUPLICATE_INTERNAL
    Party + year + a shared distinctive counterparty token, plus an exact
    URL+nucleus test inside the staged set.

VALUE HANDLING - a ceiling is not a value
-----------------------------------------
V1 does NOT refuse a row. It moves a non-consideration sum out of
`Announced_Value_USD` into `Project_Total_Value_USD` and records the reason in
`Value_Type`, so the row survives and the total does not lie. An IDIQ ceiling
is the maximum the government MAY spend across every awardee on a
multiple-award vehicle; it is not money this nation received. The largest sum
in the staging set is one of these at $151,000,000,000.

TERMS SCOPE
-----------
`docs/PUBLICATION_POLICY.md` <!-- BEGIN TERMS-SCOPE -->, ruling 2026-09-02: a
restriction binds what the restricted entity published, not a third party's
SEC filing about them. The three held EDGAR families are released on that
basis. Releasing them yields ONE deal row, not three - see the disposition.

USAGE
    py -3 code/1088_merge_staged_deals.py            # dry report, writes nothing
    py -3 code/1088_merge_staged_deals.py --execute  # write additions + refusals
    py -3 code/1088_merge_staged_deals.py verify     # exits 1 on breach
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
STAGE = CEDAR / "data" / "staging" / "deals_from_newsletters"

TODAY = date.today().isoformat()
STEM = "1088_merge_staged_deals"

ADDITIONS = CLEAN / "deals_press_edgar_ancsa_additions.csv"
REFUSALS = REVIEW / "deals_1088_refusals.csv"
DISPOSITION = REVIEW / "deals_1088_disposition.json"

# The 32 base columns every deals_*_additions.csv carries. The 20 taxonomy and
# attribution columns are DERIVED by 88_build_deals_taxonomy.py and
# 126_apply_deal_party_attribution.py; writing them here would put this script
# in competition with the enricher that owns them.
BASE_COLS = [
    "Deal_ID", "Event_Date", "Event_Year", "Event_Quarter", "Event_Month",
    "Deal_Title", "Native_Party", "Native_Party_Type", "Counterparty_or_Funder",
    "Deal_Category", "Industry", "Event_Type", "Status", "Record_Scope",
    "Announced_Value_USD", "Value_Type", "Project_Total_Value_USD", "State",
    "Location", "Description", "Native_Connection", "Source_1", "Source_1_Type",
    "Source_2", "Source_2_Type", "Verification_Status", "Confidence",
    "Threshold_Exception", "Date_Basis", "Notes", "Date_Added", "Data_As_Of",
]


# ---------------------------------------------------------------- helpers ---
def read(path, required=True):
    p = Path(path)
    if not p.exists():
        if required:
            raise SystemExit(f"MISSING INPUT: {p}")
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


GENERIC = set("""
the of and a an for inc llc corp corporation company co ltd limited incorporated
tribe tribes tribal nation nations native natives indian indians band bands
community communities pueblo rancheria village villages group holdings holding
association associations coalition federation network commission council fund
foundation american america authority enterprise enterprises services service
development corporationinc gaming health center centre institute society
""".split())


def toks(s):
    return [t for t in re.findall(r"[a-z0-9']+", (s or "").lower()) if len(t) > 2]


def distinctive(s):
    return {t for t in toks(s) if t not in GENERIC}


def host_of(url):
    try:
        return urlparse(url or "").netloc.lower().replace("www.", "")
    except Exception:
        return ""


def money(s):
    s = (s or "").strip().replace(",", "").replace("$", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ------------------------------------------------- hand-classified hosts ---
# Read once, by hand, on 2026-09-02. A host is a THIRD-PARTY PUBLISHER when the
# site's business is reporting, convening or advocacy rather than transacting.
# The reason is recorded per host so the next reader can disagree with a
# specific claim rather than with a list.
THIRD_PARTY_PUBLISHER = {
    "seminoletribune.org":     "The Seminole Tribune is a newspaper; it reports on gaming and energy companies the Tribe is not party to",
    "alaska-native-news.com":  "Statewide news aggregator; its article stream is national wire copy, not one nation's transactions",
    "osagenews.org":           "Osage News is an independent newspaper of record",
    "theonefeather.com":       "The Cherokee One Feather is a newspaper",
    "sninews.org":             "Seneca Nation news service",
    "navajotimes.com":         "The Navajo Times is a newspaper",
    "tulaliptv.com":           "Tulalip TV is a broadcast news outlet",
    "nativefederation.org":    "Alaska Federation of Natives - a convening body reporting on member corporations",
    "azindiangaming.org":      "Arizona Indian Gaming Association - a trade association reporting on member operations",
    "mnindiangamingassoc.com": "Minnesota Indian Gaming Association - a trade association reporting on member operations",
    "largetribes.org":         "Coalition of Large Tribes - an intertribal advocacy coalition reporting on member nations",
    "nafoa.org":               "NAFOA - a finance-officer association publishing explainers, not transactions",
    "nativecdfi.net":          "Native CDFI Network - a membership network reporting on members",
    "narf.org":                "Native American Rights Fund - a litigation organisation; its pages report cases, not deals",
    "critfc.org":              "Columbia River Inter-Tribal Fish Commission - an intertribal commission reporting on member nations",
    "nwifc.org":               "Northwest Indian Fisheries Commission - an intertribal commission reporting on member nations",
    "kawerak.org":             "Kawerak Inc is a regional nonprofit consortium reporting on its twenty member villages",
    "nwmt.org":                "NeighborWorks Montana - a housing intermediary reporting on partner developers",
    "montgomeryplanning.org":  "Montgomery County (Maryland) Planning Department - not an Indian Country publisher at all",
    "scprfriends.org":         "Friends of the South Congaree-Pine Ridge Library (South Carolina) - not an Indian Country publisher at all",
}

# Hand read, with the quote that convicts each. These two are not Indian
# Country entities; they entered the candidate set through a place-name match.
NOT_INDIAN_COUNTRY = {
    "FRIENDS OF SOUTH CONGAREE - PINE RIDGE LIBRARY":
        "A South Carolina library friends group. It matched the token 'Pine Ridge' (South Congaree-Pine Ridge, SC), not the Oglala Lakota reservation.",
    "FRIENDS OF TEN MILE CREEK AND LITTLE SENECA RESERVOIR":
        "A Montgomery County, Maryland watershed group published by montgomeryplanning.org. It matched the token 'Seneca' (Little Seneca Reservoir), not the Seneca Nation.",
}

PARENTAGE_PHRASE = re.compile(
    r"wholly[\s-]owned subsidiary|new subsidiary|wholly owned subsidiary", re.I)
AWARD_PHRASE = re.compile(
    r"\bawarded\b|\bwas awarded\b|awarded a contract|awarded the\b", re.I)
MILESTONE_PHRASE = re.compile(r"groundbreaking|broke ground", re.I)

# A sum that is a limit, a ceiling, a carrying amount or a programme total is
# not consideration. Matched against the staged value_basis / value_type text.
CEILING_PAT = re.compile(
    r"ceiling|idiq|indefinite[- ]delivery|multiple[- ]award|maximum|\bup to\b|"
    r"not[- ]to[- ]exceed|carrying amount|aggregate principal amount of the facility|"
    r"programme total|program total|potential value", re.I)


# ---------------------------------------------------- intra-family lookup ---
# Only these relationships put two names in ONE corporate family. A joint
# venture between two families is a transaction, not a family.
OWNED = {"wholly_owned", "subsidiary", "majority_owned", "operating_company",
         "holding_company", "division", "declared_suborganization"}

REORG_PHRASE = re.compile(
    r"now operate[s]? under|now part of|reorganiz|reorganis|renamed|"
    r"transferred to|consolidated under|newly established holding company|"
    r"family of companies|rebrand|operate under .{0,40}holding", re.I)

# A transfer verb. If the sentence performs a transfer, the sentence is a
# transaction and the family topology cannot overrule it - see the third
# correction in `intra_family`.
TRANSFER_VERB = re.compile(
    r"\bacquir\w*|\bacquisition\b|\bpurchas\w*|\bbought\b|\bbuys\b|\bsold\b|"
    r"\bsells\b|\bsale of\b|\bmerg\w*|\bdivest\w*|\btook a .{0,20}stake\b|"
    r"\bmajority interest\b|\bcontrolling interest\b", re.I)


def build_family_map():
    """name -> set(hub uid), and hub uid -> set(member names).

    Built from `nest_enterprise_relations.csv` OWNERSHIP edges only. See the
    module docstring, correction (i), for why the constellation file is not
    read here and why joint ventures are excluded.
    """
    fam = defaultdict(set)
    members = defaultdict(set)
    hub_name = {}

    def norm(n):
        n = re.sub(r"[^a-z0-9 ]", " ", (n or "").lower())
        n = re.sub(r"\b(inc|llc|ltd|limited|corp|corporation|co|company|the|lp|llp|plc)\b", " ", n)
        return re.sub(r"\s+", " ", n).strip()

    kept = 0
    # CLASS 2C: a skip counter that does not name what it skipped is a defect
    # class this repo has thirteen recorded instances of. Name them.
    skipped = Counter()
    eg = {}
    for r in read(CLEAN / "nest_enterprise_relations.csv", required=False):
        hub = r.get("owner_hub_cedar_uid") or ""
        if not hub:
            skipped["no_owner_hub_cedar_uid"] += 1
            eg.setdefault("no_owner_hub_cedar_uid",
                          r.get("child_name_as_recorded", "?"))
            continue
        rc, rel = (r.get("relation_class") or ""), (r.get("relationship") or "")
        if rc != "ownership" or rel not in OWNED:
            tag = f"{rc or 'blank'}/{rel or 'blank'}"
            skipped[tag] += 1
            eg.setdefault(tag, f"{r.get('child_name_as_recorded','?')} under "
                               f"{r.get('owner_hub_name','?')}")
            continue
        kept += 1
        hub_name[hub] = r.get("owner_hub_name") or hub
        for n in (r.get("child_name_as_recorded"),
                  r.get("parent_name_as_recorded"),
                  r.get("owner_hub_name")):
            if norm(n):
                fam[norm(n)].add(hub)
                members[hub].add(norm(n))
    print(f"  nest edges: {kept:,} ownership kept, {sum(skipped.values()):,} skipped:")
    for tag, n in skipped.most_common():
        print(f"      {n:>5}  {tag:<34} e.g. {eg[tag][:64]}")
    print("  cedar_constellation_edges.csv NOT USED as a family source: "
          "is_ownership_claim = N on all 3,153 rows")
    return fam, hub_name, norm, members


def intra_family(party, counterparty, text, fam, hub_name, norm, members,
                 has_sentence=True):
    """Shared hub is NECESSARY, never SUFFICIENT when a sentence exists.

    THIRD CORRECTION, and the one that finally made this gate honest. The
    second version asked "does the sentence name an organisation outside the
    family for the transaction to be with?" That test is CIRCULAR on exactly
    the rows it was meant to judge: a company that has just been acquired is a
    family member by the time the map is built, so the target of a successful
    acquisition is never "outside". It refused UIC/Johansen Construction,
    Choggiung/Bristol Industries, Shee Atika/Eikon Research and eleven ASRC
    Industrial acquisitions - all real, all with a named external target that
    the map had already absorbed.

    The discriminator is not topology, it is what the sentence DOES.

      * A press or filing passage that performs a TRANSFER - acquires,
        purchases, merges, divests, takes a majority interest - is a
        transaction. Family topology cannot overrule the verb, because the
        topology is downstream of the event.
      * A passage that performs a REORGANISATION - now operates under,
        transferred to, consolidated under, a newly established holding
        company - is a relabelling, and that is what G6 exists to catch.
      * An IDENTIFIER OBSERVATION has no sentence at all. There is only a
        parent-UEI flip between two nodes, and if both nodes are in one family
        that flip IS the relabelling. This is the owner's own example,
        "All Native Group -> Ho-Chunk Inc", and it is the only channel where a
        shared hub alone is sufficient.
    """
    if not (party or "").strip() or not (counterparty or "").strip():
        return False, ""
    a, b = fam.get(norm(party), set()), fam.get(norm(counterparty), set())
    shared = a & b
    if not shared:
        return False, ""
    h = sorted(shared)[0]
    label = f"hub {h} ({hub_name.get(h, h)})"

    if not has_sentence:
        return True, (f"both sides resolve to {label} in nest_enterprise_relations "
                      f"and there is no source sentence - an identifier flip inside "
                      f"one family is a relabelling, the owner's 'All Native Group -> "
                      f"Ho-Chunk Inc' case")

    if REORG_PHRASE.search(text or ""):
        return True, (f"both sides resolve to {label} in nest_enterprise_relations "
                      f"AND the passage uses a reorganisation verb, not a transfer "
                      f"verb - a relabelling of companies already inside the family")

    if TRANSFER_VERB.search(text or ""):
        return False, ""

    return True, (f"both sides resolve to {label} in nest_enterprise_relations "
                  f"and the passage performs no transfer - it states a standing "
                  f"internal relationship")


# ------------------------------------------------------------------ gates ---
def gate_newsletter(r, fam, hub_name, norm, members):
    """Return (refusal_reason, refusal_basis) or ('', '')."""
    party = (r.get("Native_Party") or "").strip()
    desc = r.get("Description") or ""
    phrase = r.get("matched_phrase") or ""
    host = host_of(r.get("Source_1"))

    if party.upper() in NOT_INDIAN_COUNTRY:
        return "G0_NOT_INDIAN_COUNTRY", NOT_INDIAN_COUNTRY[party.upper()]

    if not (r.get("Event_Date") or "").strip():
        return ("G1_DATE_NOT_IN_EVIDENCE",
                "the source sentence carries no date; methodology forbids writing the row")

    if PARENTAGE_PHRASE.search(phrase):
        return ("G2_PARENTAGE_STATEMENT_NOT_A_TRANSACTION",
                f"matched phrase {phrase!r} states standing corporate parentage, "
                f"not a dated transfer; belongs in nest_enterprise_relations.csv")

    if AWARD_PHRASE.search(phrase):
        return ("G3_FEDERAL_AWARD_NOT_A_DEAL",
                f"matched phrase {phrase!r} is a federal contract award; that event "
                f"class is prime_contracts.csv, and re-publishing it here makes a "
                f"second keyless copy")

    if MILESTONE_PHRASE.search(phrase):
        return ("G4_MILESTONE_NOT_A_TRANSACTION",
                f"matched phrase {phrase!r} is a construction milestone - no "
                f"counterparty, no consideration, no transfer")

    if host in THIRD_PARTY_PUBLISHER:
        d = distinctive(party)
        sent = set(toks(desc))
        if d and not (d & sent):
            return ("G5_PARTY_IS_PUBLISHER_NOT_TRANSACTOR",
                    f"host {host} is a third-party publisher ({THIRD_PARTY_PUBLISHER[host]}) "
                    f"and no distinctive token of {party!r} ({sorted(d)}) appears in the "
                    f"source sentence - the assigned party is the PUBLISHER, not the transactor")

    hit, basis = intra_family(party, r.get("Counterparty_or_Funder"), desc,
                              fam, hub_name, norm, members)
    if hit:
        return "G6_INTRA_FAMILY_RELABELLING", basis

    return "", ""


def gate_staged(r, fam, hub_name, norm, members):
    """EDGAR / ANCSA staged rows - hand-curated, so only the structural gates."""
    if not (r.get("event_date") or "").strip():
        return ("G1_DATE_NOT_IN_EVIDENCE",
                "the filing passage carries no date")
    hit, basis = intra_family(r.get("native_party"), r.get("counterparty"),
                              (r.get("evidence_quote") or "") + " " + (r.get("deal_title") or ""),
                              fam, hub_name, norm, members)
    if hit:
        return "G6_INTRA_FAMILY_RELABELLING", basis
    return "", ""


# ------------------------------------------------------------------ value ---
def apply_value_rule(value, basis_text):
    """(announced, project_total, value_type_note, moved).

    A ceiling never enters Announced_Value_USD. It is parked in
    Project_Total_Value_USD, which is exactly where the methodology already
    parks the Poarch Creek $24.1M FHWA total and the Native Forward $50M gift.
    """
    v = money(value)
    if v is None:
        return "", "", basis_text or "", False
    if CEILING_PAT.search(basis_text or ""):
        return ("", f"{v:.0f}",
                f"NOT CONSIDERATION - moved out of Announced_Value_USD by "
                f"code/1088 ceiling rule. Source basis: {basis_text}", True)
    return f"{v:.0f}", "", basis_text or "", False


# ------------------------------------------------------------------- main ---
def existing_ledger():
    """The ledger AS IT WAS BEFORE THIS SCRIPT.

    A merge script that de-duplicates against its own previous output is not
    idempotent, it is self-erasing: the second run sees its own 144 rows in
    `deals_classified.csv`, refuses them all as G7 duplicates, admits 64, and
    REWRITES the additions file at 64 rows - so the next rebuild silently
    loses 80. Measured on the second run of this script before the guard
    existed. `_source_file` is the discriminator and it is exact.
    """
    rows = read(CLEAN / "deals_classified.csv")
    own = ADDITIONS.name
    mine = [r for r in rows if r.get("_source_file") == own]
    if mine:
        print(f"  {len(mine)} row(s) in the ledger came from a previous run of this "
              f"script ({own}) and are EXCLUDED from the duplicate index, so a "
              f"re-run reproduces its own output instead of eroding it.")
    prior = [r for r in rows if r.get("_source_file") != own]
    idx = defaultdict(list)
    for r in prior:
        key = (norm_party(r.get("Native_Party")), (r.get("Event_Year") or "").strip())
        idx[key].append(r)
    return rows, idx, prior


def norm_party(n):
    return " ".join(sorted(distinctive(n)))


def is_dup_of_ledger(party, year, counterparty, idx):
    cands = idx.get((norm_party(party), str(year).strip()), [])
    if not cands:
        return None
    cp = distinctive(counterparty)
    for c in cands:
        if cp and cp & distinctive(c.get("Counterparty_or_Funder")):
            return c.get("Deal_ID")
    return None


def main(argv):
    execute = "--execute" in argv
    verify = "verify" in argv
    if "--selftest" in argv:
        return selftest()

    fam, hub_name, norm, members = build_family_map()
    print(f"family map: {len(fam):,} names -> {len(hub_name):,} hubs "
          f"(nest_enterprise_relations, ownership edges only)")

    ledger, lidx, prior = existing_ledger()
    # Every comparison is against the ledger MINUS this script's own prior
    # output, so a re-run reproduces its result instead of colliding with it.
    known_ids = {r["Deal_ID"] for r in prior}
    ledger_money = sum(money(r.get("Announced_Value_USD")) or 0 for r in prior)
    print(f"ledger before this script: {len(prior):,} rows, "
          f"Announced_Value_USD = ${ledger_money:,.0f}\n")

    admitted, refused = [], []
    counts = Counter()
    seq = Counter()

    def new_id(prefix, year):
        seq[(prefix, year)] += 1
        return f"{prefix}-{year}-{seq[(prefix, year)]:03d}"

    # ---------------------------------------------------- 1. newsletters ---
    nl = [r for r in read(STAGE / "deal_candidates_screened.csv")
          if r["screen_tier"] == "tier_A_promotable" and not r["duplicate_of"]]
    counts["newsletter_tierA_unique_in"] = len(nl)
    seen_nucleus = {}
    for r in nl:
        reason, basis = gate_newsletter(r, fam, hub_name, norm, members)
        # ONE ARTICLE REPORTING ONE DATED EVENT IS ONE ROW. The screen's own
        # de-duplication is per SENTENCE, so the BBNC/Alaska Growth Capital
        # acquisition of 2024-12-31 arrived as three rows off one press
        # release and the F. D. Thomas acquisition of 2018-04-11 as two. A
        # per-sentence key cannot see that; (url, date) can. The losers are
        # written WHOLE to the refusal register naming the survivor, so the
        # collapse is reversible and nothing retrieved is lost - the same
        # posture script 54 takes with a withdrawn duplicate.
        nuc = (r.get("Source_1", ""), (r.get("Event_Date") or "").strip())
        if not reason and nuc in seen_nucleus:
            reason, basis = ("G7_DUPLICATE_INTERNAL",
                             f"same source URL and same event date as "
                             f"{seen_nucleus[nuc]}, which was admitted; one article "
                             f"reporting one dated event is one row")
        if not reason:
            d = is_dup_of_ledger(r.get("Native_Party"), r.get("Event_Year"),
                                 r.get("Counterparty_or_Funder"), lidx)
            if d:
                reason, basis = ("G7_DUPLICATE_OF_LEDGER",
                                 f"party+year+counterparty token match on {d}")
        if reason:
            counts[reason] += 1
            refused.append(dict(
                staged_id=r["candidate_id"], channel="tribal_press",
                native_party=r.get("Native_Party", ""),
                counterparty=r.get("Counterparty_or_Funder", ""),
                event_date=r.get("Event_Date", ""),
                announced_value_usd=r.get("Announced_Value_USD", ""),
                source_url=r.get("Source_1", ""),
                evidence=(r.get("Description") or "")[:400],
                refusal_reason=reason, refusal_basis=basis,
                refused_by=f"code/{STEM}.py", refused_date=TODAY))
            continue

        year = (r.get("Event_Year") or (r.get("Event_Date") or "")[:4]).strip()
        av, pv, vnote, moved = apply_value_rule(r.get("Announced_Value_USD"),
                                                r.get("value_basis"))
        if moved:
            counts["V1_ceiling_moved_to_project_total"] += 1
        admitted.append({
            "Deal_ID": new_id("NLTR", year),
            "Event_Date": r.get("Event_Date", ""), "Event_Year": year,
            "Event_Quarter": "", "Event_Month": "",
            "Deal_Title": (r.get("Description") or "")[:180],
            "Native_Party": r.get("Native_Party", ""),
            "Native_Party_Type": r.get("native_party_entity_class", ""),
            "Counterparty_or_Funder": r.get("Counterparty_or_Funder", ""),
            "Deal_Category": "Private transaction",
            "Industry": "", "Event_Type": r.get("Event_Type", ""),
            "Status": r.get("Status", ""), "Record_Scope": "TRANSACTION_CANDIDATE_TRIBAL_PRESS",
            "Announced_Value_USD": av, "Value_Type": vnote,
            "Project_Total_Value_USD": pv,
            "State": r.get("State", ""), "Location": "",
            "Description": r.get("Description", ""),
            "Native_Connection": "Party is the transacting Native entity named in the source sentence; publisher-vs-party read applied by code/1088 gate G5",
            "Source_1": r.get("Source_1", ""),
            "Source_1_Type": r.get("Source_1_Type", "") or "Tribal newsletter / tribal press",
            "Source_2": "", "Source_2_Type": "",
            "Verification_Status": "Single source (tribal press)",
            "Confidence": r.get("Confidence", ""),
            "Threshold_Exception": "Yes" if (money(av) or 0) < 1_000_000 else "",
            "Date_Basis": r.get("date_basis", ""),
            "Notes": f"Staged by code/994; merged by code/{STEM}.py after gates G0-G7. "
                     f"deal_status_std from source: {r.get('deal_status_std','')}. "
                     f"{r.get('status_basis','')}",
            "Date_Added": TODAY, "Data_As_Of": r.get("retrieved_date", "") or TODAY,
        })
        seen_nucleus[nuc] = admitted[-1]["Deal_ID"]

    # -------------------------------------------------- 2. EDGAR + ANCSA ---
    for path, prefix, chan in ((REVIEW / "deals_sec_edgar_1032_staged.csv", "SECX", "sec_edgar"),
                               (REVIEW / "deals_ancsa_1031_staged.csv", "ANCSA3", "ancsa_star_portal")):
        rows = read(path)
        counts[f"{chan}_in"] = len(rows)
        for r in rows:
            reason, basis = gate_staged(r, fam, hub_name, norm, members)
            if not reason:
                d = is_dup_of_ledger(r.get("native_party"), r.get("event_year"),
                                     r.get("counterparty"), lidx)
                if d:
                    reason, basis = ("G7_DUPLICATE_OF_LEDGER",
                                     f"party+year+counterparty token match on {d}")
            if reason:
                counts[reason] += 1
                refused.append(dict(
                    staged_id=r["candidate_id"], channel=chan,
                    native_party=r.get("native_party", ""),
                    counterparty=r.get("counterparty", ""),
                    event_date=r.get("event_date", ""),
                    announced_value_usd=r.get("announced_value_usd", ""),
                    source_url=r.get("source_url", ""),
                    evidence=(r.get("evidence_quote") or "")[:400],
                    refusal_reason=reason, refusal_basis=basis,
                    refused_by=f"code/{STEM}.py", refused_date=TODAY))
                continue
            year = (r.get("event_year") or (r.get("event_date") or "")[:4]).strip()
            av, pv, vnote, moved = apply_value_rule(r.get("announced_value_usd"),
                                                    r.get("value_type"))
            if moved:
                counts["V1_ceiling_moved_to_project_total"] += 1
            src_type = ("SEC filing (EDGAR)" if chan == "sec_edgar" else
                        "ANCSA corporation annual report filed with the Alaska "
                        "Division of Banking and Securities (STAR portal)")
            admitted.append({
                "Deal_ID": new_id(prefix, year),
                "Event_Date": r.get("event_date", ""), "Event_Year": year,
                "Event_Quarter": "", "Event_Month": "",
                "Deal_Title": r.get("deal_title", ""),
                "Native_Party": r.get("native_party", ""),
                "Native_Party_Type": r.get("native_party_type", ""),
                "Counterparty_or_Funder": r.get("counterparty", ""),
                "Deal_Category": r.get("deal_category", ""),
                "Industry": r.get("industry", ""),
                "Event_Type": r.get("instrument", ""),
                "Status": r.get("status", ""),
                "Record_Scope": r.get("record_scope", ""),
                "Announced_Value_USD": av, "Value_Type": vnote,
                "Project_Total_Value_USD": pv,
                "State": r.get("state", ""), "Location": "",
                "Description": r.get("evidence_quote", ""),
                "Native_Connection": "Native party named in the filing text",
                "Source_1": r.get("source_url", ""), "Source_1_Type": src_type,
                "Source_2": "", "Source_2_Type": "",
                "Verification_Status": "Primary filing retrieved and read",
                "Confidence": r.get("confidence", ""),
                "Threshold_Exception": "Yes" if 0 < (money(av) or 0) < 1_000_000 else "",
                "Date_Basis": r.get("date_basis", ""),
                "Notes": f"Staged by {r.get('staged_by','')}; merged by code/{STEM}.py "
                         f"after gates G1/G6/G7. {r.get('notes','')}",
                "Date_Added": TODAY, "Data_As_Of": r.get("staged_date", "") or TODAY,
            })

    # ------------------------------------------- 3. terms-released EDGAR ---
    # The ruling releases three FAMILIES. Only one of the three holds a
    # transaction. Saying "3 released" and shipping 3 rows would be the
    # error; the honest count is 1.
    held = read(REVIEW / "deals_sec_edgar_1032_held_terms.csv")
    counts["terms_held_families_in"] = len(held)
    TERMS_DISPOSITION = {
        "HOLD-1030-001": ("ADMIT", None),
        "HOLD-1030-002": ("REFUSE", ("V1_CARRYING_AMOUNT_NOT_A_TRANSACTION",
                                     "$14,452 thousand is the GROSS CARRYING AMOUNT of an "
                                     "amortising intangible on MACH's balance sheet, not a "
                                     "stated purchase price, and the filing gives no transaction "
                                     "date. Terms are no longer the obstacle; the value and date "
                                     "rules are.")),
        "HOLD-1030-003": ("REFUSE", ("G8_NO_TRANSACTION_DISCLOSED",
                                     "AP Gaming Holdco's DRS/A names the Chickasaw Nation in "
                                     "market and customer context only. The filing discloses no "
                                     "transaction, so the terms release yields nothing here.")),
    }
    for r in held:
        act, ref = TERMS_DISPOSITION.get(r["hold_id"], ("REFUSE", ("G9_UNRULED", "no disposition")))
        if act == "REFUSE":
            counts[ref[0]] += 1
            refused.append(dict(
                staged_id=r["hold_id"], channel="sec_edgar_terms_released",
                native_party=r.get("restricted_family", ""), counterparty="",
                event_date="", announced_value_usd="",
                source_url=r.get("source_url", ""),
                evidence=(r.get("what_the_filing_says") or "")[:400],
                refusal_reason=ref[0], refusal_basis=ref[1],
                refused_by=f"code/{STEM}.py", refused_date=TODAY))
            continue
        counts["terms_released_admitted"] += 1
        admitted.append({
            "Deal_ID": new_id("SECX", "2020"),
            "Event_Date": "2020-02-11", "Event_Year": "2020",
            "Event_Quarter": "Q1", "Event_Month": "2020-02",
            "Deal_Title": "NANA Regional Corporation and Trilogy Metals form Ambler Metals LLC, "
                          "a 50/50 joint venture with South32",
            "Native_Party": "NANA Regional Corporation, Inc.",
            "Native_Party_Type": "Alaska Native regional corporation",
            "Counterparty_or_Funder": "Trilogy Metals Inc.; South32 Limited",
            "Deal_Category": "Joint venture", "Industry": "Mining",
            "Event_Type": "Joint venture formation", "Status": "Completed",
            "Record_Scope": "TRANSACTION",
            "Announced_Value_USD": "145000000",
            "Value_Type": "South32 subscription into Ambler Metals LLC on completion, as stated in "
                          "Trilogy Metals' filing. NANA's own consideration is a 1% net smelter "
                          "royalty plus $755/acre on the first 400 acres and is NOT a dollar sum.",
            "Project_Total_Value_USD": "", "State": "AK",
            "Location": "Upper Kobuk Mineral Projects, Alaska",
            "Description": (held[0].get("what_the_filing_says") or "")[:900],
            "Native_Connection": "NANA is a party to the NANA Agreement recited in the filing",
            "Source_1": held[0].get("source_url", ""),
            "Source_1_Type": "SEC filing (Form 10-K, Trilogy Metals Inc.)",
            "Source_2": "", "Source_2_Type": "",
            "Verification_Status": "Primary filing retrieved and read",
            "Confidence": "High",
            "Threshold_Exception": "", "Date_Basis": "Completion date stated in the filing",
            "Notes": "TERMS-SCOPE RULING 2026-09-02 (docs/PUBLICATION_POLICY.md): NANA is "
                     "TERMS_STATED_RESTRICTIVE, but those terms are NANA's own site terms. This "
                     "is Trilogy Metals' SEC filing under a federal disclosure obligation; NANA "
                     "set no terms over it and could not. Released on authorship, not subject "
                     f"matter. Merged by code/{STEM}.py.",
            "Date_Added": TODAY, "Data_As_Of": TODAY,
        })

    # ------------------------------------------ 4. identifier-driven obs ---
    ids = read(REVIEW / "1071_identifier_deal_candidates.csv")
    counts["identifier_candidates_in"] = len(ids)
    for r in ids:
        cid = r["candidate_id"]
        # An identifier flip inside one family is a relabelling. No sentence
        # exists, so the shared hub is sufficient - see intra_family().
        hit, basis = intra_family(r.get("prior_side_name"), r.get("later_side_name"),
                                  "", fam, hub_name, norm, members,
                                  has_sentence=False)
        if hit:
            counts["G6_INTRA_FAMILY_RELABELLING"] += 1
            refused.append(dict(
                staged_id=cid, channel="identifier_observation",
                native_party=r.get("prior_side_name", ""),
                counterparty=r.get("later_side_name", ""),
                event_date="", announced_value_usd="", source_url="",
                evidence=(r.get("evidence_note") or "")[:400],
                refusal_reason="G6_INTRA_FAMILY_RELABELLING", refusal_basis=basis,
                refused_by=f"code/{STEM}.py", refused_date=TODAY))
            continue
        if (r.get("already_in_deals_classified") or "").upper() == "YES":
            counts["G7_DUPLICATE_OF_LEDGER"] += 1
            refused.append(dict(
                staged_id=cid, channel="identifier_observation",
                native_party=r.get("child_name", ""),
                counterparty=r.get("later_side_name", ""),
                event_date="", announced_value_usd="",
                source_url="", evidence=(r.get("evidence_note") or "")[:400],
                refusal_reason="G7_DUPLICATE_OF_LEDGER",
                refusal_basis=f"staging marks it already in the ledger: {r.get('deal_ledger_match','')}. "
                              f"NOTE the match is a LOOSE TOKEN test and some matches are federal "
                              f"AWARD rows (FA-*), not ownership deals - kept out rather than "
                              f"double-written, and left here as a re-read task.",
                refused_by=f"code/{STEM}.py", refused_date=TODAY))
            continue
        # The name-change artefact. Same UEI, awardee name goes from an
        # organisation to an individual's personal name. That is a registration
        # correction, not a change of hands.
        if cid == "IDS-DB74DA2B0248":
            counts["G10_REGISTRATION_CORRECTION_NOT_A_TRANSACTION"] += 1
            refused.append(dict(
                staged_id=cid, channel="identifier_observation",
                native_party=r.get("prior_side_name", ""),
                counterparty=r.get("later_side_name", ""),
                event_date="", announced_value_usd="", source_url="",
                evidence=(r.get("evidence_note") or "")[:400],
                refusal_reason="G10_REGISTRATION_CORRECTION_NOT_A_TRANSACTION",
                refusal_basis="UEI H3Y4JTE3SRJ4 keeps its identifier while awardee_name goes from "
                              "'Blackfeet Utilities' to 'William Allen Talks About' - a PERSONAL "
                              "NAME. An entity does not sell itself to a person and keep its UEI; "
                              "this is a registration/data correction across FY2004-2005. "
                              "docs/PUBLICATION_POLICY.md already records that a parent change "
                              "'is not always an acquisition - it can be a re-registration, a data "
                              "correction, or an internal reorganisation.'",
                refused_by=f"code/{STEM}.py", refused_date=TODAY))
            continue
        counts["identifier_observations_admitted"] += 1
        later_fy = (r.get("transition_between_fy") or "").split("->")[-1].strip()
        admitted.append({
            "Deal_ID": new_id("IDOBS", later_fy or "0000"),
            # DELIBERATELY BLANK. A fiscal-year boundary is a GAP, not a date,
            # and the ledger's own rule forbids inventing one. Event_Year is
            # never blank in this table, so it carries the window's end and
            # Date_Basis says what it is.
            "Event_Date": "", "Event_Year": later_fy,
            "Event_Quarter": "", "Event_Month": "",
            "Deal_Title": f"{r.get('child_name','')} moves from {r.get('prior_side_name','')} "
                          f"to {r.get('later_side_name','')} "
                          f"({r.get('transition_between_fy','')}, observed in federal filings)",
            "Native_Party": (r.get("prior_side_name") if r.get("direction") == "LEFT_NATIVE_FAMILY"
                             else r.get("later_side_name")) or "",
            "Native_Party_Type": "",
            "Counterparty_or_Funder": (r.get("later_side_name") if r.get("direction") == "LEFT_NATIVE_FAMILY"
                                       else r.get("prior_side_name")) or "",
            "Deal_Category": "Ownership change observed in federal identifier data",
            "Industry": "", "Event_Type": "Change of parent",
            "Status": "Observed in filings", "Record_Scope": "CEDAR_OBSERVATION_NOT_A_PUBLISHED_ANNOUNCEMENT",
            "Announced_Value_USD": "",
            "Value_Type": "No value published. Never inferred.",
            "Project_Total_Value_USD": "", "State": "", "Location": "",
            "Description": r.get("evidence_note", ""),
            "Native_Connection": f"{r.get('identifier_type','')} {r.get('identifier','')}; "
                                 f"direction {r.get('direction','')}",
            "Source_1": "data/clean/subawards.csv + data/clean/prime_contracts.csv "
                        "(USAspending / FPDS parent-UEI runs)",
            "Source_1_Type": "Cedar observation from federal identifier data",
            "Source_2": "", "Source_2_Type": "",
            "Verification_Status": "UNVERIFIED AGAINST ANY PUBLISHED ANNOUNCEMENT - this is an "
                                   "observation Cedar made, not a claim a source published",
            "Confidence": "Observation",
            "Threshold_Exception": "",
            "Date_Basis": f"FISCAL-YEAR WINDOW, NOT A DATE. The event lies somewhere in "
                          f"{r.get('transition_between_fy','')}. Event_Date is deliberately blank "
                          f"because no date is in retrieved evidence.",
            "Notes": f"{r.get('interpretation_caution','')} | Built from "
                     f"{r.get('built_by','')}, merged by code/{STEM}.py.",
            "Date_Added": TODAY, "Data_As_Of": TODAY,
        })

    # ---------------------------------------------------------- reporting ---
    print("DISPOSITION")
    print(f"  admitted           {len(admitted):>5}")
    print(f"  refused            {len(refused):>5}")
    total_in = (counts['newsletter_tierA_unique_in'] + counts['sec_edgar_in']
                + counts['ancsa_star_portal_in'] + counts['terms_held_families_in']
                + counts['identifier_candidates_in'])
    print(f"  candidates in      {total_in:>5}")
    assert len(admitted) + len(refused) == total_in, (
        f"CONSERVATION BREACH: {len(admitted)}+{len(refused)} != {total_in}")
    print("  candidate conservation: OK (admitted + refused == in)\n")
    for k, v in sorted(counts.items()):
        print(f"    {k:<52} {v:>6}")

    new_money = sum(money(a["Announced_Value_USD"]) or 0 for a in admitted)
    parked = sum(money(a["Project_Total_Value_USD"]) or 0 for a in admitted)
    print(f"\n  new Announced_Value_USD      ${new_money:,.0f}")
    print(f"  parked in Project_Total      ${parked:,.0f}  (ceilings, never summed as consideration)")
    print(f"  ledger after (projected)     {len(prior) + len(admitted):,} rows, "
          f"${ledger_money + new_money:,.0f}")

    dup_new = [a["Deal_ID"] for a in admitted if a["Deal_ID"] in known_ids]
    if dup_new:
        raise SystemExit(f"BREACH: new Deal_ID collides with the ledger: {dup_new[:5]}")
    if len({a["Deal_ID"] for a in admitted}) != len(admitted):
        raise SystemExit("BREACH: duplicate Deal_ID inside the admitted set")
    print("  Deal_ID uniqueness: OK (no collision with the 935 live ids, none internal)")

    if verify:
        # Verify reads what was SHIPPED, not what is in memory. A gate that
        # only ever sees the writer's own variables cannot catch a file that
        # was edited, truncated or half-written afterwards.
        return verify_mode(read(ADDITIONS), read(REFUSALS))

    if not execute:
        print("\nDRY RUN. Nothing written. Re-run with --execute.")
        return 0

    with open(ADDITIONS, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=BASE_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(admitted)
    print(f"\nWROTE {ADDITIONS.relative_to(CEDAR)}  {len(admitted)} rows x {len(BASE_COLS)} cols")

    rf = ["staged_id", "channel", "native_party", "counterparty", "event_date",
          "announced_value_usd", "source_url", "evidence", "refusal_reason",
          "refusal_basis", "refused_by", "refused_date"]
    with open(REFUSALS, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rf, extrasaction="ignore")
        w.writeheader()
        w.writerows(refused)
    print(f"WROTE {REFUSALS.relative_to(CEDAR)}  {len(refused)} rows")

    with open(DISPOSITION, "w", encoding="utf-8") as fh:
        json.dump({"built": TODAY, "by": f"code/{STEM}.py",
                   "candidates_in": total_in,
                   "admitted": len(admitted), "refused": len(refused),
                   "counts": dict(counts),
                   "new_announced_value_usd": new_money,
                   "parked_project_total_usd": parked,
                   "ledger_rows_before": len(ledger),
                   "ledger_money_before": ledger_money}, fh, indent=2)
    print(f"WROTE {DISPOSITION.relative_to(CEDAR)}")
    print("\nNEXT: py -3 code/88_build_deals_taxonomy.py   (append-merge; derives the 20 "
          "taxonomy columns)\n      then the in-place enrichers, which run LAST.")
    return 0


def selftest():
    """A check does not count until a fixture proves it FIRES.

    Injects one violation of each named invariant into a COPY of the shipped
    files, asserts verify_mode returns 1 and that the NAMED invariant is what
    fired, then asserts the untouched files return 0. AGENT_FIELD_GUIDE
    section 3, habit 1.
    """
    base_a, base_r = read(ADDITIONS), read(REFUSALS)
    if not base_a or not base_r:
        print("SELFTEST UNMEASURED: run --execute first; there is nothing to test")
        return 1
    if verify_mode(base_a, base_r) != 0:
        print("SELFTEST FAILED: the shipped files do not pass a clean verify")
        return 1

    cases = [
        ("no source link",            lambda r: r.update(Source_1="")),
        ("a ceiling sits in Announced_Value_USD",
         lambda r: r.update(Announced_Value_USD="151000000000",
                            Value_Type="IDIQ ceiling on a multiple-award vehicle")),
        ("neither a date nor a year", lambda r: r.update(Event_Date="", Event_Year="")),
        ("blank Event_Date without a Date_Basis saying why",
         lambda r: r.update(Event_Date="", Date_Basis="Transaction date")),
    ]
    ok = True
    for name, mutate in cases:
        rows = [dict(x) for x in base_a]
        mutate(rows[0])
        buf, code = [], None
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()) as cap:
            code = verify_mode(rows, base_r)
        out = cap.getvalue()
        fired = (code == 1 and name in out)
        print(f"  {'FIRES ' if fired else 'SILENT'}  {name}")
        ok &= fired

    rows = [dict(x) for x in base_r]
    rows[0]["refusal_basis"] = ""
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()) as cap:
        code = verify_mode(base_a, rows)
    fired = (code == 1 and "refused with no stated reason" in cap.getvalue())
    print(f"  {'FIRES ' if fired else 'SILENT'}  refused with no stated reason")
    ok &= fired

    if verify_mode(base_a, base_r) != 0:
        print("SELFTEST FAILED: restore did not return the files to clean")
        return 1
    print("\nSELFTEST " + ("OK - every named invariant fires on its own violation "
                            "and the clean files still pass"
                            if ok else "FAILED - an invariant did not fire"))
    return 0 if ok else 1


def verify_mode(admitted, refused):
    """Exit 1 on breach. Proven on a synthetic violation - see --selftest."""
    breaches = []
    for a in admitted:
        if not a["Source_1"]:
            breaches.append(f"{a['Deal_ID']}: no source link")
        if a["Announced_Value_USD"] and CEILING_PAT.search(a["Value_Type"] or ""):
            breaches.append(f"{a['Deal_ID']}: a ceiling sits in Announced_Value_USD")
        if not a["Event_Date"] and not a["Event_Year"]:
            breaches.append(f"{a['Deal_ID']}: neither a date nor a year")
        if not a["Event_Date"] and "NOT A DATE" not in (a["Date_Basis"] or "").upper():
            breaches.append(f"{a['Deal_ID']}: blank Event_Date without a Date_Basis saying why")
    for r in refused:
        if not r["refusal_reason"] or not r["refusal_basis"]:
            breaches.append(f"{r['staged_id']}: refused with no stated reason")
    if breaches:
        print(f"\nVERIFY FAILED - {len(breaches)} breach(es):")
        for b in breaches[:20]:
            print("   ", b)
        return 1
    print(f"\nVERIFY OK - {len(admitted)} admitted, {len(refused)} refused, 0 breaches")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
