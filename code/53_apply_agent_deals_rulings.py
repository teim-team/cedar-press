#!/usr/bin/env python3
"""
Cedar Press - 53: Apply the AGENT-researched deals party rulings.

WHY THIS IS NOT SCRIPT 33
-------------------------
Script 33 reads `review/rulings_inbox_*.csv` and treats every PARTY ruling it
finds there as ELIJAH'S HAND RULING, which by the project's authority order
lands at tier A and publishes. `review/agent_rulings_deals_2026-08-05.csv`
holds 549 rulings produced by a research agent. They are well evidenced - each
carries a URL retrieved on 2026-08-05 and a quoted sentence - but they are not
Elijah's hand-checks, and a research agent's finding must not silently inherit
a human's authority. The file is therefore deliberately named OUT of the
`rulings_inbox_*` glob, exactly as `agent_rulings_nonprofit_2026-08-05.csv` is
kept out of it for script 34.

ASYMMETRIC EVIDENCE STANDARD  (the shape is script 34's; the sources differ)
---------------------------------------------------------------------------
  EXCLUDING (`Not a Native entity ...`) can only ever UNDER-attribute. A
      wrongly excluded party is missing coverage, which this project accepts.
      Applied on good agent evidence -> tier X.

  INCLUDING something as owned by a Native entity is a FALSE-ATTRIBUTION risk,
      which this project does not accept. It reaches tier A only on a PRIMARY
      source:
        * the BIA Federal Register recognition notice (91 FR 4102,
          FR Doc 2026-01899) - and only where the party IS the listed entity,
          not merely named after it;
        * an SEC filing (sec.gov/Archives/... - an EDGAR document, not a
          browse/search URL);
        * a tribal government page (a .gov host that is the tribe's own, not a
          federal award list);
        * the firm's own About / ownership page.
      Everything else - a trade article, an encyclopaedia entry, a HUD award
      list read together with a statute - lands at tier B: visible, queued for
      Elijah, NEVER published. A ruling resting on a search-results page can
      never reach tier A regardless of what else is cited.

THE IDENTITY TEST, AND WHY THE FR NOTICE IS NOT ENOUGH ON ITS OWN
-----------------------------------------------------------------
The recognition notice proves a TRIBE EXISTS. It does not prove that
"White Mountain Apache Housing Authority" is owned by the White Mountain
Apache Tribe. So the notice earns tier A only when the party and the ruled
entity are the same thing: every core token of the party must already be in
the entity's name (see `is_identity`). That passes `Taos Pueblo` ->
`Pueblo of Taos, New Mexico` and fails `<X> Housing Authority` -> `<X> Tribe`.
The 87 HUD tribally designated housing entities rest on NAHASDA
(25 U.S.C. 4103(22)) plus a name, which is a sound inference and not a primary
ownership statement. They go to tier B by design.

ELIJAH IS NEVER OVERWRITTEN
---------------------------
Every party already present in `data/clean/deals_party_attribution.csv` is
skipped outright - not re-tiered, not re-resolved, not compared. Those 34 are
final. This script writes a SEPARATE file so that re-running script 33 (which
rebuilds `deals_party_attribution.csv` from scratch each time) cannot mix the
two authorities together or clobber either.

THE SPINE GAINED THE VILLAGE CORPORATIONS
-----------------------------------------
When the agent ran, `cedar_entity_spine.csv` carried zero ANCSA village
corporations, so 14 village-corporation parties were ruled
`NATIVE ORGANIZATION - ANCSA village corporation (<village>); spine gap`
rather than forced onto the similarly named village GOVERNMENT (script 52 has
since added 173 village + 6 group corporations, spine now 866). Those rulings
are now re-resolvable, so this script retries them - but ONLY them, and only
against corporation-class spine rows.

That restriction is load-bearing. Running the same resolver over the OTHER
`NATIVE ORGANIZATION` rulings produces exactly the false attributions the
project forbids: `Tanana Chiefs Conference` -> the village of Tanana,
`Red Lake Nation College` -> the Red Lake Band, `Northern Circle Indian
Housing Authority` -> the village of Circle, `Inter-Tribal Council of Nevada`
-> a spine row called "Council". An intertribal consortium has MEMBERS, not an
owner; a tribal college and a regional housing authority have no single owner
either. Those keep `parent_native_entity` EMPTY, which is the whole point of
the NATIVE_ORGANIZATION shape.

Reads  review/agent_rulings_deals_2026-08-05.csv
       data/spine/cedar_entity_spine.csv
       data/clean/deals_party_attribution.csv        (Elijah - read only)
       data/clean/deals_classified.csv   <- THE TRUTH; the coverage
                                            denominator. Was the two root
                                            ledgers + deals_*_additions.csv,
                                            an assembled union that did not
                                            honour the withdrawal list.
                                            Fixed 2026-08-26.
Writes data/clean/deals_party_attribution_agent.csv
       review/deals_party_agent_needs_elijah_<date>.csv
       review/deals_party_agent_unresolved.csv
"""

