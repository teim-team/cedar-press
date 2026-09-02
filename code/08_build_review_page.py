#!/usr/bin/env python3
"""
Cedar Press - 08: Build the entity review page.

A working instrument, not a report. Elijah rules on uncertain attributions in
the browser and exports a rulings CSV that gets imported back as permanent
per-entity decisions - the same jurisprudence model as the do-file's per-UEI
drops, industrialised.

Queues, ordered by consequence:
  1. Authority conflicts  - hand-checked work disagrees with an automated guess
  2. Exclusion collisions - something attributed that a ruling already excluded
  3. NHO parent unknown   - 8(a)-verified firm, parent NHO not identified
  4. High-value tier B    - biggest unreviewed dollar attributions

Output
------
review/cedar_review.html
"""

import csv
import json
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
EXT = CEDAR / "data" / "raw" / "external"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

# A NEW FILE PATH MINTS A NEW ARTIFACT URL, which is how we defeat browser and
# CDN caching: Elijah refreshes and reliably sees the current queue.
#
# The cost is that localStorage is per-origin, so a new URL starts with no saved
# rulings. That is safe ONLY because already-ruled items are suppressed at build
# time - they simply are not in the new page. Un-exported work would be lost, so
# the page carries a persistent unexported-rulings warning.
def next_build_path():
    n = 1
    while (REVIEW / f"cedar_review_{TODAY}_{n:02d}.html").exists():
        n += 1
    return REVIEW / f"cedar_review_{TODAY}_{n:02d}.html", n


OUT, BUILD_N = next_build_path()
BUILD_ID = f"{TODAY} #{BUILD_N:02d}"

# Deep reserve so Elijah never hits the bottom of the queue mid-session.
# Cards render in batches so the DOM stays fast regardless of this number.
TIER_B_SHOWN = 1500
BATCH = 40

# Elijah, 2026-08-05: his fastest, highest-value contribution is looking up a
# CAGE/UEI and linking the firm to a Native entity. Everything answerable from
# online sources - nonprofit classification, place-name questions - should be
# researched by agents instead of taking his time.
#
# So this page carries ONLY identifier-to-entity work. The nonprofit queues are
# built into their own file for the research agents, not shown here.
ELIJAH_QUEUES = {"conflict", "collision", "nho", "deals_party", "quarantine", "tierb"}
AGENT_QUEUES = {"np_placename", "np_recheck"}


def read_csv(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def money(v):
    try:
        f = float(v or 0)
    except ValueError:
        return ""
    if f >= 1000:
        return f"${f/1000:,.2f}B"
    if f >= 1:
        return f"${f:,.1f}M"
    if f > 0:
        return f"${f*1000:,.0f}K"
    return ""


def build_cage_index():
    """UEI -> CAGE, from every source that carries both.

    Elijah reviews on cage.dla.mil, so CAGE must ride on every card. Where no
    CAGE exists we say so explicitly rather than leaving a silent blank - an
    absent CAGE usually means a lapsed SAM registration, which is itself a fact
    worth seeing before ruling.
    """
    idx = {}

    def put(uei, cage):
        uei = (uei or "").strip().upper()
        cage = (cage or "").strip().upper()
        if uei and cage and uei not in idx:
            idx[uei] = cage

    for r in read_csv(EXT / "sba_dsbs_native_entities.csv"):
        put(r.get("uei"), r.get("cage_code"))
    for r in read_csv(EXT / "need_v6_geocoded.csv"):
        put(r.get("enterprise_uei"), r.get("enterprise_cage_code"))
    for r in read_csv(EXT / "hawaii_nho_candidates.csv"):
        put(r.get("uei"), r.get("cage_code"))

    sam = Path(r"C:\Users\esm247\Desktop\dissertation\data\tribal_federal_spending"
               r"\sam_extracts")
    if sam.exists():
        for p in sorted(sam.glob("parsed_*.csv")):
            for r in read_csv(p):
                put(r.get("uei"), r.get("cage_code"))
    return idx


CAGE_IDX = {}


def cage_for(identifier_type, identifier):
    if identifier_type != "UEI":
        return "", ""
    c = CAGE_IDX.get((identifier or "").strip().upper(), "")
    if c:
        return c, f"https://cage.dla.mil/Search/Results?q={c}"
    return "", ""


def ledger_path():
    """The post-rulings ledger if it exists, else the pre-rulings one.

    09_import_rulings.py writes _final; 03 writes _tiered. Reading _tiered
    after rulings had been imported meant the queue and the summary tiles both
    reported pre-ruling state.
    """
    final = CLEAN / "cedar_identifier_ledger_final.csv"
    return final if final.exists() else CLEAN / "cedar_identifier_ledger_tiered.csv"


def count_elijah_rulings():
    """Distinct review_ids Elijah has actually ruled on."""
    return len(already_ruled())


def already_ruled():
    """review_ids Elijah has already settled - never show them again."""
    done = set()
    for p in sorted(REVIEW.glob("rulings_inbox_*.csv")):
        for r in read_csv(p):
            rid = (r.get("review_id") or "").strip()
            if rid and (r.get("YOUR_RULING") or "").strip():
                done.add(rid)
    return done


def write_agent_research_file(agent_items):
    """Questions answerable from online sources, routed to research agents.

    These are classification questions - is this nonprofit Native-controlled,
    or named for a place - which a web search settles. Elijah's time is worth
    far more on CAGE/UEI lookups he can do in seconds and nobody else can.
    """
    done = already_ruled()
    open_items = [it for it in agent_items if it["id"] not in done]
    rows = []
    for it in open_items:
        facts = {k: v for k, v in it.get("facts", [])}
        rows.append({
            "review_id": it["id"],
            "queue": it["queue"],
            "ein": it["id"].split(":", 1)[1] if ":" in it["id"] else "",
            "org_name": it["title"],
            "question": it["question"],
            "options": " | ".join(it.get("options", [])),
            "latest_revenue": facts.get("Latest revenue", ""),
            "state": facts.get("State", ""),
            "risk_level": facts.get("Risk level", ""),
            "AGENT_FINDING": "",
            "evidence_url": "",
            "confidence": "",
        })
    out = REVIEW / f"agent_research_queue_{TODAY}.csv"
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else
                           ["review_id", "queue", "ein", "org_name", "question",
                            "options", "latest_revenue", "state", "risk_level",
                            "AGENT_FINDING", "evidence_url", "confidence"])
        w.writeheader()
        w.writerows(rows)
    print(f"  routed {len(rows):,} research questions -> {out.name}")


