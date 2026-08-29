#!/usr/bin/env python3
"""
Cedar Press - 33: Apply Elijah's PARTY rulings to the deals dataset.

WHY THIS EXISTS
---------------
Script 09 imports rulings whose review_id is an IDENTIFIER (UEI:..., CAGE:...)
and re-tiers the identifier ledger with them. It has no path for review_ids of
the form PARTY:<name>, which is what the deals queue emits. Those rulings were
being written to review/rulings_inbox_*.csv and consumed by nothing.

This script closes that loop. A party ruling is a hand decision by Elijah and
therefore outranks every automated method in the project - it lands at tier A.

RULING GRAMMAR
--------------
The review page asks "which entity is this, or is it non-Native?" and Elijah
answers in prose. Five answer shapes carry different meanings and must not be
collapsed:

  1. <entity name>                     -> owned by that Native entity. Tier A.
  2. "Not a Native entity..."          -> excluded. Tier X. Never attribute.
  3. "NATIVE ORGANIZATION - <kind>"    -> in scope as a Native ORGANISATION, but
                                          NOT owned by a single Native entity.
                                          parent_native_entity stays EMPTY.
  4. "MULTI-ENTITY - ..."              -> real but unresolved; a single NEID
                                          would be a false attribution. HELD.
  5. anything else                     -> unparsed; held, never guessed.

Shape 3 is the one worth guarding. Cook Inlet Housing Authority and Alaska
Village Initiatives are unambiguously Native and unambiguously NOT tribally
owned. Writing a parent for them would invent an ownership fact.

PARTIAL OWNERSHIP
-----------------
ARCTEC Alaska is a joint venture, part ASRC and part a Canadian company. The
ruling attributes the party to ASRC but the deal VALUE cannot be booked whole
to ASRC. Rulings whose note contains a partial-ownership marker get
value_attribution_caution=1 so no downstream sum silently overstates.

Reads  review/rulings_inbox_*.csv        (all of them, PARTY rows only)
       data/spine/cedar_entity_spine.csv
       data/clean/deals_classified.csv   <- THE TRUTH for the deal universe
                                            (was `deals_*_additions.csv`,
                                            fixed 2026-08-26; see B-1)
Writes data/clean/deals_party_attribution.csv   settled party -> NEID, tier A
       review/party_rulings_unresolved.csv      held, with the reason
"""

import csv
import glob
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cedar_domain as DOM   # noqa: E402  - DEALS_TRUTH

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

# Ruling-shape detectors. Order matters: the negative test runs first so a
# ruling like "Not a Native entity - individually Native-owned firm" is read as
# an exclusion and not as an organisation because it contains the word Native.
NOT_NATIVE_RE = re.compile(r"^\s*not a native entity", re.I)
ORG_RE = re.compile(r"^\s*native organi[sz]ation\s*[-:]\s*(?P<kind>.+)$", re.I)
MULTI_RE = re.compile(r"^\s*multi-entity", re.I)

# TWO-SIDED DEALS (Elijah, 2026-08-05)
# -----------------------------------
# "deals can involve two parties and two entities so worth flagging that too"
#
# `NANA Regional Corporation (buyer); Arctic Slope Regional Corporation (seller)`
# is one transaction in which BOTH sides are Native entities. Booking it to one
# loses half the fact; booking it to both without roles double-counts the value.
# So a two-sided ruling produces TWO rows sharing a deal, each carrying its own
# role, and only the row whose role is the acquirer may carry the value.
TWO_SIDED_RE = re.compile(r"^\s*two-sided\s*[-:]\s*(?P<body>.+)$", re.I)
ROLE_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<role>buyer|seller|acquirer|target|"
                     r"investor|lender|borrower|partner)\)\s*$", re.I)

# Aggregate awards (Elijah: "maybe create a category thats more catch all?").
# A programme paying ~600 tribes at once is a real Native deal with NO single
# entity. It must be countable as Native activity and must never be attributed
# to any one tribe, so it gets its own party_role rather than being held.
AGGREGATE_RE = re.compile(r"aggregate award|aggregate,|\baggregate\b", re.I)

PARTIAL_MARKERS = ("partial ownership", "joint venture", "part owned")

