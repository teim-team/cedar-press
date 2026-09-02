#!/usr/bin/env python3
"""
Cedar Press - 1010: OWNERSHIP CHANGES THAT ARE VISIBLE ONLY IN FEDERAL CONTRACTING.

    py -3 code/1010_ownership_change_from_contracting.py            # measure + write
    py -3 code/1010_ownership_change_from_contracting.py measure    # same
    py -3 code/1010_ownership_change_from_contracting.py verify     # exit 1 on breach
    py -3 code/1010_ownership_change_from_contracting.py selftest   # prove verify fires

THE OWNER'S FRAMING
-------------------
    "If we see a deal that's published, we should see the federal contracting
     company change owners. Or if we see the federal contracting company change
     owners, that's not something publicly available - it's a deal we can report."

`prime_contracts.csv` carries `parent_uei` on 1,217,713 and `parent_name` on
1,217,514 of its 1,217,768 rows and a `fiscal_year` on all of them. A firm whose DECLARED PARENT
changes from one corporate family to another, and stays changed, has been
bought or sold. FPDS does not update retroactively (AGENTS.md, and Elijah's own
Dippel correspondence), so the change appears at the moment the new owner files,
which is often the only public trace there is.

THE OWNER'S EXPLICIT WARNING, WHICH IS THE HARD PART
-----------------------------------------------------
    "There could be some wonky stuff where a company changes from, like,
     All Native Group to Ho-Chunk Inc, but it's still the same Native entity."

Under the hub-and-sub-hub model a nation is the HUB and its holding company,
its casino and its several SAM registrations are SUB-HUBS. A move between two
sub-hubs of ONE hub is a relabelling, not a transaction. Every candidate is
therefore tested against five independent intra-family predicates before it is
allowed to be called a deal, and the REJECTIONS are written out beside the
candidates because the rejection count is the measure of whether the detector
is trustworthy.

The five refusals, in the order they fire:

  NAN_SENTINEL                    the parent UEI is the literal string `NAN`
                                  (`ENTITY_MATCH_RULES` rule 4 warns of this in
                                  `fpds_uei_cage_map.csv`; it is in this column
                                  too)
  SAME_NAME_REREGISTRATION        both parent names normalise to the same
                                  distinctive token string - one entity, two SAM
                                  registrations, which is a registry event
  INTRA_FAMILY_SAME_HUB           both parents resolve to hub sets that
                                  INTERSECT in the spine / ledger / alias layer
  INTRA_FAMILY_SHARED_BRAND       the two parent names share a distinctive,
                                  non-trap token (Olgoonik Innovations ->
                                  Olgoonik General)
  INTRA_FAMILY_ACRONYM            a registered acronym alias of one parent's hub
                                  is a token of the other parent's name
                                  (CIRI Development Corporation <-> Cook Inlet
                                  Region, Incorporated)

WHY WEAK EVIDENCE IS ALLOWED TO REFUSE AND NEVER TO AWARD
----------------------------------------------------------
`docs/ENTITY_MATCH_RULES.md` rule 7: *"a bare token may never AWARD a match, but
it may always BLOCK one. Blocking on weak evidence is safe in a way awarding on
it is not."* SHARED_BRAND and ACRONYM are token-level tests and would be
forbidden as matchers. They are used here only to SUPPRESS a report, which is
the safe direction: the cost of a wrong refusal is a missed story, the cost of a
wrong report is a fabricated transaction.

WHAT IS NOT CLAIMED
-------------------
A candidate is a LEAD, not a finding. FPDS parent fields are a firm's
self-declaration (AGENTS.md: "EVIDENCE, not AUTHORITY"). This script says only:
this UEI declared parent A through year X and parent B from year Y, the two
parents are not the same corporate family by any test Cedar can run, and the
deal ledger does or does not already carry it. Rung 2-5 of ENTITY_MATCH_RULES
rule 13 - the website, the address, the news article - is a human's job.

MONEY
-----
`total_obligations` on `prime_contracts.csv` is additive at transaction grain
and is reported here ONLY for the child UEI inside its own parent-run years. No
figure in this script's output may be added to any other dataset
(`MONEY_TOTALLING_RULES.md`).

OUTPUTS - this script writes ONLY its own files and never repairs another
dataset's table in place:

    review/1010_ownership_change_candidates.csv        leads, ranked by dollars
    review/1010_ownership_change_rejections.csv        every intra-family refusal
    review/1010_announced_deals_vs_contracting.csv     the reverse direction
    docs/schema/ownership_change_invariants.json       what `verify` enforces
"""
from __future__ import annotations