def build_items():
    global CAGE_IDX
    CAGE_IDX = build_cage_index()
    items = []

    for r in read_csv(REVIEW / f"conflicts_{TODAY}.csv"):
        items.append({
            "queue": "conflict",
            "id": f"{r['identifier_type']}:{r['identifier']}",
            "title": r["legal_business_name"] or r["identifier"],
            "identifier": f"{r['identifier_type']} {r['identifier']}",
            "question": "Which entity actually owns this firm?",
            "options": [r["authority_says"], r["automated_says"]],
            "facts": [
                ("Hand-checked says", r["authority_says"]),
                ("Automated says", f"{r['automated_says']}  ({r['automated_method']})"),
            ],
            "value": money(r.get("prime_dollars_M")),
            "why": "Your hand-checked work disagrees with an automated match. "
                   "Automated matches on shared name tokens are the known trap.",
        })

    for r in read_csv(REVIEW / f"false_attributions_caught_{TODAY}.csv"):
        items.append({
            "queue": "collision",
            "id": f"{r['identifier_type']}:{r['identifier']}",
            "title": r["legal_business_name"] or r["identifier"],
            "identifier": f"{r['identifier_type']} {r['identifier']}",
            "question": "Does your exclusion ruling apply here?",
            "options": ["Exclusion applies - drop it",
                        f"Scope artifact - keep {r['wrongly_attributed_to']}"],
            "facts": [
                ("Currently attributed to", r["wrongly_attributed_to"]),
                ("Excluded by", f"{r['exclusion_id']} ({r['exclusion_reason']})"),
                ("Evidence", r.get("evidence_url", "")),
            ],
            "value": money(r.get("prime_dollars_M")),
            "why": "Your Condition-1 drops mean 'not THIS lower-48 tribe', so they "
                   "may not disprove an ANC parent. Scope check needed.",
        })

    for r in read_csv(REVIEW / f"nho_parent_unknown_{TODAY}.csv"):
        items.append({
            "queue": "nho",
            "id": f"UEI:{r['uei']}",
            "title": r["firm_name"],
            "identifier": f"UEI {r['uei']}  ·  CAGE {r['cage_code']}",
            "question": "Which NHO is the parent organization?",
            "options": [],
            "facts": [
                ("Location", r.get("city", "")),
                ("SBA certifications", r.get("sba_certifications", "")),
                ("Verified by", "Active 8(a) - SBA confirmed NHO ownership"),
            ],
            "value": "",
            "why": "SBA already verified this firm as NHO-owned. Only the parent "
                   "organization is missing.",
        })

    # Nonprofit exclusions the 990 agent flagged as probably-wrong. These were
    # produced by regex filters, NOT by hand rulings, so a name like
    # "Ponca Economic Development Corporation" may have been dropped for
    # carrying a token that is also a place name.
    for r in read_csv(SPINE / "nonprofit_exclusion_rulings.csv"):
        if (r.get("recheck_candidate") or "").strip() != "1":
            continue
        items.append({
            "queue": "np_recheck",
            "id": f"EIN:{r.get('ein','')}",
            "title": r.get("org_name", ""),
            "identifier": f"EIN {r.get('ein','')}",
            # A binary is too coarse. El Pueblo de Abiquiu Library is neither a
            # place-name coincidence nor a tribally controlled entity: real
            # genizaro programming, no Indigenous governance. The taxonomy in
            # NONPROFIT_DATASET_PLAN.md already has the middle categories, so
            # the queue should offer them.
            "question": "Which classification fits?",
            "options": ["Tribally controlled / Native-controlled - reinstate",
                        "Native-serving - mission targets Native people, control unclear",
                        "Place-name coincidence - keep excluded"],
            "facts": [
                ("Excluded because", r.get("exclusion_reason", "")),
                ("State", r.get("state", "")),
                ("Rule that fired", r.get("evidence", "")),
            ],
            "value": "",
            "why": "Excluded by an automated regex filter, not a hand ruling. "
                   "Tribe names and place names overlap constantly "
                   "(Ponca, Menominee, Cheyenne, Houma are all both).",
        })

    # Deal parties with no spine identifier. This is the highest-leverage queue
    # in the project: the deals schema carries no entity id, so Dataset 5 joined
    # 0 of 247 deal rows and the dated ownership-event ledger sits outside the
    # entity-year panel. 80 rulings fixes that permanently.
    # Prefer the AUTO-RESOLVED residue over the raw queue.
    #
    # Elijah, 2026-08-05: "i feel like you are asking stuff thats obvious like
    # the tribal government is in the name... the deals were sourced on the
    # basis that they could initially be identified as an indian country deal,
    # no?" Both points were right. A row is in this ledger because it was
    # already identified as an Indian Country deal, so the card must never ask
    # WHETHER it is Native - only WHICH entity. And 416 of 501 parties resolve
    # deterministically once the good matcher runs, so asking about those was
    # pure waste: 624 of 724 deal rows settled without a human.
    #
    # `57_autoresolve_deal_parties.py` writes the residue. Fall back to the raw
    # queue only if it has not been run.
    residue = REVIEW / "deals_party_still_open.csv"
    party_rows = read_csv(residue) if residue.exists() else \
        read_csv(REVIEW / f"deals_party_queue_{TODAY}.csv")

    # Sources ride on the card, clickable. Identifying a party from the article
    # the deal came from is far faster than from the name alone. The DISCOVERY
    # channel is kept separate from the source: trade-press reporting is how a
    # deal was found, never the authority for its date or amount.
    src_idx = {r["native_party"]: r
               for r in read_csv(CLEAN / "deals_source_index.csv")}

    for r in party_rows:
        cands = [c for c in (r.get("candidate_names") or "").split("|") if c.strip()]
        sv = src_idx.get(r.get("native_party", ""), {})
        sources = [{"url": sv.get(u, ""), "label": sv.get(l, "") or "source"}
                   for u, l in (("source_1_url", "source_1_label"),
                                ("source_2_url", "source_2_label"))
                   if sv.get(u)]
        items.append({
            "queue": "deals_party",
            "id": f"PARTY:{r.get('native_party','')}",
            "title": r.get("native_party", ""),
            "identifier": f"{r.get('n_deals','0')} deal(s) · no entity id on the deals schema",
            # Never "is this Native?" - the ledger settled that before the card
            # existed. Only which entity, and "not a Native entity" stays as an
            # option solely for the sourcing errors that do slip through.
            "question": r.get("question", "Which Native entity is this?"),
            "options": [c.strip() for c in cands][:3] + ["Not a Native entity"],
            "sources": sources,
            "discovery": sv.get("discovery_channel", ""),
            "confidence": 0.0,
            "confidenceNote": ("no proposal - the matcher settled 661 of 724 "
                               "deal rows and could not settle this one"),
            "facts": [
                ("Appears in", r.get("source_files", "")),
                ("Candidates found", r.get("candidate_names", "") or "none"),
            ],
            "value": "",
            "why": "The deals ledger has no identifier column, so these rows cannot join "
                   "to funding, contracting or lobbying. Ruling this party links every "
                   "deal it appears in, and unlocks the ownership-event ledger.",
        })

    # Tier-A nonprofits whose Native status may rest only on a place name.
    # RANKED BY REVENUE: the exposure is brutally concentrated - top 1 org is
    # 36.4% of it, top 5 is 80.3%, top 25 is 96.6%. About 15 rulings settle 90%
    # of the dollars, so ordering by revenue is worth far more than alphabetical.
    scale = {}
    for r in read_csv(CLEAN / "np_org_scale.csv"):
        ein = (r.get("ein") or r.get("EIN") or "").strip()
        if ein:
            scale[ein] = r
    np_rows = []
    for r in read_csv(REVIEW / f"np_placename_risk_{TODAY}.csv"):
        ein = (r.get("ein") or "").strip()
        s = scale.get(ein, {})
        try:
            rev = float(s.get("total_revenue") or 0)
        except ValueError:
            rev = 0.0
        np_rows.append((rev, r, s))
    np_rows.sort(key=lambda x: -x[0])

    for rev, r, s in np_rows:
        revtxt = money(rev / 1_000_000) if rev else "no revenue on file"
        items.append({
            "queue": "np_placename",
            "id": f"EIN:{r.get('ein','')}",
            "title": r.get("org_name", ""),
            "identifier": f"EIN {r.get('ein','')}",
            "question": "Native-controlled, or just named for a place?",
            "options": ["Native-controlled - keep in tier A",
                        "Named for a place - demote"],
            "facts": [
                ("Latest revenue", revtxt),
                ("Filing year", s.get("latest_year", "")),
                ("Risk level", r.get("risk", "")),
                ("State", r.get("state", "")),
            ],
            "value": revtxt if rev else "",
            "why": ("Counts toward the publishable nonprofit revenue total right now. "
                    "The flag runs BOTH ways: College of the Menominee Nation ($13.9M, "
                    "an AIHEC tribal college) and Akwesasne Boys & Girls Club sit on this "
                    "list too and would be promotions, not exclusions."),
        })

    # Read the POST-rulings ledger. Reading the pre-rulings file meant an
    # identifier whose tier changed because of a ruling still showed up in the
    # queue, and the summary tiles reported pre-ruling counts.
    tierb = [r for r in read_csv(ledger_path()) if r["confidence_tier"] == "B"]

    def dollars(r):
        try:
            return float(r.get("prime_dollars_M") or 0)
        except ValueError:
            return 0.0

    # Methods Elijah's rulings have discredited get their own queue. As of
    # 2026-08-05 every ruling on a need_v6 attribution went against it (9/0).
    # Those rows carry $0, so a pure dollar sort would never surface them -
    # reserve slots for them explicitly instead.
    quarantined = {"need_v6"}
    tierb.sort(key=dollars, reverse=True)
    quar = [r for r in tierb if r["attribution_method"] in quarantined]
    rest = [r for r in tierb if r["attribution_method"] not in quarantined]
    take_quar = min(len(quar), TIER_B_SHOWN // 3)
    selection = quar[:take_quar] + rest[:TIER_B_SHOWN - take_quar]

    for r in selection:
        q = "quarantine" if r["attribution_method"] in quarantined else "tierb"

        if q == "quarantine":
            # DO NOT SHOW THE GUESS.
            #
            # Scored against Elijah's own 89 rulings on need_v6 links: 13 upheld,
            # 9 rejected outright, 67 redirected to a different entity. The
            # method is right 14.6% of the time - so its proposal is not a
            # useful prior, it is an ANCHOR pointing at the wrong tribe.
            #
            # It produced "is this North Dakota radio station owned by Ahtna?"
            # and "is this King Cove, Alaska firm owned by Lumbee?". Naming a
            # wrong owner costs more than naming none: it frames a yes/no where
            # the honest question is open, and a "No" throws away the
            # attribution instead of capturing it.
            #
            # The 67 redirects are the evidence this queue is still worth
            # showing - Elijah supplies a correct owner most of the time. It is
            # the suggestion that is worthless, not the card.
            items.append({
                "queue": q,
                "id": f"{r['identifier_type']}:{r['identifier']}",
                "title": r["legal_business_name"] or r["identifier"],
                "identifier": f"{r['identifier_type']} {r['identifier']}",
                "question": "Which Native entity owns this, if any?",
                "options": ["Not a Native entity"],
                "facts": [
                    ("State", r.get("state", "")),
                    ("Attribution", "none - unreviewed algorithmic guess "
                                    "withheld (14.6% accurate)"),
                ],
                "value": money(r.get("prime_dollars_M")),
                "why": "Name the owner if you know it. A bare 'No' only rules "
                       "out a guess you were never shown - naming the entity "
                       "is what captures the attribution.",
            })
            continue

        items.append({
            "queue": q,
            "id": f"{r['identifier_type']}:{r['identifier']}",
            "title": r["legal_business_name"] or r["identifier"],
            "identifier": f"{r['identifier_type']} {r['identifier']}",
            "question": f"Is this genuinely owned by {r['canonical_name']}?",
            "options": [f"Yes - {r['canonical_name']}", "No - not this entity"],
            "method": r["attribution_method"],
            "facts": [
                ("Claimed owner", r["canonical_name"]),
                # Entity class matters: the CICD connector carries federally
                # recognized tribes, state-recognized tribes, ANCs and AK
                # villages as distinct classes. A state-recognized parent is a
                # legitimate class, not an exclusion.
                ("Entity class", r.get("entity_class", "")),
                ("Method", r["attribution_method"]),
                ("State", r.get("state", "")),
            ],
            "value": money(r.get("prime_dollars_M")),
            "why": "Algorithmic attribution, never reviewed. Nothing in tier B "
                   "publishes until ruled.",
        })

    # Split: identifier work to Elijah, research questions to the agents.
    # Quarantine cards go to BOTH: agents research them from the open web
    # (the About-page method settled 549 deal parties in one session), and
    # Elijah still sees them because a CAGE lookup he can do in seconds beats
    # any amount of searching. Whatever research settles first drops out of his
    # queue on the next rebuild.
    agent_items = [it for it in items
                   if it["queue"] in AGENT_QUEUES or it["queue"] == "quarantine"]
    if agent_items:
        write_agent_research_file(agent_items)
    items = [it for it in items if it["queue"] not in AGENT_QUEUES]

    # Drop anything already ruled. The queue only ever shows open work.
    done = already_ruled()
    before = len(items)
    items = [it for it in items if it["id"] not in done]
    if done:
        print(f"  suppressed {before-len(items):,} items already ruled "
              f"({len(done):,} rulings on file)")

    # Attach CAGE to every card. Elijah checks on cage.dla.mil, so the CAGE and
    # a ready-made search link travel with each item.
    for it in items:
        idtype, _, ident = it["id"].partition(":")
        if idtype == "CAGE":
            # The identifier IS the CAGE - don't claim it's missing.
            it["cage"] = ident
            it["cageUrl"] = f"https://cage.dla.mil/Search/Results?q={ident}"
            it["identifier"] = f"CAGE {ident}"
        else:
            cage, url = cage_for(idtype, ident)
            it["cage"] = cage
            it["cageUrl"] = url
            it["identifier"] = (f"{idtype} {ident}  ·  CAGE {cage}" if cage
                                else f"{idtype} {ident}  ·  CAGE not on file")

    # Order by what Elijah is fastest at. His highest-value move is a CAGE/UEI
    # lookup on cage.dla.mil or SAM - seconds per card, and it links a firm to
    # an entity for every dataset at once. A deals_party card carries only a
    # company name and needs open-web research (source article -> the firm's
    # own About page), which is agent work. So identifier-bearing cards lead,
    # and among those the ones that already have a CAGE to check lead again.
    #
    # Sort is STABLE, so each queue keeps the dollar ordering it was built with
    # and the most consequential rows stay on top within each band.
    def lookup_priority(it):
        idtype = it["id"].partition(":")[0]
        return (0 if idtype in ("UEI", "CAGE") else 1,
                0 if it.get("cage") else 1)

    # CONFIDENCE, measured rather than asserted.
    #
    # Elijah: "i think it would be helpful if i can write a note on top of
    # selecting an option so you actually learn and your % confidence".
    #
    # Each method's number is its hit rate against HIS OWN past rulings on that
    # method - upheld / (upheld + rejected + redirected). A redirect counts as a
    # miss, because the method proposed the wrong entity and he supplied the
    # right one. Scoring redirects as successes is how need_v6 first looked 90%
    # accurate when it is 14.6%.
    # A learned brand is an ANSWER, not a question. `alutiiq` resolves to
    # Afognak Native Corporation across 9 firms Elijah already settled, so the
    # next Alutiiq company should arrive pre-filled with that and its evidence -
    # not as a blank "which entity is this?".
    brands = {}
    for r in read_csv(CLEAN / "brand_family_proposals.csv"):
        brands[f"{r['identifier_type']}:{r['identifier']}".upper()] = r

    n_brand = 0
    for it in items:
        b = brands.get(it["id"].upper())
        if not b:
            continue
        n_brand += 1
        proposed = b["proposed_canonical_name"]
        it["options"] = [proposed] + [o for o in it.get("options", [])
                                      if o != proposed]
        it["facts"] = [("Brand", f"“{b['brand']}” → {proposed}"),
                       ("Sibling firms already settled",
                        b["n_confirmed_siblings"])] + it.get("facts", [])
        it["why"] = (f"{b['basis']} A brand match is strong evidence, not proof - "
                     f"a joint venture or a divested company can carry the brand "
                     f"and not the owner.")
        # Confidence scales with how many siblings demonstrated the brand, and
        # is capped: a brand is never proof.
        n = int(b["n_confirmed_siblings"] or 0)
        it["confidence"] = min(0.92, 0.55 + 0.05 * n)
        it["confidenceNote"] = (f"brand seen on {n} firms you already settled, "
                               f"all the same owner")
    if n_brand:
        print(f"  pre-filled {n_brand:,} cards from learned brand families")

    scores = method_accuracy()
    for it in items:
        if it.get("confidence") is not None:
            continue
        m = it.get("method") or ("need_v6" if it["queue"] == "quarantine" else "")
        if m and m in scores:
            n_up, n_tot = scores[m]
            it["confidence"] = n_up / n_tot
            it["confidenceNote"] = f"{n_up}/{n_tot} of your rulings upheld this method"
        elif it["queue"] == "quarantine":
            it["confidence"] = 0.146
            it["confidenceNote"] = "guess withheld - 13 upheld, 9 rejected, 67 redirected"

    items.sort(key=lookup_priority)
    return items, len(tierb)


def method_accuracy():
    """Per-method hit rate against Elijah's own rulings.

    A ruling that NAMES A DIFFERENT ENTITY is a miss, not a hit. That single
    distinction is the difference between reporting need_v6 at 90% and at its
    real 14.6%.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m33 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m33)

    proposed = {}
    for r in read_csv(ledger_path()):
        proposed[f"{r['identifier_type']}:{r['identifier']}".upper()] = (
            r.get("attribution_method", ""), r.get("canonical_name", ""))

    tally = {}
    for p in sorted(REVIEW.glob("rulings_inbox_*.csv")):
        for r in read_csv(p):
            rid = (r.get("review_id") or "").strip().upper()
            ans = (r.get("YOUR_RULING") or "").strip()
            hit = proposed.get(rid)
            if not hit or not ans:
                continue
            meth, canon = hit
            if not meth:
                continue
            up, tot = tally.get(meth, (0, 0))
            a, c = m33.norm(ans), m33.norm(canon)
            tot += 1
            if c and c in a:
                up += 1
            tally[meth] = (up, tot)
    return {k: v for k, v in tally.items() if v[1] >= 3}


def main():
    items, tierb_total = build_items()
    ledger = read_csv(ledger_path())
    counts = {"A": 0, "B": 0, "C": 0, "X": 0}
    for r in ledger:
        counts[r["confidence_tier"]] = counts.get(r["confidence_tier"], 0) + 1

    stats = {
        "tierA": counts.get("A", 0),
        "tierB": counts.get("B", 0),
        "tierC": counts.get("C", 0),
        "tierX": counts.get("X", 0),
        "spine": len(read_csv(SPINE / "cedar_entity_spine.csv")),
        # Elijah's own rulings, NOT the exclusion-ruling count. The tile
        # previously showed 123 exclusions labeled "your rulings on file".
        "exclusions": count_elijah_rulings(),
        "shown": len(items),
        "tierbTotal": tierb_total,
        "batch": BATCH,
    }

    html = TEMPLATE.replace("__DATA__", json.dumps(items)) \
                   .replace("__STATS__", json.dumps(stats)) \
                   .replace("__BUILD__", BUILD_ID) \
                   .replace("__DATE__", TODAY)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    # Keep a stable copy too, so anything referencing the old path still works.
    (REVIEW / "cedar_review.html").write_text(html, encoding="utf-8")
    print(f"wrote {OUT.relative_to(CEDAR)}")
    print(f"  review items embedded : {len(items):,}")
    for q in ("conflict", "collision", "nho", "deals_party", "np_placename",
              "np_recheck", "quarantine", "tierb"):
        print(f"    {q:10s}: {sum(1 for i in items if i['queue']==q):,}")


TEMPLATE = r"""<title>Cedar Press — Entity Attribution Review</title>
<style>
:root{
  --ground:#F5F6F8; --panel:#FFFFFF; --edge:#DDE1E7;
  --ink:#161A20; --ink-2:#4B5563; --ink-3:#7B8492;
  --accent:#2F4E7A; --accent-soft:#E6ECF5;
  --ok:#1F6B45; --ok-soft:#E3F1E9;
  --warn:#8A5A12; --warn-soft:#F6EEDF;
  --stop:#8C2A2A; --stop-soft:#F6E5E5;
  --radius:3px;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace;
  --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif;
}
@media (prefers-color-scheme:dark){
  :root{
    --ground:#0F1318; --panel:#161B22; --edge:#262D38;
    --ink:#E8EBEF; --ink-2:#A8B2BF; --ink-3:#6F7B8A;
    --accent:#7BA3DB; --accent-soft:#1B2635;
    --ok:#5FBE8C; --ok-soft:#14261D;
    --warn:#D9A44E; --warn-soft:#2A2113;
    --stop:#E08585; --stop-soft:#2C1717;
  }
}
:root[data-theme="dark"]{
  --ground:#0F1318; --panel:#161B22; --edge:#262D38;
  --ink:#E8EBEF; --ink-2:#A8B2BF; --ink-3:#6F7B8A;
  --accent:#7BA3DB; --accent-soft:#1B2635;
  --ok:#5FBE8C; --ok-soft:#14261D;
  --warn:#D9A44E; --warn-soft:#2A2113;
  --stop:#E08585; --stop-soft:#2C1717;
}
:root[data-theme="light"]{
  --ground:#F5F6F8; --panel:#FFFFFF; --edge:#DDE1E7;
  --ink:#161A20; --ink-2:#4B5563; --ink-3:#7B8492;
  --accent:#2F4E7A; --accent-soft:#E6ECF5;
  --ok:#1F6B45; --ok-soft:#E3F1E9;
  --warn:#8A5A12; --warn-soft:#F6EEDF;
  --stop:#8C2A2A; --stop-soft:#F6E5E5;
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--sans);
     font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:32px 20px 140px}