# A corporate form in the name means the thing is a company. The only Native
# ENTITIES that are companies are ANCs, so a corporate name must never resolve
# to a tribal or village GOVERNMENT.
CORP_FORM_RE = re.compile(
    r"\b(corporation|corp|incorporated|inc|company|llc|l\.l\.c|ltd|limited|"
    r"holdings|enterprises)\b", re.I)

GOVERNMENT_CLASSES = {
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
    "State-recognized tribe",
}

# Structural words carry no identifying signal; two names that differ only in
# these are the same entity. Kept identical in spirit to script 32's set.
STRUCTURAL = {
    "nation", "nations", "tribe", "tribes", "tribal", "band", "bands",
    "pueblo", "community", "communities", "rancheria", "village", "villages",
    "colony", "indians", "indian", "native", "peoples", "people",
    "reservation", "confederated", "of", "the", "and",
    # CORPORATE FORMS CARRY NO IDENTITY.
    # "Cook Inlet Region, Inc." and "Cook Inlet Region, Incorporated" are the
    # same company, but while `inc` and `incorporated` counted as identifying
    # words neither name contained the other and the match failed outright -
    # Elijah: "it asks is this cook inlet and it literally says cook inlet".
    # Same for Koniag Inc / Incorporated, NANA ... Inc / Incorporated, and
    # Ahtna Inc / Incorporated.
    #
    # Stripping them here is safe for the corporate-form GUARD below, which
    # regexes the raw name and never looks at this set.
    "inc", "incorporated", "corporation", "corp", "company", "co",
    "llc", "l", "ltd", "limited", "lp", "llp", "plc", "holdings",
}


