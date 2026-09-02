# lint-ok: class6 - bill_votes.csv has this full-rebuild writer and two in-place
# enrichers, 73_bills_votes_completion.py and
# 890_bill_votes_threshold_and_titles.py. The collision is REAL and is not
# waived away: it is DECLARED, by a person, in cedar_pipeline.KNOWN_ORDERINGS
# (two entries, added 2026-09-02 with the columns each enricher owns named), so
# `enrichers_to_rerun('bill_votes.csv')` now answers instead of returning an
# empty list, and `build.py plan legislation` orders them. The ordering is
# 14 -> 73 -> 890, enrichers LAST. Something also CHECKS the columns survived,
# which is the other half class 6 asks for: `py -3 code/890_... verify` exits 1
# the moment any of its eight columns is missing from the live file. Re-run 73
# then 890 after every run of this script.
"""
14_build_bills_votes.py
Cedar Press Dataset 10 -- Native Bills & Congressional Votes.

Builds, from LOCAL COPIES ONLY (Cedar Press/data/raw/external/votingpatterns/):
  data/clean/native_bills.csv
  data/clean/bill_votes.csv
  data/clean/member_positions.csv

PRIME DIRECTIVE: zero fabrication. Every row traces to a copied source file. No vote count,
bill number, title, or member position is invented. Fields that cannot be sourced are left
blank and the reason is recorded in a *_basis / *_status column.

PRIMARY SOURCES
  Voteview (Lewis, Poole, Rosenthal et al.), voteview.com/data -- HSall_rollcalls.csv,
    HSall_votes.csv, HSall_members.csv.
  Congress.gov API v3 (Library of Congress) -- bill metadata, Congresses 103-119.

Stages (switches at bottom):
  1 inventory
  2 native_bills.csv
  3 bill_votes.csv       (needs member-level tallies from HSall_votes.csv)
  4 member_positions.csv
"""
import json
import re
import sys
import io
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
EXT = ROOT / "data" / "raw" / "external" / "votingpatterns"
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
CLEAN.mkdir(parents=True, exist_ok=True)
BUILD_DATE = "2026-08-05"

# Congress -> the Congress is complete (both sessions adjourned) as of BUILD_DATE.
# 119th Congress runs Jan 2025 - Jan 2027, so it is still in progress on 2026-08-05.
LAST_COMPLETE_CONGRESS = 118

CHAMBER_LETTER = {"House": "H", "Senate": "S"}

# Voteview bill_number prefix -> congress.gov bill type slug
PREFIX_MAP = {
    "HR": "hr", "S": "s",
    "HRES": "hres", "SRES": "sres",
    "HJRES": "hjres", "SJRES": "sjres",
    "HCONRES": "hconres", "SCONRES": "sconres",
}
HOUSE_TYPES = {"hr", "hres", "hjres", "hconres"}
SENATE_TYPES = {"s", "sres", "sjres", "sconres"}

# Voteview cast codes. 1 and 6 are votes actually cast and are what Voteview's published
# yea_count / nay_count reflect; 2-5 are paired / announced positions (not in the official
# tally); 7-8 present; 9 not voting; 0 not a member of the chamber at the time.
CAST_DETAIL = {
    1: "Yea", 2: "Paired Yea", 3: "Announced Yea",
    4: "Announced Nay", 5: "Paired Nay", 6: "Nay",
    7: "Present", 8: "Present",
    9: "Not Voting",
}
CAST_SIMPLE = {
    1: "Yea", 2: "Yea", 3: "Yea",
    4: "Nay", 5: "Nay", 6: "Nay",
    7: "Present", 8: "Present",
    9: "Not Voting",
}


def log(*a):
    print(*a, flush=True)


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def parse_billnum(raw):
    """Voteview bill_number string -> (type_slug, number, recognized_flag).
    Never guesses: an unrecognized alpha prefix is kept verbatim, lowercased, and flagged 0."""
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return ("", "", np.nan)
    s = re.sub(r"[^A-Za-z0-9]", "", str(raw)).upper()
    if not s:
        return ("", "", np.nan)
    m = re.match(r"^([A-Z]+)(\d+)$", s)
    if not m:
        return ("", "", 0)
    pre, num = m.group(1), m.group(2)
    if pre in PREFIX_MAP:
        return (PREFIX_MAP[pre], str(int(num)), 1)
    return (pre.lower(), str(int(num)), 0)


def make_bill_id(congress, type_slug, number):
    if not type_slug or number in ("", None):
        return ""
    return f"{int(congress)}-{type_slug}-{number}"


def origin_chamber_from_type(t):
    if t in HOUSE_TYPES:
        return "House"
    if t in SENATE_TYPES:
        return "Senate"
    # Structural inference only, for Voteview prefixes we do not resolve to a congress.gov
    # type: an "h"-prefixed measure originates in the House, an "s"-prefixed one in the
    # Senate, and treaty documents are Senate-only under Art. II sec. 2. The bill's identity
    # is still flagged unresolved via bill_number_prefix_recognized = 0.
    if isinstance(t, str) and t:
        if t.startswith("treatydoc"):
            return "Senate"
        if t.startswith("h"):
            return "House"
        if t.startswith("s"):
            return "Senate"
    return ""


def vote_id_of(chamber, congress, rollnumber):
    return f"{CHAMBER_LETTER.get(chamber, '?')}{int(congress):03d}-{int(rollnumber):04d}"


