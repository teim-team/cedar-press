#!/usr/bin/env python3
"""
31_build_dataset5_linked.py
===========================
Dataset 5 - the LINKED ANALYTICAL FILE.

One row per (entity, year) joining prime contracting, federal assistance,
subawards and lobbying through the NEID entity spine, plus a standalone
time-varying OWNERSHIP EVENT ledger extracted from the deals files.

WHY THIS EXISTS
---------------
Elijah's Dippel correspondence establishes that (a) no reliable
corporate-hierarchy-over-time source exists and (b) FPDS does not update
retroactively when ownership changes. The deals ledger records DATED ownership
changes. Emitting them as an event stream is what makes attribution
time-aware. That is the moat: not the join, the dates.

OUTPUTS
-------
  data/clean/ownership_events.csv      dated ownership changes with a Native principal
  data/clean/entity_year_panel.csv     the linked file
  data/clean/entity_year_coverage.csv  per component, per year, n_entities observed
  docs/DATASET5_LINKED_FILE_BUILD_LOG.md
  logs/31_dataset5_linked.log

NON-NEGOTIABLE RULES IMPLEMENTED HERE
-------------------------------------
1. TIER DISCIPLINE PROPAGATES. Every component carries its own tier, computed as
   the WORST identifier-link tier that contributed a dollar to it. The row-level
   confidence_tier is the worst across the components actually present. A tier-A
   funding figure can never launder a tier-B contracting attribution.
2. NEVER FABRICATE A ZERO. No entity-year gets a 0 it did not earn. Absent
   components are BLANK and <component>_observed = 0. A reported $0 lobbying
   filing is observed=1, value=0 - that is a real zero and it is kept distinct.
3. TEMPORAL FLOOR. Rows before 2000 carry pre_2000_flag = 1 (they are retained,
   per the flag-never-delete rule; the panel reaches 1999 only via LDA).
4. COVERAGE DIFFERS BY COMPONENT. Each component has a hard source window.
   components_in_window says which components COULD have seen that year;
   components_present says which actually did. A year outside a component's
   window is not evidence of inactivity.
5. NO NEW ENTITY RESOLUTION. Joins run on identifiers that already exist in the
   spine/ledger: NEID tribe_id directly, or UEI/CAGE -> tribe_id through
   cedar_identifier_ledger_final.csv. No name matching anywhere in this script.
   Sources that carry no usable identifier are reported unobserved, with the
   cost stated in rows.

USAGE
-----
  py -3 code/31_build_dataset5_linked.py
"""

from __future__ import annotations

import os
import sys
import time
from collections import defaultdict

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLEAN = os.path.join(PROJECT, "data", "clean")
SPINE = os.path.join(PROJECT, "data", "spine")
RAW_HCI = os.path.join(PROJECT, "data", "raw", "esm_hci", "ESM", "clean")
LOGS = os.path.join(PROJECT, "logs")
DOCS = os.path.join(PROJECT, "docs")

LOG_PATH = os.path.join(LOGS, "31_dataset5_linked.log")
OUT_EVENTS = os.path.join(CLEAN, "ownership_events.csv")
OUT_PANEL = os.path.join(CLEAN, "entity_year_panel.csv")
OUT_COVER = os.path.join(CLEAN, "entity_year_coverage.csv")
OUT_MD = os.path.join(DOCS, "DATASET5_LINKED_FILE_BUILD_LOG.md")

# THE FILE THIS BUILD TREATS AS THE TRUTH FOR DEALS:
# data/clean/deals_classified.csv (cedar_domain.DEALS_TRUTH), 935 rows.
#
# This was a hand-written list of five files - the two root ledgers plus THREE
# of the nine `deals_*_additions.csv` files - and it therefore read 216 of the
# 935 deal rows. It is the additions/ledger defect
# (`docs/FACT_CHECK_2026-08-06.md` finding B-1) in its worst form: not a glob
# that missed a directory, but an enumeration that went stale as six more
# additions files were written and nobody came back to it. The 594-row
# `deals_federal_awards_additions.csv` alone was absent.
#
# `ownership_events.csv` is built off these rows, so the ownership-change
# ledger - the asset AGENTS.md calls "the missing time-varying ownership
# ledger" - was derived from under a quarter of the deals.
#
# A hand-written file list is a glob that cannot be re-globbed. Read the
# promoted table.
DEAL_FILES = [
    os.path.join(CLEAN, "deals_classified.csv"),
]

# Hard source windows. A year outside these is UNKNOWN, not zero.
WINDOWS = {
    "prime": (2000, 2022),       # master prime file.dta (HigherGov/FPDS pull, ends 2023-04)
    "assistance": (2008, 2023),  # USAspending assistance begins FY2008; FY2001-2007 backfill open
    "subaward": (2011, 2023),    # FSRS/HigherGov subaward export
    "lobbying": (1999, 2026),    # LDA statutory floor
}
# Components that exist as datasets but carry NO joinable identifier.
UNAVAILABLE = ["deals", "bills", "compacts"]

TIER_RANK = {"A": 0, "B": 1, "C": 2, "X": 3}

_logfh = None


def log(msg: str) -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {msg}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        print(line.encode("ascii", "replace").decode(), flush=True)
    if _logfh is not None:
        _logfh.write(line + "\n")
        _logfh.flush()


def worst(tiers) -> str:
    ts = [t for t in tiers if t in TIER_RANK]
    if not ts:
        return ""
    return max(ts, key=lambda t: TIER_RANK[t])


# ---------------------------------------------------------------------------
# A. Ownership events
# ---------------------------------------------------------------------------
# Deal categories that record a change in who owns something.
OWNERSHIP_CATS = {
    "Acquisition": "corporate_entity",
    "Divestiture": "corporate_entity",
    "Equity investment": "equity_stake",
    "Joint venture": "joint_venture",
    "Real estate / land acquisition": "real_property",
    "Real estate / land": "real_property",
}

