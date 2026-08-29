#!/usr/bin/env python3
r"""
169_build_identifier_graph.py — ONE canonical identifier graph, and propagation.

    Elijah, 2026-08-26: "federal spending, prime and subcontracting datasets
    have a lot of overlap since they all use the same id system — UEI and CAGE
    code. It could be possible the IRS data links to these as well, particularly
    federal spending, so we have their EIN and CAGE code, UEI."

WHAT THIS BUILDS
----------------
Nodes are IDENTIFIERS (`UEI:...`, `CAGE:...`, `EIN:...`, `DUNS:...`) and
ENTITIES (`ENTITY:TRBF-...`). Two kinds of edge:

  IDENTITY     identifier <-> identifier   "these two strings name one registrant"
  ATTRIBUTION  identifier  -> entity       "this registrant is that Native entity"

Every edge carries its evidence, its asserting source, and its tier.

THE GOVERNING RULE THIS FILE EXISTS TO OBEY
-------------------------------------------
**A tier is INHERITED from the source row, never assigned by the consumer, and
the exactness of the KEY says nothing about the correctness of the LINK.**

This project already shipped the opposite bug (AGENTS.md, "An identifier is only
as good as the row that carries it"): a pass treated any EIN hit as tier A
because an EIN is exact, and put a Wisconsin United Way onto a California tribe.
So here:

  * Where a source row HAS a tier column, that value is copied verbatim into
    `edge_tier` and `edge_tier_source` names the column it came from.
  * Where a source has NO tier column, the tier is declared ONCE in
    `SOURCE_TIER` below with a written reason, and `edge_tier_source` records
    that it is a source-level declaration rather than a row-level inheritance.
    A co-observation of two identifiers on one transaction is evidence that a
    filer typed both; it is not a ruling, so it is never higher than B.
  * **A propagated link can never be stronger than the weakest edge in its
    path.** `derived_tier = min(tier of every edge traversed)`. The full path is
    carried on the row in `path` and its weakest link named in
    `weakest_edge_source`.
  * A tier-C attribution is the string "unattributed". It propagates NOTHING.
  * A tier-X row is a negative ruling and BLOCKS the node. It never resurfaces
    and it is never overridden by a lower-tier positive edge.

ONE-TO-MANY IS A DEFECT; MANY-TO-ONE IS NOT
-------------------------------------------
One entity legitimately holds many identifiers — the 8(a) nine-year term drives
tribes and ANCs to spin up successor firms sharing a name and an address, and
267 name-clusters covering 623 unattributed UEIs and $14.98B already show it.
So MANY identifiers -> ONE entity is expected and is never flagged.

The reverse is a defect. Where one identifier, or one propagation path, reaches
TWO OR MORE distinct entities, this script makes NO assignment, writes the row
to `review/`, and says which sources disagree. Picking the higher tier would be
the consumer assigning a tier by another name.

NOT USED AS A DISCRIMINATOR
---------------------------
SAM socio-economic flags. `americanIndianOwned = YES` appears on 2,846 of 8,273
rows of the TRIBAL extract — a self-certification that does not separate classes.

SAFETY
------
Reads everything, rewrites nothing. Other agents are live on prime_contracts,
the spine and the nonprofit tables. New outputs only:

    data/clean/cedar_identifier_graph_edges.csv
    data/clean/cedar_identifier_graph_nodes.csv
    data/clean/cedar_identifier_propagation.csv
    review/identifier_one_to_many_defects_<date>.csv
    docs/IDENTIFIER_GRAPH_BUILD_LOG.md

Zero network calls.
"""

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cedar_domain import (Tier, IdentifierType, RULED_METHODS,  # noqa: E402
                          ALGORITHMIC_METHODS, METHOD_ACCURACY, is_ruling,
                          NP_CLASSIFICATION_POSITIVE, np_ruling_is_native,
                          np_ruling_is_unrecognised)
from pathlib import Path

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

CEDAR = str(Path(__file__).resolve().parent.parent)
CLEAN = os.path.join(CEDAR, "data", "clean")
REVIEW = os.path.join(CEDAR, "review")
DOCS = os.path.join(CEDAR, "docs")
TODAY = date.today().isoformat()

# ---------------------------------------------------------------------------
# TIER ARITHMETIC
# ---------------------------------------------------------------------------
RANK = {"A": 3, "B": 2, "C": 1, "X": 0}


def weakest(tiers):
    """A path is as strong as its weakest edge. Nothing else is defensible."""
    ts = [t for t in tiers if t in RANK]
    if not ts:
        return "C"
    return min(ts, key=lambda t: RANK[t])


def norm_tier(v):
    v = (v or "").strip().upper()
    return v if v in RANK else ""


# ---------------------------------------------------------------------------
# SOURCE-LEVEL TIER DECLARATIONS — for sources with NO tier column.
# Each one is a written judgement about what the SOURCE asserts, made once,
# here, where it can be argued with. None of them is above B, because none of
# them is a ruling.
# ---------------------------------------------------------------------------
SOURCE_TIER = {
    "fpds_uei_cage_map.csv": (
        "B", "FPDS reported this CAGE and this UEI on the same transaction. "
        "That is a filer's co-declaration of two identifiers for one "
        "registration — strong evidence of identity, but an observation, not a "
        "ruling, and FPDS is known not to update retroactively."),
    "cedar_cage_backfill.csv": (
        "B", "Derived from fpds_uei_cage_map.csv; inherits that source's "
        "standing, never more."),
    "prime_contracts.csv/co-observation": (
        "B", "UEI and CAGE on one prime transaction row. Co-declaration, not a "
        "ruling."),
    "subawards.csv/co-observation": (
        "B", "UEI and CAGE on one FSRS subaward row. Co-declaration, not a "
        "ruling."),
    "federal_funding_transactions.csv/co-observation": (
        "B", "UEI and DUNS on one assistance transaction, spanning the April "
        "2022 DUNS->UEI transition. Co-declaration, not a ruling."),
    "need_v6_geocoded.csv": (
        "B", "One row of the need_v6 enterprise table asserts that a UEI, a "
        "CAGE and an EIN belong to one enterprise. `need_v6` is measured at "
        "6.5% accurate against rulings (cedar_domain.METHOD_ACCURACY) and "
        "NEVER publishes alone, so the identity it asserts is tier B at best "
        "and caps every path that runs through it."),
    "funding_identifier_harvest.csv": (
        "B", "UEI and DUNS aggregated from the same assistance recipient. "
        "Co-declaration, not a ruling."),
    "subaward_identifier_harvest.csv": (
        "B", "UEI, CAGE and DUNS aggregated from the same FSRS subaward "
        "party. Co-declaration, not a ruling."),
    "assistance_tribe_id_crosswalk.csv": (
        "B", "Maps the do-file's legacy integer tribe id onto a Cedar spine "
        "id. The file states its own tier as B on every row ('a resolver match "
        "is tier B'); this is the vocabulary hop, not a re-adjudication."),
}

# Identifier hygiene. A malformed key joins to noise.
UEI_OK = 12
CAGE_LEN = (5, 6)


def clean_uei(v):
    v = (v or "").strip().upper()
    return v if len(v) == UEI_OK and v.isalnum() else ""


def clean_cage(v):
    v = (v or "").strip().upper()
    return v if len(v) in CAGE_LEN and v.isalnum() else ""


def clean_ein(v):
    d = "".join(c for c in str(v or "") if c.isdigit())
    return d.zfill(9) if 5 <= len(d) <= 9 else ""


def clean_duns(v):
    d = "".join(c for c in str(v or "") if c.isdigit())
    return d.zfill(9) if 7 <= len(d) <= 9 else ""


CLEANER = {"UEI": clean_uei, "CAGE": clean_cage, "EIN": clean_ein,
           "DUNS": clean_duns}


def node(kind, value):
    return f"{kind}:{value}"


def f2(x):
    try:
        return float(str(x).replace(",", "").strip() or 0)
    except Exception:
        return 0.0


def rd(path, **kw):
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as fh:
        for r in csv.DictReader(fh):
            yield r


def clean(f):
    return os.path.join(CLEAN, f)


# ---------------------------------------------------------------------------
# THE GRAPH
# ---------------------------------------------------------------------------
identity = []        # dicts: a, b, tier, source, evidence, method
attribution = []     # dicts: idnode, entity, tier, source, evidence, method
blocks = []          # dicts: idnode, source, evidence  (tier X)

log = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log.append(s)