# --------------------------------------------------------------------------------------
# STAGE 1: inventory
# --------------------------------------------------------------------------------------
def stage1_inventory():
    log("=" * 78)
    log("STAGE 1 -- INVENTORY OF LOCAL COPIES")
    log("=" * 78)
    inv = []
    for f in sorted(EXT.glob("*.csv")):
        if f.name == "SOURCE_MANIFEST.csv":
            continue
        if f.name == "HSall_votes.csv":
            log(f"{f.name}: 26,262,296 physical lines (not loaded here; streamed in stage 3)")
            inv.append({"file": f.name, "rows": 26262296, "note": "streamed"})
            continue
        d = pd.read_csv(f, low_memory=False)
        cong = ""
        if "congress" in d.columns:
            cong = f"{int(d.congress.min())}-{int(d.congress.max())} (n={d.congress.nunique()})"
        cham = ""
        if "chamber" in d.columns:
            cham = ", ".join(f"{k}={v}" for k, v in d.chamber.value_counts().items())
        log(f"\n{f.name}")
        log(f"   rows={len(d):,} cols={len(d.columns)}")
        if cong:
            log(f"   congress: {cong}")
        if cham:
            log(f"   chamber:  {cham}")
        log(f"   vars: {', '.join(d.columns)}")
        inv.append({"file": f.name, "rows": len(d), "congress": cong, "chamber": cham})
    return inv


# --------------------------------------------------------------------------------------
# roll-call universe
# --------------------------------------------------------------------------------------
def build_rollcall_universe():
    """Union of every tribal-classified roll call across the five classification files.
    Returns a frame keyed (chamber, congress, rollnumber) with classification provenance."""
    t = pd.read_csv(EXT / "rollcalls_tribal.csv", low_memory=False)             # House, pro-tribal
    a = pd.read_csv(EXT / "rollcalls_all_tribal_classified.csv", low_memory=False)  # House, pro + proc-opp
    an = pd.read_csv(EXT / "rollcalls_anti_tribal.csv", low_memory=False)       # House, anti
    ex = pd.read_csv(EXT / "anti_tribal_votes_expanded.csv", low_memory=False)  # House, anti expansion
    se = pd.read_csv(EXT / "rollcalls_senate_tribal.csv", low_memory=False)     # Senate

    adj = pd.read_csv(EXT / "tribal_votes_adjudicated.csv", low_memory=False)

    recs = {}

    def put(chamber, congress, roll, **kw):
        k = (chamber, int(congress), int(roll))
        r = recs.setdefault(k, {"chamber": chamber, "congress": int(congress), "rollnumber": int(roll),
                                "in_pro_tribal": 0, "in_all_classified": 0, "in_anti_tribal": 0,
                                "in_anti_expanded": 0, "in_senate_tribal": 0,
                                "vote_type": "", "pro_tribal_is_yea": np.nan,
                                "direction_source": "", "classification_source": "",
                                "classification_kappa": "",
                                "anti_tribal_is_yea": "", "anti_tribal_category": "",
                                "anti_tribal_direction_method": "",
                                "direction_circularity_flag": 0})
        r.update({k2: v for k2, v in kw.items() if v is not None})
        return r

    for _, r in a.iterrows():
        rr = put("House", r.congress, r.rollnumber, in_all_classified=1)
        rr["vote_type"] = r.get("vote_type", "")
    for _, r in t.iterrows():
        rr = put("House", r.congress, r.rollnumber, in_pro_tribal=1)
        rr["vote_type"] = rr["vote_type"] or "pro_tribal"
    for _, r in an.iterrows():
        put("House", r.congress, r.rollnumber, in_anti_tribal=1)
    for _, r in ex.iterrows():
        rr = put("House", r.congress, r.rollnumber, in_anti_expanded=1)
        rr["vote_type"] = rr["vote_type"] or "anti_tribal_expansion"
    for _, r in se.iterrows():
        rr = put("Senate", r.congress, r.rollnumber, in_senate_tribal=1)
        rr["vote_type"] = rr["vote_type"] or "senate_tribal"
        if pd.notna(r.get("pro_tribal_direction")):
            rr["pro_tribal_is_yea"] = float(r["pro_tribal_direction"])
            rr["direction_source"] = "senate_inherit_from_house_adjudicated_by_bill"
        else:
            rr["direction_source"] = "unresolved_needs_hand_coding"

    # House pro-tribal direction from the two-coder adjudicated file (kappa = 0.952)
    adj_map = {(int(r.congress), int(r.rollnumber)): r for _, r in adj.iterrows()}
    for k, rr in recs.items():
        if rr["chamber"] != "House":
            continue
        key = (rr["congress"], rr["rollnumber"])
        if key in adj_map:
            rr["pro_tribal_is_yea"] = float(adj_map[key]["pro_tribal_is_yea_final"])
            rr["direction_source"] = "two_coder_adjudicated:" + str(adj_map[key]["adjudication_method"])

    # Anti-tribal direction. IMPORTANT INTEGRITY NOTE, carried into the output:
    # anti_tribal_is_yea in these upstream files was assigned from the OBSERVED PARTISAN
    # VOTING PATTERN (R yea rate minus D yea rate > 0.15 => yea is the anti-tribal side),
    # per 41_expand_anti_tribal.py. That makes it CIRCULAR with respect to any party-margin
    # outcome. It is carried here as a labeled field and is deliberately NOT folded into
    # republican_pro_tribal_share.
    for _, r in an.iterrows():
        rr = recs[("House", int(r.congress), int(r.rollnumber))]
        rr["anti_tribal_is_yea"] = r.get("anti_tribal_is_yea")
        rr["anti_tribal_category"] = r.get("anti_tribal_category")
        rr["anti_tribal_direction_method"] = "rule_based_31_classify_anti_tribal_votes"
    for _, r in ex.iterrows():
        rr = recs[("House", int(r.congress), int(r.rollnumber))]
        if rr["anti_tribal_is_yea"] in ("", None) or pd.isna(rr["anti_tribal_is_yea"]):
            rr["anti_tribal_is_yea"] = r.get("anti_tribal_is_yea")
            rr["anti_tribal_category"] = r.get("anti_tribal_category")
        rr["anti_tribal_direction_method"] = str(r.get("direction_method", ""))
        rr["direction_circularity_flag"] = 1   # partisan-pattern-derived direction

    # classification_source (controlled vocabulary) + documented kappa
    for k, rr in recs.items():
        if rr["chamber"] == "Senate":
            rr["classification_source"] = "single_coded_keyword_rule"
            rr["classification_kappa"] = ""
        elif rr["in_pro_tribal"]:
            rr["classification_source"] = "two_coder_adjudicated"
            rr["classification_kappa"] = "0.952"
        elif rr["in_anti_expanded"] and not rr["in_anti_tribal"]:
            rr["classification_source"] = "single_coded_8strategy_expansion"
            rr["classification_kappa"] = ""
        elif rr["in_anti_tribal"]:
            rr["classification_source"] = "two_coder_zero_overlap_adjudicated"
            rr["classification_kappa"] = "-1.000 (not meaningful: disjoint coder search strategies)"
        else:
            rr["classification_source"] = "single_coded_keyword_rule"
            rr["classification_kappa"] = ""

    for k, rr in recs.items():
        if not rr["direction_source"]:
            rr["direction_source"] = "no_direction_coded"

    u = pd.DataFrame(list(recs.values()))
    u["vote_id"] = [vote_id_of(c, g, r) for c, g, r in zip(u.chamber, u.congress, u.rollnumber)]
    return u