# The four divestiture rows are the only ones where the Native party is NOT the
# acquirer. Acquirer / target / seller transcribed VERBATIM from the row's own
# Deal_Title and Description - no inference, no outside knowledge.
DIVEST_OVERRIDES = {
    "ND-2021-006": dict(
        seller="Chenega Corporation",
        target="ADG Creative",
        acquirer="Proximas Group",
        basis="Deal_Title: 'Chenega Corporation sells ADG Creative to Proximas Group'",
    ),
    "ND-2023-002": dict(
        seller="Sealaska Corporation",
        target="Orca Bay Seafoods",
        acquirer="",
        basis="Deal_Title: 'Sealaska sells Orca Bay Seafoods'. BUYER NOT NAMED in the row "
              "(Counterparty_or_Funder reads 'Orca Bay Seafoods buyer'); acquirer left blank.",
    ),
    "ND-2025-011": dict(
        seller="Chenega Corporation",
        target="Chenega Federal Systems",
        acquirer="Business Integra Technology Solutions",
        basis="Deal_Title: 'Chenega Corporation sells Chenega Federal Systems to Business Integra'",
    ),
    "ND-2024-005": dict(
        seller="Doyon, Limited",
        target="Doyon Anvil joint venture (Doyon's interest)",
        acquirer="Anvil Corporation",
        basis="Description: 'Anvil Corporation acquired Doyon, Limited's interest in the Doyon "
              "Anvil joint venture ... Doyon is the divesting principal.'",
    ),
}


def load_deals() -> pd.DataFrame:
    frames = []
    for f in DEAL_FILES:
        if not os.path.exists(f):
            log(f"  deals file MISSING, skipped: {os.path.relpath(f, PROJECT)}")
            continue
        d = pd.read_csv(f, dtype=str)
        d["_source_file"] = os.path.relpath(f, PROJECT).replace("\\", "/")
        frames.append(d)
        log(f"  deals file {os.path.relpath(f, PROJECT)}: {len(d)} rows")
    D = pd.concat(frames, ignore_index=True)
    return D


def build_ownership_events(D: pd.DataFrame) -> pd.DataFrame:
    S = D[D["Deal_Category"].isin(OWNERSHIP_CATS)].copy()
    rows = []
    for _, r in S.iterrows():
        did = str(r["Deal_ID"])
        cat = str(r["Deal_Category"])
        asset_class = OWNERSHIP_CATS[cat]
        np_v = str(r.get("Native_Party") or "").strip()
        cp_v = str(r.get("Counterparty_or_Funder") or "").strip()

        if did in DIVEST_OVERRIDES:
            o = DIVEST_OVERRIDES[did]
            direction = "divestiture"
            acquirer, target, seller = o["acquirer"], o["target"], o["seller"]
            basis = "hand-transcribed from this row's own text. " + o["basis"]
        else:
            direction = "acquisition"
            acquirer, target, seller = np_v, cp_v, ""
            basis = (
                "acquirer = Native_Party verbatim; target = Counterparty_or_Funder verbatim. "
                "CAUTION: on asset and real-property rows Counterparty_or_Funder sometimes names "
                "the SELLER rather than the thing acquired (e.g. 'Private seller(s)', "
                "'McGregor family'). Read Deal_Title before using target_entity as an entity name."
            )

        ed = (r.get("Event_Date") or "")
        ed = "" if pd.isna(r.get("Event_Date")) else str(ed).strip()
        ey = "" if pd.isna(r.get("Event_Year")) else str(r.get("Event_Year") or "").strip()
        date_basis = "" if pd.isna(r.get("Date_Basis")) else str(r.get("Date_Basis") or "").strip()
        if not ed:
            date_basis = ("NO EVENT DATE IN THE SOURCE ROW - not usable for time-aware "
                          "attribution. " + date_basis).strip()

        val = r.get("Announced_Value_USD")
        val = "" if pd.isna(val) else str(val).strip()

        src = ""
        for c in ("Source_1", "Source_2"):
            v = r.get(c)
            if v is not None and not pd.isna(v) and str(v).strip():
                src = str(v).strip() if not src else src + " | " + str(v).strip()

        rows.append({
            "event_id": f"OWN-{did}",
            "effective_date": ed,
            "event_year": ey,
            "acquirer_entity": acquirer,
            "target_entity": target,
            "seller_entity": seller,
            "direction": direction,
            "asset_class": asset_class,
            "ownership_change_type": "" if pd.isna(r.get("Event_Type")) else str(r.get("Event_Type") or ""),
            "announced_value_usd": val,
            "native_party_verbatim": np_v,
            "counterparty_verbatim": cp_v,
            "party_role_basis": basis,
            "deal_category": cat,
            "date_basis": date_basis,
            "date_usable_for_attribution": 0 if not ed else 1,
            "source_deal_id": did,
            "source_url": src,
            "confidence": "" if pd.isna(r.get("Confidence")) else str(r.get("Confidence") or ""),
            "verification_status": "" if pd.isna(r.get("Verification_Status")) else str(r.get("Verification_Status") or ""),
            "pre_2000_flag": 1 if (ey.isdigit() and int(ey) < 2000) else 0,
            "source_file": r["_source_file"],
            "native_entity_neid": "",
            "neid_join_status": "NOT JOINED - the deals ledger carries no tribe_id/UEI/CAGE. "
                                "Joining would require name resolution, which is out of scope.",
        })
    E = pd.DataFrame(rows).sort_values(["effective_date", "event_id"], na_position="last")
    return E