def norm(s):
    """Normalise for comparison, folding diacritics FIRST.

    Without the fold, `[^a-z0-9]` turns a diacritic into a word break and
    silently splits the name: "Ukpeagvik" becomes "ukpea vik", which then
    matches nothing. That is not hypothetical - it hid Ukpeagvik Inupiat
    Corporation from its own spine row, and the same bug cost 8 Hawaiian
    organisations their EINs when a normaliser folded the okina but not the
    kahako (Hui o Kuapa vs the IRS record Hui O Kuapa).

    Alaska Inupiaq and Hawaiian orthography both carry marks that ASCII-only
    normalisation destroys, so folding is not a nicety here - it is the
    difference between finding an entity and reporting it absent.
    """
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("ʻ", "").replace("ʼ", "").replace("‘", "")
    s = s.replace("ł", "l")           # l-with-stroke survives NFKD
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def core(s):
    return frozenset(t for t in norm(s).split() if t not in STRUCTURAL)


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, rows, fields):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def resolve_entity(name, spine):
    """Map a ruled entity name onto the spine.

    Exact-normalised first, then core-set equality, then alias. Returns
    (tribe_id, canonical_name, how) or (None, None, reason). Never returns a
    fuzzy or best-effort match: an unmatched ruling is reported, not guessed.
    """
    n = norm(name)
    for r in spine:
        if norm(r["canonical_name"]) == n:
            return r["tribe_id"], r["canonical_name"], "exact"

    c = core(name)
    if c:
        hits = [r for r in spine if core(r["canonical_name"]) == c]
        if len(hits) == 1:
            return hits[0]["tribe_id"], hits[0]["canonical_name"], "core"
        if len(hits) > 1:
            return None, None, f"ambiguous_core:{len(hits)}_spine_entities"

    for r in spine:
        for a in (r.get("aliases") or "").split("|"):
            if a.strip() and norm(a) == n:
                return r["tribe_id"], r["canonical_name"], "alias"

    # Containment. The spine stores SHORT canonical names ("Sault Ste. Marie",
    # "Assiniboine and Sioux", "Saint Regis") while Elijah writes the full
    # official name. Neither exact nor core-equality can bridge that, so accept
    # a match when one core is a subset of the other - then demand that the
    # winner be strictly more specific than every rival.
    #
    # This is where the Oneida trap lives. Spine "Oneida" is the NY tribe and
    # "Oneida Nation (Wisconsin)" is spelled out. Against a ruling of "Oneida
    # Nation (NY)" only the former is a subset, so containment resolves to NY
    # correctly - but the guard below is what keeps that from being luck.
    if c:
        cands = []
        for r in spine:
            rc = core(r["canonical_name"])
            if rc and (rc <= c or c <= rc):
                cands.append((len(rc & c), r))

        # CORPORATE-FORM GUARD - narrowed 2026-08-06, and the narrowing matters.
        #
        # The broad rule "a corporate name may not resolve to a government" is
        # WRONG outside Alaska. Tribes own companies directly and routinely:
        # Chickasaw Management Services, Standing Rock Telecommunications,
        # Mescalero Apache Telecom, Tohono O'odham Utility Authority all belong
        # to their tribal governments. The broad guard refused 23 such parties
        # with the nonsensical reason "likely ANCSA village corporation" - for
        # tribes with no connection to Alaska.
        #
        # The genuine hazard is specific to ANCSA: Congress created corporations
        # to hold village assets, so where a village GOVERNMENT and its ANCSA
        # CORPORATION both exist, a company belongs to the corporation. That is
        # how "Ukpeagvik Inupiat Corporation" would otherwise land on the Native
        # Village of Barrow - different legal person, different money.
        #
        # So block only an Alaska village government, and only when a village
        # corporation counterpart is available to be the right answer.
        # (Script 55 reached this same conclusion independently after its own
        # guard over-fired; this back-ports it so the two agree.)
        if CORP_FORM_RE.search(name):
            ak_gov = [r for _, r in cands
                      if r["entity_class"] == "Federally recognized Alaska Native Village"]
            if ak_gov:
                corp_cores = {core(r["canonical_name"]) for r in spine
                              if r["tribe_id"].startswith("ANVC-")}
                blocked = [r for r in ak_gov if core(r["canonical_name"]) in corp_cores]
                if blocked:
                    cands = [(s, r) for s, r in cands if r not in blocked]
                    if not cands:
                        return None, None, ("corp_form_vs_government:"
                                            "ANCSA village corporation exists; "
                                            "refusing the village government")

        if cands:
            best = max(x[0] for x in cands)
            top = [r for score, r in cands if score == best]

            # ORDER TIE-BREAK. core() is a set, so "Shoshone-Paiute" and
            # "Paiute-Shoshone" are indistinguishable to it - two different
            # Nevada tribes. Word order is the only signal left, so prefer a
            # candidate whose name actually leads the ruled string.
            if len(top) > 1:
                lead = [r for r in top if n.startswith(norm(r["canonical_name"]))]
                if len(lead) == 1:
                    top = lead

            if len(top) == 1:
                return top[0]["tribe_id"], top[0]["canonical_name"], "containment"
            names = ", ".join(sorted(r["canonical_name"] for r in top)[:3])
            return None, None, f"ambiguous_containment:{len(top)}:{names}"

    return None, None, "no_spine_match"