# --------------------------------------------------------------------------------------
# STAGE 3 helper: member-level tallies from HSall_votes.csv
# --------------------------------------------------------------------------------------
PRESIDENT_ICPSR = set()


def tally_votes(universe, members):
    """Stream HSall_votes.csv, keep only rows for roll calls in `universe`, return
    (tally frame, member-level long frame)."""
    cache = EXT / "_hsall_votes_tribal_subset.csv"
    keys = set(zip(universe.chamber, universe.congress, universe.rollnumber))
    if cache.exists():
        v = pd.read_csv(cache, low_memory=False)
        log(f"  using cached extract {cache.name}: {len(v):,} member-vote rows")
    else:
        congresses = set(universe.congress)
        keep = []
        n_read = 0
        reader = pd.read_csv(EXT / "HSall_votes.csv",
                             usecols=["congress", "chamber", "rollnumber", "icpsr", "cast_code"],
                             chunksize=4_000_000, low_memory=False)
        for i, ch in enumerate(reader):
            n_read += len(ch)
            ch = ch[ch.congress.isin(congresses)]
            if len(ch):
                m = [(c, g, r) in keys for c, g, r in zip(ch.chamber, ch.congress, ch.rollnumber)]
                ch = ch[m]
                if len(ch):
                    keep.append(ch)
            log(f"    chunk {i+1}: cumulative read {n_read:,}; kept so far "
                f"{sum(len(x) for x in keep):,}")
        v = pd.concat(keep, ignore_index=True)
        v.to_csv(cache, index=False)
        log(f"  cached member-vote extract -> {cache.name}")
    log(f"  member-vote rows for tribal roll calls: {len(v):,}")

    v = v[v.cast_code.notna()].copy()
    v["cast_code"] = v.cast_code.astype(int)
    v = v[v.cast_code != 0].copy()          # 0 = not a member of the chamber at the time

    # Voteview records the PRESIDENT's announced position in the votes file under the voting
    # chamber's label. It is not a member vote and is excluded from official tallies. Drop by
    # the exact president ICPSR set (NOT by an icpsr>=99000 rule: Thurmond 99369, Deal 99342,
    # Forbes 99542 and Goode 99767 are real members with high ICPSR numbers).
    pres_icpsr = set(PRESIDENT_ICPSR)
    n_pres = int(v.icpsr.isin(pres_icpsr).sum())
    v = v[~v.icpsr.isin(pres_icpsr)].copy()
    log(f"  dropped {n_pres:,} presidential position rows (not member votes)")
    v["position"] = v.cast_code.map(CAST_DETAIL)
    v["position_simple"] = v.cast_code.map(CAST_SIMPLE)
    v = v.merge(members, on=["congress", "chamber", "icpsr"], how="left")

    v["party_grp"] = np.where(v.party_code == 100, "D",
                       np.where(v.party_code == 200, "R", "I"))
    v.loc[v.party_code.isna(), "party_grp"] = "U"   # unmatched to member roster

    v["vote_id"] = [vote_id_of(c, g, r) for c, g, r in zip(v.chamber, v.congress, v.rollnumber)]

    # ---- tallies. `yea`/`nay` use cast codes 1/6 only, i.e. votes actually cast, which is
    # what the official roll-call result and Voteview's published counts reflect.
    tot = v.pivot_table(index="vote_id", columns="position", values="icpsr",
                        aggfunc="count", fill_value=0)
    for c in ["Yea", "Nay", "Present", "Not Voting", "Paired Yea", "Announced Yea",
              "Paired Nay", "Announced Nay"]:
        if c not in tot.columns:
            tot[c] = 0
    tot["yea"] = tot["Yea"]
    tot["nay"] = tot["Nay"]
    tot["present"] = tot["Present"]
    tot["not_voting"] = tot["Not Voting"]
    tot["yea_paired_announced"] = tot["Paired Yea"] + tot["Announced Yea"]
    tot["nay_paired_announced"] = tot["Paired Nay"] + tot["Announced Nay"]
    tot = tot[["yea", "nay", "present", "not_voting",
               "yea_paired_announced", "nay_paired_announced"]]

    pv = v[v.position.isin(["Yea", "Nay"])]
    pb = pv.pivot_table(index="vote_id", columns=["party_grp", "position"], values="icpsr",
                        aggfunc="count", fill_value=0)
    pb.columns = [f"{a}_{b.lower()}" for a, b in pb.columns]
    for c in ["D_yea", "D_nay", "R_yea", "R_nay", "I_yea", "I_nay", "U_yea", "U_nay"]:
        if c not in pb.columns:
            pb[c] = 0
    pb = pb[["D_yea", "D_nay", "R_yea", "R_nay", "I_yea", "I_nay", "U_yea", "U_nay"]]

    tally = tot.join(pb, how="outer").fillna(0).astype(int).reset_index()
    return tally, v