header{border-bottom:2px solid var(--ink);padding-bottom:18px;margin-bottom:26px}
.eyebrow{font-family:var(--mono);font-size:11px;letter-spacing:.14em;
         text-transform:uppercase;color:var(--ink-3)}
h1{font-family:var(--serif);font-size:clamp(28px,4vw,40px);line-height:1.12;
   margin:.32em 0 .18em;font-weight:600;text-wrap:balance}
.sub{color:var(--ink-2);max-width:64ch;margin:0}
.freshness{font-family:var(--mono);font-size:12px;margin:8px 0 0;max-width:70ch}
.freshness--warn{color:var(--stop);font-weight:600}
.freshness--ok{color:var(--ok)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));
       gap:10px;margin:22px 0 30px}
.tile{background:var(--panel);border:1px solid var(--edge);border-radius:var(--radius);
      padding:12px 14px}
.tile .n{font-family:var(--mono);font-size:24px;font-variant-numeric:tabular-nums;
         font-weight:600;display:block}
.tile .l{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)}
.tile.a .n{color:var(--ok)} .tile.b .n{color:var(--warn)} .tile.x .n{color:var(--stop)}
.controls{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:22px;align-items:center}
.chip{font:inherit;font-size:13px;background:var(--panel);color:var(--ink-2);
      border:1px solid var(--edge);border-radius:99px;padding:5px 13px;cursor:pointer}
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
.chip:focus-visible,button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
section h2{font-family:var(--serif);font-size:21px;margin:34px 0 4px;font-weight:600}
section .note{color:var(--ink-2);font-size:13.5px;margin:0 0 14px;max-width:70ch}
.card{background:var(--panel);border:1px solid var(--edge);border-left:3px solid var(--ink-3);
      border-radius:var(--radius);padding:14px 16px;margin-bottom:10px}