import collections
import csv
import json
import os
import re
import sys

csv.field_size_limit(1 << 30)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIME = os.path.join(ROOT, "data", "clean", "prime_contracts.csv")
LEDGER = os.path.join(ROOT, "data", "clean", "cedar_identifier_ledger_final.csv")
SPINE = os.path.join(ROOT, "data", "spine", "cedar_entity_spine.csv")
ALIASES = os.path.join(ROOT, "data", "clean", "entity_aliases.csv")
DEALS = os.path.join(ROOT, "data", "clean", "deals_classified.csv")
OWNEV = os.path.join(ROOT, "data", "clean", "ownership_events.csv")

OUT_CAND = os.path.join(ROOT, "review", "1010_ownership_change_candidates.csv")
OUT_REJ = os.path.join(ROOT, "review", "1010_ownership_change_rejections.csv")
OUT_REV = os.path.join(ROOT, "review", "1010_announced_deals_vs_contracting.csv")
OUT_INV = os.path.join(ROOT, "docs", "schema", "ownership_change_invariants.json")

# Organisational words that carry no identity. Deliberately short: the point of
# ENTITY_MATCH_RULES is that a denylist cannot be the guard, only the tidy-up.
GENERIC = frozenset(
    """inc incorporated llc llp lp lc pllc corp corporation co company the of and a an
    group holdings holding ltd limited plc jv joint venture""".split()
)

# Dominance thresholds. A fiscal year counts as declaring ONE parent only when
# that parent holds >=80% of the year's rows over >=2 rows; anything else is
# MIXED and can neither open nor close a run. FPDS parent declaration is
# per-filing and genuinely inconsistent, which is why the bar is here at all.
DOM_SHARE = 0.80
DOM_MIN_ROWS = 2


def toks(s: str) -> list[str]:
    s = re.sub(r"[^a-z0-9]+", " ", (s or "").lower())
    return [w for w in s.split() if w and w not in GENERIC]


def nkey(s: str) -> str:
    return " ".join(toks(s))


def _name_traps() -> frozenset:
    sys.path.insert(0, os.path.join(ROOT, "code"))
    try:
        import cedar_domain  # type: ignore

        return frozenset(w.lower() for w in cedar_domain.NAME_TRAPS)
    except Exception:
        return frozenset()


# ----------------------------------------------------------------- identity ---
class Hubs:
    """Resolve a declared parent UEI / name to the set of Cedar hubs it may be.

    A SET, never a single id, because the spine genuinely holds the same name
    twice - `UKPEAGVIK INUPIAT CORPORATION` is both `ANVC-KPVKPT-00` (the
    corporation) and `AKNF-INPTAS-00-ARCSLO` (the village government), which is
    the known ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION defect. Collapsing
    it to one id would silently pick a side; keeping the set means an
    intersection test still refuses correctly.
    """

    def __init__(self) -> None:
        self.traps = _name_traps()
        self.uei2hub: dict[str, str] = {}
        self.name2hub: dict[str, set] = collections.defaultdict(set)
        self.acronym2hub: dict[str, set] = collections.defaultdict(set)
        self.hub_name: dict[str, str] = {}
        eid2tid: dict[str, str] = {}

        for r in _rows(SPINE):
            tid = r["tribe_id"]
            if not tid:
                continue
            self.hub_name[tid] = r.get("canonical_name") or tid
            if r.get("cedar_entity_id"):
                eid2tid[r["cedar_entity_id"]] = tid
            eid2tid[tid] = tid
            for f in ("canonical_name", "fr_official_name"):
                k = nkey(r.get(f))
                if k:
                    self.name2hub[k].add(tid)
            for a in (r.get("aliases") or "").split("|"):
                for b in a.split(";"):
                    k = nkey(b)
                    if k:
                        self.name2hub[k].add(tid)

        for r in _rows(LEDGER):
            t = r["identifier_type"].upper()
            ident = (r["identifier"] or "").strip().upper()
            tid = r["tribe_id"]
            if t == "UEI" and ident and tid:
                self.uei2hub[ident] = tid
            if tid:
                for f in ("legal_business_name", "canonical_name"):
                    k = nkey(r.get(f))
                    if k:
                        self.name2hub[k].add(tid)

        for r in _rows(ALIASES):
            tid = eid2tid.get(r["entity_id"])
            if not tid:
                continue
            t = toks(r["alias_name"])
            if len(t) >= 2:
                self.name2hub[" ".join(t)].add(tid)
            elif len(t) == 1 and len(t[0]) >= 3 and t[0] not in self.traps:
                # single-token aliases MAY NOT award a match; they are kept in a
                # separate index used only to refuse one.
                if (r.get("alias_type_normalized") or r.get("alias_type") or "").lower() in (
                    "acronym",
                    "brand",
                ):
                    self.acronym2hub[t[0]].add(tid)

    def of(self, uei: str, name: str) -> set:
        out: set = set()
        u = (uei or "").strip().upper()
        if u in self.uei2hub:
            out.add(self.uei2hub[u])
        k = nkey(name)
        if k:
            out |= self.name2hub.get(k, set())
        return out

    def distinctive(self, name: str) -> set:
        return {w for w in toks(name) if w not in self.traps and len(w) >= 3}

    def acronym_hit(self, name: str) -> set:
        out: set = set()
        for w in toks(name):
            out |= self.acronym2hub.get(w, set())
        return out