# --------------------------------------------------------------------------------------
# bill_scope ruling
# --------------------------------------------------------------------------------------
def build_scope_ruler():
    sp = pd.read_csv(SPINE / "cedar_entity_spine.csv", low_memory=False)
    names = set()
    for col in ["canonical_name"]:
        names |= set(sp[col].dropna().astype(str))
    for al in sp["aliases"].dropna().astype(str):
        for x in al.split("|"):
            x = x.strip()
            if x:
                names.add(x)
    # Drop names too short or too generic to be safe evidence of a tribe-specific bill.
    GENERIC = {"indian", "indians", "tribe", "tribes", "tribal", "nation", "pueblo", "band",
               "community", "village", "reservation", "native", "alaska", "hawaiian"}
    clean = []
    for n in names:
        if len(n) < 8:
            continue
        if n.strip().lower() in GENERIC:
            continue
        clean.append(n)
    clean.sort(key=len, reverse=True)
    pats = [(n, re.compile(r"\b" + re.escape(n) + r"\b", re.I)) for n in clean]

    DESIG = [
        ("Rancheria", re.compile(r"\bRancheria\b", re.I)),
        ("Pueblo of X", re.compile(r"\bPueblo of\s+[A-Z]", re.I)),
        ("Confederated Tribes", re.compile(r"\bConfederated\s+(Tribes|Salish|Bands)\b", re.I)),
        ("Band of", re.compile(r"\bBand of\b", re.I)),
        ("Indian Colony", re.compile(r"\bIndian Colony\b", re.I)),
    ]

    def rule(title):
        if not isinstance(title, str) or not title.strip():
            return ("", "no_title_available")
        for n, p in pats:
            if p.search(title):
                return ("tribe-specific", f"spine_name_match:{n}")
        for lab, p in DESIG:
            if p.search(title):
                return ("tribe-specific", f"designator_pattern:{lab}")
        return ("general", "no_specific_entity_matched")

    log(f"  scope ruler: {len(pats)} spine names, {len(DESIG)} designator patterns")
    return rule


# --------------------------------------------------------------------------------------
# outcome ruling
# --------------------------------------------------------------------------------------
RE_ENACT = re.compile(r"became (public|private) law|public law no|signed by president", re.I)
RE_VETO = re.compile(r"\bveto\b|vetoed", re.I)
RE_ONECH = re.compile(r"passed (house|senate)|agreed to in (house|senate)|"
                      r"passed/agreed to in (house|senate)|received in the (senate|house)|"
                      r"presented to president|resolving differences|held at the desk", re.I)
RE_COMMITTEE = re.compile(r"referred to|committee|introduced in|sponsor introductory remarks|"
                          r"placed on .*calendar|read twice", re.I)


def rule_outcome(latest_action, congress, final_status):
    la = latest_action if isinstance(latest_action, str) else ""
    if RE_ENACT.search(la):
        return ("enacted", "latest_action_text")
    if RE_VETO.search(la):
        return ("vetoed", "latest_action_text")
    if RE_ONECH.search(la):
        return ("passed-one-chamber", "latest_action_text")
    if la and RE_COMMITTEE.search(la):
        if int(congress) > LAST_COMPLETE_CONGRESS:
            return ("pending", f"latest_action_text; congress {int(congress)} still in session on {BUILD_DATE}")
        return ("died-in-committee", "latest_action_text")
    # fall back to the upstream classified status
    fs = str(final_status) if final_status == final_status else ""
    if fs == "enacted":
        return ("enacted", "tribal_bill_intros.final_status")
    if fs == "died_in_committee":
        return ("died-in-committee", "tribal_bill_intros.final_status")
    if fs == "reached_floor_not_enacted":
        return ("passed-one-chamber", "tribal_bill_intros.final_status")
    return ("", "no_action_record_available")


