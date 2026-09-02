#!/usr/bin/env python3
"""
Cedar Press - 604: adjudicate the MASTER QUEUE by IDENTIFIER, not by name.

    py -3 code/604_adjudicate_master_queue_by_identifier.py            # dry run
    py -3 code/604_adjudicate_master_queue_by_identifier.py --apply
    py -3 code/604_adjudicate_master_queue_by_identifier.py --selftest

WHY THIS FILE EXISTS
--------------------
`review/MASTER_QUEUE_2026-08-07.csv` holds 6,559 entity questions with $82.1B
of `dollars_at_stake` and `YOUR_RULING` filled on ZERO of them. Item 16.6 of
`review/OWNER_DECISION_QUEUE.md` is the block the owner authorised an agent to
work, 2026-09-01: *"you can review websites and SAM or annual reports as long
as you document the decisions and learn from them."*

`docs/ENTITY_MATCH_RULES.md` step 4 says **an identifier beats every name
method**. This file takes that literally and never opens a browser, because the
strongest identifier evidence for this queue is already on disk: 5,167 rows of
`data/clean/fpds_uei_edges.csv`, which are parent/child UEI relationships the
REGISTRANT DECLARED ABOUT ITSELF in SAM. That is the same evidence class shard E
used to link seven ASRC subsidiaries worth $5.43B, none of which shared a token
with "Arctic Slope".

THE THREE SWEEPS
----------------
A. **MASTER QUEUE top 50 by dollars** - the block 16.6 names.
B. **`review/prime_unlinked_top_vendors.csv`** (400 rows) - for each unlinked
   UEI, is its DECLARED PARENT already keyed? Three are, worth $277M.
C. **The reverse sweep** - every tier A/B UEI row in the ledger whose declared
   parent is keyed to a DIFFERENT entity. 129 rows, $2.82B.

SWEEP C IS THE POINT, AND ITS HEADLINE IS NOT WHAT IT LOOKS LIKE
-----------------------------------------------------------------
"129 contradicted attributions, $2.82B" is the wrong reading and acting on it
would have been a mass repointing of correct rows. Classified, it is three
different things:

  **54 rows, $2.39B - RULE 2 VIOLATIONS ON THE PARENT, not on the child.**
  `docs/ANCSA_OWNERSHIP_RULING.md` RULE 2 and
  `cedar_domain.village_government_owns_an_anc()` (always False) say a village
  GOVERNMENT never owns an ANC. Measured here: UKPEAGVIK INUPIAT CORPORATION's
  own UEI is keyed to `AKNF-INPTAS-00-ARCSLO` - the Native Village - while all
  seven Bowhead subsidiaries under it are correctly keyed to `ANVC-KPVKPT-00`,
  the corporation. **The children are right and the parent row is wrong**, so
  one bad ledger row makes 54 good ones look contradictory. $1.56B of Bowhead
  alone. Same shape at Olgoonik/Wainwright and St. George Tanaq/Pribilof. This
  is the known `ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` family
  (334 defects, $24.52B) found again by a completely independent route.

  **72 rows, $0.40B - THE EDGE IS TOO WEAK AND THE LEDGER STANDS.** Every one
  has an edge observed under 20 times against a hand or tier-A ledger row, and
  the pattern is a JOINT VENTURE: `WHH Nisqually Federal Services` declares TDX
  QUALITY as a parent exactly once. A JV genuinely has two parents, so a thin
  edge disagreeing with a hand ruling is a signal about the corporate form, not
  an error.

  **3 rows, $0.03B - GENUINE.** The one that is not an ANCSA class question:
  `Tikigaq Technology Services` is keyed to **Paiute of Utah**
  (`TRBF-PTTRUT-00`) while declaring TIKIGAQ CORPORATION (Point Hope, Alaska)
  as its parent 258 times.

WHAT IT WRITES
--------------
`data/staging/master_queue_identifier_adjudication.csv` and a rules appendix to
`docs/ENTITY_MATCH_RULES.md`. **It writes nothing to the ledger, the spine or
`data/clean`.** Every repoint it proposes is a positive attribution; the
proposal carries its evidence and an applying pass runs separately against a
green gate.
"""
from __future__ import annotations