def add_identity(a, b, tier, source, evidence, method="", tier_src=""):
    if not a or not b or a == b:
        return
    identity.append({"a": a, "b": b, "edge_tier": tier, "source": source,
                     "evidence": evidence, "method": method,
                     "edge_tier_source": tier_src})


def add_attr(idnode, entity, tier, source, evidence, method="", tier_src=""):
    if not idnode or not entity:
        return
    attribution.append({"id": idnode, "entity": entity, "edge_tier": tier,
                        "source": source, "evidence": evidence,
                        "method": method, "edge_tier_source": tier_src})


say(f"=== Cedar identifier graph — built {TODAY} ===\n")

# ---------------------------------------------------------------------------
# 1. THE IDENTIFIER LEDGER — the project's own attribution record.
#    Tier and method are inherited verbatim. X rows become blocks.
# ---------------------------------------------------------------------------
n_led = Counter()
for r in rd(clean("cedar_identifier_ledger_final.csv")):
    it = (r.get("identifier_type") or "").strip().upper()
    if it not in CLEANER:
        n_led["bad_type"] += 1
        continue
    v = CLEANER[it](r.get("identifier"))
    if not v:
        n_led["malformed"] += 1
        continue
    nd = node(it, v)
    tier = norm_tier(r.get("confidence_tier"))
    tid = (r.get("tribe_id") or "").strip()
    method = (r.get("attribution_method") or "").strip()
    ev = (r.get("tier_rationale") or "")[:300]
    if tier == "X":
        blocks.append({"id": nd, "source": "cedar_identifier_ledger_final.csv",
                       "evidence": f"tier X negative ruling; method={method}; "
                                   f"{(r.get('exclusion_evidence') or '')[:200]}"})
        n_led["X"] += 1
        continue
    if not tid:
        n_led["no_tribe_id"] += 1
        continue
    add_attr(nd, node("ENTITY", tid), tier,
             "cedar_identifier_ledger_final.csv",
             f"ledger row: method={method}; {ev}", method,
             "row column `confidence_tier`")
    n_led[tier] += 1
say("[1] identifier ledger      ", dict(n_led))

# cross_dataset_ruling_map — EXCLUSION rows are blocks
n_x = Counter()
p = clean("cross_dataset_ruling_map.csv")
if os.path.exists(p):
    for r in rd(p):
        it = (r.get("identifier_type") or "").strip().upper()
        if it not in CLEANER:
            continue
        v = CLEANER[it](r.get("identifier"))
        if not v:
            continue
        if (r.get("ruling") or "").strip().upper().startswith("EXCLUSION") or \
           "BLOCKED" in (r.get("note") or "").upper() + (r.get("ruling") or "").upper():
            blocks.append({"id": node(it, v),
                           "source": "cross_dataset_ruling_map.csv",
                           "evidence": f"{r.get('ruling','')} {r.get('note','')}"[:250]})
            n_x[it] += 1
say("[1b] ruling-map exclusions ", dict(n_x))

# ---------------------------------------------------------------------------
# 2. UEI <-> CAGE — the FPDS map, the backfill, and raw co-observation.
# ---------------------------------------------------------------------------
t, why = SOURCE_TIER["fpds_uei_cage_map.csv"]
n = 0
for r in rd(clean("fpds_uei_cage_map.csv")):
    u, c = clean_uei(r.get("uei")), clean_cage(r.get("cage_code"))
    if not (u and c):
        continue
    if (r.get("cage_malformed_flag") or "").strip():
        continue
    add_identity(node("UEI", u), node("CAGE", c), t, "fpds_uei_cage_map.csv",
                 f"FPDS co-observation on {r.get('n_observations','?')} "
                 f"transactions {r.get('first_year','')}-{r.get('last_year','')}",
                 "fpds_co_observation", "SOURCE_TIER declaration: " + why[:120])
    n += 1
say(f"[2] fpds_uei_cage_map      {n:,} UEI<->CAGE edges @ tier {t}")

t, why = SOURCE_TIER["cedar_cage_backfill.csv"]
n = 0
for r in rd(clean("cedar_cage_backfill.csv")):
    u, c = clean_uei(r.get("uei")), clean_cage(r.get("cage_code"))
    if u and c:
        add_identity(node("UEI", u), node("CAGE", c), t,
                     "cedar_cage_backfill.csv", (r.get("basis") or "")[:200],
                     "cage_backfill", "SOURCE_TIER declaration: " + why[:120])
        n += 1
say(f"[2b] cedar_cage_backfill   {n:,} UEI<->CAGE edges @ tier {t}")

# --- need_v6 enterprise table: the ONLY file that could put a UEI, a CAGE and
# --- an EIN on one row. Measured: it never does put a UEI and an EIN on one
# --- row (see the build log). Identity edges only — its tribe attributions are
# --- already in the ledger at their own tiers and re-adding them would double
# --- count the same assertion under a second name.
RAWEXT = os.path.join(CEDAR, "data", "raw", "external")
t, why = SOURCE_TIER["need_v6_geocoded.csv"]
n = Counter()
p = os.path.join(RAWEXT, "need_v6_geocoded.csv")
if os.path.exists(p):
    for r in rd(p):
        u = clean_uei(r.get("enterprise_uei"))
        c = clean_cage(r.get("enterprise_cage_code"))
        e = clean_ein(r.get("enterprise_ein"))
        ev = (f"need_v6 enterprise row '{(r.get('enterprise_name') or '')[:80]}'"
              f"; attribution_method={(r.get('attribution_method') or '')}")
        for x, y, lab in ((u and node("UEI", u), c and node("CAGE", c), "UEI-CAGE"),
                          (u and node("UEI", u), e and node("EIN", e), "UEI-EIN"),
                          (c and node("CAGE", c), e and node("EIN", e), "CAGE-EIN")):
            if x and y:
                add_identity(x, y, t, "need_v6_geocoded.csv", ev, "need_v6",
                             "SOURCE_TIER declaration: " + why[:150])
                n[lab] += 1
say("[2c] need_v6_geocoded      ", dict(n), f" identity edges @ tier {t}")

# --- harvest tables: UEI <-> DUNS / CAGE co-observation ------------------
for fn, cols in (("funding_identifier_harvest.csv",
                  [("recipient_uei", "UEI"), ("recipient_duns", "DUNS"),
                   ("recipient_ein", "EIN"), ("cage_code", "CAGE")]),
                 ("subaward_identifier_harvest.csv",
                  [("uei", "UEI"), ("cage_code", "CAGE"), ("duns", "DUNS")])):
    t, why = SOURCE_TIER[fn]
    n = Counter()
    p = clean(fn)
    if not os.path.exists(p):
        continue
    for r in rd(p):
        vals = [(k2, CLEANER[k2](r.get(c2))) for c2, k2 in cols]
        vals = [(k2, v) for k2, v in vals if v]
        for i in range(len(vals)):
            for j in range(i + 1, len(vals)):
                add_identity(node(*vals[i]), node(*vals[j]), t, fn,
                             f"co-observed on the same harvest row for "
                             f"'{(r.get('recipient_name') or r.get('legal_business_name') or '')[:70]}'",
                             "harvest_co_observation",
                             "SOURCE_TIER declaration: " + why[:120])
                n[f"{vals[i][0]}-{vals[j][0]}"] += 1
    say(f"[2d] {fn:<34}", dict(n))

# ---------------------------------------------------------------------------
# 3. EIN <-> UEI, and the nonprofit hub
# ---------------------------------------------------------------------------
n = Counter()
for r in rd(clean("np_ein_uei_bridge.csv")):
    e, u = clean_ein(r.get("ein")), clean_uei(r.get("uei"))
    if not (e and u):
        continue
    tier = norm_tier(r.get("confidence_tier")) or "B"
    add_identity(node("EIN", e), node("UEI", u), tier, "np_ein_uei_bridge.csv",
                 (r.get("match_evidence") or "")[:300],
                 (r.get("match_method") or ""), "row column `confidence_tier`")
    n[tier] += 1
say("[3] np_ein_uei_bridge      ", dict(n), " EIN<->UEI edges")

n = Counter()
for r in rd(clean("np_ein_entity_hub.csv")):
    e = clean_ein(r.get("ein"))
    eid = (r.get("entity_id") or "").strip()
    if not (e and eid):
        continue
    tier = norm_tier(r.get("link_tier")) or "B"
    add_attr(node("EIN", e), node("ENTITY", eid), tier, "np_ein_entity_hub.csv",
             f"{r.get('link_basis','')[:200]} [tier source: "
             f"{r.get('link_tier_source','')}]",
             (r.get("link_method") or ""), "row column `link_tier`")
    n[tier] += 1