# --------------------------------------------------------------------------------------
# STAGE 2: native_bills.csv
# --------------------------------------------------------------------------------------
def stage2_bills(universe, rollcalls_hs):
    log("=" * 78)
    log("STAGE 2 -- native_bills.csv")
    log("=" * 78)

    ti = pd.read_csv(EXT / "tribal_bill_intros.csv", low_memory=False)
    ai = pd.read_csv(EXT / "all_bill_intros.csv", low_memory=False)
    log(f"  tribal_bill_intros: {len(ti):,}   all_bill_intros: {len(ai):,}")

    ai["bill_id"] = [make_bill_id(c, str(t).lower(), str(int(n)))
                     for c, t, n in zip(ai.congress, ai.bill_type, ai.bill_number)]
    ai_idx = ai.drop_duplicates("bill_id").set_index("bill_id")

    ti["bill_id"] = [make_bill_id(c, str(t).lower(), str(int(n)))
                     for c, t, n in zip(ti.congress, ti.bill_type, ti.bill_number)]
    ti = ti.drop_duplicates("bill_id")
    log(f"  tribal_bill_intros unique bill_id: {len(ti):,}")

    rows = {}

    # ---- source A: Congress.gov tribal-classified introductions (103-119)
    for _, r in ti.iterrows():
        bid = r.bill_id
        la_txt, la_date = "", ""
        if bid in ai_idx.index:
            la_txt = ai_idx.at[bid, "latest_action_text"]
            la_date = ai_idx.at[bid, "latest_action_date"]
        # inclusion basis: PASS 1 = CRS-assigned policyArea "Native Americans" (Congress.gov,
        # external authority); PASS 2 = single-pass keyword rule on the title.
        pa_native = (isinstance(r.policy_area, str)
                     and r.policy_area.strip().lower() == "native americans")
        if str(r.direction_source).startswith("voteview_inherit"):
            cs, kap = "two_coder_adjudicated_inherited_from_rollcall", "0.952"
        elif pa_native:
            cs, kap = "congress_gov_policy_area_native_americans", ""
        else:
            cs, kap = "single_coded_keyword_rule_on_title", ""
        rows[bid] = {
            "bill_id": bid, "congress": int(r.congress),
            "chamber": origin_chamber_from_type(str(r.bill_type).lower()),
            "bill_type": str(r.bill_type).lower(), "number": str(int(r.bill_number)),
            "title": r.title if isinstance(r.title, str) else "",
            "policy_area": r.policy_area if isinstance(r.policy_area, str) else "",
            "sponsor": r.sponsor_name if isinstance(r.sponsor_name, str) else "",
            "sponsor_bioguide_id": r.sponsor_bioguide_id if isinstance(r.sponsor_bioguide_id, str) else "",
            "introduced_date": r.introduced_date if isinstance(r.introduced_date, str) else "",
            "latest_action": la_txt if isinstance(la_txt, str) else "",
            "latest_action_date": la_date if isinstance(la_date, str) else "",
            "final_status_upstream": r.final_status,
            "cosponsor_count": r.cosponsor_count,
            "record_basis": "congress_api_bill_metadata",
            "classification_source": cs, "classification_kappa": kap,
            "source_file": "tribal_bill_intros.csv",
        }

    # ---- source B: bills carrying a tribal roll call but absent from source A
    rc = rollcalls_hs.copy()
    rc["key"] = list(zip(rc.chamber, rc.congress, rc.rollnumber))
    ukeys = set(zip(universe.chamber, universe.congress, universe.rollnumber))
    rc = rc[[k in ukeys for k in rc.key]].copy()
    parsed = [parse_billnum(b) for b in rc.bill_number]
    rc["bt"] = [p[0] for p in parsed]
    rc["bnum"] = [p[1] for p in parsed]
    rc["prefix_recognized"] = [p[2] for p in parsed]
    rc["bill_id"] = [make_bill_id(c, t, n) if t and n else ""
                     for c, t, n in zip(rc.congress, rc.bt, rc.bnum)]

    n_new = 0
    for bid, grp in rc[rc.bill_id != ""].groupby("bill_id"):
        if bid in rows:
            continue
        g0 = grp.iloc[0]
        title, pa, spons, intro, la_txt, la_date, fs = "", "", "", "", "", "", ""
        basis = "voteview_rollcall_only"
        if bid in ai_idx.index:
            a = ai_idx.loc[bid]
            title = a["title"] if isinstance(a["title"], str) else ""
            pa = a["policy_area"] if isinstance(a["policy_area"], str) else ""
            spons = a["sponsor_name"] if isinstance(a["sponsor_name"], str) else ""
            intro = a["introduced_date"] if isinstance(a["introduced_date"], str) else ""
            la_txt = a["latest_action_text"] if isinstance(a["latest_action_text"], str) else ""
            la_date = a["latest_action_date"] if isinstance(a["latest_action_date"], str) else ""
            basis = "voteview_rollcall + congress_api_bill_metadata"
        rows[bid] = {
            "bill_id": bid, "congress": int(g0.congress),
            "chamber": origin_chamber_from_type(g0.bt),
            "bill_type": g0.bt, "number": g0.bnum,
            "title": title, "policy_area": pa, "sponsor": spons,
            "sponsor_bioguide_id": "",
            "introduced_date": intro, "latest_action": la_txt, "latest_action_date": la_date,
            "final_status_upstream": "", "cosponsor_count": "",
            "record_basis": basis,
            "classification_source": "", "classification_kappa": "",
            "source_file": "HSall_rollcalls.csv (via tribal roll-call classification)",
        }
        n_new += 1
    log(f"  bills added from roll-call universe not present in tribal_bill_intros: {n_new}")

    # classification_source for roll-call-only bills = strongest source among its roll calls
    RANK = {"two_coder_adjudicated": 3, "two_coder_zero_overlap_adjudicated": 2,
            "single_coded_8strategy_expansion": 1, "single_coded_keyword_rule": 0}
    uni = universe.copy()
    uni["key"] = list(zip(uni.chamber, uni.congress, uni.rollnumber))
    cls_by_key = dict(zip(uni.key, uni.classification_source))
    kap_by_key = dict(zip(uni.key, uni.classification_kappa))
    best = {}
    for _, r in rc[rc.bill_id != ""].iterrows():
        cs = cls_by_key.get(r.key, "")
        if not cs:
            continue
        cur = best.get(r.bill_id)
        if cur is None or RANK.get(cs, -1) > RANK.get(cur[0], -1):
            best[r.bill_id] = (cs, kap_by_key.get(r.key, ""))
    for bid, (cs, kap) in best.items():
        if bid in rows and not rows[bid]["classification_source"]:
            rows[bid]["classification_source"] = cs
            rows[bid]["classification_kappa"] = kap

    nb = pd.DataFrame(list(rows.values()))

    # roll-call linkage counts
    rcnt = rc[rc.bill_id != ""].groupby("bill_id").size()
    nb["n_rollcalls"] = nb.bill_id.map(rcnt).fillna(0).astype(int)
    nb["has_rollcall"] = (nb.n_rollcalls > 0).astype(int)

    # bill_scope
    ruler = build_scope_ruler()
    sc = [ruler(t) for t in nb.title]
    nb["bill_scope"] = [x[0] for x in sc]
    nb["bill_scope_basis"] = [x[1] for x in sc]

    # outcome
    oc = [rule_outcome(la, c, fs) for la, c, fs in
          zip(nb.latest_action, nb.congress, nb.final_status_upstream)]
    nb["outcome"] = [x[0] for x in oc]
    nb["outcome_basis"] = [x[1] for x in oc]

    # companion_bill_id: identical normalized title, same congress, opposite chamber.
    def norm_title(t):
        if not isinstance(t, str):
            return ""
        t = t.lower().strip()
        t = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", t))
        return t.strip()

    ai["ntitle"] = [norm_title(t) for t in ai.title]
    ai_valid = ai[(ai.ntitle.str.len() >= 25)]
    comp_idx = {}
    for (cong, nt), grp in ai_valid.groupby(["congress", "ntitle"]):
        comp_idx[(cong, nt)] = grp
    nb["ntitle"] = [norm_title(t) for t in nb.title]
    comps, comp_basis = [], []
    for _, r in nb.iterrows():
        cid, cb = "", ""
        if r.ntitle and len(r.ntitle) >= 25:
            g = comp_idx.get((r.congress, r.ntitle))
            if g is not None:
                other = g[(g.bill_id != r.bill_id) &
                          (g.bill_type.str.lower().map(origin_chamber_from_type) != r.chamber)]
                if len(other):
                    cid = other.iloc[0].bill_id
                    cb = "identical_normalized_title_same_congress_opposite_chamber"
        comps.append(cid)
        comp_basis.append(cb)
    nb["companion_bill_id"] = comps
    nb["companion_basis"] = comp_basis
    nb["affected_entities"] = ""   # deliberately blank: entity linking is a separate build step
    nb["build_date"] = BUILD_DATE

    order = ["bill_id", "congress", "chamber", "number", "title", "policy_area", "bill_scope",
             "affected_entities", "sponsor", "introduced_date", "latest_action", "outcome",
             "companion_bill_id",
             # provenance / support columns
             "bill_type", "sponsor_bioguide_id", "latest_action_date", "cosponsor_count",
             "n_rollcalls", "has_rollcall", "bill_scope_basis", "outcome_basis",
             "companion_basis", "classification_source", "classification_kappa",
             "record_basis", "source_file", "build_date"]
    nb = nb[order].sort_values(["congress", "bill_type", "number"]).reset_index(drop=True)

    nb.to_csv(CLEAN / "native_bills.csv", index=False)
    log(f"  WROTE native_bills.csv  rows={len(nb):,}")
    log(f"    congress range: {nb.congress.min()}-{nb.congress.max()}")
    log(f"    chamber: {nb.chamber.value_counts().to_dict()}")
    log(f"    bill_scope: {nb.bill_scope.value_counts(dropna=False).to_dict()}")
    log(f"    outcome: {nb.outcome.value_counts(dropna=False).to_dict()}")
    log(f"    classification_source: {nb.classification_source.value_counts(dropna=False).to_dict()}")
    log(f"    with >=1 roll call: {int(nb.has_rollcall.sum()):,}")
    log(f"    companion linked: {(nb.companion_bill_id != '').sum():,}")
    return nb, rc