def _rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


# ----------------------------------------------------------- parent series ---
def scan_prime():
    """One pass over prime_contracts.csv.

    Returns per awardee_uei: {fy: {parent_uei: [rows, usd]}}, name counters and
    the tribe_id/cedar_uid Cedar currently ships for the child.
    """
    series = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0.0])))
    child_name = collections.defaultdict(collections.Counter)
    parent_name = collections.defaultdict(collections.Counter)
    child_hub = collections.defaultdict(collections.Counter)
    nan_rows = 0
    nan_usd = 0.0
    total_rows = 0

    with open(PRIME, newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        head = next(rd)
        ix = {c: i for i, c in enumerate(head)}
        i_u, i_fy, i_pu, i_pn = ix["awardee_uei"], ix["fiscal_year"], ix["parent_uei"], ix["parent_name"]
        i_an, i_ob, i_tid, i_cn = ix["awardee_name"], ix["total_obligations"], ix["tribe_id"], ix["canonical_name"]
        for row in rd:
            total_rows += 1
            u = row[i_u].strip().upper()
            if not u:
                continue
            pu = row[i_pu].strip().upper()
            try:
                ob = float(row[i_ob] or 0)
            except ValueError:
                ob = 0.0
            if pu == "NAN":
                nan_rows += 1
                nan_usd += ob
            cell = series[u][row[i_fy]][pu]
            cell[0] += 1
            cell[1] += ob
            child_name[u][row[i_an]] += 1
            if pu:
                parent_name[pu][row[i_pn]] += 1
            if row[i_tid]:
                child_hub[u][(row[i_tid], row[i_cn])] += 1
    return series, child_name, parent_name, child_hub, nan_rows, nan_usd, total_rows


def runs_for(years: dict):
    """Collapse a UEI's per-year declared parents into consecutive runs."""
    out = []
    for fy in sorted(years, key=lambda x: int(x)):
        cnt = years[fy]
        tot = sum(v[0] for v in cnt.values())
        p, v = max(cnt.items(), key=lambda kv: kv[1][0])
        lab = p if (tot >= DOM_MIN_ROWS and v[0] / tot >= DOM_SHARE) or tot < DOM_MIN_ROWS else "MIXED"
        if tot < DOM_MIN_ROWS:
            lab = p
        usd = sum(v[1] for v in cnt.values())
        if out and out[-1]["parent"] == lab:
            out[-1]["last_fy"] = int(fy)
            out[-1]["rows"] += tot
            out[-1]["usd"] += usd
        else:
            out.append({"parent": lab, "first_fy": int(fy), "last_fy": int(fy), "rows": tot, "usd": usd})
    return out


def transitions(series):
    """A UEI qualifies only when its solid parent runs are STRICTLY TIME-ORDERED.

    If parent A reappears after parent B, the declaration is oscillating and
    that is FPDS inconsistency, not an ownership event. Requiring disjoint,
    ordered spans is what separates a transaction from a filing habit.
    """
    for u, years in series.items():
        rr = runs_for(years)
        solid = [r for r in rr if r["parent"] != "MIXED"]
        byp = collections.defaultdict(list)
        for r in solid:
            byp[r["parent"]].append(r)
        if len(byp) < 2:
            continue
        span = {
            p: (min(x["first_fy"] for x in v), max(x["last_fy"] for x in v),
                sum(x["rows"] for x in v), sum(x["usd"] for x in v))
            for p, v in byp.items()
        }
        order = sorted(span, key=lambda p: span[p][0])
        if not all(span[order[i]][1] < span[order[i + 1]][0] for i in range(len(order) - 1)):
            continue
        for i in range(len(order) - 1):
            yield u, order[i], span[order[i]], order[i + 1], span[order[i + 1]]


# -------------------------------------------------------------- deal ledger ---
# An ownership change can only be ANNOUNCED by a row that is itself about
# ownership. A grant row naming the same company is not the announcement of its
# sale, and treating it as one is how a detector reports itself clean.
OWNERSHIP_CATEGORIES = (
    "acquisition", "divestiture", "merger", "equity investment", "joint venture",
    "capital contribution", "ownership_event",
)


def deal_index():
    """The rows of Cedar's own deal ledger that assert an ownership change.

    Used only to answer ANNOUNCED / NOT ANNOUNCED. A hit means Cedar already
    reports the transaction; a miss means nobody here has written it down, which
    is the whole product.
    """
    idx = []
    for r in _rows(DEALS):
        cat = (r.get("Deal_Category") or "") + "|" + (r.get("transaction_type") or "")
        if not any(c in cat.lower() for c in OWNERSHIP_CATEGORIES):
            continue
        try:
            yr = int(r["Event_Year"])
        except (TypeError, ValueError):
            continue
        blob = " ".join(
            [r.get("Native_Party") or "", r.get("Counterparty_or_Funder") or "",
             r.get("Deal_Title") or "", r.get("Description") or "",
             r.get("native_party_canonical_name") or ""]
        )
        idx.append((yr, toks(blob), r["Deal_ID"], (r.get("Deal_Category") or "")))
    for r in _rows(OWNEV):
        try:
            yr = int(r["event_year"])
        except (TypeError, ValueError):
            continue
        blob = " ".join([r.get("acquirer_entity") or "", r.get("target_entity") or "",
                         r.get("seller_entity") or "", r.get("native_party_verbatim") or "",
                         r.get("counterparty_verbatim") or ""])
        idx.append((yr, toks(blob), r["event_id"], "ownership_event"))
    return idx


def _contains_run(hay: list, needle: list) -> bool:
    """The deal row must LITERALLY NAME the company - contiguous tokens.

    A set-intersection test matched `Rnb Technologies -> Oasis Systems` to an
    unrelated ANCSA acquisition on the token `systems`, and a grant row to an
    acquisition on `technologies`. Requiring the child's whole distinctive name
    as a contiguous run is what makes the ANNOUNCED answer worth anything.
    """
    if not needle:
        return False
    n = len(needle)
    return any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def deal_hit(idx, traps, child, pa, pb, year, window=5):
    """Window is WIDE on purpose: the declaration lags the transaction.

    `North Wind Group acquires LBYD Engineers` is `MA2020-004`, dated 2020, and
    LBYD's FPDS parent did not become Cook Inlet Region until FY2025. AGENTS.md
    records the cause - FPDS does not update retroactively - so a narrow window
    would report a five-year-old, already-published deal as unannounced. Five
    years is the empirical lag ceiling seen in this file; a hit is still graded
    by whether the deal row also names one of the two parents.
    """
    cd = toks(child)
    if not cd or (len(cd) == 1 and (cd[0] in traps or len(cd[0]) < 4)):
        return ""
    side = {w for w in toks(pa) + toks(pb) if w not in traps and len(w) >= 4}
    best = []
    for yr, blob, did, cat in idx:
        if abs(yr - year) > window:
            continue
        if _contains_run(blob, cd):
            grade = "child+party" if side & set(blob) else "child-name-only"
            best.append(f"{did}({yr};{cat};{grade})")
    return ";".join(best[:4])


# ------------------------------------------------------------------- build ---
REV_COLS = [
    "deal_id", "event_year", "deal_category", "deal_title",
    "native_party", "counterparty", "announced_value_usd",
    "matched_prime_awardee_name", "matched_prime_uei",
    "uei_first_fy", "uei_last_fy", "uei_prime_obligations_usd",
    "parent_change_seen_in_window", "parent_change_detail", "reconciliation_verdict",
]


def reverse_check(series, cname, pname):
    """THE OTHER HALF OF THE OWNER'S SENTENCE.

        "If we see a deal that's published, we should see the federal
         contracting company change owners."

    So walk Cedar's own announced ownership deals and ask contracting whether it
    agrees. Three honest answers, and only one of them is a defect:

      TARGET_NOT_A_FEDERAL_PRIME     the company never appears in
                                     prime_contracts.csv. Expected, and not a
                                     disagreement: most of this ledger is
                                     casinos, hotels, land and broadband.
      CONFIRMED_BY_CONTRACTING       the target is a prime AND its declared
                                     parent changed inside the window. The two
                                     datasets corroborate each other.
      NO_PARENT_CHANGE_IN_FPDS       the target is a prime, kept filing, and
                                     NEVER changed its declared parent. This is
                                     the disagreement worth reporting: either
                                     the firm never re-filed (which is the
                                     documented FPDS behaviour and makes the
                                     deal ledger the only ownership source), or
                                     the deal did not close as recorded.

    The target is found by requiring a prime awardee's WHOLE distinctive name to
    appear as a contiguous token run inside the deal title. No token matching -
    `cherokee` alone put 820 rows and $181,881,441.37 on the wrong nation.
    """
    # Token rarity across the whole awardee population. `analytical services`,
    # `management services` and `technology solutions` are real awardee names
    # AND ordinary English, and each one matched a deal title about a different
    # company. A name qualifies to be searched for only if it carries at least
    # one token that is rare in this population - the structural version of
    # ENTITY_MATCH_RULES step 1, "compute the distinctive token set".
    df = collections.Counter()
    n_names = 0
    for u, c in cname.items():
        for nm in c:
            n_names += 1
            df.update(set(toks(nm)))
    rare_max = max(3, int(0.002 * n_names))

    prime_names = collections.defaultdict(set)
    for u, c in cname.items():
        for nm, _ in c.items():
            k = tuple(toks(nm))
            # >=2 distinctive tokens, always. A single-token name matched
            # `defense` and `personal` inside deal prose and turned two unrelated
            # sentences into corporate identities.
            if len(k) >= 2 and any(df[t] <= rare_max for t in k):
                prime_names[k].add(u)

    changed = collections.defaultdict(list)
    for u, a, sa, b, sb in transitions(series):
        changed[u].append((sa[1], sb[0], a, b))

    out = []
    for r in _rows(DEALS):
        cat = (r.get("Deal_Category") or "") + "|" + (r.get("transaction_type") or "")
        if not any(c in cat.lower() for c in OWNERSHIP_CATEGORIES):
            continue
        try:
            yr = int(r["Event_Year"])
        except (TypeError, ValueError):
            continue
        # THE TARGET IS ON THE RIGHT OF THE VERB. Searching the whole title
        # matched the ACQUIRER - eight separate rows resolved to
        # `chickasaw nation industries` and reported that CNI's own declared
        # parent never changed, which is true and is not a finding. Cutting the
        # title at the transaction verb leaves the company that was bought.
        # TITLE ONLY. Including `Description` matched `analytical services` and
        # `sierra nevada` on prose that DESCRIBED the target rather than naming
        # it - a sector descriptor is not a company.
        title_all = r.get("Deal_Title") or ""
        cut = re.split(
            r"\b(?:acquires?|acquisition of|acquired|buys?|buy[- ]?out of|purchases?|"
            r"sells?|sale of|divests?|invests? in|agrees to acquire|takes? majority|"
            r"becomes majority owner of)\b",
            title_all, maxsplit=1, flags=re.I)
        has_verb = len(cut) > 1
        title = toks(cut[1]) if has_verb else []
        acquirer = set(toks(cut[0])) | set(toks(r.get("Native_Party") or "")) if has_verb else set()
        hit_key, hit_ueis = None, set()
        for k, ueis in prime_names.items():
            if _contains_run(title, list(k)) and not set(k) <= acquirer:
                if hit_key is None or len(k) > len(hit_key):
                    hit_key, hit_ueis = k, ueis
        row = {
            "deal_id": r["Deal_ID"], "event_year": yr,
            "deal_category": r.get("Deal_Category") or "",
            "deal_title": (r.get("Deal_Title") or "")[:200],
            "native_party": r.get("Native_Party") or "",
            "counterparty": r.get("Counterparty_or_Funder") or "",
            "announced_value_usd": r.get("Announced_Value_USD") or "",
            "matched_prime_awardee_name": " ".join(hit_key) if hit_key else "",
            "matched_prime_uei": "|".join(sorted(hit_ueis)),
        }
        if not hit_key:
            row.update({"uei_first_fy": "", "uei_last_fy": "", "uei_prime_obligations_usd": "",
                        "parent_change_seen_in_window": "", "parent_change_detail": "",
                        "reconciliation_verdict": ("TARGET_NOT_A_FEDERAL_PRIME" if has_verb
                                                   else "TARGET_NOT_NAMED_IN_TITLE")})
            out.append(row)
            continue
        fys, usd, detail = [], 0.0, []
        for u in hit_ueis:
            for fy, cnt in series[u].items():
                fys.append(int(fy))
                usd += sum(v[1] for v in cnt.values())
            for last_prior, first_later, a, b in changed.get(u, []):
                if abs(first_later - yr) <= 5:
                    detail.append(f"{u}:{a}->{b} FY{last_prior}->{first_later}")
        row.update({
            "uei_first_fy": min(fys) if fys else "", "uei_last_fy": max(fys) if fys else "",
            "uei_prime_obligations_usd": round(usd, 2),
            "parent_change_seen_in_window": "1" if detail else "0",
            "parent_change_detail": ";".join(detail[:3]),
            "reconciliation_verdict": "CONFIRMED_BY_CONTRACTING" if detail else "NO_PARENT_CHANGE_IN_FPDS",
        })
        out.append(row)
    out.sort(key=lambda r: (r["reconciliation_verdict"], -(float(r["uei_prime_obligations_usd"] or 0))))
    return out


CAND_COLS = [
    "child_uei", "child_name", "child_shipped_tribe_id", "child_shipped_name",
    "prior_parent_uei", "prior_parent_name", "prior_first_fy", "prior_last_fy",
    "prior_rows", "prior_hubs",
    "later_parent_uei", "later_parent_name", "later_first_fy", "later_last_fy",
    "later_rows", "later_hubs",
    "transition_between_fy", "child_prime_obligations_usd_in_runs",
    "direction", "native_side_present", "child_name_token_overlap",
    "interpretation_caution", "deal_ledger_match", "announced_status", "evidence_note",
]
REJ_COLS = [
    "refusal", "child_uei", "child_name", "prior_parent_uei", "prior_parent_name",
    "prior_first_fy", "prior_last_fy", "later_parent_uei", "later_parent_name",
    "later_first_fy", "later_last_fy", "shared_evidence",
]


def build():
    hubs = Hubs()
    traps = hubs.traps
    series, cname, pname, chub, nan_rows, nan_usd, total_rows = scan_prime()
    idx = deal_index()

    cands, rejs = [], []
    for u, a, sa, b, sb in transitions(series):
        cn = (cname[u].most_common(1) or [("", 0)])[0][0]
        na = (pname[a].most_common(1) or [("", 0)])[0][0] if a != u else cn
        nb = (pname[b].most_common(1) or [("", 0)])[0][0] if b != u else cn
        na = na or cn if a == u else na
        nb = nb or cn if b == u else nb
        ha, hb = hubs.of(a, na), hubs.of(b, nb)
        da, db = hubs.distinctive(na), hubs.distinctive(nb)

        refusal, shared = "", ""
        if a == "NAN" or b == "NAN":
            refusal, shared = "NAN_SENTINEL", "literal string NAN in parent_uei"
        elif nkey(na) and nkey(na) == nkey(nb):
            refusal, shared = "SAME_NAME_REREGISTRATION", nkey(na)
        elif ha & hb:
            refusal, shared = "INTRA_FAMILY_SAME_HUB", "|".join(sorted(ha & hb))
        elif da & db:
            refusal, shared = "INTRA_FAMILY_SHARED_BRAND", "|".join(sorted(da & db))
        elif (hubs.acronym_hit(na) & hb) or (hubs.acronym_hit(nb) & ha):
            refusal = "INTRA_FAMILY_ACRONYM"
            shared = "|".join(sorted((hubs.acronym_hit(na) & hb) | (hubs.acronym_hit(nb) & ha)))

        if refusal:
            rejs.append({
                "refusal": refusal, "child_uei": u, "child_name": cn,
                "prior_parent_uei": a, "prior_parent_name": na,
                "prior_first_fy": sa[0], "prior_last_fy": sa[1],
                "later_parent_uei": b, "later_parent_name": nb,
                "later_first_fy": sb[0], "later_last_fy": sb[1],
                "shared_evidence": shared,
            })
            continue

        shipped = (chub[u].most_common(1) or [(("", ""), 0)])[0][0]
        native_before = bool(ha)
        native_after = bool(hb)
        if a == u:
            direction = "ACQUIRED_INTO_A_PARENT" if native_after else "PARENT_DECLARED"
        elif b == u:
            direction = "SPUN_OUT_OF_PARENT"
        elif native_before and not native_after:
            direction = "SOLD_OUT_OF_NATIVE_OWNERSHIP"
        elif native_after and not native_before:
            direction = "ACQUIRED_BY_NATIVE_OWNER"
        elif native_before and native_after:
            direction = "MOVED_BETWEEN_NATIVE_FAMILIES"
        else:
            direction = "NEITHER_SIDE_RESOLVES_TO_A_CEDAR_HUB"

        # Does the CHILD's own name point at one parent and not the other? If it
        # does, the parent it does NOT point at is as likely a mis-filing as an
        # ownership fact - `ALEUT FACILITIES SUPPORT SERVICES` declaring NANA
        # Regional Corporation for four years is not obviously a NANA company.
        dc = hubs.distinctive(cn)
        if a == u or b == u:
            # One side IS the firm declaring itself its own parent. The overlap
            # is then trivially total and says nothing about mis-filing.
            ov = "SELF_PARENT_SIDE"
        else:
            ov = ("BOTH" if (dc & da and dc & db) else
                  "PRIOR_PARENT" if dc & da else
                  "LATER_PARENT" if dc & db else "NONE")
        caution = ""
        if ov == "LATER_PARENT":
            caution = ("child name shares a distinctive token with the LATER parent only "
                       f"({'|'.join(sorted(dc & db))}); the prior declaration may be a mis-filing")
        elif ov == "PRIOR_PARENT":
            caution = ("child name shares a distinctive token with the PRIOR parent only "
                       f"({'|'.join(sorted(dc & da))}); the later declaration may be a mis-filing")
        if not (ha or hb or shipped[0]):
            caution = (caution + "; " if caution else "") + \
                "no side resolves to a Cedar hub - outside Cedar's population unless a hub is established"

        year = sb[0]
        hit = deal_hit(idx, traps, cn, na, nb, year)
        cands.append({
            "child_uei": u, "child_name": cn,
            "child_shipped_tribe_id": shipped[0], "child_shipped_name": shipped[1],
            "prior_parent_uei": a, "prior_parent_name": na,
            "prior_first_fy": sa[0], "prior_last_fy": sa[1], "prior_rows": sa[2],
            "prior_hubs": "|".join(sorted(ha)),
            "later_parent_uei": b, "later_parent_name": nb,
            "later_first_fy": sb[0], "later_last_fy": sb[1], "later_rows": sb[2],
            "later_hubs": "|".join(sorted(hb)),
            "transition_between_fy": f"{sa[1]}->{sb[0]}",
            "child_prime_obligations_usd_in_runs": round(sa[3] + sb[3], 2),
            "direction": direction,
            "native_side_present": "1" if (ha or hb or shipped[0]) else "0",
            "child_name_token_overlap": ov,
            "interpretation_caution": caution,
            "deal_ledger_match": hit,
            "announced_status": "IN_CEDAR_DEAL_LEDGER" if hit else "NOT_IN_CEDAR_DEAL_LEDGER",
            "evidence_note": (
                f"prime_contracts.csv awardee_uei={u}: parent_uei={a} FY{sa[0]}-{sa[1]} "
                f"({sa[2]} rows), parent_uei={b} FY{sb[0]}-{sb[1]} ({sb[2]} rows)"
            ),
        })

    rev = reverse_check(series, cname, pname)
    cands.sort(key=lambda r: -r["child_prime_obligations_usd_in_runs"])
    rejs.sort(key=lambda r: (r["refusal"], r["child_name"]))
    return cands, rejs, rev, {
        "prime_rows_scanned": total_rows,
        "distinct_awardee_uei": len(series),
        "parent_uei_nan_rows": nan_rows,
        "parent_uei_nan_usd": round(nan_usd, 2),
    }


def invariants(cands, rejs, rev, extra):
    by_ref = collections.Counter(r["refusal"] for r in rejs)
    by_dir = collections.Counter(r["direction"] for r in cands)
    return {
        "n_candidates": len(cands),
        "n_rejected_intra_family_or_registry": len(rejs),
        "rejections_by_reason": dict(by_ref),
        "candidates_by_direction": dict(by_dir),
        "n_candidates_not_in_deal_ledger": sum(1 for r in cands if not r["deal_ledger_match"]),
        "n_candidates_with_a_native_side": sum(1 for r in cands if r["native_side_present"] == "1"),
        "n_unannounced_with_a_native_side": sum(
            1 for r in cands if r["native_side_present"] == "1" and not r["deal_ledger_match"]),
        "candidate_prime_obligations_usd": round(sum(r["child_prime_obligations_usd_in_runs"] for r in cands), 2),
        "announced_deals_checked": len(rev),
        "announced_deals_by_verdict": dict(collections.Counter(r["reconciliation_verdict"] for r in rev)),
        **extra,
    }


def write_csv(path, cols, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def structural_check(cands, hubs):
    """The invariant that matters: NOTHING intra-family may reach the candidates.

    Re-derived from the emitted rows rather than trusted from the build, so a
    future edit to the classifier that lets a relabelling through is caught here
    and not by a customer.
    """
    bad = []
    for r in cands:
        ha = set(filter(None, r["prior_hubs"].split("|")))
        hb = set(filter(None, r["later_hubs"].split("|")))
        if ha & hb:
            bad.append((r["child_uei"], "hub sets intersect: " + "|".join(sorted(ha & hb))))
        elif nkey(r["prior_parent_name"]) and nkey(r["prior_parent_name"]) == nkey(r["later_parent_name"]):
            bad.append((r["child_uei"], "parent names normalise identically"))
        elif hubs.distinctive(r["prior_parent_name"]) & hubs.distinctive(r["later_parent_name"]):
            bad.append((r["child_uei"], "parent names share a distinctive token"))
        elif r["prior_parent_uei"] == "NAN" or r["later_parent_uei"] == "NAN":
            bad.append((r["child_uei"], "NAN sentinel reached the candidate list"))
    return bad


def main(argv):
    mode = (argv[1] if len(argv) > 1 else "measure").lower()

    if mode == "selftest":
        # Prove the structural check fires. Inject a row that IS a relabelling -
        # two sub-hubs of the same nation - into the candidate list and confirm
        # the invariant rejects it. Nothing is written.
        hubs = Hubs()
        synthetic = [{
            "child_uei": "SYNTHETIC0001", "child_name": "All Native Group",
            "prior_parent_uei": "AAAAAAAAAAAA", "prior_parent_name": "ALL NATIVE GROUP",
            "prior_hubs": "TRBF-WNNBGO-00",
            "later_parent_uei": "BBBBBBBBBBBB", "later_parent_name": "HO-CHUNK, INC.",
            "later_hubs": "TRBF-WNNBGO-00",
        }]
        bad = structural_check(synthetic, hubs)
        if not bad:
            print("SELFTEST FAILED: the invariant did not fire on a synthetic "
                  "intra-family relabelling (All Native Group -> Ho-Chunk Inc).")
            return 1
        print("SELFTEST PASSED: invariant fired ->", bad)
        # And the reverse: a genuine cross-hub change must NOT trip it.
        ok = [{
            "child_uei": "SYNTHETIC0002", "child_name": "Corvid Technologies",
            "prior_parent_uei": "CCCCCCCCCCCC", "prior_parent_name": "CORVID HOLDINGS",
            "prior_hubs": "",
            "later_parent_uei": "DDDDDDDDDDDD", "later_parent_name": "CHICKASAW NATION",
            "later_hubs": "TRBF-CHKSWN-00",
        }]
        if structural_check(ok, hubs):
            print("SELFTEST FAILED: the invariant fired on a legitimate cross-hub change.")
            return 1
        print("SELFTEST PASSED: invariant silent on a legitimate cross-hub change.")
        return 0

    cands, rejs, rev, extra = build()
    hubs = Hubs()
    bad = structural_check(cands, hubs)
    inv = invariants(cands, rejs, rev, extra)

    if mode == "verify":
        fail = False
        if bad:
            fail = True
            print("INVARIANT BREACH - intra-family rows reached the candidate list:")
            for b in bad[:20]:
                print("   ", b)
        if not os.path.exists(OUT_INV):
            print(f"INVARIANT BREACH - {OUT_INV} is missing; run measure first.")
            return 1
        rec = json.load(open(OUT_INV, encoding="utf-8"))
        for k, v in rec.get("invariants", {}).items():
            if inv.get(k) != v:
                fail = True
                print(f"INVARIANT BREACH - {k}: recorded {v}, measured {inv.get(k)}")
        if fail:
            return 1
        print("VERIFY OK -", json.dumps(inv, indent=2, sort_keys=True))
        return 0

    if bad:
        print("REFUSING TO WRITE - intra-family rows reached the candidate list:")
        for b in bad[:20]:
            print("   ", b)
        return 1

    write_csv(OUT_CAND, CAND_COLS, cands)
    write_csv(OUT_REJ, REJ_COLS, rejs)
    write_csv(OUT_REV, REV_COLS, rev)
    os.makedirs(os.path.dirname(OUT_INV), exist_ok=True)
    json.dump({"built_by": "code/1010_ownership_change_from_contracting.py",
               "source": "data/clean/prime_contracts.csv",
               "invariants": inv}, open(OUT_INV, "w", encoding="utf-8"), indent=2, sort_keys=True)
    print(json.dumps(inv, indent=2, sort_keys=True))
    print("wrote", OUT_CAND)
    print("wrote", OUT_REJ)
    print("wrote", OUT_REV)
    print("wrote", OUT_INV)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