say("[3b] np_ein_entity_hub     ", dict(n), " EIN->ENTITY edges")

# np_orgs: EIN -> entity, tier inherited from cedar_link_tier. X rows block.
n = Counter()
for r in rd(clean("np_orgs.csv")):
    e = clean_ein(r.get("EIN"))
    if not e:
        continue
    tier = norm_tier(r.get("cedar_link_tier"))
    eid = (r.get("cedar_spine_entity_id") or r.get("tribe_id") or "").strip()
    if tier == "X" or (r.get("excluded_by_prior_ruling") or "").strip() in ("1", "Y", "YES"):
        blocks.append({"id": node("EIN", e), "source": "np_orgs.csv",
                       "evidence": f"cedar_link_tier=X / excluded_by_prior_ruling; "
                                   f"{(r.get('exclusion_reason') or '')[:180]}"})
        n["X"] += 1
        continue
    if not (tier and eid):
        n["no_link"] += 1
        continue
    add_attr(node("EIN", e), node("ENTITY", eid), tier, "np_orgs.csv",
             (r.get("cedar_link_basis") or "")[:250],
             (r.get("entity_match_method") or ""), "row column `cedar_link_tier`")
    n[tier] += 1
say("[3c] np_orgs               ", dict(n), " EIN->ENTITY edges")

# ---------------------------------------------------------------------------
# 4. BIE / UIO identifier links — tribe_id carrying UEI, EIN and DUNS
# ---------------------------------------------------------------------------
n = Counter()
for r in rd(clean("bie_uio_identifier_links.csv")):
    tid = (r.get("tribe_id") or "").strip()
    tier = norm_tier(r.get("confidence_tier")) or "B"
    ev = (r.get("tier_rationale") or "")[:250]
    for col, kind in (("uei", "UEI"), ("ein", "EIN"), ("duns_internal_only", "DUNS")):
        v = CLEANER[kind](r.get(col))
        if v and tid:
            add_attr(node(kind, v), node("ENTITY", tid), tier,
                     "bie_uio_identifier_links.csv", ev,
                     (r.get("match_method") or ""), "row column `confidence_tier`")
            n[kind] += 1
say("[4] bie_uio_identifier_links", dict(n))

# ---------------------------------------------------------------------------
# 5. ASSISTANCE legacy tribe-id vocabulary hop
# ---------------------------------------------------------------------------
legacy2cedar = {}
t, why = SOURCE_TIER["assistance_tribe_id_crosswalk.csv"]
for r in rd(clean("assistance_tribe_id_crosswalk.csv")):
    lg = (r.get("legacy_tribe_id") or "").strip()
    cd = (r.get("proposed_cedar_tribe_id") or "").strip()
    if lg and cd:
        legacy2cedar[lg] = (cd, norm_tier(r.get("confidence_tier")) or t)
say(f"[5] assistance legacy->cedar crosswalk: {len(legacy2cedar):,} legacy ids")

# ---------------------------------------------------------------------------
# 6. THE TRANSACTION DATASETS — attribution edges and co-observations
# ---------------------------------------------------------------------------
DS = {}          # dataset -> uei -> stats


def ds_slot(dsname, u):
    return DS.setdefault(dsname, {}).setdefault(
        u, {"rows": 0, "usd": 0.0, "unatt_rows": 0, "unatt_usd": 0.0,
            "tiers": Counter(), "name": ""})


# --- prime ---------------------------------------------------------------
t_co, why_co = SOURCE_TIER["prime_contracts.csv/co-observation"]
n_attr = Counter()
seen_uc = set()
for r in rd(clean("prime_contracts.csv")):
    u = clean_uei(r.get("awardee_uei"))
    if not u:
        continue
    o = f2(r.get("total_obligations"))
    s = ds_slot("prime_contracts", u)
    s["rows"] += 1
    s["usd"] += o
    tier = norm_tier(r.get("confidence_tier"))
    s["tiers"][tier or "?"] += 1
    if not s["name"]:
        s["name"] = (r.get("awardee_name") or "").strip()
    attributed = str(r.get("attributed_flag") or "").strip() in ("1", "1.0")
    if not attributed:
        s["unatt_rows"] += 1
        s["unatt_usd"] += o
    c = clean_cage(r.get("cage_code"))
    if c and (u, c) not in seen_uc:
        seen_uc.add((u, c))
        add_identity(node("UEI", u), node("CAGE", c), t_co,
                     "prime_contracts.csv",
                     "UEI and CAGE reported on the same prime transaction",
                     "row_co_observation",
                     "SOURCE_TIER declaration: " + why_co[:120])
    tid = (r.get("tribe_id") or "").strip()
    if tid and tier and tier != "C":
        k = (u, tid, tier)
        if k not in n_attr:
            add_attr(node("UEI", u), node("ENTITY", tid), tier,
                     "prime_contracts.csv",
                     f"prime row attribution; method="
                     f"{(r.get('attribution_method') or '').strip()}",
                     (r.get("attribution_method") or "").strip(),
                     "row column `confidence_tier`")
        n_attr[k] = n_attr.get(k, 0) + 1
say(f"[6] prime_contracts        {len(DS['prime_contracts']):,} UEIs, "
    f"{len(set((a,b) for a,b,_ in n_attr)):,} distinct UEI->entity attributions")

# --- assistance ----------------------------------------------------------
t_co, why_co = SOURCE_TIER["federal_funding_transactions.csv/co-observation"]
n_attr_a = set()
seen_ud = set()
n_legacy_hop = Counter()
for r in rd(clean("federal_funding_transactions.csv")):
    u = clean_uei(r.get("recipient_uei"))
    o = f2(r.get("obligated_usd"))
    if u:
        s = ds_slot("federal_funding", u)
        s["rows"] += 1
        s["usd"] += o
        tier = norm_tier(r.get("confidence_tier"))
        s["tiers"][tier or "?"] += 1
        if not s["name"]:
            s["name"] = (r.get("recipient_name") or "").strip()
        if str(r.get("attributed_flag") or "").strip() not in ("1", "1.0"):
            s["unatt_rows"] += 1
            s["unatt_usd"] += o
        d = clean_duns(r.get("recipient_duns"))
        if d and (u, d) not in seen_ud:
            seen_ud.add((u, d))
            add_identity(node("UEI", u), node("DUNS", d), t_co,
                         "federal_funding_transactions.csv",
                         "UEI and DUNS reported on the same assistance "
                         "transaction", "row_co_observation",
                         "SOURCE_TIER declaration: " + why_co[:120])
        tid = (r.get("tribe_id") or "").strip()
        # POLARITY, fixed 2026-08-26 with the np_orgs ruling test above. This
        # read `tier not in ("C",)` and then handled X in an inner branch - an
        # allow-list of negatives, so ANY tier token nobody had enumerated
        # propagated a link. Today the vocabulary is exactly {A, B, C, X}, so
        # this is behaviour-identical; the difference is what happens when a
        # fifth token appears, and the answer must be "it does not propagate".
        if tid and tier in (Tier.A.value, Tier.B.value):
            # legacy integer ids need the vocabulary hop, which is its own
            # (tier B) edge and therefore caps the path.
            if tid.isdigit():
                hop = legacy2cedar.get(tid)
                n_legacy_hop["hit" if hop else "miss"] += 1
                if not hop:
                    continue
                cid, htier = hop
                et = weakest([tier, htier])
                k = (u, cid, et)
                if k not in n_attr_a:
                    n_attr_a.add(k)
                    add_attr(node("UEI", u), node("ENTITY", cid), et,
                             "federal_funding_transactions.csv",
                             f"assistance row attribution tier {tier} on "
                             f"legacy tribe_id {tid}, mapped to {cid} by "
                             f"assistance_tribe_id_crosswalk.csv (tier "
                             f"{htier}); weakest of the two = {et}",
                             (r.get("attribution_method") or "").strip(),
                             "row column `confidence_tier`, capped by the "
                             "crosswalk hop")
            else:
                k = (u, tid, tier)
                if k not in n_attr_a:
                    n_attr_a.add(k)
                    add_attr(node("UEI", u), node("ENTITY", tid), tier,
                             "federal_funding_transactions.csv",
                             "assistance row attribution; method="
                             f"{(r.get('attribution_method') or '').strip()}",
                             (r.get("attribution_method") or "").strip(),
                             "row column `confidence_tier`")