import sys as _sys_cd
from pathlib import Path as _Path_cd
_sys_cd.path.insert(0, str(_Path_cd(__file__).resolve().parent))
import cedar_domain as DOM   # noqa: E402  - DEALS_TRUTH, PROMOTED_TABLES

import csv
import re
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

RULINGS = REVIEW / "agent_rulings_deals_2026-08-05.csv"

# Ruling-shape detectors, copied from script 33 so the two scripts read the
# same grammar. Order matters: the negative test runs first so "Not a Native
# entity - ..." is an exclusion and not an organisation.
NOT_NATIVE_RE = re.compile(r"^\s*not a native entity", re.I)
ORG_RE = re.compile(r"^\s*native organi[sz]ation\s*[-:]\s*(?P<kind>.+)$", re.I)
MULTI_RE = re.compile(r"^\s*multi-entity", re.I)
UNRESOLVED_RE = re.compile(r"^\s*unresolved", re.I)

# Value-attribution caution, per the ARCTEC precedent in script 33: a party
# string covering a joint venture, a two-sided buyer/seller row or two tribes
# must not have the whole deal value booked to the resolved entity. The agent
# writes these markers in several shapes ("- PARTIAL", "PARTIAL:", "Split the
# value or flag partial", "do not book the full value"), so match the word
# itself as well as the phrases. Over-flagging here is harmless; the flag adds
# caution and never adds an attribution.
PARTIAL_RE = re.compile(
    r"\bpartial\b|joint venture|part owned|two-sided row|50/50|"
    r"do not (?:book|attribute)|split the value", re.I)

# Only the ANCSA corporation rulings are retried against the spine. See the
# module docstring for why widening this is a false-attribution generator.
ANCSA_CORP_RE = re.compile(r"ancsa (village|group|urban) corporation", re.I)
CORPORATION_CLASSES = {
    "Alaska Native Village Corporation",
    "ANCSA Group Corporation",
    "Alaska Native Regional Corporation",
}

# ---- evidence classification ------------------------------------------------
URL_RE = re.compile(r"https?://[^\s,\)\]\"'>]+")

# The BIA recognition notice this run used as its census.
BIA_FR_DOC = "2026-01899"

# Federal hosts that are NOT a tribe's own page. hud.gov and eda.gov publish
# the AWARD LIST a deal row came from; uscode.house.gov supplies NAHASDA's
# definition of a tribally designated housing entity. Both are real evidence
# and neither states who owns a named housing authority.
FEDERAL_HOSTS = {
    "federalregister.gov", "www.federalregister.gov",
    "hud.gov", "www.hud.gov", "uscode.house.gov",
    "eda.gov", "www.eda.gov", "energy.gov", "www.energy.gov",
    "broadbandusa.ntia.gov", "ntia.gov", "www.ntia.gov",
    "sec.gov", "www.sec.gov", "usaspending.gov", "www.usaspending.gov",
    "sam.gov", "www.sam.gov", "grants.gov", "www.grants.gov",
    # A State of Hawaii executive department, ruled NOT a Native entity in
    # this very file - it must never count as a tribal government page.
    "dhhl.hawaii.gov",
}