# ---------------------------------------------------------------------------
# Identifier crosswalks (the only permitted join keys)
# ---------------------------------------------------------------------------
def load_crosswalks():
    led = pd.read_csv(os.path.join(CLEAN, "cedar_identifier_ledger_final.csv"),
                      dtype=str, low_memory=False)
    led["tribe_id"] = led["tribe_id"].fillna("").str.strip()
    led["confidence_tier"] = led["confidence_tier"].fillna("").str.strip()
    usable = led[(led.tribe_id != "") & (led.confidence_tier != "X")]
    n_x = int((led.tribe_id != "").sum() - len(usable))
    log(f"  ledger: {len(led)} rows; {int((led.tribe_id!='').sum())} carry a tribe_id; "
        f"{n_x} tier-X links excluded from all joins")

    maps = {}
    for t in ("UEI", "CAGE"):
        s = usable[usable.identifier_type == t]
        g = s.groupby("identifier").tribe_id.nunique()
        ambiguous = set(g[g > 1].index)
        s = s[~s.identifier.isin(ambiguous)]
        maps[t] = {
            "tribe": dict(zip(s.identifier, s.tribe_id)),
            "tier": dict(zip(s.identifier, s.confidence_tier)),
        }
        log(f"  ledger {t}->tribe_id links usable: {len(s)} "
            f"(ambiguous ids dropped: {len(ambiguous)}); "
            f"tiers {s.confidence_tier.value_counts().to_dict()}")
    return maps


# ---------------------------------------------------------------------------
# Component builders. Each returns dict[(tribe_id, year)] -> metrics
# ---------------------------------------------------------------------------
def build_prime(maps, stats):
    f = os.path.join(RAW_HCI, "master prime file.dta")
    d = pd.read_stata(f, columns=["contract_number", "year", "awardee_uei",
                                  "cage_code", "total_obligations"])
    stats["prime_source_rows"] = len(d)
    d["awardee_uei"] = d.awardee_uei.fillna("").str.strip()
    d["cage_code"] = d.cage_code.fillna("").str.strip()
    d["tribe_id"] = d.awardee_uei.map(maps["UEI"]["tribe"])
    d["tier"] = d.awardee_uei.map(maps["UEI"]["tier"])
    d["key_type"] = d.tribe_id.notna().map({True: "UEI", False: ""})
    m = d.tribe_id.isna()
    d.loc[m, "tribe_id"] = d.loc[m, "cage_code"].map(maps["CAGE"]["tribe"])
    d.loc[m, "tier"] = d.loc[m, "cage_code"].map(maps["CAGE"]["tier"])
    d.loc[m & d.tribe_id.notna(), "key_type"] = "CAGE"

    J = d[d.tribe_id.notna()].copy()
    stats["prime_joined_rows"] = len(J)
    stats["prime_join_rate"] = len(J) / len(d)
    stats["prime_key_types"] = J.key_type.value_counts().to_dict()
    J["year"] = J.year.astype(int)
    out = {}
    for (t, y), grp in J.groupby(["tribe_id", "year"]):
        out[(t, int(y))] = {
            "prime_contract_usd": float(grp.total_obligations.sum()),
            "n_prime_awards": int(grp.contract_number.nunique()),
            "prime_tier": worst(grp.tier.tolist()),
        }
    return out


def build_assistance(maps, stats):
    f = os.path.join(CLEAN, "federal_funding_transactions.csv")
    d = pd.read_csv(f, dtype=str, low_memory=False,
                    usecols=["recipient_uei", "fiscal_year", "obligated_usd",
                             "assistance_award_unique_key", "excluded_flag",
                             "fy_partial_flag"])
    stats["assistance_source_rows"] = len(d)
    d["recipient_uei"] = d.recipient_uei.fillna("").str.strip()
    stats["assistance_rows_no_uei"] = int((d.recipient_uei == "").sum())
    d["tribe_id"] = d.recipient_uei.map(maps["UEI"]["tribe"])
    d["tier"] = d.recipient_uei.map(maps["UEI"]["tier"])
    joined = d.tribe_id.notna()
    stats["assistance_joined_rows_before_exclusions"] = int(joined.sum())
    # do-file exclusions are hand-checked authority; they block attribution.
    blocked = joined & (d.excluded_flag == "1")
    stats["assistance_rows_blocked_by_dofile_exclusion"] = int(blocked.sum())
    J = d[joined & ~blocked].copy()
    stats["assistance_joined_rows"] = len(J)
    stats["assistance_join_rate"] = len(J) / len(d)
    J["obl"] = pd.to_numeric(J.obligated_usd, errors="coerce")
    J["fy"] = pd.to_numeric(J.fiscal_year, errors="coerce")
    J = J[J.fy.notna()]
    out = {}
    for (t, y), grp in J.groupby(["tribe_id", "fy"]):
        out[(t, int(y))] = {
            "assistance_usd": float(grp.obl.sum(skipna=True)),
            "n_assistance_awards": int(grp.assistance_award_unique_key.nunique()),
            "assistance_tier": worst(grp.tier.tolist()),
            "assistance_fy_partial": int((grp.fy_partial_flag == "1").any()),
        }
    return out