say(f"[6b] federal_funding       {len(DS['federal_funding']):,} UEIs, "
    f"{len(n_attr_a):,} distinct UEI->entity attributions; "
    f"legacy hop {dict(n_legacy_hop)}")

# --- subawards -----------------------------------------------------------
t_co, why_co = SOURCE_TIER["subawards.csv/co-observation"]
n_attr_s = set()
seen_sc = set()
for r in rd(clean("subawards.csv")):
    o = f2(r.get("subaward_amount"))
    for role, uk, ck, tk, tierk, nk in (
            ("sub", "sub_uei", "sub_cage", "sub_native_tribe_id",
             "sub_native_tier", "sub_name"),
            ("prime", "prime_uei", "prime_cage", "prime_native_tribe_id",
             "prime_native_tier", "prime_name")):
        u = clean_uei(r.get(uk))
        if not u:
            continue
        if role == "sub":
            s = ds_slot("subawards", u)
            s["rows"] += 1
            s["usd"] += o
            if not s["name"]:
                s["name"] = (r.get(nk) or "").strip()
            if not (r.get(tk) or "").strip():
                s["unatt_rows"] += 1
                s["unatt_usd"] += o
            s["tiers"][norm_tier(r.get(tierk)) or "?"] += 1
        c = clean_cage(r.get(ck))
        if c and (u, c) not in seen_sc:
            seen_sc.add((u, c))
            add_identity(node("UEI", u), node("CAGE", c), t_co, "subawards.csv",
                         "UEI and CAGE reported on the same FSRS subaward row",
                         "row_co_observation",
                         "SOURCE_TIER declaration: " + why_co[:120])
        tid = (r.get(tk) or "").strip()
        tier = norm_tier(r.get(tierk))
        if tid and tier and tier != "C":
            k = (u, tid, tier)
            if k not in n_attr_s:
                n_attr_s.add(k)
                add_attr(node("UEI", u), node("ENTITY", tid), tier,
                         "subawards.csv",
                         f"subaward {role}-side attribution", "",
                         f"row column `{tierk}`")
say(f"[6c] subawards             {len(DS.get('subawards', {})):,} UEIs, "
    f"{len(n_attr_s):,} distinct UEI->entity attributions")

# --- FAADS (DUNS only) ---------------------------------------------------
for r in rd(clean("faads_transactions_all_agencies.csv")):
    d = clean_duns(r.get("recipient_duns"))
    if not d:
        continue
    s = DS.setdefault("faads", {}).setdefault(
        d, {"rows": 0, "usd": 0.0, "unatt_rows": 0, "unatt_usd": 0.0,
            "tiers": Counter(), "name": ""})
    s["rows"] += 1
    o = f2(r.get("obligated_usd"))
    s["usd"] += o
    if not (r.get("tribe_id") or "").strip():
        s["unatt_rows"] += 1
        s["unatt_usd"] += o
    if not s["name"]:
        s["name"] = (r.get("recipient_name") or "").strip()
say(f"[6d] faads                 {len(DS.get('faads', {})):,} DUNS")

say(f"\nEDGES: identity {len(identity):,} · attribution {len(attribution):,} "
    f"· blocks {len(blocks):,}")

# ---------------------------------------------------------------------------
# 7. DEFECT DETECTION — one identifier reaching many entities
# ---------------------------------------------------------------------------
blocked = {b["id"] for b in blocks}
block_reason = {}
for b in blocks:
    block_reason.setdefault(b["id"], f"{b['source']}: {b['evidence'][:200]}")

# direct attribution conflicts
by_id = defaultdict(list)
for e in attribution:
    by_id[e["id"]].append(e)

direct_defects = []
for k, es in by_id.items():
    ents = {e["entity"] for e in es}
    if len(ents) > 1:
        direct_defects.append((k, es))
say(f"[7] identifiers carrying >1 distinct entity (DIRECT): "
    f"{len(direct_defects):,}")

# identity-edge defects: one CAGE/DUNS shared by many UEIs
adj = defaultdict(set)
edge_meta = {}
for e in identity:
    adj[e["a"]].add(e["b"])
    adj[e["b"]].add(e["a"])
    key = tuple(sorted((e["a"], e["b"])))
    prev = edge_meta.get(key)
    # keep the STRONGEST assertion of the same identity edge, and record all
    # asserting sources
    if prev is None:
        edge_meta[key] = dict(e, sources={e["source"]})
    else:
        prev["sources"].add(e["source"])
        if RANK.get(e["edge_tier"], 1) > RANK.get(prev["edge_tier"], 1):
            prev.update({k2: v2 for k2, v2 in e.items() if k2 != "sources"})

shared = []
for nd, nbrs in adj.items():
    if nd.startswith(("CAGE:", "DUNS:", "EIN:")):
        ueis = {x for x in nbrs if x.startswith("UEI:")}
        if len(ueis) > 1:
            shared.append((nd, sorted(ueis)))
say(f"[7b] non-UEI identifiers shared by >1 UEI: {len(shared):,}")

# ---------------------------------------------------------------------------
# 8. PROPAGATION — bounded BFS over identity edges, carrying the weakest tier
# ---------------------------------------------------------------------------
MAX_HOPS = 3

# THE HUB GUARD.
# A CAGE, DUNS or EIN that sits on ONE UEI is an identity. The same string
# sitting on SEVERAL UEIs is a HUB, and walking through it is how "one
# identifier -> many entities" becomes an attribution: UEI-A -> CAGE-X ->
# UEI-B -> UEI-B's tribe. That is the shape of the defect this project has
# already paid for, so a hub is REACHABLE (its own attributions are inherited
# by the UEIs that carry it — many-identifiers-to-one-entity is expected) but
# it is NEVER EXPANDED THROUGH to another UEI on the strict path.
#
# The permissive answer is still measured, marked `via_ambiguous_hub`, and sent
# to review rather than counted in the headline lift — the difference between
# the two numbers is itself the finding.
ambiguous_hub = set()


def build_hub_set():
    for nd, nbrs in adj.items():
        if nd.startswith("UEI:"):
            continue
        if len({x for x in nbrs if x.startswith("UEI:")}) > 1:
            ambiguous_hub.add(nd)


def resolve(start, allow_hub=False):
    """Return {entity: (tier, path, weakest_source, via_hub)} reachable from
    `start`, honouring blocks and the hub guard."""
    if start in blocked:
        return {}, "BLOCKED"
    found = {}

    def offer(ent, tier, path, weak_src, via_hub):
        cur = found.get(ent)
        if cur is None or RANK[tier] > RANK[cur[0]] or (
                RANK[tier] == RANK[cur[0]] and via_hub < cur[3]):
            found[ent] = (tier, path, weak_src, via_hub)

    for e in by_id.get(start, ()):
        if e["edge_tier"] in ("C", "X", ""):
            continue
        offer(e["entity"], e["edge_tier"],
              f"{start} -[{e['source']} {e['edge_tier']}]-> {e['entity']}",
              e["source"], 0)

    seen = {start}
    frontier = [(start, "A", start, 0)]     # (node, tier so far, path, via_hub)
    for _ in range(MAX_HOPS):
        nxt = []
        for nd, tr, path, vh in frontier:
            # never expand THROUGH an ambiguous hub on the strict path
            if nd != start and nd in ambiguous_hub and not allow_hub:
                continue
            for nb in adj.get(nd, ()):
                if nb in seen or nb in blocked:
                    continue
                em = edge_meta[tuple(sorted((nd, nb)))]
                ntier = weakest([tr, em["edge_tier"]])
                nvh = vh or (1 if (nd in ambiguous_hub and nd != start) else 0)
                npath = (f"{path} -[{'|'.join(sorted(em['sources']))} "
                         f"{em['edge_tier']}]-> {nb}")
                seen.add(nb)
                nxt.append((nb, ntier, npath, nvh))
                for e in by_id.get(nb, ()):
                    if e["edge_tier"] in ("C", "X", ""):
                        continue
                    dt = weakest([ntier, e["edge_tier"]])
                    weak_src = (em["source"]
                                if RANK[em["edge_tier"]] <= RANK[e["edge_tier"]]
                                else e["source"])
                    offer(e["entity"], dt,
                          f"{npath} -[{e['source']} {e['edge_tier']}]-> "
                          f"{e['entity']}", weak_src, nvh)
        frontier = nxt
        if not frontier:
            break
    return found, ""


