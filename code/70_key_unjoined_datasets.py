#!/usr/bin/env python3
"""
Cedar Press - 70: Give the six unjoined datasets an entity key.

THE PROBLEM
-----------
Cedar Press sells cross-dataset linkage. It was true of four datasets and false
of six. Compacts, bills, nonprofits, federal actions, ownership events and
gaming all carried a 0%-populated entity key, so they joined to nothing.

Most of the answer was already on disk. 97 of 98 ownership events resolve from
party mappings built by scripts 33/53/57; compacts and gaming decisions resolve
against spine aliases at ~99%. This is PROPAGATION, not research.

ONE RESOLVER
------------
`33_apply_party_rulings.resolve_entity` is imported, never re-implemented
(standing rule 8). It carries the diacritic fold, containment matching against
the spine's SHORT canonical names, the narrowed ANCSA corporate-form guard and
the word-order tie-break. Nothing here re-does any of that.

TWO SHAPES OF OUTPUT
--------------------
  ONE-TO-ONE   the row names a single Native entity -> `tribe_id` written in
               place (compacts, compact events/terms, gaming facilities,
               gaming land decisions, ownership events, nonprofits).
  MANY-TO-MANY the row concerns several entities -> a bridge table, never a
               single key. A bill affects many tribes; a Federal Register
               notice can name several. Collapsing those to one tribe_id would
               be a false attribution by construction.

TIERING (the caller's rule, applied strictly)
---------------------------------------------
  A   exact name, alias, or a documented ruling (Elijah's, or an agent ruling
      already carrying a primary source under script 53's standard), or
      structural inheritance from a tier-A parent row.
  B   core-set equality or containment. Correct far more often than not, and
      it still does not publish. Every distinct tier-B name goes to a
      promotion queue so one ruling settles many rows.
  refused  nothing is written. A refusal is a good outcome.

`entity_id` is set ONLY at tier A - it is the publishable key. `tribe_id`
carries every match and must be read together with `entity_tier`.

THE GUARDS (each one has already caused a real false attribution here)
----------------------------------------------------------------------
 1. ORGANISATION TYPE IS A BAR, NOT A SCORE. A municipality, mining company,
    power district, cooperative or university cannot be a Native entity.
    SALT RIVER PROJECT cost $28.71M on the alias `river salt`. Logic reused
    from `65_lobbying_organization_type_guard.py`.
 2. NAME TRAPS, ARBITRATED BY STATE. creek, cherokee, colorado, ojibwe,
    shawnee, oneida, apache - the set from
    `23_cross_dataset_propagation.NAME_TRAPS`. Several distinct federally
    recognized governments share each token, so the SHORT form identifies
    none of them. A partial match resting only on a trap token is refused
    unless a state corroborates it; a WHOLE-name match carrying one still
    needs the state before it publishes. This is what catches the compact
    filed as `Oneida Nation` / **Wisconsin**, which the resolver lands on
    spine `Oneida` / **NY** - the $716M Oneida mis-split, in a new dataset.
    It is deliberately narrower than the first draft, which refused
    `Cherokee Nation` and `Shawnee Tribe` - the tribes themselves.
 3. STATE DISAGREEMENT. PUEBLO OF SAN JUAN (NM) is not San Juan Southern
    Paiute (AZ). Where both sides carry a state and they disagree, the match
    is demoted. On compacts the state column names the state that SIGNED the
    compact rather than the tribe's own, so there it arbitrates traps only.
 4. VILLAGE CORPORATION != VILLAGE GOVERNMENT. 77 live namesake pairs in
    `review/village_corp_namesake_pairs.csv`; $27.59B was once booked to
    village governments that was corporation revenue. The resolver's own
    ANCSA guard does the refusing; every surviving link onto an AKNF
    government from a corporate-looking name is flagged here as well.
 5. BIA INDEX DEFECT. The BIA compact index misaligns `Tribes` with `Title`
    on 41 of these 707 rows and the gaming-decision index on 3 of 138. Those
    rows may not reach tier A off the defective column.
 6. NONPROFITS. `funnel_stage = verified_strict` is a strict NAME match, NOT
    verified Native status - 282 place-name coincidences once sat at tier A.
    So a nonprofit reaches tier A only on an explicit ruling, or on an exact/
    alias match that additionally clears the place-name and civic-descriptor
    flags the 990 build already computed.
 7. FREE TEXT needs more than the resolver. Scanning bill titles and Federal
    Register titles matches spine name STRINGS as token sequences. Three
    extra bars apply there and only there:
      - a name string whose tokens are all generic ("Council", "Little
        River", "Tribal Self-Governance") is never matched in free text. The
        spine really does contain an entity whose canonical name is the
        single word `Council` (AKNF-COUNCL-00, the Native Village of
        Council), and an alias `Tribal Self-Governance` on an intertribal
        organisation. Both are landmines in prose.
      - acronym aliases (CNHA, CERT, TSG) are excluded from free text.
      - a span matching two or more entities is ambiguous and refused.

Reads   data/spine/cedar_entity_spine.csv
        data/clean/deals_party_attribution.csv        (Elijah, tier A)
        data/clean/deals_party_attribution_agent.csv  (agent, script 53)
        data/clean/deals_party_autoresolved.csv       (script 57)
        review/village_corp_namesake_pairs.csv
Writes  data/clean/{compacts,compact_events,compact_terms}.csv      in place
        data/clean/{gaming_facilities,gaming_land_decisions}.csv    in place
        data/clean/{ownership_events,np_orgs}.csv                   in place
        data/clean/native_bills_entity_bridge.csv                   new
        data/clean/bill_votes_entity_bridge.csv                     new
        data/clean/federal_actions_entity_bridge.csv                new
        review/entity_key_refusals_<date>.csv
        review/entity_key_tierB_promotion_queue_<date>.csv
        docs/ENTITY_KEY_PROPAGATION_LOG.md
"""

import csv
import functools
import importlib.util
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
DOCS = CEDAR / "docs"
TODAY = date.today().isoformat()

csv.field_size_limit(10 ** 8)
# Entity names carry Inupiaq, Hawaiian and Luiseno orthography. The Windows
# console is cp1252 and raises on them, so a progress print must not be able
# to kill a run that has already written half its outputs.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ---------------------------------------------------------------- resolver ---


def load_m33():
    """Standing rule 8: ONE resolver. Import it; never re-implement matching."""
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


M = load_m33()

# Pure memoization of the resolver's two helpers. `resolve_entity` recomputes
# norm()/core() over all 952 spine names on EVERY lookup, which makes a 12,764
# row nonprofit pass take tens of minutes. Both are pure functions of a string,
# so caching cannot change a single answer - it only stops the same 952 names
# being re-normalised a million times. This is a speed change, not a logic one.
M.norm = functools.lru_cache(maxsize=None)(M.norm)
M.core = functools.lru_cache(maxsize=None)(M.core)

norm, core, STRUCTURAL = M.norm, M.core, M.STRUCTURAL

# ------------------------------------------------------------------ guards ---

# From 23_cross_dataset_propagation.NAME_TRAPS. Each was paid for.
NAME_TRAPS = {
    "creek": "Jade Creek -> Berry Creek, Tshimakain Creek -> Berry Creek. "
             "Matched 3+ times on this token alone.",
    "cherokee": "Cherokee General Corp is Doyon-owned, not Cherokee Nation; "
                "~31 'owned by individual Cherokees' drops in hci_analysis.do.",
    "colorado": "Colorado Professional Resources -> 'Colorado River'.",
    "ojibwe": "Ojibwe Hazardous Abatement -> 'Mille Lacs'.",
    "shawnee": "Absentee Shawnee vs Shawnee Tribe vs Eastern Shawnee - three "
               "distinct federally recognized governments.",
    "oneida": "Oneida NY vs Oneida WI - $716M was mis-split between them.",
    "apache": "Fort Sill Apache vs Apache Tribe of Oklahoma vs San Carlos.",
}