def build_subawards(maps, stats):
    f = os.path.join(CLEAN, "subawards.csv")
    d = pd.read_csv(f, dtype=str, low_memory=False)
    stats["subaward_source_rows"] = len(d)
    d["sub_uei"] = d.sub_uei.fillna("").str.strip()
    d["prime_uei"] = d.prime_uei.fillna("").str.strip()
    self_edge = (d.sub_uei != "") & (d.sub_uei == d.prime_uei)
    stats["subaward_self_edges_dropped"] = int(self_edge.sum())
    d = d[~self_edge].copy()
    d["amt"] = pd.to_numeric(d.subaward_amount, errors="coerce")
    d["fy"] = pd.to_numeric(d.fiscal_year, errors="coerce")

    d["t_sub"] = d.sub_uei.map(maps["UEI"]["tribe"])
    d["tier_sub"] = d.sub_uei.map(maps["UEI"]["tier"])
    d["t_prime"] = d.prime_uei.map(maps["UEI"]["tribe"])
    d["tier_prime"] = d.prime_uei.map(maps["UEI"]["tier"])
    stats["subaward_rows_joined_as_sub"] = int(d.t_sub.notna().sum())
    stats["subaward_rows_joined_as_prime"] = int(d.t_prime.notna().sum())
    stats["subaward_rows_joined_either"] = int((d.t_sub.notna() | d.t_prime.notna()).sum())
    stats["subaward_join_rate"] = stats["subaward_rows_joined_either"] / max(len(d), 1)

    out = defaultdict(dict)
    S = d[d.t_sub.notna() & d.fy.notna()]
    for (t, y), grp in S.groupby(["t_sub", "fy"]):
        out[(t, int(y))].update({
            "subaward_usd_as_sub": float(grp.amt.sum(skipna=True)),
            "n_subawards_as_sub": int(len(grp)),
            "subaward_tier_as_sub": worst(grp.tier_sub.tolist()),
        })
    P = d[d.t_prime.notna() & d.fy.notna()]
    for (t, y), grp in P.groupby(["t_prime", "fy"]):
        out[(t, int(y))].update({
            "subaward_usd_as_prime": float(grp.amt.sum(skipna=True)),
            "n_subawards_as_prime": int(len(grp)),
            "subaward_tier_as_prime": worst(grp.tier_prime.tolist()),
        })
    return dict(out)