.card.q-conflict{border-left-color:var(--stop)}
.card.q-collision{border-left-color:var(--warn)}
.card.q-nho{border-left-color:var(--accent)}
.card.q-tierb{border-left-color:var(--ink-3)}
.card.q-quarantine{border-left-color:var(--warn)}
.card.ruled{border-left-color:var(--ok);opacity:.62}
.card.settling{transition:opacity .2s ease,transform .2s ease;opacity:0;
     transform:translateX(14px)}
.cleared-note{color:var(--ok);font-size:13.5px;font-weight:600;
     border:1px dashed var(--ok);border-radius:var(--radius);padding:10px 13px;margin:0}
.chip.toggle[aria-pressed="true"]{background:var(--ok);border-color:var(--ok)}
.loadmore{font:inherit;font-size:13px;padding:8px 15px;margin:4px 0 8px;
     border:1px dashed var(--edge);border-radius:var(--radius);
     background:transparent;color:var(--ink-2);cursor:pointer;width:100%}
.loadmore:hover{border-color:var(--accent);color:var(--accent)}
/* [hidden] must beat the display rule below, or the panel can never close. */
.exportpanel[hidden]{display:none}
.card[hidden]{display:none}
.exportpanel{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);
  width:min(760px,92vw);background:var(--panel);border:1px solid var(--edge);
  border-radius:var(--radius);box-shadow:0 18px 50px rgba(0,0,0,.32);
  padding:16px 18px;z-index:50;display:flex;flex-direction:column;gap:9px}