# Legal forms a Native ENTITY cannot be. Lifted from code/65 - a statement
# about what the organisation IS, not a similarity judgement.
BARRED = [
    (re.compile(r"^\s*city of\b", re.I), "a municipality"),
    (re.compile(r"^\s*town of\b", re.I), "a municipality"),
    (re.compile(r"^\s*county of\b|\bcounty government\b", re.I), "a county"),
    (re.compile(r"^\s*state of\b", re.I), "a state government"),
    (re.compile(r"\bmines?\b|\bmining (co|corp|company)\b", re.I),
     "a mining company"),
    (re.compile(r"\b(power|irrigation|water|utility|electric)\s+district\b", re.I),
     "a special district"),
    (re.compile(r"\bsalt river project\b", re.I),
     "the Salt River Project, an Arizona public power and irrigation district - "
     "NOT the Salt River Pima-Maricopa Indian Community"),
    (re.compile(r"\buniversity\b|\bcollege of\b", re.I),
     "a university (tribal colleges are ruled separately, by name)"),
    (re.compile(r"\bcooperative\b|\bco-?op\b|\bemc\b", re.I), "a member cooperative"),
    (re.compile(r"\bschool district\b", re.I), "a school district"),
    (re.compile(r"\bchamber of commerce\b", re.I), "a chamber of commerce"),
]
EXEMPT = re.compile(
    r"salish kootenai college|haskell|dine college|ilisagvik|"
    r"college of the menominee|sinte gleska|oglala lakota college|"
    r"tribal college|navajo technical", re.I)

# Tokens that carry no identifying signal in FREE TEXT. Only used by the text
# scanner - the column resolvers never see this set.
GENERIC = {
    "council", "self", "governance", "association", "consortium", "authority",
    "conference", "commission", "congress", "alliance", "coalition", "center",
    "centre", "institute", "foundation", "society", "development", "economic",
    "business", "enterprise", "enterprises", "services", "service", "group",
    "national", "american", "america", "united", "states", "state", "federal",
    "first", "new", "north", "south", "east", "west", "northern", "southern",
    "eastern", "western", "great", "big", "little", "upper", "lower", "old",
    "grand", "fort", "port", "saint", "st", "lake", "lakes", "river", "creek",
    "valley", "hill", "hills", "spring", "springs", "town", "city", "county",
    "health", "housing", "education", "energy", "resource", "resources",
    "technology", "communication", "educational", "regional", "area", "point",
    "island", "bay", "mountain", "mountains", "canyon", "mesa", "rock", "rocky",
    "white", "black", "red", "blue", "green", "gold", "golden", "sand", "cold",
    "warm", "clear", "round", "square", "middle", "central", "inc",
}

# Words that mark the thing just named as a tribal/entity designation.
#
# `indian` SINGULAR is deliberately absent. It qualifies far too many
# ordinary place names - the measured case is `Rio Salado Environmental
# Restoration, Salt River and INDIAN BEND WASH, Cities of Phoenix and Tempe`,
# where it lent tier A to a river. Dropping it costs nothing real, because
# every genuine tribal name that contains it also contains a strong
# designator: `Samish Indian NATION`, `Kalispel Indian COMMUNITY`,
# `Tejon Indian TRIBE`, `La Jolla Band of Luiseno INDIANS`.
DESIGNATOR = {
    "tribe", "tribes", "tribal", "band", "bands", "nation", "nations",
    "pueblo", "rancheria", "community", "village", "villages", "indians",
    "reservation", "corporation", "colony", "peoples",
}
# `corporation` counts INSIDE a matched span - every ANC name carries it - but
# not as surrounding context, where it certifies any company that happens to
# sit next to a place name. Measured: `Klamath River Renewal Corporation;
# PacifiCorp` reached tier A on the Klamath Tribes. It is a dam-removal entity.
DESIGNATOR_CONTEXT = DESIGNATOR - {"corporation"}

GOVERNMENT_CLASSES = {
    "Federally recognized tribe",
    "Federally recognized Alaska Native Village",
    "State-recognized tribe",
}

CORP_FORM_RE = M.CORP_FORM_RE

# ------------------------------------------------------------------ io ------


def rd(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def wr(p, rows, fields=None):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0].keys()) if rows else [])
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"    wrote {p.relative_to(CEDAR)}  ({len(rows):,} rows)")


def rewrite_in_place(p, rows, extra_cols):
    """Add columns to an existing dataset. Backs up first; never drops a row.

    The backup is written ONCE. Re-running must not overwrite the pre-70 copy
    with an already-modified file - that would destroy the only record of what
    the dataset looked like before this script touched it.
    """
    p = Path(p)
    bak = p.with_suffix(f".csv.bak_{TODAY}_pre70")
    if not bak.exists():
        shutil.copy2(p, bak)
    fields = list(rows[0].keys())
    for c in extra_cols:
        if c not in fields:
            fields.append(c)
    wr(p, rows, fields)


REFUSALS = []        # every refusal, with its reason
PROMOTIONS = []      # distinct tier-B names, for one-ruling-settles-many


def refuse(dataset, name, reason, detail="", n_rows=1, extra=""):
    REFUSALS.append({"dataset": dataset, "source_name": name, "reason": reason,
                     "detail": detail, "n_rows": n_rows, "context": extra,
                     "refused_date": TODAY})


# ------------------------------------------------------- the keying core -----

SPINE_ROWS = rd(SPINE / "cedar_entity_spine.csv")
SPINE_BY_ID = {r["tribe_id"]: r for r in SPINE_ROWS}
ANVC_CORES = {core(r["canonical_name"]) for r in SPINE_ROWS
              if r["tribe_id"].startswith("ANVC-")}
# Every name the spine itself uses, normalised. Used only to stop the
# organisation-type bar from refusing an entity that is already on the roster.
SPINE_NAME_STRINGS = {
    norm(s) for r in SPINE_ROWS
    for s in [r["canonical_name"]] + (r.get("aliases") or "").split("|")
    if s.strip()}

STATE_ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}


def st(v):
    v = (v or "").strip()
    if not v:
        return ""
    if len(v) == 2:
        return v.upper()
    return STATE_ABBR.get(v.lower(), "")


_CACHE = {}