# Which nodes do we bother resolving? Every identifier node that appears in any
# dataset, plus every node in the graph.
all_nodes = set(adj) | set(by_id)
for dsname, m in DS.items():
    kind = "DUNS" if dsname == "faads" else "UEI"
    for v in m:
        all_nodes.add(node(kind, v))

build_hub_set()
say(f"\n[8] resolving {len(all_nodes):,} identifier nodes, max {MAX_HOPS} "
    f"identity hops")
say(f"    ambiguous hubs refused as through-paths: {len(ambiguous_hub):,} "
    f"(" + ", ".join(f"{k}={sum(1 for h in ambiguous_hub if h.startswith(k+':'))}"
                     for k in ("CAGE", "DUNS", "EIN")) + ")")

resolved = {}
conflicts = []
hub_only = {}
for nd in all_nodes:
    found, flag = resolve(nd)
    if flag == "BLOCKED":
        continue
    if len(found) > 1:
        conflicts.append((nd, found))
        continue
    if found:
        ent, (tier, path, weak, vh) = next(iter(found.items()))
        resolved[nd] = {"entity": ent, "tier": tier, "path": path,
                        "weakest_edge_source": weak,
                        "hops": path.count("-[") - 1, "via_hub": vh}
        continue
    # nothing on the strict path — what would the permissive walk have found?
    f2_, fl2 = resolve(nd, allow_hub=True)
    if fl2 != "BLOCKED" and f2_:
        hub_only[nd] = f2_

say(f"    resolved to exactly one entity : {len(resolved):,}")
say(f"    ONE-TO-MANY DEFECTS (refused)   : {len(conflicts):,}")
say(f"    reachable ONLY through an ambiguous hub (refused, to review): "
    f"{len(hub_only):,}")

# ---------------------------------------------------------------------------
# 9. LIFT PER DATASET
# ---------------------------------------------------------------------------
lift_rows = []
for dsname, m in DS.items():
    kind = "DUNS" if dsname == "faads" else "UEI"
    tot_ids = len(m)
    tot_rows = sum(v["rows"] for v in m.values())
    tot_usd = sum(v["usd"] for v in m.values())
    un_ids = [k for k, v in m.items() if v["unatt_rows"] == v["rows"]]
    un_rows = sum(v["unatt_rows"] for v in m.values())
    un_usd = sum(v["unatt_usd"] for v in m.values())
    gain_ids = gain_rows = 0
    gain_usd = 0.0
    by_tier = Counter()
    gained = []
    for k in un_ids:
        r = resolved.get(node(kind, k))
        if not r:
            continue
        # a link that came only from THIS dataset's own rows is not a lift
        if r["hops"] == 0 and dsname.replace("federal_funding",
                                             "federal_funding_transactions") \
                in r["path"]:
            continue
        gain_ids += 1
        gain_rows += m[k]["unatt_rows"]
        gain_usd += m[k]["unatt_usd"]
        by_tier[r["tier"]] += 1
        gained.append((k, r))
    lift_rows.append({
        "dataset": dsname, "id_kind": kind, "ids": tot_ids, "rows": tot_rows,
        "usd": tot_usd, "unattributed_ids": len(un_ids),
        "unattributed_rows": un_rows, "unattributed_usd": un_usd,
        "propagated_ids": gain_ids, "propagated_rows": gain_rows,
        "propagated_usd": gain_usd, "by_tier": dict(by_tier),
        "gained": gained})

say("\n=== LIFT PER DATASET (propagation only, no new human ruling) ===")
say(f"{'dataset':<26}{'ids':>8}{'unatt ids':>11}{'gain ids':>10}"
    f"{'unatt $B':>11}{'gain $B':>10}  tiers")
for L in lift_rows:
    say(f"{L['dataset']:<26}{L['ids']:>8,}{L['unattributed_ids']:>11,}"
        f"{L['propagated_ids']:>10,}{L['unattributed_usd']/1e9:>11.2f}"
        f"{L['propagated_usd']/1e9:>10.2f}  {L['by_tier']}")

# ---------------------------------------------------------------------------
# 9b. THE PARENT-UEI ROUTE — measured, and deliberately NOT an identity edge.
#
# AGENTS.md: "Federal hierarchy fields are EVIDENCE, not AUTHORITY... Use
# parent_uei to GROUP candidates and to find families. Do NOT publish parent_uei
# as our statement of the hierarchy." A parent is a DIFFERENT legal person from
# its subsidiary, so a parent edge is not an identity edge and must never carry
# an attribution silently. It is measured here and written to review.
# ---------------------------------------------------------------------------
parent_of = defaultdict(set)
p = clean("fpds_uei_edges.csv")
if os.path.exists(p):
    for r in rd(p):
        c = clean_uei(r.get("child_uei"))
        pu = clean_uei(r.get("parent_uei"))
        if c and pu and not (r.get("blocklisted_parent") or "").strip():
            parent_of[c].add(pu)
parent_candidates = []
for dsname, m in DS.items():
    if dsname == "faads":
        continue
    for k, v in m.items():
        if v["unatt_rows"] != v["rows"]:
            continue
        if node("UEI", k) in resolved or node("UEI", k) in blocked:
            continue
        ents = {}
        for pu in parent_of.get(k, ()):
            r2 = resolved.get(node("UEI", pu))
            if r2:
                ents[r2["entity"]] = r2
        if len(ents) == 1:
            ent, r2 = next(iter(ents.items()))
            parent_candidates.append({
                "dataset": dsname, "identifier": k,
                "observed_name": v["name"],
                "parent_entity": ent.split(":", 1)[1],
                "parent_tier": r2["tier"],
                "usd": round(v["usd"], 2)})
say(f"\n[9b] parent-UEI route (REFUSED as an identity edge, sent to review): "
    f"{len(parent_candidates):,} identifiers, "
    f"${sum(c['usd'] for c in parent_candidates)/1e9:.3f}B")

# ---------------------------------------------------------------------------
# 10. WRITE
# ---------------------------------------------------------------------------
os.makedirs(REVIEW, exist_ok=True)


def write(path, rows, cols):
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)
    say(f"    wrote {os.path.basename(path)}  {len(rows):,} rows")


say("\n[10] writing")

# --- edges ---------------------------------------------------------------
edge_rows = []
for key, e in edge_meta.items():
    a, b = key
    edge_rows.append({
        "edge_kind": "IDENTITY",
        "from_node": a, "to_node": b,
        "from_type": a.split(":")[0], "to_type": b.split(":")[0],
        "edge_tier": e["edge_tier"],
        "edge_tier_source": e["edge_tier_source"],
        "asserting_source": "|".join(sorted(e["sources"])),
        "n_asserting_sources": len(e["sources"]),
        "method": e["method"], "evidence": e["evidence"],
        "built_by": "169_build_identifier_graph.py", "built_date": TODAY})
seen_attr = set()
for e in attribution:
    k = (e["id"], e["entity"], e["source"], e["edge_tier"])
    if k in seen_attr:
        continue
    seen_attr.add(k)
    edge_rows.append({
        "edge_kind": "ATTRIBUTION",
        "from_node": e["id"], "to_node": e["entity"],
        "from_type": e["id"].split(":")[0], "to_type": "ENTITY",
        "edge_tier": e["edge_tier"],
        "edge_tier_source": e["edge_tier_source"],
        "asserting_source": e["source"], "n_asserting_sources": 1,
        "method": e["method"], "evidence": e["evidence"],
        "built_by": "169_build_identifier_graph.py", "built_date": TODAY})
for b in blocks:
    edge_rows.append({
        "edge_kind": "BLOCK", "from_node": b["id"], "to_node": "",
        "from_type": b["id"].split(":")[0], "to_type": "",
        "edge_tier": "X", "edge_tier_source": "row column (negative ruling)",
        "asserting_source": b["source"], "n_asserting_sources": 1,
        "method": "", "evidence": b["evidence"],
        "built_by": "169_build_identifier_graph.py", "built_date": TODAY})
write(os.path.join(CLEAN, "cedar_identifier_graph_edges.csv"), edge_rows,
      ["edge_kind", "from_node", "to_node", "from_type", "to_type",
       "edge_tier", "edge_tier_source", "asserting_source",
       "n_asserting_sources", "method", "evidence", "built_by", "built_date"])

# --- nodes ---------------------------------------------------------------
node_rows = []
in_ds = defaultdict(set)
usd_of = defaultdict(float)
rows_of = defaultdict(int)
name_of = {}
for dsname, m in DS.items():
    kind = "DUNS" if dsname == "faads" else "UEI"
    for k, v in m.items():
        nd = node(kind, k)
        in_ds[nd].add(dsname)
        usd_of[nd] += v["usd"]
        rows_of[nd] += v["rows"]
        if v["name"] and nd not in name_of:
            name_of[nd] = v["name"]