# --------------------------------------------------------------------------------------
# STAGE 3: bill_votes.csv
# --------------------------------------------------------------------------------------
def stage3_votes(universe, rollcalls_hs, rc_bills, members):
    log("=" * 78)
    log("STAGE 3 -- bill_votes.csv")
    log("=" * 78)

    tally, mv = tally_votes(universe, members)
    tally.to_csv(CLEAN / "_bill_votes_tallies_tmp.csv", index=False)

    hs = rollcalls_hs.copy()
    hs["key"] = list(zip(hs.chamber, hs.congress, hs.rollnumber))
    ukeys = set(zip(universe.chamber, universe.congress, universe.rollnumber))
    hs = hs[[k in ukeys for k in hs.key]].copy()
    hs["vote_id"] = [vote_id_of(c, g, r) for c, g, r in zip(hs.chamber, hs.congress, hs.rollnumber)]

    bid_map = dict(zip(rc_bills.vote_id if "vote_id" in rc_bills.columns else
                       [vote_id_of(c, g, r) for c, g, r in zip(rc_bills.chamber, rc_bills.congress, rc_bills.rollnumber)],
                       rc_bills.bill_id))
    prefix_ok = dict(zip([vote_id_of(c, g, r) for c, g, r in
                          zip(rc_bills.chamber, rc_bills.congress, rc_bills.rollnumber)],
                         rc_bills.prefix_recognized))

    v = universe.merge(
        hs[["vote_id", "date", "vote_question", "vote_result", "vote_desc", "bill_number",
            "yea_count", "nay_count", "dtl_desc"]],
        on="vote_id", how="left")
    v = v.merge(tally, on="vote_id", how="left")

    v["bill_id"] = v.vote_id.map(bid_map).fillna("")
    v["bill_number_prefix_recognized"] = v.vote_id.map(prefix_ok)

    # Structural vehicle type, straight off the bill type. Votes on H.Res./S.Res. vehicles are
    # very often votes on the RULE providing for consideration, or on a motion to recommit --
    # near party-line by construction and not a vote on the tribal measure itself. Flagged, not
    # dropped, so the user can decide.
    bt_of = dict(zip(rc_bills.bill_id, rc_bills.bt))
    def vehicle(bid):
        if not bid:
            return "no_bill_number"
        t = bt_of.get(bid, "")
        if t in {"hr", "s", "hjres", "sjres"}:
            return "bill"
        if t in {"hres", "sres", "hconres", "sconres"}:
            return "resolution_vehicle"
        if t.startswith("treatydoc"):
            return "treaty_document"
        return "unresolved_bill_type"
    v["vehicle_type"] = [vehicle(b) for b in v.bill_id]

    for c in ["yea", "nay", "present", "not_voting", "yea_paired_announced",
              "nay_paired_announced", "D_yea", "D_nay", "R_yea", "R_nay",
              "I_yea", "I_nay", "U_yea", "U_nay"]:
        v[c] = v[c].fillna(0).astype(int)

    # Voteview supplies vote_question / vote_result only for the later Congresses; for the
    # earlier ones only dtl_desc exists. Nothing is invented to fill the gap: the source of
    # each field is recorded, and a purely arithmetic majority_side is offered separately.
    v["question_source"] = np.where(v.vote_question.fillna("").astype(str).str.strip() != "",
                                    "voteview_vote_question", "not_supplied_by_voteview")
    v["result_source"] = np.where(v.vote_result.fillna("").astype(str).str.strip() != "",
                                  "voteview_vote_result", "not_supplied_by_voteview")
    v["vote_description"] = v.vote_desc.fillna("").astype(str)
    blank = v.vote_description.str.strip() == ""
    v.loc[blank, "vote_description"] = v.loc[blank, "dtl_desc"].fillna("").astype(str)
    v["vote_description_source"] = np.where(
        v.vote_desc.fillna("").astype(str).str.strip() != "", "voteview_vote_desc",
        np.where(v.dtl_desc.fillna("").astype(str).str.strip() != "", "voteview_dtl_desc", ""))

    v["margin"] = v.yea - v.nay
    v["majority_side"] = np.where(v.yea > v.nay, "yea",
                          np.where(v.nay > v.yea, "nay", "tie"))
    rden = v.R_yea + v.R_nay
    dden = v.D_yea + v.D_nay
    v["republican_yea_share"] = np.where(rden > 0, v.R_yea / rden, np.nan)
    v["democrat_yea_share"] = np.where(dden > 0, v.D_yea / dden, np.nan)
    v["n_republican_voting"] = rden
    v["n_democrat_voting"] = dden

    # direction-adjusted (pro-tribal) Republican share where direction is coded
    ptiy = pd.to_numeric(v.pro_tribal_is_yea, errors="coerce")
    v["republican_pro_tribal_share"] = np.where(
        ptiy == 1, v.republican_yea_share,
        np.where(ptiy == 0, 1 - v.republican_yea_share, np.nan))

    # cross-check Voteview's own published counts against the member-level recount
    v["voteview_yea_count"] = v.yea_count
    v["voteview_nay_count"] = v.nay_count
    v["tally_matches_voteview"] = ((v.yea == v.yea_count) & (v.nay == v.nay_count)).astype(int)
    log(f"  recount matches Voteview published yea/nay on "
        f"{int(v.tally_matches_voteview.sum()):,}/{len(v):,} roll calls")

    v = v.rename(columns={"vote_question": "question", "vote_result": "result"})
    v["build_date"] = BUILD_DATE

    order = ["vote_id", "bill_id", "chamber", "congress", "rollnumber", "date", "question",
             "result", "yea", "nay", "present", "not_voting",
             "D_yea", "D_nay", "R_yea", "R_nay", "I_yea", "I_nay",
             "margin", "republican_yea_share",
             # support / provenance
             "vehicle_type", "majority_side", "question_source", "result_source",
             "vote_description", "vote_description_source",
             "democrat_yea_share", "republican_pro_tribal_share", "pro_tribal_is_yea",
             "direction_source", "vote_type", "n_republican_voting", "n_democrat_voting",
             "U_yea", "U_nay", "yea_paired_announced", "nay_paired_announced",
             "voteview_yea_count", "voteview_nay_count",
             "tally_matches_voteview", "bill_number", "bill_number_prefix_recognized",
             "anti_tribal_is_yea", "anti_tribal_category",
             "anti_tribal_direction_method", "direction_circularity_flag",
             "classification_source", "classification_kappa", "build_date"]
    v = v[order].sort_values(["congress", "chamber", "rollnumber"]).reset_index(drop=True)
    v.to_csv(CLEAN / "bill_votes.csv", index=False)
    log(f"  WROTE bill_votes.csv  rows={len(v):,}")
    log(f"    chamber: {v.chamber.value_counts().to_dict()}")
    log(f"    congress range: {v.congress.min()}-{v.congress.max()}")
    log(f"    linked to a bill_id: {(v.bill_id != '').sum():,}")
    log(f"    republican_yea_share non-missing: {v.republican_yea_share.notna().sum():,}")
    log(f"    mean republican_yea_share: {v.republican_yea_share.mean():.4f}")
    log(f"    mean democrat_yea_share:   {v.democrat_yea_share.mean():.4f}")
    log(f"    question populated by Voteview: "
        f"{(v.question_source == 'voteview_vote_question').sum():,}/{len(v):,}")
    log(f"    result populated by Voteview:   "
        f"{(v.result_source == 'voteview_vote_result').sum():,}/{len(v):,}")
    log(f"    vote_description populated:     "
        f"{(v.vote_description.str.strip() != '').sum():,}/{len(v):,}")
    log(f"    direction coded (pro_tribal_is_yea non-missing): "
        f"{v.pro_tribal_is_yea.notna().sum():,}/{len(v):,}")
    log(f"    partisan-pattern-derived direction (CIRCULAR for party outcomes): "
        f"{int((v.direction_circularity_flag == 1).sum()):,}")
    log(f"    vehicle_type: {v.vehicle_type.value_counts().to_dict()}")
    return v, mv