def key_name(name, dataset, src_state="", allow_org_bar=True,
             state_role="full"):
    """Resolve one entity NAME to the spine, with every guard applied.

    Returns dict(tribe_id, canonical_name, method, tier, basis) or
    dict(tribe_id="") with `basis` carrying the refusal reason.
    """
    name = (name or "").strip()
    if not name:
        return {"tribe_id": "", "canonical_name": "", "method": "",
                "tier": "", "basis": "no_source_name"}

    ck = (name, src_state, allow_org_bar, state_role)
    if ck in _CACHE:
        return dict(_CACHE[ck])

    def out(**kw):
        r = {"tribe_id": "", "canonical_name": "", "method": "", "tier": "",
             "basis": ""}
        r.update(kw)
        _CACHE[ck] = dict(r)
        return r

    # GUARD 1 - organisation type is a bar, not a score.
    #
    # It does NOT apply to a name that is already a spine name string. The bar
    # exists to stop a similarity match onto an organisation that cannot be a
    # Native entity; it has no business overruling the spine's own roster.
    #
    # Measured cost of getting this wrong: the first run refused
    # `Klawock Cooperative Association` as "a member cooperative". It is a
    # federally recognized Alaska Native village GOVERNMENT - Cooperative
    # Association is the standard IRA-era name for one, shared by Hydaburg and
    # Wrangell, and Association by Angoon, Craig, Douglas, Hoonah, Petersburg,
    # Chilkoot, Nenana and Stebbins. That is a guard eating something true,
    # which is exactly what code/65's EXEMPT list exists to prevent.
    if allow_org_bar and norm(name) not in SPINE_NAME_STRINGS \
            and not EXEMPT.search(name):
        for rx, why in BARRED:
            if rx.search(name):
                return out(basis=f"org_type_barred:{why}")

    tid, canon, how = M.resolve_entity(name, SPINE_ROWS)
    if not tid:
        return out(basis=how)

    ent = SPINE_BY_ID[tid]
    method = how.split(":")[0]

    # Confirm the resolver's answer against the spine's own strings, so an
    # exact/alias identity is recognised as such even when core matched first.
    # This can only CONFIRM a match the resolver already made - it never
    # creates one.
    n = norm(name)
    if n == norm(ent["canonical_name"]):
        method = "exact"
    elif any(a.strip() and norm(a) == n
             for a in (ent.get("aliases") or "").split("|")):
        method = "alias"

    # GUARD 2/3 - name traps, arbitrated by state.
    #
    # NARROWED after the first run, which refused `Cherokee Nation`, `Shawnee
    # Tribe` and `Oneida Indian Nation` - the tribes THEMSELVES. The trap is a
    # match that rests on a shared token when the source names something else
    # (Cherokee General Corp -> Cherokee Nation). An exact match on the whole
    # official name is not a token coincidence and must not be refused.
    #
    # What the token really signals is that several distinct federally
    # recognized governments share it, so the SHORT form does not identify one.
    # State settles it, and settles it decisively:
    #   compact `Oneida Nation`, state Wisconsin -> the resolver's core match
    #   lands on `Oneida` (NY). That is the $716M Oneida mis-split. Refused.
    #   compact `Oneida Indian Nation`, state New York -> NY == NY. Kept.
    shared = core(name) & core(ent["canonical_name"])
    trapped = shared & set(NAME_TRAPS)
    a, b = st(src_state), st(ent.get("state"))
    state_conflict = bool(a and b and a != b)
    state_agrees = bool(a and b and a == b)
    whole_name = method in ("exact", "alias")

    if trapped:
        if state_conflict:
            return out(basis=f"trap_token_state_conflict:{a}!={b}:"
                             f"{'|'.join(sorted(trapped))} - several distinct "
                             f"federally recognized governments share this token")
        if not whole_name and shared <= set(NAME_TRAPS) and not state_agrees:
            return out(basis=f"match_rests_only_on_trap_token:"
                             f"{'|'.join(sorted(shared))} - and no state "
                             f"corroboration is available")

    # GUARD 4 - a corporate name resolving onto an Alaska village GOVERNMENT
    # that has a namesake ANCSA corporation. The resolver refuses this itself;
    # this is a belt-and-braces check that also covers the alias route.
    if (CORP_FORM_RE.search(name)
            and ent["entity_class"] == "Federally recognized Alaska Native Village"
            and core(ent["canonical_name"]) in ANVC_CORES):
        return out(basis="village_corporation_namesake_exists:"
                         "refusing the village government")

    tier = "A" if whole_name else "B"
    basis = f"resolver_{method}"
    # `state_role="trap_only"`: on compacts the state column names the state
    # that SIGNED the compact, not the tribe's own registered state, and a
    # tribe's lands can cross a line. That makes it decisive for arbitrating a
    # trap token but wrong as a blanket demotion, so it is used only above.
    if state_conflict and state_role == "full":
        tier = "B"
        basis += f";state_conflict:{a}!={b}"
    if trapped and tier == "A":
        # A whole-name match carrying a trap token still needs the state to
        # agree before it publishes. `Cherokee Nation` + OK == OK -> A.
        # `Shawnee Tribe` with no state anywhere -> B, because three distinct
        # Shawnee governments exist and nothing here says which.
        if state_agrees:
            basis += f";contains_trap_token:{'|'.join(sorted(trapped))};" \
                     f"state corroborates ({a})"
        else:
            tier = "B"
            basis += f";contains_trap_token:{'|'.join(sorted(trapped))};" \
                     f"no state corroboration - several distinct governments " \
                     f"share this token"

    return out(tribe_id=tid, canonical_name=ent["canonical_name"],
               method=method, tier=tier, basis=basis)


def apply_column(rows, name_col, dataset, state_col=None, allow_org_bar=True,
                 block_tierA=None, block_reason="", state_role="full"):
    """Key a one-to-one dataset off a name column. Returns a report Counter."""
    seen_B = defaultdict(int)
    seen_ref = defaultdict(int)
    stat = Counter()
    for r in rows:
        res = key_name(r.get(name_col), dataset,
                       r.get(state_col) if state_col else "",
                       allow_org_bar=allow_org_bar, state_role=state_role)
        tier, basis = res["tier"], res["basis"]
        if res["tribe_id"] and tier == "A" and block_tierA and block_tierA(r):
            tier = "B"
            basis += f";{block_reason}"
        r["tribe_id"] = res["tribe_id"]
        r["tribe_canonical_name"] = res["canonical_name"]
        r["entity_match_method"] = res["method"]
        r["entity_tier"] = tier
        r["entity_match_basis"] = basis
        r["entity_keyed_date"] = TODAY
        # entity_id is the PUBLISHABLE key: tier A only.
        r["entity_id"] = res["tribe_id"] if tier == "A" else ""
        if res["tribe_id"]:
            stat[f"tier_{tier}"] += 1
            if tier == "B":
                seen_B[(r.get(name_col, "").strip(), res["tribe_id"],
                        res["canonical_name"], basis)] += 1
        else:
            stat["refused"] += 1
            if basis != "no_source_name":
                seen_ref[(r.get(name_col, "").strip(), basis)] += 1
            else:
                stat["no_name"] += 1
    for (nm, tid, canon, basis), n in seen_B.items():
        PROMOTIONS.append({"dataset": dataset, "source_name": nm,
                           "proposed_tribe_id": tid, "proposed_name": canon,
                           "n_rows": n, "basis": basis, "queued": TODAY,
                           "YOUR_RULING": "", "YOUR_NOTE": ""})
    for (nm, basis), n in seen_ref.items():
        refuse(dataset, nm, basis.split(":")[0], basis, n)
    return stat


def show(label, rows, stat):
    a, b, ref = stat.get("tier_A", 0), stat.get("tier_B", 0), stat.get("refused", 0)
    keyed = a + b
    print(f"  {label:34s} {len(rows):>7,} rows | keyed {keyed:>6,} "
          f"({keyed/len(rows)*100 if rows else 0:5.1f}%) | A {a:>6,} | "
          f"B {b:>6,} | refused {ref:>5,}")
    return {"dataset": label, "rows": len(rows), "keyed": keyed,
            "pct_keyed": round(keyed / len(rows) * 100, 1) if rows else 0,
            "tier_A": a, "tier_B": b, "refused": ref}


SUMMARY = []


def queue_bridge_tierB(bridge, dataset, id_col):
    """Distinct tier-B (span -> entity) pairs from a bridge, for one ruling to
    settle every row carrying that span."""
    agg = defaultdict(int)
    for r in bridge:
        if r["entity_tier"] == "B":
            agg[(r["matched_span"], r["tribe_id"], r["tribe_canonical_name"],
                 r["entity_match_basis"].split(":")[0])] += 1
    for (span, tid, canon, basis), n in agg.items():
        PROMOTIONS.append({"dataset": dataset, "source_name": span,
                           "proposed_tribe_id": tid, "proposed_name": canon,
                           "n_rows": n, "basis": basis, "queued": TODAY,
                           "YOUR_RULING": "", "YOUR_NOTE": ""})

# =============================================================== 1. deals ====