for nd in sorted(all_nodes):
    r = resolved.get(nd)
    node_rows.append({
        "node": nd, "identifier_type": nd.split(":")[0],
        "identifier": nd.split(":", 1)[1],
        "observed_name": name_of.get(nd, ""),
        "datasets": "|".join(sorted(in_ds.get(nd, ()))),
        "n_datasets": len(in_ds.get(nd, ())),
        "rows_observed": rows_of.get(nd, 0),
        "usd_observed": round(usd_of.get(nd, 0.0), 2),
        "degree": len(adj.get(nd, ())),
        "blocked": "Y" if nd in blocked else "",
        "block_reason": block_reason.get(nd, ""),
        "resolved_entity": r["entity"].split(":", 1)[1] if r else "",
        "resolved_tier": r["tier"] if r else "",
        "resolution_hops": r["hops"] if r else "",
        "one_to_many_defect": "Y" if any(nd == c[0] for c in conflicts) else "",
        "built_date": TODAY})
write(os.path.join(CLEAN, "cedar_identifier_graph_nodes.csv"), node_rows,
      ["node", "identifier_type", "identifier", "observed_name", "datasets",
       "n_datasets", "rows_observed", "usd_observed", "degree", "blocked",
       "block_reason", "resolved_entity", "resolved_tier", "resolution_hops",
       "one_to_many_defect", "built_date"])

# --- propagation result --------------------------------------------------
prop_rows = []
for L in lift_rows:
    kind = L["id_kind"]
    for k, r in L["gained"]:
        prop_rows.append({
            "dataset": L["dataset"], "identifier_type": kind, "identifier": k,
            "observed_name": DS[L["dataset"]][k]["name"],
            "proposed_entity_id": r["entity"].split(":", 1)[1],
            "derived_tier": r["tier"],
            "derived_tier_rule": "weakest edge on the path; a propagated link "
                                 "is never stronger than its weakest edge",
            "weakest_edge_source": r["weakest_edge_source"],
            # cedar_domain.METHOD_ACCURACY records need_v6 at 6.5% against
            # rulings. A path that runs through it is not merely tier B, it is
            # tier B for a measured reason, and that reason belongs on the row.
            "path_through_low_accuracy_method": (
                "need_v6 (6.5% accurate against rulings)"
                if "need_v6" in r["path"] else ""),
            "identity_hops": r["hops"],
            "path": r["path"],
            "rows_unattributed_in_dataset": DS[L["dataset"]][k]["unatt_rows"],
            "usd_unattributed_in_dataset": round(
                DS[L["dataset"]][k]["unatt_usd"], 2),
            "publishable": "YES" if r["tier"] == "A" else "NO",
            "caveat": "Tier is INHERITED along the path and capped at its "
                      "weakest edge. Tier B never publishes alone. This row is "
                      "a PROPOSED link produced with no new human ruling.",
            "built_by": "169_build_identifier_graph.py", "built_date": TODAY})
write(os.path.join(CLEAN, "cedar_identifier_propagation.csv"), prop_rows,
      ["dataset", "identifier_type", "identifier", "observed_name",
       "proposed_entity_id", "derived_tier", "derived_tier_rule",
       "weakest_edge_source", "path_through_low_accuracy_method",
       "identity_hops", "path",
       "rows_unattributed_in_dataset", "usd_unattributed_in_dataset",
       "publishable", "caveat", "built_by", "built_date"])

# --- defects -------------------------------------------------------------
def classify_defect(ents):
    """A pile of 874 conflicts is not actionable; four named families are.
    Each family is a shape this project has already paid for once."""
    pre = sorted({e.split(":", 1)[1].split("-")[0] for e in ents})
    ids = [e.split(":", 1)[1] for e in ents]
    if "AKNF" in pre and ("ANVC" in pre or "ANRC" in pre):
        return ("ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION",
                "AGENTS.md, the containment defect, direction 'record subset of "
                "entity': NATIVE VILLAGE OF ELIM -> Elim Native CORPORATION. "
                "One ruling on which side an 8(a) operating company sits "
                "settles the whole family.")
    if "CNSF" in pre and "TRBF" in pre:
        return ("CONSTITUENT_BAND_VS_UMBRELLA_TRIBE",
                "cedar_domain.NEVER_OWNERSHIP: constituent_band_of does not "
                "carry dollars upward. Which of the two holds the registration "
                "is a fact about the registration, not about the hierarchy.")
    if "ITO" in pre or "SGVF" in pre:
        return ("INTERTRIBAL_ORGANISATION_VS_MEMBER_TRIBE",
                "A consortium's registration is the consortium's. Booking it to "
                "one member tribe attributes the whole membership's money to "
                "one government.")
    if len(pre) == 1 and pre[0] == "TRBF":
        return ("TWO_DIFFERENT_TRIBES_ON_ONE_IDENTIFIER",
                "A genuine disagreement about which nation owns a registrant, "
                "or a spine short-name collision (AGENTS.md: 161 entities carry "
                "a 1-2 word canonical name). Test against the RAW spine before "
                "reporting a resolver defect.")
    return ("MIXED_CLASS", "Entities of different classes: " + "|".join(ids))


def_rows = []
fam_count = Counter()
fam_usd = Counter()
for nd, found in conflicts:
    ents = sorted(found)
    fam, fam_why = classify_defect(ents)
    fam_count[fam] += 1
    fam_usd[fam] += usd_of.get(nd, 0.0)
    def_rows.append({
        "defect_family": fam, "defect_family_note": fam_why,
        "defect_type": "ONE_IDENTIFIER_MANY_ENTITIES",
        "node": nd, "identifier_type": nd.split(":")[0],
        "identifier": nd.split(":", 1)[1],
        "observed_name": name_of.get(nd, ""),
        "n_entities": len(ents),
        "entities": "|".join(e.split(":", 1)[1] for e in ents),
        "tiers": "|".join(found[e][0] for e in ents),
        "paths": " ;; ".join(found[e][1] for e in ents),
        "datasets": "|".join(sorted(in_ds.get(nd, ()))),
        "usd_observed": round(usd_of.get(nd, 0.0), 2),
        "action": "REFUSED — no attribution assigned. Needs a human ruling on "
                  "which entity this identifier belongs to, or a ruling that "
                  "the disagreeing source is wrong.",
        "built_date": TODAY})
for nd, found in hub_only.items():
    ents = sorted(found)
    def_rows.append({
        "defect_type": "REACHABLE_ONLY_THROUGH_AN_AMBIGUOUS_HUB",
        "node": nd, "identifier_type": nd.split(":")[0],
        "identifier": nd.split(":", 1)[1],
        "observed_name": name_of.get(nd, ""),
        "n_entities": len(ents),
        "entities": "|".join(e.split(":", 1)[1] for e in ents),
        "tiers": "|".join(found[e][0] for e in ents),
        "paths": " ;; ".join(found[e][1] for e in ents),
        "datasets": "|".join(sorted(in_ds.get(nd, ()))),
        "usd_observed": round(usd_of.get(nd, 0.0), 2),
        "action": "REFUSED on the strict path. The only route to an entity "
                  "runs through a CAGE/DUNS/EIN shared by several UEIs, which "
                  "is the shape of the one-identifier-many-entities defect. "
                  "Rule whether the shared identifier is a successor family "
                  "(then this is correct) or a data error (then it is not).",
        "built_date": TODAY})
for c in parent_candidates:
    def_rows.append({
        "defect_type": "PARENT_UEI_CANDIDATE_NOT_AN_IDENTITY",
        "node": node("UEI", c["identifier"]), "identifier_type": "UEI",
        "identifier": c["identifier"], "observed_name": c["observed_name"],
        "n_entities": 1, "entities": c["parent_entity"],
        "tiers": c["parent_tier"], "paths": "",
        "datasets": c["dataset"], "usd_observed": c["usd"],
        "action": "NOT PROPAGATED. FPDS names this UEI's ultimate parent, and "
                  "that parent resolves to a Native entity — but a parent is a "
                  "different legal person and FPDS hierarchy is evidence, not "
                  "authority (AGENTS.md). Needs a ruling that the subsidiary "
                  "is owned, not merely reported under, that parent.",
        "built_date": TODAY})