SEARCH_PAGE_HINTS = ("google.com/search", "bing.com/search", "duckduckgo.com",
                     "/search?", "search-results", "causeiq.com/search",
                     "cgi-bin/browse-edgar")

QUOTE_RE = re.compile(r"[\"\u201c\u2018']([^\"\u201c\u201d]{40,})[\"\u201d\u2019']")

PRIMARY_CLASSES = {"bia_fr_notice", "sec_filing", "tribal_gov_page",
                   "firm_own_page"}


# --- copied verbatim from code/33_apply_party_rulings.py ---------------------
# Do not rewrite these. norm() folds diacritics BEFORE stripping punctuation;
# without that fold `[^a-z0-9]` turns a diacritic into a word break and
# "Ukpeagvik" becomes "ukpea vik", which matches nothing - it hid Ukpeagvik
# Inupiat Corporation from its own spine row.
STRUCTURAL = {
    "nation", "nations", "tribe", "tribes", "tribal", "band", "bands",
    "pueblo", "community", "communities", "rancheria", "village", "villages",
    "colony", "indians", "indian", "native", "peoples", "people",
    "reservation", "confederated", "of", "the", "and",
}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("\u02bb", "").replace("\u02bc", "").replace("\u2018", "")
    s = s.replace("\u0142", "l")      # l-with-stroke survives NFKD
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def core(s):
    return frozenset(t for t in norm(s).split() if t not in STRUCTURAL)


CORP_FORM_RE = re.compile(
    r"\b(corporation|corp|incorporated|inc|company|llc|l\.l\.c|ltd|limited|"
    r"holdings|enterprises)\b", re.I)

GOVERNMENT_CLASSES = {
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
    "State-recognized tribe",
}