def do_ownership_events():
    print("\n[1] ownership_events.csv - propagate the deals party maps")
    p = CLEAN / "ownership_events.csv"
    rows = rd(p)

    # Priority: Elijah > agent (script 53's asymmetric standard) > script 57.
    # Each already carries its own tier; we never raise one.
    party = {}
    for f, auth, prio in [("deals_party_autoresolved.csv", "script57_autoresolved", 1),
                          ("deals_party_attribution_agent.csv", "agent_ruling", 2),
                          ("deals_party_attribution.csv", "elijah_ruling", 3)]:
        for r in rd(CLEAN / f):
            k = norm(r["native_party"])
            if not k:
                continue
            if k in party and party[k]["_prio"] > prio:
                continue
            party[k] = {"_prio": prio, "auth": auth, **r}

    # Withdrawn deals still sitting in this derived file (STATE_OF_BUILD).
    withdrawn = {w.get("deal_id") or w.get("Deal_ID") or ""
                 for w in rd(REVIEW / "deals_withdrawn_duplicates.csv")}

    stat = Counter()
    seen_B, seen_ref = defaultdict(int), defaultdict(int)
    for r in rows:
        r["source_deal_withdrawn"] = "1" if r.get("source_deal_id") in withdrawn else "0"
        nm = (r.get("native_party_verbatim") or "").strip()
        rec = party.get(norm(nm))
        tid = canon = method = tier = basis = ""
        if rec:
            tid = (rec.get("tribe_id") or "").strip()
            canon = (rec.get("canonical_name") or "").strip()
            role = rec.get("party_role", "")
            src_tier = rec.get("confidence_tier", "")
            src_meth = rec.get("match_method", "")
            if src_tier == "X" or role == "EXCLUDED":
                basis = f"ruled_not_a_native_entity({rec['auth']})"
                tid = canon = ""
                tier = "X"
            elif not tid:
                # NATIVE_ORGANIZATION / MULTI-ENTITY: real but not one entity.
                basis = f"{rec['auth']}:{role or 'no_single_entity'}"
                tier = ""
            else:
                method = f"{rec['auth']}+{src_meth}"
                # A ruling is a documented ruling -> tier A. Script 57's
                # autoresolve is algorithmic, so it keeps tier A only where it
                # was exact or alias; core/containment drop to B.
                if rec["auth"] == "script57_autoresolved":
                    tier = "A" if src_meth in ("deterministic_exact",
                                               "deterministic_alias") else "B"
                else:
                    tier = src_tier if src_tier in ("A", "B") else "B"
                basis = f"propagated_from_{rec['auth']}"
        else:
            res = key_name(nm, "ownership_events")
            tid, canon = res["tribe_id"], res["canonical_name"]
            method, tier, basis = res["method"], res["tier"], res["basis"]
            if tid:
                basis = "resolver_" + res["method"]

        r["tribe_id"] = tid
        r["tribe_canonical_name"] = canon
        r["entity_match_method"] = method
        r["entity_tier"] = tier
        r["entity_match_basis"] = basis
        r["entity_keyed_date"] = TODAY
        r["entity_id"] = tid if tier == "A" else ""
        # keep the legacy columns consistent rather than contradicting them
        if tid:
            r["native_entity_neid"] = tid
            r["neid_join_status"] = f"JOINED tier {tier} - {basis}"
        else:
            r["neid_join_status"] = f"NOT JOINED - {basis}"

        if tid:
            stat[f"tier_{tier}"] += 1
            if tier == "B":
                seen_B[(nm, tid, canon, basis)] += 1
        else:
            stat["refused"] += 1
            seen_ref[(nm, basis)] += 1

    for (nm, tid, canon, basis), n in seen_B.items():
        PROMOTIONS.append({"dataset": "ownership_events", "source_name": nm,
                           "proposed_tribe_id": tid, "proposed_name": canon,
                           "n_rows": n, "basis": basis, "queued": TODAY,
                           "YOUR_RULING": "", "YOUR_NOTE": ""})
    for (nm, basis), n in seen_ref.items():
        refuse("ownership_events", nm, basis.split(":")[0].split("(")[0], basis, n)

    rewrite_in_place(p, rows, ["tribe_id", "tribe_canonical_name",
                               "entity_match_method", "entity_tier",
                               "entity_match_basis", "entity_keyed_date",
                               "source_deal_withdrawn"])
    SUMMARY.append(show("ownership_events", rows, stat))


# ============================================================ 2. compacts ====


def do_compacts():
    print("\n[2] compacts.csv + events + terms")
    p = CLEAN / "compacts.csv"
    rows = rd(p)
    # GUARD 5 - the BIA index misaligns Tribes with Title on 41 rows. A row
    # flagged `bia_tribes_column_conflict` may not publish off that column.
    # The compact's `state` is the COMPACTING STATE, not the tribe's registered
    # state, so it is used ONLY to arbitrate a name trap - where it is
    # decisive. `Oneida Nation` / Wisconsin against spine `Oneida` / NY is the
    # $716M mis-split, and this is what catches it.
    stat = apply_column(
        rows, "tribe", "compacts", state_col="state", state_role="trap_only",
        block_tierA=lambda r: r.get("bia_tribes_column_conflict") == "1",
        block_reason="bia_tribes_column_conflict:index defective at source")
    rewrite_in_place(p, rows, ["tribe_id", "tribe_canonical_name",
                               "entity_match_method", "entity_tier",
                               "entity_match_basis", "entity_keyed_date"])
    SUMMARY.append(show("compacts", rows, stat))

    by_compact = {r["compact_id"]: r for r in rows if r.get("compact_id")}

    for fname, label in [("compact_events.csv", "compact_events"),
                         ("compact_terms.csv", "compact_terms")]:
        pp = CLEAN / fname
        rr = rd(pp)
        st_ = Counter()
        direct = [r for r in rr if not by_compact.get(r.get("compact_id"))]
        # STRUCTURAL INHERITANCE from the parent compact row. A child row of a
        # tier-A compact is tier A; it can never exceed its parent.
        for r in rr:
            par = by_compact.get(r.get("compact_id"))
            if par and par.get("tribe_id"):
                r["tribe_id"] = par["tribe_id"]
                r["tribe_canonical_name"] = par["tribe_canonical_name"]
                r["entity_match_method"] = "inherited_from_compact_id"
                r["entity_tier"] = par["entity_tier"]
                r["entity_match_basis"] = (
                    f"structural inheritance from {par['compact_id']} "
                    f"({par['entity_match_basis']})")
                r["entity_keyed_date"] = TODAY
                r["entity_id"] = r["tribe_id"] if r["entity_tier"] == "A" else ""
                st_[f"tier_{r['entity_tier']}"] += 1
            else:
                r["tribe_id"] = ""
        if direct:
            st2 = apply_column(direct, "tribe", label)
            st_ += st2
        rewrite_in_place(pp, rr, ["tribe_id", "tribe_canonical_name",
                                  "entity_match_method", "entity_tier",
                                  "entity_match_basis", "entity_keyed_date"])
        SUMMARY.append(show(label, rr, st_))


# ============================================================== 3. gaming ====