# --------------------------------------------------------------------------------------
# STAGE 4: member_positions.csv
# --------------------------------------------------------------------------------------
def stage4_positions(mv, votes):
    log("=" * 78)
    log("STAGE 4 -- member_positions.csv")
    log("=" * 78)
    bid = dict(zip(votes.vote_id, votes.bill_id))
    mp = mv.copy()
    mp["bill_id"] = mp.vote_id.map(bid).fillna("")
    mp["party"] = mp.party_grp.map({"D": "D", "R": "R", "I": "I", "U": ""})
    mp["district"] = mp.district_code
    cos = load_cosponsor_flags()
    if cos is not None:
        key = list(zip(mp.bill_id, mp.bioguide_id.fillna("")))
        mp["cosponsor_flag"] = [1 if k in cos else (0 if k[0] in cos_bills else "")
                                for k in key]
    else:
        mp["cosponsor_flag"] = ""
    mp["build_date"] = BUILD_DATE
    out = mp[["vote_id", "bill_id", "bioguide_id", "icpsr", "party", "party_code",
              "state_abbrev", "district", "position", "cosponsor_flag", "position_simple",
              "chamber", "congress", "rollnumber", "cast_code", "bioname", "build_date"]]
    out = out.sort_values(["congress", "chamber", "rollnumber", "icpsr"]).reset_index(drop=True)
    out.to_csv(CLEAN / "member_positions.csv", index=False)
    log(f"  WROTE member_positions.csv  rows={len(out):,}")
    log(f"    unique votes: {out.vote_id.nunique():,}  unique members: {out.icpsr.nunique():,}")
    log(f"    position: {out.position.value_counts().to_dict()}")
    log(f"    bioguide_id present: {out.bioguide_id.notna().sum():,} "
        f"({100*out.bioguide_id.notna().mean():.1f}%)")
    cf = out.cosponsor_flag.astype(str)
    log(f"    cosponsor_flag: 1={int((cf=='1').sum()):,}  0={int((cf=='0').sum()):,}  "
        f"blank={int((cf=='').sum()):,}")
    return out