for nd, ueis in shared:
    if len(ueis) < 2:
        continue
    def_rows.append({
        "defect_type": "ONE_IDENTIFIER_SHARED_BY_MANY_UEIS",
        "node": nd, "identifier_type": nd.split(":")[0],
        "identifier": nd.split(":", 1)[1],
        "observed_name": name_of.get(nd, ""),
        "n_entities": len(ueis),
        "entities": "|".join(u.split(":", 1)[1] for u in ueis[:25]),
        "tiers": "", "paths": "",
        "datasets": "|".join(sorted(in_ds.get(nd, ()))),
        "usd_observed": round(usd_of.get(nd, 0.0), 2),
        "action": "A CAGE/DUNS/EIN bridging several UEIs is a hub. It is NOT "
                  "used as a propagation path in this build (see the guard); "
                  "review whether it is a legitimate successor family or a "
                  "data defect.",
        "built_date": TODAY})
say("\n[9c] one-to-many defect families")
for f_, n_ in fam_count.most_common():
    say(f"    {f_:<52}{n_:>5}   ${fam_usd[f_]/1e9:>8.3f}B observed")
write(os.path.join(REVIEW, f"identifier_one_to_many_defects_{TODAY}.csv"),
      def_rows,
      ["defect_family", "defect_type", "node", "identifier_type", "identifier",
       "observed_name", "n_entities", "entities", "tiers", "datasets",
       "usd_observed", "action", "defect_family_note", "paths", "built_date"])

# ---------------------------------------------------------------------------
# 11. THE IRS HYPOTHESIS, TESTED EXPLICITLY
#
#   "It could be possible the IRS data links to these as well, particularly
#    federal spending, so we have their EIN and CAGE code, UEI."
#
# A measured zero is a finding. A guess is not. Everything below is counted.
# ---------------------------------------------------------------------------
say("\n=== 11. THE IRS / EIN HYPOTHESIS ===")

SPEND_FILES = {
    "prime_contracts.csv": clean("prime_contracts.csv"),
    "federal_funding_transactions.csv": clean("federal_funding_transactions.csv"),
    "subawards.csv": clean("subawards.csv"),
    "faads_transactions_all_agencies.csv":
        clean("faads_transactions_all_agencies.csv"),
}
irs = {}
say("\n(a) Does any spending dataset carry an EIN COLUMN at all?")
for nm, p in SPEND_FILES.items():
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        cols = next(csv.reader(fh))
    ein_cols = [c for c in cols
                if "ein" in c.lower().replace("recipient", "").split("_")
                or c.lower().endswith("_ein") or c.lower() == "ein"]
    say(f"    {nm:<40} EIN columns: {ein_cols if ein_cols else 'NONE'}")
    irs.setdefault("ein_columns", {})[nm] = ein_cols

np_ein = set()
np_ruled_native = set()
# POLARITY, fixed 2026-08-26. This read
#
#     if classification_ruling not in ("", "UNRULED", "place_name_coincidence")
#
# - an ALLOW-LIST OF NEGATIVES. Every value the author had not thought of read
# as *ruled Native*, so the correctness of a load-bearing graph input depended
# on nobody upstream ever inventing a new way to say no. `not_a_native_entity`
# - the obvious token - would have done exactly that, which is why `code/251`
# had to reuse `place_name_coincidence` instead of writing the honest value.
# The test is now an ALLOW-LIST OF POSITIVES, declared once in
# `cedar_domain.NP_CLASSIFICATION_POSITIVE`, and an unrecognised token is
# UNKNOWN, never Native. A new negative is now silently CORRECT; a new
# POSITIVE is silently conservative AND is counted and named below, which is
# the direction this project can afford to be wrong in.
np_unrecognised_rulings = Counter()
for r in rd(clean("np_orgs.csv")):
    e = clean_ein(r.get("EIN"))
    if not e:
        continue
    np_ein.add(e)
    ruling = (r.get("classification_ruling") or "").strip()
    if np_ruling_is_native(ruling):
        np_ruled_native.add(e)
    elif np_ruling_is_unrecognised(ruling):
        np_unrecognised_rulings[ruling] += 1
si_filer, si_recip = set(), set()
for r in rd(clean("np_schedule_i_grants.csv")):
    f_ = clean_ein(r.get("filer_ein"))
    if f_:
        si_filer.add(f_)
    r_ = clean_ein(r.get("recipient_ein"))
    if r_:
        si_recip.add(r_)
led_ein = {n2.split(":", 1)[1] for n2 in all_nodes if n2.startswith("EIN:")}

spend_uei = set()
for dsname, m in DS.items():
    if dsname != "faads":
        spend_uei |= {k for k in m}

say(f"\n(b) Populations")
say(f"    np_orgs distinct EIN                     {len(np_ein):,}")
say(f"    ...with a Native classification ruling   {len(np_ruled_native):,}")
say(f"    [positive ruling allow-list: "
    f"{', '.join(sorted(NP_CLASSIFICATION_POSITIVE))}]")
if np_unrecognised_rulings:
    # NAME them. A count of "rulings I did not recognise" is not actionable;
    # the token is. A new vocabulary upstream shows up here the day it lands.
    say(f"    !! classification_ruling tokens in NONE of "
        f"cedar_domain's three declared sets - treated as UNKNOWN, i.e. NOT "
        f"Native. If one of these is a POSITIVE ruling, add it to "
        f"NP_CLASSIFICATION_POSITIVE:")
    for tok, n_tok in np_unrecognised_rulings.most_common():
        say(f"       {tok!r}  {n_tok:,} rows")
else:
    say(f"    every classification_ruling token is declared in cedar_domain "
        f"(no unrecognised vocabulary upstream)")
say(f"    Schedule I distinct filer EIN            {len(si_filer):,}")
say(f"    Schedule I distinct recipient EIN        {len(si_recip):,}")
say(f"    distinct UEIs across the 3 UEI datasets  {len(spend_uei):,}")

say(f"\n(c) EIN -> UEI, through EVERY identity edge in the graph "
    f"({MAX_HOPS} hops, hub guard on)")
reach = {}
for e in np_ein | si_filer | si_recip:
    nd = node("EIN", e)
    if nd not in adj:
        continue
    hits = set()
    seen = {nd}
    frontier = [nd]
    for _ in range(MAX_HOPS):
        nxt = []
        for x in frontier:
            if x != nd and x in ambiguous_hub:
                continue
            for y in adj.get(x, ()):
                if y in seen:
                    continue
                seen.add(y)
                nxt.append(y)
                if y.startswith("UEI:") and y.split(":", 1)[1] in spend_uei:
                    hits.add(y.split(":", 1)[1])
        frontier = nxt
    if hits:
        reach[e] = hits
say(f"    EINs with ANY identity edge in the graph : "
    f"{sum(1 for e in np_ein | si_filer | si_recip if node('EIN', e) in adj):,}")
say(f"    EINs reaching a SPENDING UEI             : {len(reach):,}")
say(f"      ...of which np_orgs EINs               : "
    f"{len(set(reach) & np_ein):,} of {len(np_ein):,}")
say(f"      ...of which Schedule I filer EINs      : "
    f"{len(set(reach) & si_filer):,} of {len(si_filer):,}")
say(f"      ...of which Schedule I recipient EINs  : "
    f"{len(set(reach) & si_recip):,} of {len(si_recip):,}")
reached_uei = set().union(*reach.values()) if reach else set()
usd_reached = 0.0
for dsname, m in DS.items():
    if dsname == "faads":
        continue
    usd_reached += sum(m[u]["usd"] for u in reached_uei if u in m)
say(f"    spending UEIs reached                    : {len(reached_uei):,}")
say(f"    dollars on those UEIs                    : ${usd_reached/1e9:.3f}B")

say(f"\n(d) The reverse direction: spending UEIs reaching an IRS EIN")
rev = {u for u in spend_uei
       if any(y.startswith("EIN:") for y in adj.get(node("UEI", u), ()))}
say(f"    spending UEIs with ANY EIN edge          : {len(rev):,} of "
    f"{len(spend_uei):,} ({len(rev)/max(len(spend_uei),1):.2%})")

say(f"\n(e) The bridges that could carry it, and how big they actually are")
say(f"    np_ein_uei_bridge.csv rows               : "
    f"{sum(1 for _ in rd(clean('np_ein_uei_bridge.csv'))):,}")
n_both = n_ein_only = 0
p = os.path.join(RAWEXT, "need_v6_geocoded.csv")
if os.path.exists(p):
    for r in rd(p):
        e = clean_ein(r.get("enterprise_ein"))
        u = clean_uei(r.get("enterprise_uei"))
        if e and u:
            n_both += 1
        elif e:
            n_ein_only += 1