def do_gaming():
    print("\n[3] gaming_land_decisions.csv + gaming_facilities.csv")

    p = CLEAN / "gaming_land_decisions.csv"
    rows = rd(p)
    # GUARD 5 again - 3 of 138 rows carry the BIA Tribe(s) column defect.
    # `tribe_from_title` is the corroborated candidate; use it where present.
    for r in rows:
        if r.get("bia_tribes_column_conflict") == "1" and (r.get("tribe_from_title") or "").strip():
            r["_key_name"] = r["tribe_from_title"]
        else:
            r["_key_name"] = r.get("tribe", "")
    stat = apply_column(
        rows, "_key_name", "gaming_land_decisions", state_col="state_abbr",
        block_tierA=lambda r: (r.get("bia_tribes_column_conflict") == "1"
                               and not (r.get("tribe_from_title") or "").strip()),
        block_reason="bia_tribes_column_conflict:index defective, no title corroboration")
    for r in rows:
        if r.get("bia_tribes_column_conflict") == "1" and (r.get("tribe_from_title") or "").strip():
            r["entity_match_basis"] += ";keyed_from_tribe_from_title (BIA Tribe(s) column defective)"
        r.pop("_key_name", None)
    rewrite_in_place(p, rows, ["tribe_id", "tribe_canonical_name",
                               "entity_match_method", "entity_tier",
                               "entity_match_basis", "entity_keyed_date"])
    SUMMARY.append(show("gaming_land_decisions", rows, stat))

    p = CLEAN / "gaming_facilities.csv"
    rows = rd(p)
    idq = {r.get("facility_id") for r in
           rd(REVIEW / "gaming_facility_identity_queue_2026-08-06.csv")}
    # A row whose SUBJECT is undefined cannot be attributed at tier A, however
    # well its tribe name resolves. VP-0169 fuses an Otoe-Missouria brand, a
    # Ponca attribution and an Osage location.
    stat = apply_column(
        rows, "tribe", "gaming_facilities", state_col="state",
        block_tierA=lambda r: r.get("facility_id") in idq,
        block_reason="facility_identity_queue:the row's subject is disputed")
    rewrite_in_place(p, rows, ["tribe_id", "tribe_canonical_name",
                               "entity_match_method", "entity_tier",
                               "entity_match_basis", "entity_keyed_date"])
    SUMMARY.append(show("gaming_facilities", rows, stat))


# =========================================================== 4. nonprofits ===


def ledger_negative_ein_rulings():
    """EIN -> the owner's NEGATIVE ruling text, from the ledger's tier-X rows.

    ADDED 2026-08-26 by code/251_apply_np_ein_exclusions_to_np_orgs.py.

    THE DEFECT THIS CLOSES. `do_np_orgs` consulted `excluded_by_prior_ruling`
    and `funnel_stage` and **not the ledger's tier-X EIN leg**, which is where
    the owner's nonprofit exclusions actually live. So 27 links this column
    carries were forbidden by a ruling made 2026-08-12 and stayed live:

        COLVILLE ROTARY CHARITABLE FOUNDATION  tribe_id = TRBF-COLVLL-00
        KIOWA COUNTY FARM BUREAU ASSOCIATION   tribe_id = TRBF-KIOWAT-00
        COWLITZ COUNTY DRUG COURT FOUNDATION   tribe_id = TRBF-COWLTZ-00

    All 27 arrived by `containment` WITH A RECORDED STATE CONFLICT
    (`resolver_containment;state_conflict:KS!=OK`) - the place-name defect
    AGENTS.md has paid for ten times. `167_link_nonprofit_family_via_ein_hub.py`
    found them and correctly refused to patch another script's column, marking
    its own `cedar_link_tier = X` and filing
    `review/np_ein_hub_exclusion_hits_2026-08-26.csv`. That was the right
    caution and it left a forbidden link live in a shipping column, which is
    not an outcome. This function makes 70 read the ruling itself, so a rebuild
    of `np_orgs.csv` re-derives the exclusion instead of losing it.

    WHY THE WHOLE EIN IS BLOCKED AND NOT JUST ONE ENTITY. Every one of these
    rulings reads, verbatim and identically, **"Ruled by Elijah 2026-08-12: not
    a Native entity"**. That is a ruling about the ORGANISATION, not a redirect
    naming a better owner. Where a ruling names a different owner the correct
    handling is a REDIRECT (09/124's `elijah_ruling_redirect`), never a block -
    see `docs/ANCSA_OWNERSHIP_RULING.md`, "corrections are made, never erased".
    So only the blanket-negative grammar blocks here; a redirect is left alone
    for the appliers that own it.

    A RULED METHOD IS NOT AUTOMATICALLY A POSITIVE RULING - and the mirror of
    that is true too: the SIGN is read here, not the method. Only tier X counts.
    """
    neg = {}
    for r in rd(CLEAN / "cedar_identifier_ledger_final.csv"):
        if (r.get("identifier_type") or "").strip().upper() != "EIN":
            continue
        if (r.get("confidence_tier") or "").strip().upper() != "X":
            continue
        why = (r.get("tier_rationale") or "").strip()
        if "not a native entity" not in why.lower():
            continue                    # a redirect, not a blanket negative
        e = re.sub(r"\D", "", r.get("identifier") or "")
        if e:
            neg.setdefault(e, (why, (r.get("attribution_method") or "").strip(),
                               (r.get("canonical_name") or "").strip()))
    return neg


def do_np_orgs():
    print("\n[4] np_orgs.csv - the strictest bar in the run")
    p = CLEAN / "np_orgs.csv"
    rows = rd(p)
    stat = Counter()
    seen_B, seen_ref = defaultdict(int), defaultdict(int)
    neg_ein = ledger_negative_ein_rulings()
    print(f"    ledger negative EIN rulings loaded: {len(neg_ein):,}")

    for r in rows:
        nm = (r.get("org_name") or "").strip()
        tid = canon = method = tier = basis = ""
        ein = re.sub(r"\D", "", r.get("EIN") or "")

        # An exclusion ruling blocks unconditionally.
        if ein and ein in neg_ein:
            why, meth, against = neg_ein[ein]
            tier, basis = "X", (f"ruled_not_a_native_entity(ledger EIN leg, "
                                f"{meth}, tier X against {against}): {why}")
            stat["excluded by a ledger tier-X EIN ruling"] += 1
        elif r.get("excluded_by_prior_ruling") == "1" or \
                r.get("funnel_stage") == "ruled_not_native":
            tier, basis = "X", ("excluded_by_prior_ruling:"
                                + (r.get("exclusion_reason") or "prior ruling"))
            stat["excluded"] += 1
        else:
            res = key_name(nm, "np_orgs", r.get("state"))
            tid, canon = res["tribe_id"], res["canonical_name"]
            method, tier, basis = res["method"], res["tier"], res["basis"]
            if tid:
                # TRAP 6. `verified_strict` is a strict NAME match, not
                # verified Native status. So an exact/alias hit is NOT enough
                # on its own: it must also clear the place-name and civic
                # descriptor flags the 990 build already computed, or carry an
                # explicit ruling.
                # POLARITY, fixed 2026-08-26 by the 293 lint-consolidation
                # pass. This read `ruling_authority not in ("",
                # "agent_research")` - an ALLOW-LIST OF NEGATIVES. It is safe
                # only while nobody upstream invents a new authority token:
                # `agent_research_two_leg`, `vendor`, `web_verified` would each
                # have read as AN OWNER RULING and SUPPRESSED the tier-A
                # demotion below, which is regression rule 4 ("never treat
                # agent research as Elijah's ruling") failing open. The
                # authorities that actually count are NAMED. Measured in
                # np_orgs.csv today: '' 12,362 - agent_research 375 -
                # elijah_ruling 27, so this is behaviour-identical now and
                # correct when the vocabulary grows.
                OWNER_RULING_AUTHORITIES = {"elijah_ruling"}
                ruled = (r.get("funnel_stage") == "ruled_native_verified"
                         or (r.get("ruling_authority") or "").strip()
                         in OWNER_RULING_AUTHORITIES)
                if tier == "A" and not ruled:
                    risky = []
                    if (r.get("placename_risk_flag") or "").strip():
                        risky.append("placename_risk_flag="
                                     + r["placename_risk_flag"])
                    if (r.get("review_flag") or "").strip():
                        risky.append("review_flag=" + r["review_flag"])
                    if risky:
                        tier = "B"
                        basis += ";" + ";".join(risky)
                    else:
                        basis += ";name match clears placename and civic flags"
                elif ruled:
                    basis += ";ruled_native_verified"
                stat[f"tier_{tier}"] += 1
                if tier == "B":
                    seen_B[(nm, tid, canon, basis)] += 1
            else:
                stat["refused"] += 1
                if basis != "no_source_name":
                    seen_ref[(nm, basis)] += 1

        r["tribe_id"] = tid
        r["tribe_canonical_name"] = canon
        r["entity_match_method"] = method
        r["entity_tier"] = tier
        r["entity_match_basis"] = basis
        r["entity_keyed_date"] = TODAY
        r["entity_id"] = tid if tier == "A" else ""

    # The promotion queue for 12k nonprofits would be unusable, so it carries
    # only names appearing on more than one org or with a tier-B exact/alias
    # hit - the ones a single ruling actually settles.
    for (nm, tid, canon, basis), n in seen_B.items():
        if n > 1 or "resolver_exact" in basis or "resolver_alias" in basis:
            PROMOTIONS.append({"dataset": "np_orgs", "source_name": nm,
                               "proposed_tribe_id": tid, "proposed_name": canon,
                               "n_rows": n, "basis": basis, "queued": TODAY,
                               "YOUR_RULING": "", "YOUR_NOTE": ""})
    agg = Counter()
    for (nm, basis), n in seen_ref.items():
        agg[basis.split(":")[0]] += n
    for reason, n in agg.items():
        refuse("np_orgs", "(aggregated)", reason,
               f"{n:,} nonprofit rows refused for this reason", n)
    # ...and the org-type bar individually, because those are the expensive ones
    for (nm, basis), n in seen_ref.items():
        if basis.startswith("org_type_barred") or basis.startswith("match_rests_only"):
            refuse("np_orgs", nm, basis.split(":")[0], basis, n)

    rewrite_in_place(p, rows, ["tribe_id", "tribe_canonical_name",
                               "entity_match_method", "entity_tier",
                               "entity_match_basis", "entity_keyed_date"])
    s = show("np_orgs", rows, stat)
    s["excluded_X"] = stat.get("excluded", 0)
    SUMMARY.append(s)