cos_bills = set()


def load_cosponsor_flags():
    """Cosponsor sets built by 14_pull_cosponsors.py, if that stage has run."""
    global cos_bills
    f = CLEAN / "_cosponsors.csv"
    if not f.exists():
        log("  cosponsor file not found -- cosponsor_flag left blank (documented in build log)")
        return None
    c = pd.read_csv(f, low_memory=False)
    # cosponsor_flag = 0 only where the API actually answered for that bill (including an
    # honest "zero cosponsors"); bills the API could not serve stay blank, never 0.
    fl = CLEAN / "_cosponsor_fetch_log.csv"
    if fl.exists():
        g = pd.read_csv(fl, low_memory=False)
        cos_bills = set(g.loc[g.status.isin(["ok", "zero_cosponsors_reported"]), "bill_id"])
        log(f"  cosponsor fetch log: {g.status.value_counts().to_dict()}")
    else:
        cos_bills = set(c.bill_id.unique())
    log(f"  cosponsor file: {len(c):,} rows; bills with a usable API answer: {len(cos_bills):,}")
    return set(zip(c.bill_id, c.bioguide_id))


# --------------------------------------------------------------------------------------
def main():
    stage1_inventory()

    log("\nBuilding roll-call universe ...")
    universe = build_rollcall_universe()
    log(f"  unique tribal roll calls: {len(universe):,}  "
        f"{universe.chamber.value_counts().to_dict()}")
    log(f"  congress range: {universe.congress.min()}-{universe.congress.max()}")
    log(f"  classification_source: {universe.classification_source.value_counts().to_dict()}")

    hs = pd.read_csv(EXT / "HSall_rollcalls.csv", low_memory=False)
    mem_all = pd.read_csv(EXT / "HSall_members.csv", low_memory=False,
                          usecols=["congress", "chamber", "icpsr", "state_icpsr", "district_code",
                                   "state_abbrev", "party_code", "bioname", "bioguide_id"])
    global PRESIDENT_ICPSR
    PRESIDENT_ICPSR = set(mem_all.loc[mem_all.chamber == "President", "icpsr"].unique())
    log(f"  president ICPSR codes identified: {len(PRESIDENT_ICPSR)}")
    mem = mem_all[mem_all.chamber != "President"]

    nb, rc_bills = stage2_bills(universe, hs)
    votes, mv = stage3_votes(universe, hs, rc_bills, mem)
    stage4_positions(mv, votes)

    tmp = CLEAN / "_bill_votes_tallies_tmp.csv"
    if tmp.exists():
        tmp.unlink()
    log("\nDONE")


if __name__ == "__main__":
    main()