def main():
    print("=== Cedar Press 33: apply PARTY rulings ===\n")

    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    print(f"spine entities: {len(spine):,}")

    # Collect PARTY rulings across every inbox. Later files win, so a
    # re-ruled party supersedes its earlier answer.
    rulings = {}
    for p in sorted(REVIEW.glob("rulings_inbox_*.csv")):
        n = 0
        for r in read_csv(p):
            rid = (r.get("review_id") or "").strip()
            ans = (r.get("YOUR_RULING") or "").strip()
            if not rid.upper().startswith("PARTY:") or not ans:
                continue
            party = rid.split(":", 1)[1].strip()
            rulings[party] = {
                "party": party,
                "ruling": ans,
                "note": (r.get("YOUR_NOTE") or "").strip(),
                "inbox": p.name,
            }
            n += 1
        if n:
            print(f"  {p.name}: {n} party rulings")
    print(f"\ndistinct parties ruled: {len(rulings):,}")

    settled, held = [], []
    kinds = Counter()

    for party, r in sorted(rulings.items()):
        ans, note = r["ruling"], r["note"]
        caution = int(any(m in note.lower() for m in PARTIAL_MARKERS))

        if NOT_NATIVE_RE.match(ans):
            kinds["excluded"] += 1
            settled.append({
                "native_party": party, "tribe_id": "", "canonical_name": "",
                "party_role": "EXCLUDED", "parent_native_entity": "",
                "confidence_tier": "X", "match_method": "elijah_ruling",
                "value_attribution_caution": 0,
                "ruling_text": ans, "ruling_note": note,
                "ruled_date": TODAY, "source_inbox": r["inbox"],
            })
            continue

        m = ORG_RE.match(ans)
        if m:
            kinds["native_organization"] += 1
            settled.append({
                "native_party": party, "tribe_id": "", "canonical_name": party,
                "party_role": "NATIVE_ORGANIZATION",
                # Deliberately empty: ruled Native, ruled NOT entity-owned.
                "parent_native_entity": "",
                "confidence_tier": "A", "match_method": "elijah_ruling",
                "value_attribution_caution": caution,
                "ruling_text": ans, "ruling_note": note,
                "org_kind": m.group("kind").strip(),
                "ruled_date": TODAY, "source_inbox": r["inbox"],
            })
            continue

        if MULTI_RE.match(ans):
            kinds["multi_entity_held"] += 1
            held.append({"native_party": party, "ruling": ans, "note": note,
                         "reason": "multi_entity_needs_enumeration",
                         "source_inbox": r["inbox"]})
            continue

        tid, canon, how = resolve_entity(ans, spine)
        if tid:
            kinds["entity_owned"] += 1
            settled.append({
                "native_party": party, "tribe_id": tid, "canonical_name": canon,
                "party_role": "ENTITY_OWNED", "parent_native_entity": canon,
                "confidence_tier": "A", "match_method": f"elijah_ruling+{how}",
                "value_attribution_caution": caution,
                "ruling_text": ans, "ruling_note": note,
                "ruled_date": TODAY, "source_inbox": r["inbox"],
            })
        else:
            kinds["unresolved_to_spine"] += 1
            held.append({"native_party": party, "ruling": ans, "note": note,
                         "reason": how, "source_inbox": r["inbox"]})

    print("\nruling outcomes")
    for k, v in kinds.most_common():
        print(f"  {v:5d}  {k}")
    print(f"  {len(held):5d}  HELD (never attributed)")

    write_csv(CLEAN / "deals_party_attribution.csv", settled, [
        "native_party", "tribe_id", "canonical_name", "party_role",
        "parent_native_entity", "confidence_tier", "match_method",
        "value_attribution_caution", "org_kind", "ruling_text", "ruling_note",
        "ruled_date", "source_inbox",
    ])
    write_csv(REVIEW / "party_rulings_unresolved.csv", held,
              ["native_party", "ruling", "note", "reason", "source_inbox"])

    # ---- coverage against the actual deal rows ---------------------------
    by_party = {s["native_party"].lower(): s for s in settled}
    seen, matched, excluded_rows = Counter(), 0, 0
    total = 0
    # THE TRUTH FOR THIS DENOMINATOR: the PROMOTED table,
    # data/clean/deals_classified.csv (cedar_domain.DEALS_TRUTH).
    #
    # This read `glob(deals_*_additions.csv)` until 2026-08-26 - the ADDITIONS
    # to the ledger, never the ledger itself - so the coverage percentage
    # printed below was computed against 790 rows when the ledger held 935.
    # A coverage denominator that omits 145 rows OVERSTATES coverage, which is
    # the direction that stops anyone looking. Same defect as
    # `docs/FACT_CHECK_2026-08-06.md` finding B-1; see
    # `cedar_domain.PROMOTED_TABLES`.
    for row in read_csv(CEDAR / DOM.DEALS_TRUTH):
        p = (row.get("Native_Party") or "").strip()
        if not p:
            continue
        total += 1
        seen[p] += 1
        s = by_party.get(p.lower())
        if s:
            matched += 1
            if s["party_role"] == "EXCLUDED":
                excluded_rows += 1

    print(f"\ndeal rows with a Native_Party : {total:,}")
    print(f"  covered by a ruling          : {matched:,} "
          f"({matched/total*100:.1f}%)" if total else "")
    print(f"  of which ruled NOT Native    : {excluded_rows:,}  "
          f"<- these must not be charted as Native deals")
    print(f"  distinct parties in deals    : {len(seen):,}")
    print(f"  distinct parties still unruled: "
          f"{sum(1 for p in seen if p.lower() not in by_party):,}")


if __name__ == "__main__":
    main()