# =========================================== 5. free text -> bridge tables ===

def build_text_index():
    """Spine name strings as token sequences, with the free-text bars applied."""
    names = defaultdict(set)
    label = {}
    dropped = []
    for r in SPINE_ROWS:
        strings = [r["canonical_name"]] + [a.strip() for a in
                                           (r.get("aliases") or "").split("|")]
        for s in strings:
            s = s.strip()
            if not s:
                continue
            # BAR: acronym aliases are landmines in prose.
            if len(s) <= 6 and s.isupper() and " " not in s:
                dropped.append((r["tribe_id"], s, "acronym_alias"))
                continue
            toks = tuple(norm(s).split())
            if not toks:
                continue
            ident = [t for t in toks if t not in STRUCTURAL]
            if not ident:
                dropped.append((r["tribe_id"], s, "all_structural"))
                continue
            # BAR: a name string whose identifying tokens are ALL generic is
            # never matched in free text. `Council`, `Little River`,
            # `Tribal Self-Governance` are real spine strings and real traps.
            if all(t in GENERIC for t in ident):
                dropped.append((r["tribe_id"], s, "all_generic_tokens"))
                continue
            names[toks].add(r["tribe_id"])
            label[toks] = s
    by_first = defaultdict(list)
    for toks in names:
        by_first[toks[0]].append(toks)
    for k in by_first:
        by_first[k].sort(key=len, reverse=True)   # longest match wins
    return names, label, by_first, dropped


TXT_NAMES, TXT_LABEL, TXT_BY_FIRST, TXT_DROPPED = build_text_index()


def scan_text(text):
    """Find spine name strings in free text. Returns [(span, tribe_id, tier,
    basis)] with tribe_id empty where refused.

    TWO BARS THAT WERE ADDED AFTER MEASURING THE FIRST RUN, because the first
    run produced false attributions of exactly the kind this project has paid
    for before. Both are recorded here rather than quietly fixed.

    (a) A TRIBAL DESIGNATOR IS REQUIRED FOR TIER A. Tribes are named after
        places and places after tribes, so a bare place-name span proves
        nothing. The first run put 157 documents on the San Juan tribe (AZ)
        including `Business Development Center Applications: San Juan, PR` and
        a Rio Grande National Forest plan, and 114 on the Las Vegas Paiute
        tribe including `Business Development Center Applications: Las Vegas,
        Nevada`. `St. Mary's County, MD` landed on an Alaska Native village.
        This is the same defect that left 282 place-name coincidences at
        publishable tier A in the nonprofit dataset.

        So tier A now requires a designator word - tribe, band, nation, pueblo,
        rancheria, community, village, indians, reservation - inside the span,
        within 4 tokens after it, or within 3 tokens before it. `Las Vegas
        Paiute Tribe Liquor Control Ordinance` still reaches A; `Las Vegas,
        Nevada` drops to B.

    (b) COMPOUND TRIBAL NAMES MUST NOT BE SPLIT. `Confederated Salish and
        Kootenai Tribes` matched `Confederated Salish` (CSKT, Montana) and
        then `Kootenai` (the Kootenai Tribe of IDAHO) as separate entities -
        which is precisely the TRBF-KTNIID-00 conflation that invariant 2 of
        the regression check exists to prevent, reappearing in a new dataset.

        Two spans separated by two tokens or fewer with NO designator between
        them are one compound name, and both are demoted. A genuine list keeps
        its designators - `Navajo Nation, Hopi Tribe, and Crow Tribe` has
        `tribe` in every gap, and `Little Traverse Bay Bands of Odawa Indians
        and the Little River Band of Ottawa Indians` has seven - so lists
        survive while compounds do not.

        KNOWN RECALL COST, stated rather than hidden: a bare comma-separated
        list (`Hopi, Zuni and Navajo`) is indistinguishable from a compound
        once punctuation is normalised away, so both members are demoted to
        tier B. They stay in the bridge and enter the promotion queue, so
        nothing is lost - but the tier-A count for federal actions is a floor,
        not a ceiling. Recovering them needs punctuation preserved through
        `norm()`, which is the shared resolver's function and is not forked
        here.
    """
    toks = norm(text).split()
    raw, i = [], 0
    while i < len(toks):
        hit = None
        for cand in TXT_BY_FIRST.get(toks[i], ()):
            if tuple(toks[i:i + len(cand)]) == cand:
                hit = cand
                break
        if not hit:
            i += 1
            continue
        raw.append((i, i + len(hit), hit))
        i += len(hit)

    # (b) compound detection over adjacent spans. Two spans naming the SAME
    # entity are a repetition ("Omaha, Nebraska ... the Omaha Tribe"), not a
    # compound name, so only differing entities are flagged.
    compound = {}
    for k in range(1, len(raw)):
        pe, cs = raw[k - 1][1], raw[k][0]
        gap = toks[pe:cs]
        if len(gap) > 2 or (set(gap) & DESIGNATOR):
            continue
        if TXT_NAMES[raw[k - 1][2]] == TXT_NAMES[raw[k][2]]:
            continue
        compound[k - 1] = k
        compound[k] = k - 1

    out = []
    for k, (s, e, hit) in enumerate(raw):
        ids = TXT_NAMES[hit]
        span = TXT_LABEL[hit]
        ident = [t for t in hit if t not in STRUCTURAL]
        strong = [t for t in ident if t not in GENERIC]
        ctx = set(toks[e:e + 4]) | set(toks[max(0, s - 3):s])
        desig = bool(set(hit) & DESIGNATOR) or bool(ctx & DESIGNATOR_CONTEXT)

        if len(ids) > 1:
            out.append((span, "", "", f"ambiguous_span:{len(ids)}_entities:"
                                      + ",".join(sorted(ids)[:3])))
            continue
        if set(strong) and set(strong) <= set(NAME_TRAPS):
            out.append((span, "", "", "span_is_only_a_trap_token:"
                                      + "|".join(sorted(strong))))
            continue
        if not strong:
            out.append((span, "", "", "no_non_generic_token_in_span"))
            continue

        tid = next(iter(ids))
        if k in compound:
            other = TXT_LABEL[raw[compound[k]][2]]
            out.append((span, tid, "B",
                        f"compound_name_ambiguous:adjacent to '{other}' with no "
                        f"designator between them - probably one compound tribal "
                        f"name, not two entities"))
        elif not desig:
            out.append((span, tid, "B",
                        "no_tribal_designator_in_context:a bare place name "
                        "proves nothing - tribes and places share names"))
        elif len(strong) >= 2:
            out.append((span, tid, "A",
                        "multi_token_exact_span_with_tribal_designator"))
        else:
            out.append((span, tid, "A",
                        "exact_span_with_tribal_designator_in_context"))
    return out