.ephead{display:flex;justify-content:space-between;align-items:center}
.epclose{font:inherit;font-size:13px;background:transparent;border:1px solid var(--edge);
  border-radius:var(--radius);padding:4px 11px;color:var(--ink-2);cursor:pointer}
.epstatus{margin:0;font-size:13px;color:var(--ink-2)}
#csvout{width:100%;font-family:var(--mono);font-size:12px;line-height:1.5;
  border:1px solid var(--edge);border-radius:var(--radius);padding:9px;
  background:var(--ground);color:var(--ink);resize:vertical}
.epacts{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
#copycsv{font:inherit;font-size:13.5px;font-weight:600;padding:7px 15px;
  border-radius:var(--radius);border:1px solid var(--accent);background:var(--accent);
  color:#fff;cursor:pointer}
.ephint{font-size:12px;color:var(--ink-3)}
.chead{display:flex;justify-content:space-between;gap:14px;align-items:baseline;flex-wrap:wrap}
.ctitle{font-weight:600;font-size:15.5px}
.cval{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:13px;
      color:var(--ink-2);white-space:nowrap}
.cid{font-family:var(--mono);font-size:11.5px;color:var(--ink-3);margin:2px 0 9px}
.notelab{font-size:11px;color:var(--ink-3);margin-bottom:3px}
.conf{display:inline-block;font-size:11px;padding:2px 8px;border-radius:99px;margin:4px 0}
.conf-hi{background:#E6F4EA;color:#1E6B37}
.conf-mid{background:#FFF4E5;color:#8A5A00}
.conf-lo{background:#FDECEC;color:#A02222}
.srcline{font-size:12px;color:var(--ink-2);margin:4px 0 2px}
.disc{color:var(--ink-3);font-style:italic}
.cagelink{color:var(--accent);text-decoration:none;border-bottom:1px solid transparent}
.cagelink:hover{border-bottom-color:var(--accent)}
.facts{display:grid;grid-template-columns:auto 1fr;gap:2px 14px;font-size:13.5px;margin-bottom:9px}
.facts dt{color:var(--ink-3);white-space:nowrap}
.facts dd{margin:0;overflow-wrap:anywhere}
.why{font-size:12.5px;color:var(--ink-3);border-top:1px dotted var(--edge);
     padding-top:8px;margin-bottom:10px}
.q{font-size:13.5px;font-weight:600;margin-bottom:7px}
.acts{display:flex;flex-wrap:wrap;gap:6px}
.act{font:inherit;font-size:13px;padding:5px 12px;border-radius:var(--radius);
     border:1px solid var(--edge);background:transparent;color:var(--ink);cursor:pointer}
.act:hover{border-color:var(--accent)}
.act[aria-pressed="true"]{background:var(--ok-soft);border-color:var(--ok);
     color:var(--ok);font-weight:600}
.act.no[aria-pressed="true"]{background:var(--stop-soft);border-color:var(--stop);color:var(--stop)}
.act.skip[aria-pressed="true"]{background:var(--warn-soft);border-color:var(--warn);color:var(--warn)}
.freeform{font:inherit;font-size:13px;padding:5px 9px;border:1px solid var(--edge);
     border-radius:var(--radius);background:var(--ground);color:var(--ink);min-width:230px}
.notewrap{margin-top:8px}
.notefield{width:100%;font:inherit;font-size:12.5px;line-height:1.45;padding:6px 9px;
     border:1px dashed var(--edge);border-radius:var(--radius);
     background:var(--ground);color:var(--ink);resize:vertical}
.notefield:focus{border-style:solid;border-color:var(--accent);outline:none}
.notefield:not(:placeholder-shown){border-style:solid;border-color:var(--accent-soft)}
.bar{position:fixed;left:0;right:0;bottom:0;background:var(--panel);
     border-top:1px solid var(--edge);padding:11px 20px;display:flex;
     justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}
.bar .count{font-family:var(--mono);font-size:13px;font-variant-numeric:tabular-nums}
.savedwrap{flex:1;min-width:0}
#saved{font-family:var(--mono);font-size:11.5px;color:var(--ink-3);
       transition:color .2s ease}
#saved.on{color:var(--ok);font-weight:600}
.bar button{font:inherit;font-size:13.5px;font-weight:600;padding:8px 17px;
     border-radius:var(--radius);border:1px solid var(--accent);
     background:var(--accent);color:#fff;cursor:pointer}
.bar button.ghost{background:transparent;color:var(--accent)}
.bar button.ghost.danger{background:var(--stop-soft);border-color:var(--stop);color:var(--stop)}
.empty{color:var(--ink-3);font-size:14px;padding:14px 0}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>

<div class="wrap">
<header>
  <div class="eyebrow">Cedar Press · Entity Spine · build __BUILD__</div>
  <p class="freshness" id="freshness"></p>
  <h1>Attribution review</h1>
  <p class="sub">Every link below is one an automated method proposed and no human
  has confirmed. Nothing here publishes until you rule on it. Rule, export, and the
  decisions import back as permanent per-entity jurisprudence.</p>
</header>

<div class="tiles" id="tiles"></div>

<div class="controls" id="filters"></div>
<div id="queues"></div>
</div>

<div class="exportpanel" id="exportpanel" hidden>
  <div class="ephead">
    <strong>Rulings</strong>
    <button type="button" id="closeexport" class="epclose">Close</button>
  </div>
  <p class="epstatus" id="exportstatus"></p>
  <textarea id="csvout" readonly rows="10" spellcheck="false"></textarea>
  <div class="epacts">
    <button type="button" id="copycsv">Copy to clipboard</button>
    <span class="ephint">Claude can also read these straight out of this page — just ask.</span>
  </div>
</div>

<div class="bar">
  <span class="count" id="progress">0 ruled</span>
  <span class="savedwrap"><span id="saved"></span></span>
  <span style="display:flex;gap:8px">
    <button class="ghost" id="clear" type="button">Clear rulings</button>
    <button id="export" type="button">Export rulings CSV</button>
  </span>
</div>

<script>
const ITEMS = __DATA__;
const STATS = __STATS__;

// Rulings persist to localStorage on every click. A ruling Elijah made is work
// product, and losing it to a page reload is unacceptable.
const STORE_KEY = "cedar_rulings_v1";
const NOTE_KEY  = "cedar_notes_v1";
let rulings = {};
let notes = {};
try { rulings = JSON.parse(localStorage.getItem(STORE_KEY) || "{}"); }
catch(e) { rulings = {}; }
try { notes = JSON.parse(localStorage.getItem(NOTE_KEY) || "{}"); }
catch(e) { notes = {}; }

function save(){
  try {
    localStorage.setItem(NOTE_KEY, JSON.stringify(notes));
    localStorage.setItem(STORE_KEY, JSON.stringify(rulings));
    localStorage.setItem(STORE_KEY+"_at", new Date().toISOString());
    flashSaved();
  } catch(e) {
    const s=document.getElementById("saved");
    if(s) s.textContent = "could not save to this browser";
  }
}
let flashTimer=null;
function flashSaved(){
  const s=document.getElementById("saved"); if(!s) return;
  s.textContent="saved";
  s.classList.add("on");
  clearTimeout(flashTimer);
  flashTimer=setTimeout(()=>s.classList.remove("on"),1400);
}

const QUEUES = [
  {key:"conflict",  title:"Authority conflicts",
   note:"Your hand-checked work disagrees with an automated match. Every one of these so far has been a shared-name-token trap, and the hand-checked answer won."},
  {key:"collision", title:"Exclusion scope checks",
   note:"Something is attributed that one of your 123 exclusion rulings also names. Condition-1 drops mean \u201cnot this lower-48 tribe\u201d, so they may not disprove an ANC parent."},
  {key:"nho",       title:"NHO parent unknown",
   note:"SBA has already verified these firms as NHO-owned through 8(a). Only the parent organization is missing \u2014 one lookup each."},
  {key:"deals_party", title:"Deal parties — no entity ID on the schema",
   note:"Highest leverage in the project. The deals ledger carries no identifier column, so all 247 deal rows failed to join in Dataset 5 and the dated ownership-event ledger sits outside the entity-year panel. Ruling a party links every deal it appears in."},
  {key:"np_placename", title:"Tier-A nonprofits — place name or Native?",
   note:"These count toward the publishable nonprofit revenue total right now. Umatilla Electric Cooperative and Yavapai Community Hospital are in this class — named for places, not necessarily Native-controlled."},
  {key:"np_recheck", title:"Nonprofits possibly excluded in error",
   note:"Dropped by an automated regex filter rather than a hand ruling. Tribe names and place names collide constantly, so some of these are almost certainly real tribal institutions."},
  {key:"quarantine", title:"Owner unknown — guess withheld",
   note:"These came from a roster that is right 14.6% of the time (13 upheld, 9 rejected, 67 redirected across your 89 rulings), so its guess is hidden rather than shown — naming a wrong tribe anchors you toward it. Name the owner if you know it; a bare 'No' only rules out something you were never shown."},
  {key:"tierb",     title:"Highest-value unreviewed attributions",
   note:"Algorithmic guesses ranked by dollars at stake."},
];

function el(t, cls, txt){const e=document.createElement(t); if(cls)e.className=cls;
  if(txt!==undefined)e.textContent=txt; return e;}

function renderTiles(){
  const t=document.getElementById("tiles");
  [["spine","Spine entities",STATS.spine,""],
   ["a","Publishable",STATS.tierA,"a"],
   ["b","Need a ruling",STATS.tierB,"b"],
   ["x","Excluded",STATS.tierX,"x"],
   ["e","Your rulings on file",STATS.exclusions,""]].forEach(([k,label,n,cls])=>{
    const d=el("div","tile "+cls);
    d.appendChild(el("span","n",n.toLocaleString()));
    d.appendChild(el("span","l",label));
    t.appendChild(d);
  });
}

function renderFilters(){
  const f=document.getElementById("filters");
  const all=el("button","chip","All"); all.type="button";
  all.setAttribute("aria-pressed","true"); all.dataset.q="all";
  all.dataset.title="All"; f.appendChild(all);
  QUEUES.forEach(q=>{
    const n=ITEMS.filter(i=>i.queue===q.key).length;
    if(!n) return;
    const b=el("button","chip",`${q.title} (${n})`); b.type="button";
    b.setAttribute("aria-pressed","false"); b.dataset.q=q.key;
    b.dataset.title=q.title; f.appendChild(b);
  });

  const spacer=el("span"); spacer.style.flex="1"; f.appendChild(spacer);
  const rb=el("button","chip toggle","Show ruled"); rb.type="button";
  rb.setAttribute("aria-pressed","false"); rb.dataset.q="__ruled";
  f.appendChild(rb);

  f.addEventListener("click",e=>{
    const b=e.target.closest(".chip"); if(!b) return;
    if(b.dataset.q==="__ruled"){
      showRuled = b.getAttribute("aria-pressed")!=="true";
      b.setAttribute("aria-pressed", showRuled?"true":"false");
      b.textContent = showRuled ? "Hide ruled" : "Show ruled";
      applyAll();
      return;
    }
    [...f.querySelectorAll(".chip:not(.toggle)")].forEach(c=>
      c.setAttribute("aria-pressed", c===b?"true":"false"));
    const q=b.dataset.q;
    document.querySelectorAll("section[data-q]").forEach(s=>{
      s.hidden = !(q==="all" || s.dataset.q===q);
    });
  });
}

function card(item, idx){
  const c=el("div","card q-"+item.queue);
  c.dataset.idx=idx;
  const head=el("div","chead");
  head.appendChild(el("div","ctitle",item.title));
  if(item.value) head.appendChild(el("div","cval",item.value));
  c.appendChild(head);
  const idline=el("div","cid");
  idline.appendChild(document.createTextNode(item.identifier+"  "));
  if(item.cageUrl){
    const a=document.createElement("a");
    a.href=item.cageUrl; a.target="_blank"; a.rel="noopener";
    a.className="cagelink"; a.textContent="check on cage.dla.mil ↗";
    idline.appendChild(a);
  }
  c.appendChild(idline);

  /* How much the proposal on this card is actually worth, measured against
     Elijah's own rulings on the same method. Shown so attention goes where the
     machine is weakest instead of every card being read equally. */
  if(item.confidence !== undefined && item.confidence !== null){
    const cf=el("div","conf");
    const pct=Math.round(item.confidence*100);
    cf.textContent="matcher confidence "+pct+"%"+(item.confidenceNote?" · "+item.confidenceNote:"");
    cf.classList.add(pct>=80?"conf-hi":(pct>=40?"conf-mid":"conf-lo"));
    c.appendChild(cf);
  }

  /* Sources, clickable. Elijah: "make sure for these that the source is
     included so it can be clicked on". A deal party is far faster to identify
     from the article the deal came from than from the name alone. */
  if(item.sources && item.sources.length){
    const sl=el("div","srcline");
    sl.appendChild(document.createTextNode("source: "));
    item.sources.forEach(function(sv,i){
      if(i) sl.appendChild(document.createTextNode(" · "));
      if(/^https?:/.test(sv.url)){
        const a=document.createElement("a");
        a.href=sv.url; a.target="_blank"; a.rel="noopener";
        a.className="cagelink"; a.textContent=sv.label+" ↗";
        sl.appendChild(a);
      } else {
        sl.appendChild(document.createTextNode(sv.label));
      }
    });
    if(item.discovery){
      const d=el("span","disc");
      d.textContent="  found via "+item.discovery;
      sl.appendChild(d);
    }
    c.appendChild(sl);
  }

  if(item.facts && item.facts.length){
    const dl=el("dl","facts");
    item.facts.forEach(([k,v])=>{ if(!v) return;
      dl.appendChild(el("dt",null,k)); dl.appendChild(el("dd",null,v)); });
    c.appendChild(dl);
  }
  if(item.why) c.appendChild(el("div","why",item.why));
  c.appendChild(el("div","q",item.question));

  const acts=el("div","acts");
  const existing = rulings[item.id];

  const mk=(label,val,cls)=>{
    const b=el("button","act "+(cls||""),label); b.type="button";
    b.setAttribute("aria-pressed", existing===val ? "true":"false");
    b.dataset.val=val;
    b.addEventListener("click",()=>{
      const on=b.getAttribute("aria-pressed")==="true";
      [...acts.querySelectorAll(".act")].forEach(x=>x.setAttribute("aria-pressed","false"));
      const free=acts.querySelector(".freeform");
      if(on){ delete rulings[item.id]; c.classList.remove("ruled"); }
      else {
        b.setAttribute("aria-pressed","true");
        rulings[item.id]=val;
        c.classList.add("ruled");
        if(free) free.value="";
      }
      save(); settle(c); updateProgress();
    });
    return b;
  };
  (item.options||[]).forEach((o,i)=> acts.appendChild(mk(o,o, i>0?"no":"")));

  const free=el("input","freeform"); free.type="text";
  free.placeholder = item.queue==="nho" ? "Parent NHO name\u2026" : "Other ruling\u2026";
  // Restore a free-text ruling: one that matches no preset button.
  const presets=(item.options||[]).concat(["UNSURE"]);
  if(existing && presets.indexOf(existing)===-1) free.value=existing;
  free.addEventListener("input",()=>{
    const v=free.value.trim();
    [...acts.querySelectorAll(".act")].forEach(x=>x.setAttribute("aria-pressed","false"));
    if(v){ rulings[item.id]=v; c.classList.add("ruled"); }
    else { delete rulings[item.id]; c.classList.remove("ruled"); }
    save(); updateProgress();
  });
  // Free text settles on blur, not per keystroke, so typing is not interrupted.
  free.addEventListener("blur",()=>{ if(free.value.trim()) settle(c); });
  acts.appendChild(free);
  acts.appendChild(mk("Unsure \u2014 needs research","UNSURE","skip"));
  c.appendChild(acts);

  // Notes ride alongside the ruling, not inside it. A ruling is the decision;
  // a note is the evidence, caveat, or URL that justifies it - and it must
  // survive into the export so the reasoning is never lost.
  const noteWrap=el("div","notewrap");
  const nlab=el("div","notelab");
  nlab.textContent="Your note — state the RULE, not just the answer; it teaches the matcher";
  noteWrap.appendChild(nlab);
  const note=el("textarea","notefield");
  note.rows=2;
  note.placeholder="Notes \u2014 evidence, source URL, caveats, why\u2026";
  note.value = notes[item.id] || "";
  note.addEventListener("input",()=>{
    const v=note.value.trim();
    if(v) notes[item.id]=v; else delete notes[item.id];
    save(); updateProgress();
  });
  noteWrap.appendChild(note);
  c.appendChild(noteWrap);

  if(existing) c.classList.add("ruled");
  return c;
}

function renderQueues(){
  const root=document.getElementById("queues");
  QUEUES.forEach(q=>{
    const rows=ITEMS.map((it,i)=>[it,i]).filter(([it])=>it.queue===q.key);
    if(!rows.length) return;
    const s=el("section"); s.dataset.q=q.key;
    const h=el("h2",null,`${q.title} — ${rows.length}`);
    h.dataset.title=q.title;
    s.appendChild(h);
    s.appendChild(el("p","note",q.note));

    // Render in batches. With a deep reserve the queue never runs dry, but
    // rendering 1,500 cards up front would make the page crawl.
    const holder=el("div","cards"); s.appendChild(holder);
    let drawn=0;
    const more=el("button","loadmore",""); more.type="button";
    const draw=()=>{
      const next=rows.slice(drawn, drawn+STATS.batch);
      next.forEach(([it,i])=> holder.appendChild(card(it,i)));
      drawn+=next.length;
      const left=rows.length-drawn;
      more.textContent = left>0 ? `Load ${Math.min(STATS.batch,left)} more (${left} remaining)` : "";
      more.hidden = left<=0;
      applyAll();
    };
    more.addEventListener("click",draw);
    draw();
    s.appendChild(more);

    const cleared=el("p","cleared-note","Queue cleared. Every item here has a ruling.");
    cleared.hidden=true;
    s.appendChild(cleared);
    root.appendChild(s);
  });
  if(!ITEMS.length) root.appendChild(el("p","empty","No items awaiting review."));
}

// A ruled item leaves the queue. It is not deleted - "Show ruled" brings it
// back so a decision can be revisited - but the open queue only ever shows
// what still needs Elijah.
let showRuled = false;

function settle(card){
  const ruled = card.classList.contains("ruled");
  if(ruled && !showRuled){
    card.classList.add("settling");
    const done=()=>{ card.hidden=true; card.classList.remove("settling"); recount(); };
    if(window.matchMedia("(prefers-reduced-motion: reduce)").matches){ done(); }
    else { setTimeout(done, 220); }
  } else {
    card.hidden=false; recount();
  }
}

function applyAll(){
  document.querySelectorAll(".card").forEach(c=>{
    c.hidden = c.classList.contains("ruled") && !showRuled;
  });
  recount();
}

function recount(){
  document.querySelectorAll("section[data-q]").forEach(s=>{
    const open=[...s.querySelectorAll(".card")].filter(c=>!c.hidden).length;
    const more=s.querySelector(".loadmore");
    const undrawn = more && !more.hidden;   // reserve still waiting to render
    const h=s.querySelector("h2");
    if(h) h.textContent = `${h.dataset.title} — ${open}` + (undrawn ? "+" : "");
    // Only truly cleared when nothing is open AND nothing is left to load.
    const done=s.querySelector(".cleared-note");
    if(done) done.hidden = !(open===0 && !undrawn);
    s.classList.toggle("cleared", open===0 && !undrawn);
  });
  document.querySelectorAll("#filters .chip[data-q]").forEach(b=>{
    const q=b.dataset.q; if(q==="all"||q==="__ruled") return;
    const s=document.querySelector(`section[data-q="${q}"]`); if(!s) return;
    const open=[...s.querySelectorAll(".card")].filter(c=>!c.hidden).length;
    b.textContent = `${b.dataset.title} (${open})`;
  });
}

// Rulings are only safe once exported: a fresh build lands on a NEW URL, and
// localStorage does not travel between origins. So the page states plainly how
// much unexported work is at risk.
let exportedCount = 0;

function updateProgress(){
  const n=Object.keys(rulings).length;
  document.getElementById("progress").textContent =
    `${n} ruled of ${ITEMS.length} shown  ·  ${STATS.tierB.toLocaleString()} in tier B total`;
  const ex=document.getElementById("export");
  if(ex) ex.textContent = n ? `Export ${n} rulings` : "Export rulings CSV";

  const fresh=document.getElementById("freshness");
  if(fresh){
    const unexported = n - exportedCount;
    if(unexported > 0){
      fresh.textContent = `${unexported} ruling${unexported===1?"":"s"} not yet exported. `
        + `Export before asking for a new link — a new link starts with an empty slate.`;
      fresh.className = "freshness freshness--warn";
    } else if(n > 0){
      fresh.textContent = `All ${n} rulings exported. Safe to request a fresh link.`;
      fresh.className = "freshness freshness--ok";
    } else {
      fresh.textContent = "";
      fresh.className = "freshness";
    }
  }
}

// Warn on leaving with unexported work. Browsers show their own generic text.
window.addEventListener("beforeunload", (e) => {
  if(Object.keys(rulings).length > exportedCount){
    e.preventDefault();
    e.returnValue = "";
  }
});

// Restored-session notice, so it is obvious the work survived a reload.
(function(){
  const n=Object.keys(rulings).length;
  if(!n) return;
  const at=localStorage.getItem(STORE_KEY+"_at");
  const s=document.getElementById("saved");
  if(s) s.textContent = `${n} rulings restored` + (at ? ` · ${at.slice(0,16).replace("T"," ")}` : "");
})();

// Export must never fail. Artifacts render in a sandboxed iframe where
// programmatic downloads are commonly blocked, so the CSV is shown on the page
// as selectable text. Download and clipboard are attempted as conveniences;
// the visible textarea is the guarantee.
// Export walks the RULINGS, not the rendered items. If a later build drops an
// item Elijah already ruled on, the ruling still exports. Nothing is ever lost
// to a page rebuild.
function buildCSV(){
  const esc=v=>`"${String(v==null?"":v).replace(/"/g,'""')}"`;
  const byId={}; ITEMS.forEach(it=>{ byId[it.id]=it; });
  const lines=[["review_id","queue","uei","cage_code","entity_or_firm","question","YOUR_RULING","YOUR_NOTE"].join(",")];
  // Union of ruled and noted ids - a note without a ruling is still worth
  // keeping, and must not be silently dropped from the export.
  const ids=Object.keys(Object.assign({}, rulings, notes)).sort();
  ids.forEach(id=>{
    const r=rulings[id]||"";
    const n=notes[id]||"";
    if(!r && !n) return;
    const it=byId[id];
    const ident=id.split(":")[1]||"";
    lines.push([
      id,
      it ? it.queue : "carried_over",
      ident,
      it ? (it.cage||"") : "",
      it ? it.title : "",
      it ? it.question : "",
      r, n
    ].map(esc).join(","));
  });
  return lines;
}

function showExport(){
  const lines=buildCSV();
  const n=lines.length-1;
  const panel=document.getElementById("exportpanel");
  const ta=document.getElementById("csvout");
  const status=document.getElementById("exportstatus");

  if(!n){
    status.textContent="No rulings recorded yet.";
    panel.hidden=false; ta.value=""; return;
  }
  const csv=lines.join("\n");
  ta.value=csv;
  panel.hidden=false;
  status.textContent=`${n} ruling${n===1?"":"s"}. Select all below and copy, or use the buttons.`;
  ta.focus(); ta.select();
  exportedCount = n;
  updateProgress();

  // Best-effort download; silently ignored if the sandbox blocks it.
  try{
    const blob=new Blob([csv],{type:"text/csv;charset=utf-8"});
    const url=URL.createObjectURL(blob);
    const a=document.createElement("a");
    a.href=url; a.download="cedar_rulings___DATE__.csv";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(()=>URL.revokeObjectURL(url), 4000);
  }catch(e){ /* textarea is the fallback */ }
}

document.getElementById("export").addEventListener("click", showExport);

document.getElementById("copycsv").addEventListener("click",()=>{
  const ta=document.getElementById("csvout");
  const status=document.getElementById("exportstatus");
  ta.focus(); ta.select();
  let ok=false;
  try{ ok=document.execCommand("copy"); }catch(e){ ok=false; }
  if(ok){ status.textContent="Copied. Paste into a file in Cedar Press/review/."; return; }
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(ta.value).then(
      ()=>{ status.textContent="Copied. Paste into a file in Cedar Press/review/."; },
      ()=>{ status.textContent="Copy blocked. The text is selected — press Ctrl+C."; });
  } else {
    status.textContent="Copy blocked. The text is selected — press Ctrl+C.";
  }
});

document.getElementById("closeexport").addEventListener("click",()=>{
  document.getElementById("exportpanel").hidden=true;
});

// Two-step confirm. Sandboxed iframes block confirm()/alert(), so a native
// dialog would silently do nothing - which is exactly the bug this replaces.
let clearArmed=false, clearTimer=null;
const clearBtn=document.getElementById("clear");
clearBtn.addEventListener("click",()=>{
  const n=Object.keys(rulings).length;
  if(!n){
    clearBtn.textContent="Nothing to clear";
    setTimeout(()=>{clearBtn.textContent="Clear rulings";},1500);
    return;
  }
  if(!clearArmed){
    clearArmed=true;
    clearBtn.textContent=`Discard ${n}? Click again`;
    clearBtn.classList.add("danger");
    clearTimeout(clearTimer);
    clearTimer=setTimeout(()=>{
      clearArmed=false;
      clearBtn.textContent="Clear rulings";
      clearBtn.classList.remove("danger");
    },4000);
    return;
  }
  clearArmed=false;
  clearTimeout(clearTimer);
  clearBtn.textContent="Clear rulings";
  clearBtn.classList.remove("danger");
  Object.keys(rulings).forEach(k=>delete rulings[k]);
  try{ localStorage.removeItem(STORE_KEY); localStorage.removeItem(STORE_KEY+"_at"); }catch(e){}
  document.querySelectorAll(".act").forEach(b=>b.setAttribute("aria-pressed","false"));
  document.querySelectorAll(".freeform").forEach(i=>i.value="");
  document.querySelectorAll(".card").forEach(c=>{c.classList.remove("ruled");c.hidden=false;});
  save(); recount(); updateProgress();
  const s=document.getElementById("saved");
  if(s) s.textContent="all rulings cleared";
});

renderTiles(); renderFilters(); renderQueues(); applyAll(); updateProgress();
</script>
"""

if __name__ == "__main__":
    main()