say(f"    need_v6 rows with BOTH an EIN and a UEI  : {n_both:,}")
say(f"    need_v6 rows with an EIN and NO UEI      : {n_ein_only:,}")

irs.update({
    "np_orgs_eins": len(np_ein),
    "np_orgs_eins_with_native_ruling": len(np_ruled_native),
    "schedule_i_filer_eins": len(si_filer),
    "schedule_i_recipient_eins": len(si_recip),
    "spending_ueis": len(spend_uei),
    "eins_reaching_a_spending_uei": len(reach),
    "np_orgs_eins_reaching_spending": len(set(reach) & np_ein),
    "schedule_i_filer_eins_reaching_spending": len(set(reach) & si_filer),
    "schedule_i_recipient_eins_reaching_spending": len(set(reach) & si_recip),
    "spending_ueis_reached": len(reached_uei),
    "usd_on_reached_ueis": round(usd_reached, 2),
    "spending_ueis_with_any_ein_edge": len(rev),
    "need_v6_rows_with_ein_and_uei": n_both,
    "need_v6_rows_with_ein_only": n_ein_only,
})

# ---------------------------------------------------------------------------
# 12. CODEBOOK FRAGMENT — per-dataset FRAGMENT ONLY.
#
# `41_build_codebooks.py` writes codebook_master.csv in "w" mode and would now
# delete 21 of 43 blocks, so it is never run and the master is never touched
# here. This writes ONE new fragment, `05b_identifier_graph`, and appends only.
#
# ACCESS TIER: every one of these tables carries DUNS rows, and DUNS is
# D&B-licensed (cedar_domain.LICENSED_IDENTIFIER_TYPES). A published view must
# filter `identifier_type != 'DUNS'` first, so the tables themselves are
# registered INTERNAL rather than public.
# ---------------------------------------------------------------------------
FRAG = os.path.join(CLEAN, "codebook")
os.makedirs(FRAG, exist_ok=True)
CB_FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
             "published", "access_tier", "description", "generated"]
DESCR = {
    "node": "Typed identifier node, `<TYPE>:<value>`. Type lives in the string "
            "AND in `identifier_type`; never inferred elsewhere.",
    "edge_kind": "IDENTITY (two identifiers name one registrant), ATTRIBUTION "
                 "(an identifier belongs to a Native entity), or BLOCK (a tier-X "
                 "negative ruling on the identifier).",
    "from_node": "Source node of the edge.",
    "to_node": "Target node. ENTITY:<tribe_id> on an ATTRIBUTION edge; blank on "
               "a BLOCK.",
    "from_type": "UEI / CAGE / EIN / DUNS / ENTITY.",
    "to_type": "UEI / CAGE / EIN / DUNS / ENTITY.",
    "edge_tier": "A/B/C/X, INHERITED from the asserting source row. Never "
                 "assigned by this script.",
    "edge_tier_source": "Names the column the tier was inherited from, or "
                        "quotes the SOURCE_TIER declaration where the source "
                        "has no tier column.",
    "asserting_source": "The file that asserts this edge. Pipe-separated where "
                        "several sources assert the same identity edge.",
    "n_asserting_sources": "How many distinct sources assert this edge. "
                           "Corroboration is RECORDED and never promotes a tier "
                           "- two-leg promotion is a ledger method.",
    "method": "The asserting source's own match method, verbatim.",
    "evidence": "Why, in the source's words.",
    "identifier_type": "UEI / CAGE / EIN / DUNS.",
    "identifier": "The identifier value. DUNS values are D&B-licensed and never "
                  "publish.",
    "observed_name": "A name observed on the identifier in a transaction "
                     "dataset. Evidence, never a key.",
    "datasets": "Which transaction datasets the identifier appears in.",
    "n_datasets": "Count of the above.",
    "rows_observed": "Transaction rows carrying this identifier.",
    "usd_observed": "Obligated dollars on those rows.",
    "degree": "Identity-edge degree in the graph.",
    "blocked": "Y where a tier-X negative ruling bars the identifier.",
    "block_reason": "The ruling, quoted.",
    "resolved_entity": "The single entity the identifier resolves to, or blank "
                       "where it resolves to none or to more than one.",
    "resolved_tier": "Weakest tier on the resolving path.",
    "resolution_hops": "Identity hops traversed. 0 = a direct attribution.",
    "one_to_many_defect": "Y where the identifier reaches two or more distinct "
                          "entities. No attribution is made; the row is in "
                          "review/.",
    "dataset": "The transaction dataset the propagated link applies to.",
    "proposed_entity_id": "PROPOSED spine entity. Not written back to any "
                          "source table by this script.",
    "derived_tier": "Weakest edge on the path. A propagated link is never "
                    "stronger than its weakest edge.",
    "derived_tier_rule": "The rule above, restated on every row.",
    "weakest_edge_source": "Which source supplied the weakest edge.",
    "path_through_low_accuracy_method": "Names `need_v6` where the path runs "
                                        "through it - measured at 6.5% accurate "
                                        "against rulings.",
    "identity_hops": "Identity edges traversed before the attribution edge.",
    "path": "The full path, node by node, with each edge's source and tier.",
    "rows_unattributed_in_dataset": "Rows in that dataset the link would key.",
    "usd_unattributed_in_dataset": "Dollars on those rows.",
    "publishable": "YES only at tier A.",
    "caveat": "Standing caveat carried on every propagated row.",
    "built_by": "Script that wrote the row.",
    "built_date": "Run date.",
    "generated": "Run date.",
}


def register(dsname, path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rr = csv.DictReader(fh)
        cols = rr.fieldnames or []
        filled = Counter()
        n = 0
        for row in rr:
            n += 1
            for c2 in cols:
                if (row.get(c2) or "").strip():
                    filled[c2] += 1
    out = []
    for c2 in cols:
        out.append({
            "dataset": dsname, "variable": c2,
            "type": "number" if c2 in ("usd_observed", "rows_observed",
                                       "degree", "n_datasets", "n_entities",
                                       "identity_hops", "resolution_hops",
                                       "n_asserting_sources",
                                       "rows_unattributed_in_dataset",
                                       "usd_unattributed_in_dataset")
                    else "text",
            "units": "USD" if "usd" in c2 else ("count" if c2.startswith("n_")
                                                or c2.endswith("_hops")
                                                or c2 in ("degree",
                                                          "rows_observed")
                                                else "code"),
            "pct_filled": round(100.0 * filled[c2] / max(n, 1), 1),
            "n_rows": n, "published": 0, "access_tier": "internal",
            "description": DESCR.get(c2, "See docs/IDENTIFIER_GRAPH_BUILD_LOG.md."),
            "generated": TODAY})
    return out


frag_path = os.path.join(FRAG, "05b_identifier_graph.csv")
existing = []
if os.path.exists(frag_path):
    existing = list(rd(frag_path))
have = {(r["dataset"], r["variable"]) for r in existing}
new = []
for dsn, fn in (("05b_identifier_graph_edges",
                 os.path.join(CLEAN, "cedar_identifier_graph_edges.csv")),
                ("05b_identifier_graph_nodes",
                 os.path.join(CLEAN, "cedar_identifier_graph_nodes.csv")),
                ("05b_identifier_propagation",
                 os.path.join(CLEAN, "cedar_identifier_propagation.csv"))):
    for row in register(dsn, fn):
        if (row["dataset"], row["variable"]) not in have:
            new.append(row)
if new or not existing:
    tmp = frag_path + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CB_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(existing + new)
    os.replace(tmp, frag_path)
say(f"\n[12] codebook fragment 05b_identifier_graph.csv: "
    f"{len(existing)} existing + {len(new)} appended")

# --- run log -------------------------------------------------------------
with open(os.path.join(DOCS, "IDENTIFIER_GRAPH_RUN.txt"), "w",
          encoding="utf-8") as fh:
    fh.write("\n".join(log))
json.dump({"lift": [{k: v for k, v in L.items() if k != "gained"}
                    for L in lift_rows],
           "n_conflicts": len(conflicts), "n_shared_hubs": len(shared),
           "n_resolved": len(resolved), "n_blocked": len(blocked),
           "n_parent_candidates": len(parent_candidates),
           "irs_hypothesis": irs},
          open(os.path.join(DOCS, "IDENTIFIER_GRAPH_SUMMARY.json"), "w"),
          indent=1)
say("\nDONE")