def do_bills():
    print("\n[5] native_bills -> bridge (a bill affects MANY tribes)")
    bills = rd(CLEAN / "native_bills.csv")
    bridge, stat = [], Counter()
    keyed_bills = set()
    ref = defaultdict(int)
    for b in bills:
        seen = {}
        for src in ("title",):
            for span, tid, tier, basis in scan_text(b.get(src) or ""):
                if not tid:
                    ref[(span, basis)] += 1
                    continue
                # keep the strongest tier per (bill, entity)
                if tid not in seen or (tier == "A" and seen[tid][1] == "B"):
                    seen[tid] = (span, tier, basis, src)
        for tid, (span, tier, basis, src) in seen.items():
            bridge.append({
                "bill_id": b["bill_id"], "tribe_id": tid,
                "tribe_canonical_name": SPINE_BY_ID[tid]["canonical_name"],
                "matched_span": span, "matched_in": src,
                "entity_tier": tier, "entity_match_method": "spine_name_in_title",
                "entity_match_basis": basis,
                "bill_scope": b.get("bill_scope", ""),
                "congress": b.get("congress", ""),
                "bill_title": b.get("title", ""),
                "entity_keyed_date": TODAY})
            stat[f"tier_{tier}"] += 1
            keyed_bills.add(b["bill_id"])
    for (span, basis), n in ref.items():
        refuse("native_bills", span, basis.split(":")[0], basis, n)

    wr(CLEAN / "native_bills_entity_bridge.csv", bridge)
    queue_bridge_tierB(bridge, "native_bills_bridge", "bill_id")
    print(f"    bills with >=1 entity : {len(keyed_bills):,} of {len(bills):,} "
          f"({len(keyed_bills)/len(bills)*100:.1f}%)")
    ts = [b for b in bills if b.get("bill_scope") == "tribe-specific"]
    tsk = sum(1 for b in ts if b["bill_id"] in keyed_bills)
    print(f"    tribe-specific bills  : {tsk:,} of {len(ts):,} "
          f"({tsk/len(ts)*100:.1f}%) keyed")
    SUMMARY.append({"dataset": "native_bills (bridge)", "rows": len(bills),
                    "keyed": len(keyed_bills),
                    "pct_keyed": round(len(keyed_bills) / len(bills) * 100, 1),
                    "tier_A": stat.get("tier_A", 0), "tier_B": stat.get("tier_B", 0),
                    "refused": len(bills) - len(keyed_bills),
                    "note": f"{len(bridge):,} bill-entity links"})

    # bill_votes reach entities THROUGH bill_id. The bridge below is a pure
    # join, added because it is small and directly useful; member_positions
    # (136,119 rows) is deliberately NOT expanded - it joins through bill_id
    # like everything else, and materialising 136k x N links would invent
    # nothing but would triple the file for no information.
    by_bill = defaultdict(list)
    for x in bridge:
        by_bill[x["bill_id"]].append(x)
    votes = rd(CLEAN / "bill_votes.csv")
    vb = []
    vk = set()
    for v in votes:
        for x in by_bill.get(v.get("bill_id"), ()):
            vb.append({"vote_id": v["vote_id"], "bill_id": v["bill_id"],
                       "tribe_id": x["tribe_id"],
                       "tribe_canonical_name": x["tribe_canonical_name"],
                       "entity_tier": x["entity_tier"],
                       "entity_match_method": "inherited_via_bill_id",
                       "entity_match_basis":
                           f"structural inheritance from {v['bill_id']} "
                           f"({x['entity_match_basis']})",
                       "chamber": v.get("chamber", ""), "date": v.get("date", ""),
                       "entity_keyed_date": TODAY})
            vk.add(v["vote_id"])
    wr(CLEAN / "bill_votes_entity_bridge.csv", vb)
    SUMMARY.append({"dataset": "bill_votes (bridge)", "rows": len(votes),
                    "keyed": len(vk),
                    "pct_keyed": round(len(vk) / len(votes) * 100, 1) if votes else 0,
                    "tier_A": sum(1 for x in vb if x["entity_tier"] == "A"),
                    "tier_B": sum(1 for x in vb if x["entity_tier"] == "B"),
                    "refused": len(votes) - len(vk),
                    "note": f"{len(vb):,} vote-entity links, inherited via bill_id"})
    SUMMARY.append({"dataset": "member_positions", "rows": len(rd(CLEAN / "member_positions.csv")),
                    "keyed": 0, "pct_keyed": 0.0, "tier_A": 0, "tier_B": 0,
                    "refused": 0,
                    "note": "NOT KEYED BY DESIGN - joins through bill_id to the "
                            "bill bridge. A member position is a person's vote, "
                            "not an entity fact."})


def do_federal_actions():
    print("\n[6] federal_actions -> bridge (a notice can name several tribes)")
    rows = rd(CLEAN / "federal_actions.csv")
    NAMED = {"ancsa_conveyance", "tribal_state_compact", "land_into_trust",
             "liquor_ordinance", "federal_acknowledgment",
             "reservation_proclamation", "gaming_land_decision",
             "irrigation_rates", "recognition_list_update", "consultation"}
    bridge, stat, ref = [], Counter(), defaultdict(int)
    keyed = set()
    for r in rows:
        named = r.get("action_type") in NAMED
        seen = {}
        srcs = [("title", r.get("title") or "")]
        # The abstract is scanned only inside the ten named buckets, which are
        # 82-100% precise. Scanning 134k 'other'/'rulemaking' abstracts would
        # multiply the trap surface for material that mostly names no tribe.
        if named:
            srcs.append(("abstract", r.get("abstract") or ""))
        for src, txt in srcs:
            if not txt:
                continue
            for span, tid, tier, basis in scan_text(txt):
                if not tid:
                    if src == "title":
                        ref[(span, basis)] += 1
                    continue
                # An abstract hit is weaker evidence of subject-hood than a
                # title hit, so it never publishes on its own.
                if src == "abstract" and tier == "A":
                    tier, basis = "B", basis + ";matched_in_abstract_not_title"
                if tid not in seen or (tier == "A" and seen[tid][1] == "B"):
                    seen[tid] = (span, tier, basis, src)
        for tid, (span, tier, basis, src) in seen.items():
            bridge.append({
                "document_number": r.get("document_number"),
                "tribe_id": tid,
                "tribe_canonical_name": SPINE_BY_ID[tid]["canonical_name"],
                "matched_span": span, "matched_in": src,
                "entity_tier": tier, "entity_match_method": "spine_name_in_text",
                "entity_match_basis": basis,
                "action_type": r.get("action_type", ""),
                "publication_date": r.get("publication_date", ""),
                "title_abstract_term_hit": r.get("title_abstract_term_hit", ""),
                "document_title": (r.get("title") or "")[:300],
                "entity_keyed_date": TODAY})
            stat[f"tier_{tier}"] += 1
            keyed.add(r.get("document_number"))
    for (span, basis), n in ref.items():
        refuse("federal_actions", span, basis.split(":")[0], basis, n)

    wr(CLEAN / "federal_actions_entity_bridge.csv", bridge)
    queue_bridge_tierB(bridge, "federal_actions_bridge", "document_number")
    named_rows = [r for r in rows if r.get("action_type") in NAMED]
    nk = sum(1 for r in named_rows if r.get("document_number") in keyed)
    print(f"    documents with >=1 entity : {len(keyed):,} of {len(rows):,} "
          f"({len(keyed)/len(rows)*100:.1f}%)")
    print(f"    within the 10 named buckets: {nk:,} of {len(named_rows):,} "
          f"({nk/len(named_rows)*100:.1f}%)")
    SUMMARY.append({"dataset": "federal_actions (bridge)", "rows": len(rows),
                    "keyed": len(keyed),
                    "pct_keyed": round(len(keyed) / len(rows) * 100, 1),
                    "tier_A": stat.get("tier_A", 0),
                    "tier_B": stat.get("tier_B", 0),
                    "refused": len(rows) - len(keyed),
                    "note": f"{len(bridge):,} document-entity links; "
                            f"{nk:,}/{len(named_rows):,} of the named buckets keyed"})