import collections
import csv
import re
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, "code")
REVIEW = os.path.join(ROOT, "review")
CLEAN = os.path.join(ROOT, "data", "clean")
OUT = os.path.join(ROOT, "data", "staging",
                   "master_queue_identifier_adjudication.csv")
RULES_DOC = os.path.join(ROOT, "docs", "ENTITY_MATCH_RULES.md")
TODAY = "2026-09-01"
BY = "int-3-review"

csv.field_size_limit(2_000_000_000 if sys.maxsize > 2**32 else 2**31 - 1)

# An edge observed fewer than this many times, standing against a hand or
# tier-A ledger row, is read as a JOINT VENTURE rather than a correction.
# Set from the data: every one of the 72 rows below this threshold is a JV or a
# one-off co-award, and every RULE 2 case above it is observed 100+ times.
WEAK_EDGE = 20

VILLAGE_GOV = "Federally recognized Alaska Native Village"
ANC_CLASSES = {"Alaska Native Village Corporation",
               "Alaska Native Regional Corporation",
               "ANCSA Group Corporation"}


def load503():
    spec = importlib.util.spec_from_file_location(
        "id503", os.path.join(CODE, "503_identity.py"))
    m = importlib.util.module_from_spec(spec)
    sys.modules["id503"] = m
    spec.loader.exec_module(m)
    return m