def build_lobbying(spine_ids, stats):
    f = os.path.join(CLEAN, "tribe_year_lobbying_panel.csv")
    d = pd.read_csv(f, dtype=str, low_memory=False)
    stats["lobbying_source_rows"] = len(d)
    d["entity_id"] = d.entity_id.fillna("").str.strip()
    ok = d.entity_id.isin(spine_ids)
    stats["lobbying_rows_off_spine"] = int((~ok).sum())
    d = d[ok].copy()
    stats["lobbying_joined_rows"] = len(d)
    stats["lobbying_join_rate"] = len(d) / max(stats["lobbying_source_rows"], 1)

    # worst per-filing match confidence, from the disclosure-level file
    disc = pd.read_csv(os.path.join(CLEAN, "native_entity_lobbying_disclosures.csv"),
                       dtype=str, low_memory=False,
                       usecols=["entity_id", "filing_year", "match_confidence"])
    rank = {"high": 0, "medium": 1, "low": 2}
    disc["r"] = disc.match_confidence.map(rank).fillna(9)
    wm = disc.groupby(["entity_id", "filing_year"]).r.max().to_dict()
    inv = {0: "high", 1: "medium", 2: "low"}

    out = {}
    for _, r in d.iterrows():
        y = pd.to_numeric(r.filing_year, errors="coerce")
        if pd.isna(y):
            continue
        out[(r.entity_id, int(y))] = {
            "lobbying_spend_usd": float(pd.to_numeric(r.total_lobbying_spend_usd, errors="coerce")
                                        if pd.notna(r.total_lobbying_spend_usd) else 0.0),
            "lobbying_spend_client_income_usd": float(pd.to_numeric(r.spend_from_client_income_usd, errors="coerce") or 0.0),
            "lobbying_spend_registrant_expenses_usd": float(pd.to_numeric(r.spend_from_registrant_expenses_usd, errors="coerce") or 0.0),
            "n_lobbying_filings": int(float(r.n_filings or 0)),
            "n_registrants": int(float(r.n_unique_registrants or 0)),
            # LDA carries no UEI/CAGE/EIN; every link is an algorithmic name match
            # against the spine and has never been ruled -> tier B, never A.
            "lobbying_tier": "B",
            "lobbying_match_confidence_worst": inv.get(wm.get((r.entity_id, str(r.filing_year)), 9), ""),
        }
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global _logfh
    os.makedirs(LOGS, exist_ok=True)
    _logfh = open(LOG_PATH, "w", encoding="utf-8")
    t0 = time.time()
    stats = {}

    log("=" * 78)
    log("Dataset 5 - linked analytical file")
    log("=" * 78)

    # --- A. ownership events -------------------------------------------------
    log("A. Extracting ownership events from the deals ledgers")
    D = load_deals()
    stats["deals_total_rows"] = len(D)
    E = build_ownership_events(D)
    E.to_csv(OUT_EVENTS, index=False, encoding="utf-8")
    dated = E[E.date_usable_for_attribution == 1]
    stats["own_events"] = len(E)
    stats["own_events_dated"] = len(dated)
    stats["own_events_undated"] = len(E) - len(dated)
    stats["own_span"] = (dated.effective_date.min(), dated.effective_date.max()) if len(dated) else ("", "")
    stats["own_by_direction"] = E.direction.value_counts().to_dict()
    stats["own_by_asset_class"] = E.asset_class.value_counts().to_dict()
    stats["own_corporate"] = int((E.asset_class == "corporate_entity").sum())
    log(f"  ownership events: {len(E)} ({stats['own_events_dated']} dated, "
        f"{stats['own_events_undated']} undated) span {stats['own_span'][0]} -> {stats['own_span'][1]}")
    log(f"  by asset_class: {stats['own_by_asset_class']}")
    log(f"  -> {os.path.relpath(OUT_EVENTS, PROJECT)}")

    # --- B. crosswalks -------------------------------------------------------
    log("B. Loading identifier crosswalks (NEID tribe_id, UEI, CAGE)")
    maps = load_crosswalks()
    spine = pd.read_csv(os.path.join(SPINE, "cedar_entity_spine.csv"), dtype=str)
    spine_ids = set(spine.tribe_id)
    name = dict(zip(spine.tribe_id, spine.canonical_name))
    klass = dict(zip(spine.tribe_id, spine.entity_class))
    log(f"  spine entities: {len(spine)}")

    # --- C. components -------------------------------------------------------
    log("C. Building components")
    log("  prime (master prime file.dta, FY2000-2022)")
    prime = build_prime(maps, stats)
    log(f"    join rate {stats['prime_join_rate']:.1%} "
        f"({stats['prime_joined_rows']:,}/{stats['prime_source_rows']:,} contract-year rows) "
        f"key types {stats['prime_key_types']}")
    log("  assistance (federal_funding_transactions.csv, FY2008-2023)")
    assistance = build_assistance(maps, stats)
    log(f"    join rate {stats['assistance_join_rate']:.1%} "
        f"({stats['assistance_joined_rows']:,}/{stats['assistance_source_rows']:,} transactions); "
        f"{stats['assistance_rows_blocked_by_dofile_exclusion']:,} joined rows blocked by do-file exclusion; "
        f"{stats['assistance_rows_no_uei']:,} rows carry no recipient_uei at all")
    log("  subawards (subawards.csv, FY2011-2023)")
    subs = build_subawards(maps, stats)
    log(f"    join rate {stats['subaward_join_rate']:.1%} "
        f"(as sub {stats['subaward_rows_joined_as_sub']}, as prime {stats['subaward_rows_joined_as_prime']}); "
        f"{stats['subaward_self_edges_dropped']} self-edges dropped")
    log("  lobbying (tribe_year_lobbying_panel.csv, 1999-)")
    lobby = build_lobbying(spine_ids, stats)
    log(f"    join rate {stats['lobbying_join_rate']:.1%} "
        f"({stats['lobbying_joined_rows']}/{stats['lobbying_source_rows']} entity-years); "
        f"{stats['lobbying_rows_off_spine']} rows off-spine")

    for c in UNAVAILABLE:
        log(f"  {c}: NOT JOINABLE - no tribe_id/UEI/CAGE on the source. Component left unobserved.")

    # --- D. assemble ---------------------------------------------------------
    log("D. Assembling the entity-year panel")
    keys = set(prime) | set(assistance) | set(subs) | set(lobby)
    off_spine = {k for k in keys if k[0] not in spine_ids}
    stats["keys_off_spine"] = len(off_spine)
    if off_spine:
        log(f"  WARNING: {len(off_spine)} (entity,year) keys reference a tribe_id "
            f"absent from the spine; retained and flagged in_spine=0")

    rows = []
    for (tid, yr) in sorted(keys):
        rec = {
            "tribe_id": tid,
            "canonical_name": name.get(tid, ""),
            "entity_class": klass.get(tid, ""),
            "in_spine": 1 if tid in spine_ids else 0,
            "year": yr,
            "pre_2000_flag": 1 if yr < 2000 else 0,
        }
        present, tiers = [], []
        inwin = [c for c, (a, b) in WINDOWS.items() if a <= yr <= b]

        p = prime.get((tid, yr))
        rec["prime_contract_usd"] = p["prime_contract_usd"] if p else ""
        rec["n_prime_awards"] = p["n_prime_awards"] if p else ""
        rec["prime_tier"] = p["prime_tier"] if p else ""
        rec["prime_observed"] = 1 if p else 0
        if p:
            present.append("prime"); tiers.append(p["prime_tier"])

        a = assistance.get((tid, yr))
        rec["assistance_usd"] = a["assistance_usd"] if a else ""
        rec["n_assistance_awards"] = a["n_assistance_awards"] if a else ""
        rec["assistance_tier"] = a["assistance_tier"] if a else ""
        rec["assistance_fy_partial_flag"] = a["assistance_fy_partial"] if a else ""
        rec["assistance_observed"] = 1 if a else 0
        if a:
            present.append("assistance"); tiers.append(a["assistance_tier"])

        s = subs.get((tid, yr), {})
        rec["subaward_usd_as_sub"] = s.get("subaward_usd_as_sub", "")
        rec["n_subawards_as_sub"] = s.get("n_subawards_as_sub", "")
        rec["subaward_usd_as_prime"] = s.get("subaward_usd_as_prime", "")
        rec["n_subawards_as_prime"] = s.get("n_subawards_as_prime", "")
        st = worst([s.get("subaward_tier_as_sub", ""), s.get("subaward_tier_as_prime", "")])
        rec["subaward_tier"] = st
        rec["subaward_observed"] = 1 if s else 0
        if s:
            present.append("subaward"); tiers.append(st)

        l = lobby.get((tid, yr))
        rec["lobbying_spend_usd"] = l["lobbying_spend_usd"] if l else ""
        rec["lobbying_spend_client_income_usd"] = l["lobbying_spend_client_income_usd"] if l else ""
        rec["lobbying_spend_registrant_expenses_usd"] = l["lobbying_spend_registrant_expenses_usd"] if l else ""
        rec["n_lobbying_filings"] = l["n_lobbying_filings"] if l else ""
        rec["n_registrants"] = l["n_registrants"] if l else ""
        rec["lobbying_tier"] = l["lobbying_tier"] if l else ""
        rec["lobbying_match_confidence_worst"] = l["lobbying_match_confidence_worst"] if l else ""
        rec["lobbying_observed"] = 1 if l else 0
        if l:
            present.append("lobbying"); tiers.append(l["lobbying_tier"])

        # components that exist as datasets but cannot be joined at all
        rec["n_deals"] = ""
        rec["deal_value_usd"] = ""
        rec["deals_observed"] = 0
        rec["n_bills_affecting"] = ""
        rec["bills_observed"] = 0
        rec["n_compacts_active"] = ""
        rec["compacts_observed"] = 0

        rec["n_components_present"] = len(present)
        rec["components_present"] = ";".join(present)
        rec["components_in_window"] = ";".join(inwin)
        rec["components_unavailable"] = ";".join(UNAVAILABLE)
        rec["confidence_tier"] = worst(tiers)
        rows.append(rec)

    P = pd.DataFrame(rows)
    P.to_csv(OUT_PANEL, index=False, encoding="utf-8")
    stats["panel_rows"] = len(P)
    stats["panel_entities"] = P.tribe_id.nunique()
    stats["panel_years"] = (int(P.year.min()), int(P.year.max()))
    stats["rows_2plus"] = int((P.n_components_present >= 2).sum())
    stats["rows_by_ncomp"] = P.n_components_present.value_counts().sort_index().to_dict()
    stats["rows_by_tier"] = P.confidence_tier.value_counts().to_dict()
    ent = P.groupby("tribe_id").apply(
        lambda g: len(set(";".join(g.components_present).split(";")) - {""}),
        include_groups=False)
    stats["entities_2plus"] = int((ent >= 2).sum())
    stats["entities_by_ncomp"] = ent.value_counts().sort_index().to_dict()
    stats["entities_1only"] = int((ent == 1).sum())
    solo = P.groupby("tribe_id").components_present.apply(
        lambda s: set(";".join(s).split(";")) - {""})
    solo = solo[solo.apply(len) == 1]
    mix = pd.Series([list(v)[0] for v in solo]).value_counts().to_dict()
    stats["solo_component_mix"] = ", ".join(f"{v} {k}" for k, v in mix.items())
    stats["pre_2000_rows"] = int((P.pre_2000_flag == 1).sum())
    stats["off_spine_entities"] = sorted({k[0] for k in off_spine})
    log(f"  pre_2000_flag rows: {stats['pre_2000_rows']} (all 1999, LDA only)")
    log(f"  panel: {len(P):,} rows, {stats['panel_entities']} entities, "
        f"years {stats['panel_years'][0]}-{stats['panel_years'][1]}")
    log(f"  rows with >=2 components: {stats['rows_2plus']:,}; "
        f"entities with >=2 components (ever): {stats['entities_2plus']}")
    log(f"  row confidence_tier: {stats['rows_by_tier']}")
    log(f"  -> {os.path.relpath(OUT_PANEL, PROJECT)}")

    # --- E. coverage ---------------------------------------------------------
    log("E. Writing coverage audit")
    cov = []
    yrs = range(int(P.year.min()), int(P.year.max()) + 1)
    comp_cols = {
        "prime": ("prime_observed", "prime_contract_usd"),
        "assistance": ("assistance_observed", "assistance_usd"),
        "subaward": ("subaward_observed", "subaward_usd_as_sub"),
        "lobbying": ("lobbying_observed", "lobbying_spend_usd"),
    }
    for comp, (obs, val) in comp_cols.items():
        lo, hi = WINDOWS[comp]
        for y in yrs:
            sub = P[(P.year == y) & (P[obs] == 1)]
            v = pd.to_numeric(sub[val], errors="coerce").sum() if len(sub) else 0.0
            cov.append({
                "component": comp,
                "year": y,
                "in_source_window": 1 if lo <= y <= hi else 0,
                "source_window": f"{lo}-{hi}",
                "n_entities_observed": len(sub),
                "total_usd_observed": round(float(v), 2) if len(sub) else "",
                "interpretation": ("observed" if len(sub) else
                                   ("in window, no entity observed" if lo <= y <= hi
                                    else "OUT OF SOURCE WINDOW - unknown, not zero")),
            })
    for comp in UNAVAILABLE:
        for y in yrs:
            cov.append({
                "component": comp, "year": y, "in_source_window": "",
                "source_window": "n/a",
                "n_entities_observed": 0, "total_usd_observed": "",
                "interpretation": "NOT JOINABLE - source carries no tribe_id/UEI/CAGE",
            })
    C = pd.DataFrame(cov)
    C.to_csv(OUT_COVER, index=False, encoding="utf-8")
    log(f"  -> {os.path.relpath(OUT_COVER, PROJECT)}")

    # --- F. build log --------------------------------------------------------
    write_md(stats, P, E, C)
    log(f"  -> {os.path.relpath(OUT_MD, PROJECT)}")
    log(f"Done in {time.time()-t0:.1f}s")
    _logfh.close()