# ================================================================== main =====


def main():
    print("=== Cedar Press 70: key the six unjoined datasets ===\n")
    print(f"spine entities: {len(SPINE_ROWS):,}")
    print(f"free-text index: {len(TXT_NAMES):,} name strings usable; "
          f"{len(TXT_DROPPED):,} barred from prose "
          f"({Counter(d[2] for d in TXT_DROPPED).most_common()})")

    do_ownership_events()
    do_compacts()
    do_gaming()
    do_np_orgs()
    do_bills()
    do_federal_actions()

    for tid, s, why in TXT_DROPPED:
        refuse("free_text_index", s, why,
               f"{tid}: this spine name string is barred from free-text "
               f"matching", 0)

    wr(REVIEW / f"entity_key_refusals_{TODAY}.csv",
       sorted(REFUSALS, key=lambda r: (-r["n_rows"], r["dataset"])),
       ["dataset", "source_name", "reason", "detail", "n_rows", "context",
        "refused_date"])
    wr(REVIEW / f"entity_key_tierB_promotion_queue_{TODAY}.csv",
       sorted(PROMOTIONS, key=lambda r: -r["n_rows"]),
       ["dataset", "source_name", "proposed_tribe_id", "proposed_name",
        "n_rows", "basis", "queued", "YOUR_RULING", "YOUR_NOTE"])

    print("\n=== SUMMARY ===")
    hdr = f"{'dataset':30s} {'rows':>9s} {'keyed':>9s} {'%':>6s} {'A':>8s} {'B':>8s}"
    print(hdr)
    print("-" * len(hdr))
    for s in SUMMARY:
        print(f"{s['dataset']:30s} {s['rows']:>9,} {s['keyed']:>9,} "
              f"{s['pct_keyed']:>5.1f}% {s['tier_A']:>8,} {s['tier_B']:>8,}")

    write_log()


def write_log():
    L = [f"# Entity-key propagation log", "",
         f"*Written by `code/70_key_unjoined_datasets.py` on {TODAY}.*",
         f"*Every number below is measured from the data at run time; "
         f"regenerate rather than hand-edit.*", "",
         "Six datasets carried a 0%-populated entity key and joined to nothing.",
         "This run keys them against the 952-entity spine using the ONE resolver",
         "(`33_apply_party_rulings.resolve_entity`).", "",
         "## Result", "",
         "| Dataset | Rows | Keyed | % | Tier A | Tier B | Note |",
         "|---|---:|---:|---:|---:|---:|---|"]
    for s in SUMMARY:
        L.append(f"| {s['dataset']} | {s['rows']:,} | {s['keyed']:,} | "
                 f"{s['pct_keyed']}% | {s['tier_A']:,} | {s['tier_B']:,} | "
                 f"{s.get('note','')} |")
    L += ["",
          "## How to read the new columns", "",
          "| Column | Meaning |", "|---|---|",
          "| `tribe_id` | The spine entity. Present at EVERY tier - read `entity_tier` before using it. |",
          "| `entity_id` | The **publishable** key. Written only at tier A, blank otherwise. |",
          "| `entity_tier` | `A` publishable · `B` never publishes until ruled · `X` excluded by ruling |",
          "| `entity_match_method` | exact / alias / core / containment / inherited / propagated ruling |",
          "| `entity_match_basis` | Why, in words, including every guard that fired |",
          "",
          "Roll-up joins `tribe_id` to the spine and aggregates on",
          "`ultimate_parent_entity_id`.", "",
          "## Tier rule applied", "",
          "Tier A requires an **exact** name match, an **alias** match, a",
          "**documented ruling**, or **structural inheritance** from a tier-A",
          "parent row. Core-set equality and containment are tier B, however",
          "obviously right they look. Every distinct tier-B name is queued in",
          f"`review/entity_key_tierB_promotion_queue_{TODAY}.csv` so one ruling",
          "settles every row carrying that name.", "",
          "## Many-to-many, modelled as bridges", "",
          "A bill affects many tribes and a Federal Register notice can name",
          "several. Those get bridge tables, never a single `tribe_id`:", "",
          "- `data/clean/native_bills_entity_bridge.csv`",
          "- `data/clean/bill_votes_entity_bridge.csv` (inherited via `bill_id`)",
          "- `data/clean/federal_actions_entity_bridge.csv`", "",
          "`member_positions.csv` is deliberately **not** keyed. It joins",
          "through `bill_id` to the bill bridge; a member's vote is a fact",
          "about a person, not about an entity.", "",
          "## What refused, and why", "",
          "A refusal is a good outcome. Full list:",
          f"`review/entity_key_refusals_{TODAY}.csv`.", "",
          "| Reason | Rows |", "|---|---:|"]
    agg = Counter()
    for r in REFUSALS:
        agg[r["reason"]] += r["n_rows"]
    for k, v in agg.most_common(25):
        L.append(f"| `{k}` | {v:,} |")
    L += ["",
          "## The guards that fired", "",
          "1. **Organisation type is a bar, not a score** - reused from",
          "   `code/65`. A municipality, mining company, power district,",
          "   cooperative or university cannot be a Native entity.",
          "2. **Name traps** - a match resting entirely on `creek`, `cherokee`,",
          "   `colorado`, `ojibwe`, `shawnee`, `oneida` or `apache` is refused.",
          "3. **State disagreement** demotes; with a trap token it refuses.",
          "4. **Village corporation != village government** - the resolver's",
          "   ANCSA guard, re-checked here on the alias route.",
          "5. **BIA index defect** - the 41 compact rows and 3 gaming-decision",
          "   rows with `bia_tribes_column_conflict` cannot reach tier A off",
          "   the defective column.",
          "6. **Nonprofits** - `verified_strict` is a NAME match, not verified",
          "   Native status, so an exact hit still needs to clear the",
          "   place-name and civic-descriptor flags.",
          "7. **Free text** additionally bars generic-token name strings",
          f"   (`Council`, `Little River`, `Tribal Self-Governance`) and acronym",
          f"   aliases. {len(TXT_DROPPED):,} spine name strings are excluded from",
          "   prose matching for this reason.", ""]
    (DOCS / "ENTITY_KEY_PROPAGATION_LOG.md").write_text("\n".join(L),
                                                        encoding="utf-8")
    print(f"\n  wrote docs/ENTITY_KEY_PROPAGATION_LOG.md")


if __name__ == "__main__":
    main()