def resolve_entity(name, spine):
    """Map a ruled entity name onto the spine. Copied from script 33.

    Exact-normalised first, then core-set equality, then alias, then
    containment with a corporate-form guard and an order tie-break. Never
    returns a fuzzy or best-effort match: an unmatched ruling is reported.
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

    if c:
        cands = []
        for r in spine:
            rc = core(r["canonical_name"])
            if rc and (rc <= c or c <= rc):
                cands.append((len(rc & c), r))

        # The spine now HOLDS village corporations, so this guard no longer
        # refuses outright - it steers a corporate name away from the
        # identically named village GOVERNMENT and onto the corporation.
        if CORP_FORM_RE.search(name):
            blocked = [r for _, r in cands
                       if r["entity_class"] in GOVERNMENT_CLASSES]
            cands = [(s, r) for s, r in cands
                     if r["entity_class"] not in GOVERNMENT_CLASSES]
            if blocked and not cands:
                return None, None, ("corp_form_vs_government:"
                                    "no corporation-class spine row")

        if cands:
            best = max(x[0] for x in cands)
            top = [r for score, r in cands if score == best]
            if len(top) > 1:
                lead = [r for r in top
                        if n.startswith(norm(r["canonical_name"]))]
                if len(lead) == 1:
                    top = lead
            if len(top) == 1:
                return top[0]["tribe_id"], top[0]["canonical_name"], "containment"
            names = ", ".join(sorted(r["canonical_name"] for r in top)[:3])
            return None, None, f"ambiguous_containment:{len(top)}:{names}"

    return None, None, "no_spine_match"
# --- end of copied block -----------------------------------------------------


def read_csv(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


def write_csv(p, rows, fields):
    # REGENERATE GUARD (ADR-017, 2026-09-02): derive the header, do not declare it.
    fields = _carry_live_columns(p, fields)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"  wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def urls(note):
    """Every URL in the note, unwrapping Wayback so the ORIGIN host is judged.

    asrc.com renders client-side and serves a fetcher nothing, so its 2001
    annual report was read through web.archive.org. The evidence is still
    ASRC's own document and should be classed as such.
    """
    out = []
    for u in URL_RE.findall(note or ""):
        if "web.archive.org" in u:
            m = re.search(r"/(https?://.+)$", u)
            if m:
                u = m.group(1)
        parts = u.split("/")
        if len(parts) > 2:
            out.append((parts[2].lower(), u))
    return out


def host_label(host):
    h = host[4:] if host.startswith("www.") else host
    return re.sub(r"[^a-z0-9]", "", h.split(".")[0])


def is_own_domain(host, names):
    """Is this host the named organisation's own site?

    Three shapes, all observed in this file:
      whole word     sealaska.com, chenega.com, koniag.com
      leading token  beringstraits.com, northwindgrp.com, aleutcorp.com
      acronym        asrc.com, bbnc.net, uicalaska.com, bnc-alaska.com
    """
    lab = host_label(host)
    if len(lab) < 4:
        return False
    for name in names:
        toks = [t for t in norm(name).split() if len(t) >= 4]
        if lab in toks:
            return True
        if any(lab.startswith(t) for t in toks):
            return True
        initials = "".join(t[0] for t in norm(name).split() if len(t) > 1)
        if len(initials) >= 3 and (lab == initials or lab.startswith(initials)):
            return True
    return False


def classify_evidence(note, names):
    """Return (evidence_class, is_primary, rests_on_search_page).

    First primary hit wins; `secondary` is the honest default.
    """
    low = (note or "").lower()
    search = any(h in low for h in SEARCH_PAGE_HINTS)
    for host, u in urls(note):
        if "sec.gov/archives" in u.lower():
            return "sec_filing", True, search
        if is_own_domain(host, names):
            return "firm_own_page", True, search
        if host.endswith(".gov") and host not in FEDERAL_HOSTS:
            return "tribal_gov_page", True, search
    if BIA_FR_DOC in (note or ""):
        return "bia_fr_notice", True, search
    return "secondary", False, search


def is_identity(party, ruled):
    """Is the party the ruled entity ITSELF, rather than something named after it?

    The test is DIRECTIONAL and that is the whole of it: every core token of
    the party must already appear in the ruled entity's name. Extra tokens on
    the ENTITY side are Federal Register listing verbiage (`Pueblo of Taos,
    New Mexico` for the party `Taos Pueblo`, `... of the Fort Apache
    Reservation, Arizona`), so a subset that way round is still the same
    thing. Extra tokens on the PARTY side are a different legal person -
    `Kaw Nation Housing Authority` is not the Kaw Nation, and
    `Seminole Tribe of Florida / Hard Rock International` is a two-party
    string, not the tribe.

    Tested symmetrically this leaked 45 tribally designated housing entities
    to tier A off a recognition notice that says nothing about who owns them.

    This is deliberately over-strict and it costs recall: 139 parties that are
    plainly the same entity under a documented variant spelling - `Modoc Tribe
    of Oklahoma` -> `Modoc Nation`, `Chickasaw Nation of Oklahoma` -> `The
    Chickasaw Nation`, `Tunica-Biloxi Tribe of Louisiana` -> `Tunica-Biloxi
    Indian Tribe` - fail it on a trailing state name and go to tier B.

    Allowing the reverse subset would recover all of them AND would promote
    `Cherokee Nation Businesses` -> `Cherokee Nation` to tier A off the
    recognition notice alone. That is the Cherokee Inc. trap exactly. Telling
    the two apart needs a list of enterprise words (businesses, ventures,
    holdings, solutions, ...) that is open-ended, and any word missing from it
    becomes a false attribution. Missing coverage is expandable; a wrong
    attribution is not - so the strict test stands and the variants wait in
    the queue, where `party_extra_tokens` makes each one a single glance.
    """
    a, b = core(party), core(ruled)
    if not a or not b:
        return False
    return a <= b


def main():
    print("=== Cedar Press 53: apply AGENT deals party rulings ===\n")

    if not RULINGS.exists():
        raise SystemExit(f"missing {RULINGS}")

    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    n_corp = sum(1 for r in spine if r["entity_class"] in CORPORATION_CLASSES)
    print(f"spine entities        : {len(spine):,}  "
          f"({n_corp} corporation-class, incl. the ANCSA additions)")

    # ---- Elijah's settled parties are read ONLY to be protected ------------
    elijah = read_csv(CLEAN / "deals_party_attribution.csv")
    # Keyed through norm(), not lower(), so a diacritic or punctuation variant
    # of a party Elijah has already settled cannot slip past the guard and be
    # re-ruled at a different tier by the agent.
    elijah_parties = {norm(r["native_party"]) for r in elijah}
    print(f"Elijah settled parties: {len(elijah_parties):,}  (never overwritten)")

    rulings = read_csv(RULINGS)
    print(f"agent rulings         : {len(rulings):,}\n")

    settled, held, needs_elijah = [], [], []
    kinds, tiers, evclass = Counter(), Counter(), Counter()
    skipped_elijah = 0

    for r in rulings:
        rid = (r.get("review_id") or "").strip()
        if not rid.upper().startswith("PARTY:"):
            continue
        party = rid.split(":", 1)[1].strip()
        ans = (r.get("YOUR_RULING") or "").strip()
        note = (r.get("YOUR_NOTE") or "").strip()
        if not party or not ans:
            continue

        # Elijah first, always. Not re-tiered, not re-resolved, not compared.
        if norm(party) in elijah_parties:
            skipped_elijah += 1
            continue

        firm = (r.get("entity_or_firm") or "").strip()
        caution = int(bool(PARTIAL_RE.search(f"{note} {ans} {party}")))

        base = {
            "native_party": party,
            "uei": (r.get("uei") or "").strip(),
            "cage_code": (r.get("cage_code") or "").strip(),
            "ruling_authority": "agent_research",
            "value_attribution_caution": caution,
            "ruling_text": ans,
            "ruling_note": note,
            "ruled_date": TODAY,
            "source_file": RULINGS.name,
        }

        # ---- 1. EXCLUSION: the safe direction ------------------------------
        if NOT_NATIVE_RE.match(ans):
            ev, primary, search = classify_evidence(note, [party, firm])
            kinds["excluded (NOT_NATIVE)"] += 1
            tiers["X"] += 1
            evclass[ev] += 1
            settled.append(dict(base, tribe_id="", canonical_name="",
                                party_role="EXCLUDED", parent_native_entity="",
                                confidence_tier="X",
                                match_method="agent_ruling",
                                evidence_class=ev,
                                rests_on_search_page=int(search),
                                spine_match="", org_kind=""))
            continue

        # ---- 2. MULTI-ENTITY / UNRESOLVED: held, never attributed ----------
        if MULTI_RE.match(ans) or UNRESOLVED_RE.match(ans):
            kinds["held (multi-entity / unresolved)"] += 1
            held.append({"native_party": party, "ruling": ans, "note": note,
                         "reason": "multi_entity_needs_enumeration"
                                   if MULTI_RE.match(ans) else "agent_unresolved",
                         "source_file": RULINGS.name})
            continue

        # ---- 3. NATIVE ORGANIZATION ----------------------------------------
        m = ORG_RE.match(ans)
        if m:
            kind = m.group("kind").strip()
            ev, primary, search = classify_evidence(note, [party, firm])
            tid = canon = how = ""

            # Retry ONLY the ANCSA corporation rulings against the spine that
            # did not exist when they were written. Everything else keeps an
            # empty parent - see the module docstring.
            if ANCSA_CORP_RE.search(kind):
                t, c, h = resolve_entity(party, spine)
                if t:
                    cls = next((s["entity_class"] for s in spine
                                if s["tribe_id"] == t), "")
                    if cls in CORPORATION_CLASSES:
                        tid, canon, how = t, c, h
                    else:
                        how = f"rejected_non_corporation_class:{cls}"
                else:
                    how = h

            if tid:
                # The party IS this ANCSA corporation (or its named subsidiary).
                tier = "A" if (primary and not search) else "B"
                kinds[f"ANCSA corporation resolved to spine ({tier})"] += 1
                tiers[tier] += 1
                evclass[ev] += 1
                settled.append(dict(base, tribe_id=tid, canonical_name=canon,
                                    party_role="ENTITY_OWNED",
                                    parent_native_entity=canon,
                                    confidence_tier=tier,
                                    match_method=f"agent_ruling+{how}",
                                    evidence_class=ev,
                                    rests_on_search_page=int(search),
                                    spine_match=how, org_kind=kind))
                if tier == "B":
                    needs_elijah.append({
                        "native_party": party, "proposed_entity": canon,
                        "proposed_role": "ENTITY_OWNED", "org_kind": kind,
                        "evidence_class": ev,
                        "rests_on_search_page": int(search),
                        "party_extra_tokens": "",
                        "why_not_tier_A": "no primary ownership source",
                        "evidence": note})
                continue

            # Native, but NOT owned by a single entity: parent stays EMPTY.
            tier = "A" if (primary and not search) else "B"
            kinds[f"NATIVE_ORGANIZATION, no owner ({tier})"] += 1
            tiers[tier] += 1
            evclass[ev] += 1
            settled.append(dict(base, tribe_id="", canonical_name=party,
                                party_role="NATIVE_ORGANIZATION",
                                parent_native_entity="",
                                confidence_tier=tier,
                                match_method="agent_ruling",
                                evidence_class=ev,
                                rests_on_search_page=int(search),
                                spine_match=how, org_kind=kind))
            if tier == "B":
                needs_elijah.append({
                    "native_party": party, "proposed_entity": "",
                    "proposed_role": "NATIVE_ORGANIZATION", "org_kind": kind,
                    "evidence_class": ev, "rests_on_search_page": int(search),
                    "why_not_tier_A": "no primary source for Native status",
                    "evidence": note})
            continue

        # ---- 4. ENTITY_OWNED: the false-attribution risk --------------------
        tid, canon, how = resolve_entity(ans, spine)
        if not tid:
            kinds["held (ruling will not resolve to spine)"] += 1
            held.append({"native_party": party, "ruling": ans, "note": note,
                         "reason": how, "source_file": RULINGS.name})
            continue

        ev, primary, search = classify_evidence(note, [party, ans, canon, firm])
        ident = is_identity(party, ans)

        # The recognition notice evidences the ENTITY, not an ownership link.
        # It earns tier A only where the party is that entity.
        if ev == "bia_fr_notice" and not ident:
            tier, why = "B", ("BIA notice evidences the entity, not that this "
                              "party is owned by it")
        elif primary and not search:
            tier, why = "A", ""
        elif search:
            tier, why = "B", "rests on a search-results page"
        else:
            tier, why = "B", "no primary ownership source"

        kinds[f"ENTITY_OWNED ({tier})"] += 1
        tiers[tier] += 1
        evclass[ev] += 1
        settled.append(dict(base, tribe_id=tid, canonical_name=canon,
                            party_role="ENTITY_OWNED",
                            parent_native_entity=canon,
                            confidence_tier=tier,
                            match_method=f"agent_ruling+{how}",
                            evidence_class=ev,
                            rests_on_search_page=int(search),
                            spine_match=how, org_kind=""))
        if tier == "B":
            needs_elijah.append({
                "native_party": party, "proposed_entity": canon,
                "proposed_role": "ENTITY_OWNED", "org_kind": "",
                "evidence_class": ev, "rests_on_search_page": int(search),
                "why_not_tier_A": why,
                # What the party name says that the entity name does not. A
                # trailing state ("oklahoma") reads as a variant spelling; an
                # organisational role ("housing authority", "businesses")
                # reads as a separate legal person. One glance either way.
                "party_extra_tokens": " ".join(sorted(core(party) - core(ans))),
                "evidence": note})

    # ---- report -------------------------------------------------------------
    print(f"skipped - already ruled by Elijah : {skipped_elijah:,}\n")
    print("outcomes")
    for k, v in kinds.most_common():
        print(f"  {v:5d}  {k}")
    print(f"  {len(held):5d}  HELD (never attributed)")

    print("\nconfidence tier")
    for k in ("A", "B", "X"):
        print(f"  {k}: {tiers.get(k, 0):,}")

    print("\nevidence class (settled rows)")
    for k, v in evclass.most_common():
        mark = "primary" if k in PRIMARY_CLASSES else "secondary"
        print(f"  {v:5d}  {k:16s} {mark}")

    write_csv(CLEAN / "deals_party_attribution_agent.csv", settled, [
        "native_party", "tribe_id", "canonical_name", "party_role",
        "parent_native_entity", "confidence_tier", "ruling_authority",
        "match_method", "evidence_class", "rests_on_search_page",
        "value_attribution_caution", "org_kind", "spine_match", "uei",
        "cage_code", "ruling_text", "ruling_note", "ruled_date", "source_file",
    ])
    for r in needs_elijah:
        r.setdefault("party_extra_tokens", "")
    write_csv(REVIEW / f"deals_party_agent_needs_elijah_{TODAY}.csv",
              needs_elijah, ["native_party", "proposed_entity",
                             "proposed_role", "org_kind", "party_extra_tokens",
                             "evidence_class", "rests_on_search_page",
                             "why_not_tier_A", "evidence"])
    write_csv(REVIEW / "deals_party_agent_unresolved.csv", held,
              ["native_party", "ruling", "note", "reason", "source_file"])

    # ---- coverage against the ACTUAL deal rows ------------------------------
    # THE TRUTH: data/clean/deals_classified.csv (cedar_domain.DEALS_TRUTH).
    #
    # The comment here used to read: "Script 33 counts only
    # `deals_*_additions.csv` and so undercounts by the 132 rows in the two
    # root ledgers. Script 32 builds the queue from all eleven files; this
    # uses the same list so the denominators agree."
    #
    # That was CORRECT about 33 and it is the only place in this repo that
    # spotted the defect in code rather than in a document - and it still did
    # not fix 33, so 33 carried it for another three weeks. Naming a defect in
    # a neighbour's comment is not fixing it. 33 is fixed now, and all three
    # scripts read the promoted table, so the denominators agree on 935 rather
    # than agreeing on an assembled 936 that double-counts the withdrawn
    # MA2020-008. See `cedar_domain.PROMOTED_TABLES`.
    files = [CEDAR / DOM.DEALS_TRUTH]

    # Party strings are matched through norm(). The ledger spells the same
    # corporation both ways - `Ukpeaġvik Iñupiat Corporation` in the 2026 file
    # and `Ukpeagvik Inupiat Corporation` in the ANCSA-portal files - and a
    # lower() key treats those as two different companies, losing 5 deal rows
    # to a diacritic.
    by_party = {}
    for row in elijah:
        by_party[norm(row["native_party"])] = ("elijah", row)
    for row in settled:
        by_party.setdefault(norm(row["native_party"]), ("agent", row))

    seen = Counter()
    for f in files:
        for row in read_csv(f):
            p = (row.get("Native_Party") or "").strip()
            if p:
                seen[p] += 1
    total = sum(seen.values())

    buckets = Counter()
    for p, n in seen.items():
        hit = by_party.get(norm(p))
        if not hit:
            buckets["unruled"] += n
            continue
        who, row = hit
        tier = row.get("confidence_tier", "")
        role = row.get("party_role", "")
        if who == "elijah":
            buckets["Elijah, tier A/X"] += n
        elif role == "EXCLUDED":
            buckets["agent, tier X (ruled NOT Native)"] += n
        elif tier == "A":
            buckets["agent, tier A (publishable)"] += n
        else:
            buckets["agent, tier B (awaits Elijah)"] += n

    print(f"\ndeal rows across {len(files)} ledger files : {total:,}")
    for k in ("Elijah, tier A/X", "agent, tier A (publishable)",
              "agent, tier B (awaits Elijah)",
              "agent, tier X (ruled NOT Native)", "unruled"):
        v = buckets.get(k, 0)
        print(f"  {v:5d}  ({v / total * 100:5.1f}%)  {k}")

    covered = total - buckets.get("unruled", 0)
    print(f"\n  covered by SOME ruling  : {covered:,} of {total:,} "
          f"({covered / total * 100:.1f}%)")
    unruled = sorted((p for p in seen if norm(p) not in by_party),
                     key=lambda p: -seen[p])
    print(f"  distinct parties in deals     : {len(seen):,}")
    print(f"  distinct parties still unruled: {len(unruled):,}")
    if unruled:
        print("  largest unruled parties:")
        for p in unruled[:10]:
            print(f"    {seen[p]:3d}  {p[:70]}")


if __name__ == "__main__":
    main()