def read(p):
    with open(p, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def build(m):
    edges = read(os.path.join(CLEAN, "fpds_uei_edges.csv"))
    byc = collections.defaultdict(list)
    for e in edges:
        byc[e["child_uei"].strip().upper()].append(e)
    led = read(os.path.join(CLEAN, "cedar_identifier_ledger_final.csv"))
    keyed = {}
    for x in led:
        i = (x.get("identifier") or "").strip().upper()
        t = (x.get("tribe_id") or "").strip()
        if i and t and (x.get("confidence_tier") or "") in ("A", "B"):
            keyed.setdefault(i, (t, x.get("canonical_name", ""),
                                 x.get("confidence_tier")))
    spine = {x["tribe_id"]: x
             for x in read(os.path.join(ROOT, "data", "spine",
                                        "cedar_entity_spine.csv"))}

    def names(tid):
        s = spine.get(tid, {})
        return (m.tokens(s.get("canonical_name", ""))
                | m.tokens(s.get("fr_official_name", ""))
                | m.tokens((s.get("aliases") or "").replace(";", " ")
                           .replace("|", " ")))
    return byc, led, keyed, spine, names


UEI_IN_QUESTION = re.compile(r"\bUEI ([A-Z0-9]{12})\b")


def already_ruled_corpus():
    """Everything `review/_already_ruled_removals/` records as already ruled.

    Built because a MASTER QUEUE row can be stale in a way its own columns hide:
    2,443 of its 6,559 rows carry an EMPTY `identifier`, so a join on that
    column silently matches nothing and reports a queue as wholly unseen. The
    UEI is present - inside the free-text `question` - and this reads it.
    """
    names, ids = set(), set()
    d = os.path.join(REVIEW, "_already_ruled_removals")
    if not os.path.isdir(d):
        return names, ids
    for f in sorted(os.listdir(d)):
        if not f.lower().endswith(".csv"):
            continue
        for x in read(os.path.join(d, f)):
            for k in ("entity_name", "recipient_name", "org_name",
                      "record_name", "legal_business_name", "name"):
                if x.get(k):
                    names.add(x[k].strip().upper())
            for k in ("identifier", "recipient_uei", "uei", "ein"):
                if x.get(k):
                    ids.add(x[k].strip().upper())
    return names, ids


def negative_rulings(led):
    """UEI -> the tier-X rationale. A tier X row is a NEGATIVE ruling and the
    question it answers must not be asked again (START_HERE 1b)."""
    out = {}
    for x in led:
        if (x.get("confidence_tier") or "").strip() == "X":
            i = (x.get("identifier") or "").strip().upper()
            if i:
                out[i] = (x.get("tier_rationale") or "")[:220]
    return out


def strongest_keyed_parent(byc, keyed, uei):
    for e in sorted(byc.get(uei, []),
                    key=lambda z: -int(z["n_observations"] or 0)):
        p = (e["parent_uei"] or "").strip().upper()
        if not p or p == uei or (e.get("blocklisted_parent") or "").strip():
            continue
        k = keyed.get(p)
        if k:
            return e, k
    return None, None


def row(**kw):
    base = dict(sweep="", subject="", identifier="", usd_m="",
                current_entity_id="", current_tier="", current_method="",
                declared_parent="", declared_parent_entity_id="",
                edge_observations="", disposition="", evidence_class="",
                proposed_entity_id="", reason="", decided_by=BY,
                decided_date=TODAY)
    base.update(kw)
    return base


# ===========================================================================
def sweep_b(byc, keyed, spine, out):
    """Unlinked top vendors whose DECLARED PARENT is already keyed."""
    n = 0
    for x in read(os.path.join(REVIEW, "prime_unlinked_top_vendors.csv")):
        uei = (x.get("awardee_uei") or "").strip().upper()
        usd = float(x.get("obligations_usd") or 0) / 1e6
        e, k = strongest_keyed_parent(byc, keyed, uei)
        if not e:
            out.append(row(
                sweep="B_unlinked_vendor", subject=x.get("awardee_name", ""),
                identifier=uei, usd_m=f"{usd:.1f}", disposition="FLOOR",
                evidence_class="none",
                reason="No declared parent UEI resolves to a keyed Cedar "
                       "entity. Unlinked is an honest state (ADR-010); a "
                       "top-vendor list is not a list of Native firms."))
            continue
        nobs = int(e["n_observations"] or 0)
        if nobs < WEAK_EDGE:
            disp, ev, prop = "HOLD", "identifier_weak", ""
            why = (f"Declared parent {e['parent_name']} is keyed to {k[0]}, but "
                   f"the edge is observed only {nobs} time(s) - below the "
                   f"{WEAK_EDGE}-observation floor at which a declared parent "
                   "is read as ownership rather than a co-award.")
        else:
            disp, ev, prop = "ACCEPT", "declared_parent_uei", k[0]
            why = (f"Declared parent {e['parent_name']} ({e['parent_uei']}) is "
                   f"keyed to {k[0]} ({k[1]}), observed {nobs} times. An "
                   "identifier the registrant filed about itself beats every "
                   "name method. PROPOSED AT TIER B: the parent's own tier "
                   f"({k[2]}) describes the PARENT's link and does not "
                   "transfer - a tier is inherited from the source row, never "
                   "assigned by the consumer.")
            n += 1
        out.append(row(
            sweep="B_unlinked_vendor", subject=x.get("awardee_name", ""),
            identifier=uei, usd_m=f"{usd:.1f}",
            declared_parent=e["parent_name"],
            declared_parent_entity_id=k[0], edge_observations=str(nobs),
            disposition=disp, evidence_class=ev, proposed_entity_id=prop,
            reason=why))
    return n


# ===========================================================================
def sweep_c(byc, led, keyed, spine, names, out):
    counts = collections.Counter()
    usd_by = collections.Counter()
    for x in led:
        if (x.get("identifier_type") or "") != "UEI":
            continue
        uei = (x.get("identifier") or "").strip().upper()
        tid = (x.get("tribe_id") or "").strip()
        tier = (x.get("confidence_tier") or "").strip()
        if not tid or tier not in ("A", "B"):
            continue
        e, k = strongest_keyed_parent(byc, keyed, uei)
        if not e or k[0] == tid:
            continue
        try:
            usd = float(x.get("prime_dollars_M") or 0)
        except ValueError:
            usd = 0.0
        nobs = int(e["n_observations"] or 0)
        ptid = k[0]
        same_family = bool(m_tokens(e["parent_name"]) & names(tid)) or \
            bool(names(ptid) & names(tid))
        pc = (spine.get(ptid, {}) or {}).get("entity_class", "")
        cc = (spine.get(tid, {}) or {}).get("entity_class", "")
        if same_family:
            disp, ev, prop = "DEFECT", "ancsa_rule2", ""
            why = ("The child is keyed to the CORPORATION and its declared "
                   f"parent's own UEI is keyed to {ptid} "
                   f"({(spine.get(ptid,{}) or {}).get('canonical_name','')}), "
                   f"class {pc!r}. ANCSA_OWNERSHIP_RULING RULE 2 and "
                   "cedar_domain.village_government_owns_an_anc() (always "
                   "False) say a village GOVERNMENT never owns an ANC, so the "
                   "PARENT row is the defect and the child attribution stands. "
                   "Fix one ledger row, not 54.")
            if not (pc == VILLAGE_GOV and cc in ANC_CLASSES):
                why = ("Both ids name the same corporate family, so this is a "
                       "single-entity-held-twice defect in the identity layer "
                       "rather than a wrong attribution. The child stands.")
        elif nobs < WEAK_EDGE:
            disp, ev, prop = "AFFIRM", "joint_venture", ""
            why = (f"Declared parent {e['parent_name']} is keyed to {ptid}, but "
                   f"observed only {nobs} time(s) against a "
                   f"{x.get('attribution_method','')} tier-{tier} ledger row. "
                   "A joint venture genuinely has two parents; a thin edge "
                   "disagreeing with a hand ruling describes the corporate "
                   "form, not an error. Ledger stands.")
        else:
            disp, ev, prop = "REFUSE", "declared_parent_uei", ptid
            why = (f"CONTRADICTED BY AN IDENTIFIER. The ledger keys this UEI to "
                   f"{tid} ({x.get('canonical_name','')}) by "
                   f"{x.get('attribution_method','')}, but the registrant "
                   f"declares {e['parent_name']} as its parent {nobs} times, "
                   f"and that parent is keyed to {ptid} ({k[1]}). Repoint "
                   "proposed at tier B.")
        counts[disp] += 1
        usd_by[disp] += usd
        out.append(row(
            sweep="C_ledger_vs_declared_parent",
            subject=x.get("legal_business_name", ""), identifier=uei,
            usd_m=f"{usd:.1f}", current_entity_id=tid, current_tier=tier,
            current_method=x.get("attribution_method", ""),
            declared_parent=e["parent_name"], declared_parent_entity_id=ptid,
            edge_observations=str(nobs), disposition=disp, evidence_class=ev,
            proposed_entity_id=prop, reason=why))
    return counts, usd_by


_M = None


def m_tokens(s):
    return _M.tokens(s)


# ===========================================================================
def sweep_a(byc, keyed, out, prior_by_uei, ruled_names, ruled_ids, negatives):
    """MASTER QUEUE top 50 by dollars - the block item 16.6 names."""
    q = read(os.path.join(REVIEW, "MASTER_QUEUE_2026-08-07.csv"))
    q.sort(key=lambda x: -float(x["dollars_at_stake"] or 0))
    n_dec = 0
    for x in q[:50]:
        name = x["entity_name"].strip()
        uei = (x.get("identifier") or "").strip().upper()
        mq = UEI_IN_QUESTION.search(x.get("question") or "")
        quei = mq.group(1) if mq else ""
        anchor = uei or quei
        usd = float(x["dollars_at_stake"] or 0) / 1e6
        prior = prior_by_uei.get(quei) or prior_by_uei.get(uei)
        neg = negatives.get(anchor)
        stale = (name.upper() in ruled_names or (uei and uei in ruled_ids)
                 or (quei and quei in ruled_ids))

        if neg:
            disp, ev, prop = "ALREADY_RULED", "negative_ruling", ""
            why = ("A tier-X NEGATIVE ruling already answers this: " + neg
                   + " The queue row is stale and must not be re-asked.")
            n_dec += 1
        elif stale and not prior:
            disp, ev, prop = "ALREADY_RULED", "already_ruled_removal", ""
            why = ("Recorded in review/_already_ruled_removals/ as ALREADY_RULED "
                   "and removed from the live queue on 2026-08-26, yet still "
                   "sitting here with an empty YOUR_RULING. The MASTER QUEUE is "
                   "stale for this row.")
            n_dec += 1
        elif prior:
            disp, ev, prop = prior[0], "ruled_under_16.6", prior[1]
            why = ("Decided by ruling 16.6 (lineage reconciliation against the "
                   "registrant's own declared name): " + prior[2])
        elif not anchor:
            disp, ev, prop = "HOLD", "none", ""
            why = ("No identifier on the row or in its question text, and no "
                   "16.6 disposition. Nothing to anchor an identifier-first "
                   "decision to.")
        else:
            e, k = strongest_keyed_parent(byc, keyed, anchor)
            if e and int(e["n_observations"] or 0) >= WEAK_EDGE:
                disp, ev, prop = "ACCEPT", "declared_parent_uei", k[0]
                why = (f"Declared parent {e['parent_name']} ({e['parent_uei']}) "
                       f"keyed to {k[0]} ({k[1]}), observed "
                       f"{e['n_observations']} times. Proposed at tier B.")
            elif e:
                disp, ev, prop = "HOLD", "identifier_weak", ""
                why = (f"Declared parent {e['parent_name']} keyed to {k[0]} but "
                       f"observed only {e['n_observations']} time(s) - under "
                       f"the {WEAK_EDGE}-observation joint-venture floor.")
            else:
                disp, ev, prop = "REFUSE", "no_identifier", ""
                why = ("No declared parent UEI resolves to a keyed Cedar "
                       "entity. The queue row itself says 'candidate, NOT a "
                       "Native attribution' - a big vendor is not a Native "
                       "firm because it is unlinked.")
            n_dec += 1
        out.append(row(
            sweep="A_master_queue_top50", subject=name, identifier=anchor,
            usd_m=f"{usd:.1f}", disposition=disp, evidence_class=ev,
            proposed_entity_id=prop, reason=why))
    return n_dec


# ===========================================================================
RULES_APPENDIX = """

---

# Rules 7–12 — added 2026-09-01 by `int-3-review`

*Derived while deciding the `review/` backlog (`docs/REVIEW_BACKLOG_RULINGS.md`,
`code/603_*`, `code/604_*`). Each one is here because it settled a class, not a
row.*

## 7. An entity's own official name is the arbiter of its own boundary

When a filed name and a Cedar entity are being compared, the question is not
"do they share tokens" but **"is every distinctive word in the filed name
accounted for by that entity's own official name?"** Take the union of
`canonical_name`, `fr_official_name` and `aliases` from the spine and subtract
it from the filed name's distinctive tokens. What is left is the **residue**,
and the residue decides:

| residue | meaning | disposition |
|---|---|---|
| empty | the same entity | ACCEPT |
| place or spelling variant — `PINE, RIDGE`; `LOUSIANA`; `RESERVATI` | still the entity | ACCEPT |
| an institution form — `SCHOOL`, `AUTHORITY`, `COLLEGE`, `UTILITY`, `HOUSING` | a body the nation created | HOLD |
| four or more distinctive words | a different name | HOLD |

**Why this and not set equality.** Cedar's canonical names are deliberately
short (`Rosebud` for the Rosebud Sioux Tribe), so requiring equality holds 280
correct rows worth $23.4B. **Why this and not containment.** Containment in the
other direction accepts `TURTLE MOUNTAIN COMMUNITY COLLEGE` as the Turtle
Mountain Band, `MENOMINEE INDIAN SCHOOL DISTRICT` as the Menominee Tribe and
`NAVAJO TRIBAL UTILITY AUTHORITY` as the Navajo Nation. A tribal college, a
school district and a utility are real entities and they are not the nation.

**The residue cap is empirical, not chosen.** Over 281 accepts, the largest
residue on a correct one is three (`NAMBE PUEBLO GOVERNOR'S OFFICE`), and
exactly one wrong accept carried no institution-form word at all:
`LEECH LAKE BAND OF OJIBWE NATURAL WILD RICE` → the Band, residue
`NATURAL, OJIBWE, RICE, WILD`. No denylist could have caught it — `RICE` is not
an organisational form — and the structural fact that it adds four distinctive
words is what separates it.

## 8. A ruled METHOD is not a positive ruling, and an agent ruling may not mint tier A

Already true of `attribution_method` (START_HERE 1b: all 317 `elijah_ruling`
EIN rows are tier X, NEGATIVE). Extended here to propagation:
`propagated_from_agent_ruling` may not carry a row to tier A. Tier A is an
**identifier** grade. Measured: of 1,223 rows queued for tier B → tier A
promotion, **not one carries an identifier**, so the correct number of
promotions is zero.

## 9. Containment never accepts alone

Containment and token-subset are WEAK classes (checklist step 2) and need a
second independent signal. With no corroborator, containment is REFUSED where a
link would be created and HELD where one already exists at tier B. This is the
class that produced 41 wrong links onto `Council Native Corporation`.

## 10. An alias needs three independent observations

One Federal Register notice spelling a name a particular way is a typesetter.
Two is often the same notice reissued. **Three or more independent notices is
corroboration.** Calibration: the earlier recognition-alias pass rejected
**76 of 228** proposals on review — a 33% error rate, far too high to
auto-apply at n=1. Applied to 1,049 NAGPRA proposals: 211 accept, 168 hold,
670 refuse.

## 11. A DECLARED PARENT UEI outranks a name, and 20 observations is the floor

`fpds_uei_edges.csv` carries parent/child UEI relationships **the registrant
filed about itself**. That is the identifier evidence rule 4 asks for and it is
already on disk — no browser needed. Two thresholds make it usable:

- **An edge observed 20+ times is ownership.** Below that it is a **joint
  venture or a co-award**, and a JV genuinely has two parents. Measured: all 72
  ledger rows whose declared parent disagrees on a sub-20 edge are JVs
  (`WHH Nisqually Federal Services` declares TDX Quality exactly **once**),
  while every real ownership case is observed 100+ times.
- **The parent's tier does not transfer.** A link resolved through a tier-A
  parent is proposed at **tier B**: the parent's tier describes the parent's
  own link. A tier is inherited from the source row, never assigned by the
  consumer.

## 12. When a declared parent contradicts an attribution, suspect the PARENT row first

The most valuable rule here, and the least obvious. Sweeping every tier A/B UEI
in the ledger against its declared parent produced **129 contradictions on
$2.82B** — a number that reads like 129 wrong attributions and is not:

- **54 rows, $2.39B — the PARENT row is the defect.** Every Bowhead subsidiary
  is correctly keyed to `ANVC-KPVKPT-00`, Ukpeaġvik Iñupiat Corporation, while
  **the corporation's own UEI is keyed to `AKNF-INPTAS-00-ARCSLO`, the Native
  Village**. `ANCSA_OWNERSHIP_RULING` RULE 2 and
  `cedar_domain.village_government_owns_an_anc()` (always `False`) say that
  link cannot exist. One bad parent row makes 54 good child rows look wrong.
  Same shape at Olgoonik/Wainwright and St. George Tanaq/Pribilof. This is the
  known `ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION` family (334 defects,
  $24.52B) reached by an independent route.
- **72 rows, $0.40B — rule 11's JV floor.** Ledger stands.
- **3 rows, $0.03B — genuine.** The only non-ANCSA one:
  `Tikigaq Technology Services` keyed to **Paiute of Utah**
  (`TRBF-PTTRUT-00`) while declaring **TIKIGAQ CORPORATION** (Point Hope,
  Alaska) as its parent **258 times**.

**So a contradiction sweep must classify before it acts.** Acting on the raw
129 would have repointed 126 correct rows to chase 3 wrong ones.
"""


def selftest():
    ok = True
    print("RULE 11 (JV floor at 20 observations):")
    for n, want in ((1, "HOLD"), (19, "HOLD"), (20, "ACCEPT"), (258, "ACCEPT")):
        got = "ACCEPT" if n >= WEAK_EDGE else "HOLD"
        good = got == want
        ok &= good
        print(f"  {'OK ' if good else 'BAD'} n={n:<4} -> {got}")
    print("RULE 12 (a village government may not own an ANC):")
    good = (VILLAGE_GOV not in ANC_CLASSES
            and "Alaska Native Village Corporation" in ANC_CLASSES)
    print(f"  {'OK ' if good else 'BAD'} village-government class is not an "
          "ANC class")
    ok &= good
    spec = importlib.util.spec_from_file_location(
        "cedar_domain", os.path.join(CODE, "cedar_domain.py"))
    cd = importlib.util.module_from_spec(spec)
    sys.modules["cedar_domain"] = cd
    spec.loader.exec_module(cd)
    good = cd.village_government_owns_an_anc(VILLAGE_GOV,
                                             "Alaska Native Village "
                                             "Corporation") is False
    print(f"  {'OK ' if good else 'BAD'} cedar_domain agrees (returns False)")
    ok &= good
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    global _M
    if "--selftest" in sys.argv:
        return selftest()
    apply = "--apply" in sys.argv
    _M = load503()
    byc, led, keyed, spine, names = build(_M)

    # Join 16.6 by UEI, never by name: 65 recipient names in that file are
    # carried by more than one UEI (NAVAJO NATION TRIBAL GOVERNMENT by twelve),
    # so a name-keyed dict is last-write-wins and reported THREE AFFILIATED
    # TRIBES as a FLOOR when its own row is an ACCEPT.
    prior_by_uei = {}
    p = os.path.join(ROOT, "data", "staging",
                     "review_backlog_class_dispositions.csv")
    if os.path.exists(p):
        for x in read(p):
            if x["ruling"] != "16.6":
                continue
            u = (x["key"].split("|", 1)[-1] or "").strip().upper()
            if u:
                prior_by_uei[u] = (x["disposition"], x["proposed_entity_id"],
                                   x["reason"][:180])
    ruled_names, ruled_ids = already_ruled_corpus()
    negatives = negative_rulings(led)

    out: list[dict] = []
    n_a = sweep_a(byc, keyed, out, prior_by_uei, ruled_names, ruled_ids,
                  negatives)
    n_b = sweep_b(byc, keyed, spine, out)
    counts, usd_by = sweep_c(byc, led, keyed, spine, names, out)

    print(f"A. MASTER QUEUE top 50 by dollars: 50 rows, {n_a} decided here by "
          f"identifier, {50 - n_a} inherited from ruling 16.6")
    print(f"B. prime_unlinked_top_vendors: {n_b} links made on a declared "
          "parent UEI")
    print("C. ledger vs declared parent: "
          + ", ".join(f"{d}={n} (${usd_by[d]/1e3:.2f}B)"
                      for d, n in counts.most_common()))
    tot = collections.Counter(d["disposition"] for d in out)
    print("\noverall: " + "  ".join(f"{k}={v}" for k, v in tot.most_common()))

    if not apply:
        print(f"\nDRY RUN. Re-run with --apply to write "
              f"{os.path.relpath(OUT, ROOT)} and append rules 7-12 to "
              f"{os.path.relpath(RULES_DOC, ROOT)}.")
        return 0

    cols = list(row().keys())
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    print(f"\nWROTE  {os.path.relpath(OUT, ROOT)}  {len(out):,} rows")

    cur = open(RULES_DOC, encoding="utf-8").read()
    if "# Rules 7–12" in cur:
        print("rules appendix already present - not duplicated")
    else:
        with open(RULES_DOC, "a", encoding="utf-8") as fh:
            fh.write(RULES_APPENDIX)
        print(f"APPENDED rules 7-12 to {os.path.relpath(RULES_DOC, ROOT)}")
    print("\nNothing written to the ledger, the spine or data/clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