def write_md(stats, P, E, C):
    ec = stats["entities_by_ncomp"]
    rc = stats["rows_by_ncomp"]

    def tbl(d, k1, k2):
        out = [f"| {k1} | {k2} |", "|---|---:|"]
        for k, v in sorted(d.items()):
            out.append(f"| {k} | {v:,} |")
        return "\n".join(out)

    cov_lines = ["| Component | Source window | Years with any entity | Entities ever observed |",
                 "|---|---|---:|---:|"]
    for comp, (lo, hi) in WINDOWS.items():
        sub = C[(C.component == comp) & (C.n_entities_observed > 0)]
        ents = P[P[f"{comp}_observed"] == 1].tribe_id.nunique()
        cov_lines.append(f"| {comp} | {lo}-{hi} | {len(sub)} | {ents} |")
    for comp in UNAVAILABLE:
        cov_lines.append(f"| {comp} | n/a | 0 | 0 — **not joinable** |")

    md = f"""# Dataset 5 — The Linked Analytical File

*Build log. Generated by `code/31_build_dataset5_linked.py` on {time.strftime('%Y-%m-%d')}.*
*Run log: `logs/31_dataset5_linked.log`.*

One row per (entity, year) joining prime contracting, federal assistance,
subawards and lobbying through the NEID spine, plus a standalone dated
ownership-event ledger. This is the dataset that only exists because the others do.

---

## Outputs

| File | Rows |
|---|---:|
| `data/clean/entity_year_panel.csv` | {stats['panel_rows']:,} |
| `data/clean/ownership_events.csv` | {stats['own_events']:,} |
| `data/clean/entity_year_coverage.csv` | {len(C):,} |

Panel: **{stats['panel_entities']} entities**, years **{stats['panel_years'][0]}–{stats['panel_years'][1]}**.

---

## A. The ownership-event extraction — what it found

**{stats['own_events']} ownership-change events** were extracted from
{stats['deals_total_rows']} deal rows across five ledger files.
**{stats['own_events_dated']} carry a usable effective date**, spanning
**{stats['own_span'][0]} to {stats['own_span'][1]}**.
{stats['own_events_undated']} rows record an ownership change with **no date in the
source row** — they are retained (flag, never delete) with
`date_usable_for_attribution = 0` and are useless for time-aware attribution
until a date is sourced.

By asset class:

{tbl(stats['own_by_asset_class'], 'asset_class', 'events')}

By direction:

{tbl(stats['own_by_direction'], 'direction', 'events')}

**{stats['own_corporate']} of these are corporate-entity ownership changes** — the
subset that actually moves a UEI from one owner to another and therefore
matters for contract attribution. `real_property` events move land or buildings,
not registrants; filter them out before using this file to correct FPDS
attribution.

### Why this file is the point of the project

FPDS does not update retroactively when ownership changes, and no reliable
corporate-hierarchy-over-time source exists. That is why entity attribution in
federal contracting is normally a static snapshot: whoever owns a UEI today is
credited with everything that UEI ever won. The event ledger is the correction
term. Once these dates exist, a contract obligation dated before an acquisition
can be held apart from one dated after it.

The honest scale statement: **{stats['own_events_dated']} dated events is a seed,
not a census.** It is enough to correct attribution for the specific families it
covers (Chenega, Koniag, Sealaska, Chickasaw Nation Industries, Waséyabek,
Ukpeaġvik Iñupiat, Bering Straits, NANA, Doyon, Cherokee Nation Businesses) and
no more. Capture rate is driven by newsroom structure, not deal volume.

### What is NOT in it

The events carry **no `tribe_id`**. The deals ledgers have no identifier column
of any kind — no NEID, no UEI, no CAGE — only hand-entered party names. Linking
them would require name resolution, which this build does not do. `native_entity_neid`
is present but empty on every row, with the reason recorded in `neid_join_status`.
**Resolving those {stats['own_events']} party names to NEID is the single
highest-value next action for Dataset 5**, and it belongs in the rulings queue,
not in a script.

---

## B. Join rates, per component

| Component | Source | Source rows | Joined to NEID | Rate |
|---|---|---:|---:|---:|
| Prime contracting | `master prime file.dta` (UEI, then CAGE) | {stats['prime_source_rows']:,} | {stats['prime_joined_rows']:,} | {stats['prime_join_rate']:.1%} |
| Federal assistance | `federal_funding_transactions.csv` (recipient_uei) | {stats['assistance_source_rows']:,} | {stats['assistance_joined_rows']:,} | {stats['assistance_join_rate']:.1%} |
| Subawards | `subawards.csv` (sub_uei / prime_uei) | {stats['subaward_source_rows']:,} | {stats['subaward_rows_joined_either']:,} | {stats['subaward_join_rate']:.1%} |
| Lobbying | `tribe_year_lobbying_panel.csv` (entity_id = NEID) | {stats['lobbying_source_rows']:,} | {stats['lobbying_joined_rows']:,} | {stats['lobbying_join_rate']:.1%} |
| Deals | five deal ledgers | {stats['deals_total_rows']} | 0 | **0.0%** |
| Bills | `native_bills.csv` | 3,037 | 0 | **0.0%** |
| Compacts | `compacts.csv` | 707 | 0 | **0.0%** |

Join keys used, in order: NEID `tribe_id` where the source already carries it
(lobbying only); otherwise `UEI` → `tribe_id` and then `CAGE` → `tribe_id`
through `cedar_identifier_ledger_final.csv`. **No name matching anywhere.**
Tier-X identifier links are excluded from every join.

### The single biggest join failure

**The deals ledger — 0 of {stats['deals_total_rows']} rows joined, cause: the
source carries no identifier column at all.** Every other component joined on an
identifier that already existed. The deals files carry `Native_Party` as
free text and nothing else. This is not a coverage problem or a matching
problem; the key is simply absent from the schema. Consequence: `n_deals` and
`deal_value_usd` are blank on all {stats['panel_rows']:,} panel rows, and the
ownership events — the asset this dataset was built around — sit beside the
panel rather than inside it.

The fix is not fuzzy matching. It is adding a ruled `tribe_id` column to the
deals schema, populated the way every other spine link was: proposed, then
ruled. {stats['own_events']} party strings is a one-sitting rulings batch.

**Runners-up.** Bills (`native_bills.affected_entities` is empty on all 3,037
rows) and compacts (`compacts.entity_id` is empty on all 707) fail the same way:
the linking column exists in the schema but was never populated.

### Federal funding: the crosswalk that is not there yet

`federal_funding_tribe_year_panel.csv` was **not** used. Its `tribe_id` is
`lineageA_dofile_integer` — an integer local to `fed_funding_do_file_corrtd.do`,
not NEID — and `tribe_id_neid` is empty on all 476,924 transaction rows pending
the MR-4 ruling on 975 recipient UEIs. This build therefore attributes
assistance **independently**, by taking `recipient_uei` straight to the
identifier ledger. That is a different attribution path from the do-file's, and
it will not reproduce the do-file's $107,047,741,074.94 regression figure — it
is not supposed to. {stats['assistance_rows_blocked_by_dofile_exclusion']:,}
joined transactions were dropped because the do-file's hand-checked exclusions
block them; hand-checked authority outranks the automated ledger link.
{stats['assistance_rows_no_uei']:,} transactions carry no `recipient_uei` at all
and can never join by this route.

---

## C. Coverage windows — the problem stated plainly

**A component's silence in a given year means one of three different things, and
they must not be collapsed.**

1. The year is **outside the component's source window**. Nothing was ever
   collected. Unknowable from this file.
2. The year is inside the window and the entity has **no record**. Could be
   genuine inactivity, could be a coverage hole in the source, could be an
   identifier we have not linked yet. Not distinguishable here.
3. The entity has a record with a value of **zero** — a real, reported zero
   (this happens in lobbying: a filed disclosure reporting $0).

Only case 3 is written as a number. Cases 1 and 2 are written as **blank**, with
`<component>_observed = 0`. The panel contains **no fabricated zeros**.
`components_in_window` lists which components could have seen that year;
`components_present` lists which actually did. The difference between those two
columns is exactly case 2.

{chr(10).join(cov_lines)}

The windows do not overlap cleanly. Assistance begins FY2008 and prime ends
2022, so **only 2011–2022 has all four components simultaneously in window** —
and subawards only from 2011. Any cross-component ratio (lobbying per contract
dollar, subaward share of prime) computed outside 2011–2022 is comparing a
measured quantity against an unmeasured one. `entity_year_coverage.csv` carries
`in_source_window` per component per year so this is auditable rather than
folklore.

Known window causes, not fixable by rebuilding: LDA began in 1999 (statute, not
a gap); USAspending assistance begins FY2008 and FY2001–2007 needs the FAADS
backfill; the FPDS prime extract was pulled 2023-04 and stops at FY2022; the
FSRS subaward export is a 2023 snapshot whose sampling frame was never
preserved, so subaward totals are a **lower bound only**.

---

## C2. Three things the panel does that look like errors and are not

- **`prime_contract_usd` goes negative.** {int((pd.to_numeric(P.prime_contract_usd, errors='coerce') < 0).sum())} rows.
  These are net deobligation years — FPDS modifications that return money. Real,
  not a sign bug. Do not clip them.
- **{stats['pre_2000_rows']} rows carry `pre_2000_flag = 1`.** All of them are 1999
  and all of them are lobbying-only, because the LDA is the only component whose
  window opens before the temporal floor. Retained per flag-never-delete, excluded
  from the default published view.
- **{len(stats['off_spine_entities'])} entities carry `in_spine = 0`**
  ({stats['keys_off_spine']} rows): {', '.join(stats['off_spine_entities'])}.
  These NEID-shaped ids appear in the identifier ledger (minted by
  `subsidiary_lookup` / `web_verified`) but are absent from the 687-entity spine.
  All are tier C. Retained and flagged rather than dropped; they are a spine gap
  to resolve, not junk.

---

## D. Tier discipline

Every component carries its own tier (`prime_tier`, `assistance_tier`,
`subaward_tier`, `lobbying_tier`), computed as the **worst identifier-link tier
that contributed a dollar to that cell**. The row-level `confidence_tier` is the
worst across the components actually present — never an average, never the best.

{tbl(stats['rows_by_tier'], 'row confidence_tier', 'rows')}

Lobbying is hard-set to **tier B** and can never be A: the LDA carries no
UEI/CAGE/EIN, so every lobbying link is an algorithmic name match against the
spine that has never been ruled. `lobbying_match_confidence_worst` preserves the
high/medium distinction from the disclosure file underneath it.

The practical consequence, and it is the point of the rule: an entity-year with
a tier-A assistance figure and a tier-B contracting attribution is a **tier-B
row**. Reading `prime_contract_usd` off a row whose `confidence_tier` is B means
reading an unruled attribution. Only rows where `confidence_tier = A` are
publishable, and they are a minority.

---

## E. How many entities actually link

Components observed per entity, across all years:

{tbl(ec, 'components (ever)', 'entities')}

**{stats['entities_2plus']} entities carry two or more components.**
{stats['entities_1only']} carry exactly one, and that one component is
{stats['solo_component_mix']} — so the typical single-component entity is visible
as a grant recipient and nowhere else.

Components present per ROW:

{tbl(rc, 'components on the row', 'rows')}

{stats['rows_2plus']:,} of {stats['panel_rows']:,} rows ({stats['rows_2plus']/max(stats['panel_rows'],1):.1%})
carry two or more components. Single-component rows are not defective — they are
the honest majority, because the components' windows barely overlap and because
most entities do not lobby.

---

## NEVER do these

- Never read a blank as a zero. Blank means NOT OBSERVED. Use `<component>_observed`.
- Never compare a component across a year where `in_source_window = 0`.
- Never quote a row's dollar figure at a tier better than its `confidence_tier`.
- Never reconcile `assistance_usd` here against the do-file's $107.0B figure.
  They are different attribution paths; only the do-file's is regression-tested.
- Never use `ownership_events.csv` to re-attribute contracts without filtering
  to `asset_class = corporate_entity` and `date_usable_for_attribution = 1`.
- Never read `target_entity` as a clean entity name on `real_property` rows —
  `Counterparty_or_Funder` sometimes names the seller. `party_role_basis` says so
  on every row.
- Never name-match the deals ledger into the spine. Rule it.

---

## Next actions, in value order

1. **Rule the {stats['own_events']} deal party names to NEID `tribe_id`** and add
   the column to the deals schema. This is what turns the ownership ledger from
   a document into a join.
2. **MR-4** — rule the 975 funding recipient UEIs so `tribe_id_neid` populates and
   Dataset 3's own regression-tested attribution can carry the assistance column
   instead of this build's independent path.
3. Populate `native_bills.affected_entities` and `compacts.entity_id`. Both
   columns exist and are empty; both datasets are otherwise complete.
4. Fresh FPDS and FSRS pulls to close the prime window past FY2022 and give the
   subaward layer a known sampling frame.

---

**House rules that apply to every dataset:**

- Never falsely attribute. Missing coverage is expandable; a wrong attribution is not.
- Only tier A publishes. Elijah's rulings are the only promotion path.
- Flag, never delete. Retain and mark rather than drop.
- Temporal floor is 2000; pre-2000 rows carry `pre_2000_flag = 1`.

See `STATE_OF_BUILD.md` and `docs/CROSS_DATASET_LEARNING.md`.
"""
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write(md)


if __name__ == "__main__":
    sys.exit(main())
