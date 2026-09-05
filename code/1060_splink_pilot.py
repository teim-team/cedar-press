#!/usr/bin/env python3
"""Cedar Press - 1060: SPLINK PILOT against the contractor->nation backlog.

    py -3 code/1060_splink_pilot.py prep        # build the record + truth tables
    py -3 code/1060_splink_pilot.py baseline    # score the INCUMBENT matcher (503 resolve)
    py -3 code/1060_splink_pilot.py splink      # train + score splink, held-out
    py -3 code/1060_splink_pilot.py collisions  # the three named collision cases
    py -3 code/1060_splink_pilot.py queue       # write the owner adjudication queue
    py -3 code/1060_splink_pilot.py verify      # invariants; exits 1 when one breaks
    py -3 code/1060_splink_pilot.py all

WHAT THIS IS AND IS NOT
-----------------------
It is a MEASUREMENT, not an adoption. Nothing here writes to data/clean,
data/spine, the ledger or the register. Every output goes to
    data/interim/splink_pilot/     (working tables + scores)
    review/splink_pilot_*          (the adjudication queue + the report)
and every proposed link is a PROPOSAL carrying its score and its evidence.
No cedar_uid is minted, retired or repointed.

THE TASK
--------
Link a federal contractor (one row per `awardee_uei` in prime_contracts) to the
Native entity that owns it (a `cedar_uid` in the spine).

GROUND TRUTH is the owner's own adjudications, already in the ledger:
  POSITIVE  cedar_identifier_ledger_final.csv rows with identifier_type=UEI,
            confidence_tier=A and attribution_method in the RULED set
            (hand / bgov_manual / elijah_ruling / elijah_ruling_redirect /
            web_verified). START_HERE calls this metric `tier_A_ruled`.
  NEGATIVE  confidence_tier=X UEI rows. START_HERE 1b: tier X is a NEGATIVE
            ruling. A high-confidence link onto one of these is a measured
            false positive against a human who already said no.

The positive set is SPLIT and held out. A model that has seen a pair may not be
scored on it.

THE CEILING, MEASURED BEFORE ANY MODEL WAS BUILT
------------------------------------------------
Of the 690 truth pairs present in prime_contracts, 596 (86.4%) share at least
one distinctive token with some name their owner carries in the spine. 94
(13.6%) share NONE - PCI GOVERNMENT SERVICES, RIVERTECH, TALU, TUKNIK, CNI
CONSTRUCTION, PADUCAH REMEDIATION. That is the ASRC-files-as-BROADLEAF class
and NO name-similarity method can reach it, splink included. 86.4% is therefore
the recall ceiling of this whole family of approach, and any recall figure below
has to be read against it.

CONFIDENCE BANDS ARE THE DELIVERABLE (owner, 2026-09-02)
--------------------------------------------------------
"it's easier for us to call stuff than miss things ... they'll be so very
confident about it, and then somewhere less confident, and then I can
adjudicate them."

So the objective is recall subject to a clean auto-accept band, and the middle
band is a first-class output, not a leftover. Cut points are chosen from the
held-out precision curve and stated with the numbers that chose them - never
from round numbers.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
OUT = ROOT / "data" / "interim" / "splink_pilot"
REVIEW = ROOT / "review"
TODAY = date.today().isoformat()
SEED = 20260902

csv.field_size_limit(10_000_000)

PRIME = ROOT / "data" / "clean" / "prime_contracts.csv"
LEDGER = ROOT / "data" / "clean" / "cedar_identifier_ledger_final.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
ALIASES = ROOT / "data" / "clean" / "entity_aliases.csv"

RULED = ("hand", "bgov_manual", "elijah_ruling",
         "elijah_ruling_redirect", "web_verified")

# Generic vocabulary. Deliberately a SUPERSET of 503's GENERIC because the left
# side here is company names, not government names: LLC / TECHNOLOGIES /
# SOLUTIONS carry no identity. State and place words stay ABSENT - OKLAHOMA is
# what separates the Seminole Nation of Oklahoma from the Seminole Tribe of
# Florida, and this pilot is judged on exactly that pair.
GENERIC = set("""THE OF AND A AN IN AT FOR DU DE LA LE LOS LAS EL
NATION NATIONS TRIBE TRIBES TRIBAL BAND BANDS INDIAN INDIANS NATIVE NATIVES
VILLAGE VILLAGES COMMUNITY COMMUNITIES RESERVATION RANCHERIA PUEBLO COLONY TOWN
GOVERNMENT GOVERNMENTAL COUNCIL COMMITTEE BUSINESS EXECUTIVE ORGANIZATION
INC INCORPORATED LLC LLP LP LTD LIMITED LIABILITY COMPANY CO CORP CORPORATION
GROUP HOLDING HOLDINGS SERVICES SERVICE SOLUTIONS SOLUTION TECHNOLOGIES
TECHNOLOGY TECHNICAL SYSTEMS SYSTEM ENTERPRISES ENTERPRISE INDUSTRIES
INTERNATIONAL NATIONAL FEDERAL MANAGEMENT CONSULTING CONSULTANTS CONTRACTING
CONSTRUCTION DEVELOPMENT ASSOCIATES PARTNERS VENTURES JV JOINT PROFESSIONAL
GENERAL AMERICA AMERICAN USA US""".split())

CANON_FIX = {"STE": "SAINTE", "ST": "SAINT", "MT": "MOUNT", "FT": "FORT"}


def norm(s: str) -> str:
    s = (s or "").upper().replace("&", " AND ")
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return " ".join(CANON_FIX.get(w, w) for w in s.split())


def toks(s: str) -> list:
    return sorted({w for w in norm(s).split() if w not in GENERIC and len(w) > 1})


def log(*a):
    print(*a, flush=True)


def duck():
    import duckdb  # noqa: F401  (kept: types/exceptions)
    import cedar_duck
    return cedar_duck.connect()


# ===================== prep =====================

def cmd_prep(args) -> int:
    """Build contractors.csv, entities.csv, truth.csv, negatives.csv."""
    import duckdb
    OUT.mkdir(parents=True, exist_ok=True)
    con = duck()
    t0 = time.time()
    con.sql(f"""create view pc as select * from read_csv('{PRIME.as_posix()}',
            all_varchar=true, sample_size=200000, ignore_errors=true)""")
    con.sql(f"""create view led as select * from read_csv('{LEDGER.as_posix()}',
            all_varchar=true, sample_size=-1)""")

    # ---- contractors: one row per awardee_uei ----
    # The modal name / city / state per UEI, not the first: a UEI can be filed
    # under several spellings and the modal one is the stable identity.
    con.sql("""create table contractors as
      with r as (
        select awardee_uei uei, awardee_name nm,
               upper(coalesce(recipient_state_code,'')) st,
               upper(coalesce(recipient_city_name,'')) city,
               coalesce(parent_name,'') pn, coalesce(parent_uei,'') pu,
               coalesce(cage_code,'') cage,
               try_cast(total_obligations as double) d,
               coalesce(cedar_uid,'') cu,
               coalesce(naics_description,'') naics,
               try_cast(fiscal_year as int) fy
        from pc where coalesce(awardee_uei,'') <> ''
      ),
      r2 as (
        -- `mode()` IS NOT DETERMINISTIC ON A TIE, and that leaked into the
        -- BASELINE. Two `prep` runs on the same bytes chose different modal
        -- awardee_names for the same UEI, which changed what 503 was asked to
        -- resolve, which moved the incumbent's own held-out score (205/186 on
        -- one run, 204/190 on the next). A non-deterministic primary attribute
        -- is class 7 in `293_lint_bug_classes.py`. Replaced with an explicit
        -- ordering: most frequent, ties broken lexicographically.
        select *,
               count(*) over (partition by uei, nm)    c_nm,
               count(*) over (partition by uei, st)    c_st,
               count(*) over (partition by uei, city)  c_city,
               count(*) over (partition by uei, cage)  c_cage,
               count(*) over (partition by uei, naics) c_naics
        from r
      ),
      m as (
        -- FY COMES FROM THE SAME AGGREGATE, NOT A SELF-JOIN.
        -- The first draft did `from r left join (select awardee_uei, fiscal_year
        -- from pc) on uei` to get the year range. That is a FANOUT: every row
        -- of r was duplicated once per row that UEI has, so `sum(d)` was
        -- multiplied by n_rows. The queue reported $2,880.88B of prime
        -- obligations against a table whose whole content is $310.01B - a 9.3x
        -- overstatement, and it looked like a plausible big number until it was
        -- put next to the total. AGENT_FIELD_GUIDE section 3, exactly.
        select uei,
               (array_agg(nm    order by c_nm    desc, nm))[1]    nm,
               (array_agg(st    order by c_st    desc, st))[1]    st,
               (array_agg(city  order by c_city  desc, city))[1]  city,
               (array_agg(cage  order by c_cage  desc, cage))[1]  cage,
               (array_agg(naics order by c_naics desc, naics))[1] naics,
               max(pn) parent_name, max(pu) parent_uei,
               sum(d) dollars, count(*) n_rows,
               max(cu) current_cedar_uid,
               min(fy) fy_min, max(fy) fy_max
        from r2
        group by uei
      )
      select * from m""")
    n_c, d_c = con.sql("select count(*), sum(dollars) from contractors").fetchone()
    d_pc = con.sql("""select sum(try_cast(total_obligations as double))
                      from pc where coalesce(awardee_uei,'')<>''""").fetchone()[0]
    log(f"  contractors: {n_c:,} distinct awardee_uei  ({time.time()-t0:.1f}s)")
    # CONSERVATION CHECK, because the fanout above was caught by nothing else.
    log(f"  dollars: aggregated ${d_c/1e9:,.2f}B vs source ${d_pc/1e9:,.2f}B  "
        f"(delta {abs(d_c-d_pc):,.2f})")
    if abs(d_c - d_pc) > 1.0:
        log("  !! DOLLAR CONSERVATION BROKEN in the contractor aggregate")
        return 1

    rows = con.sql("""select uei, nm, st, city, cage, naics, parent_name,
                      parent_uei, dollars, n_rows, current_cedar_uid,
                      fy_min, fy_max from contractors
                      order by uei""").fetchall()
    with (OUT / "contractors.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["unique_id", "name_raw", "name_norm", "name_tokens", "state",
                    "city", "cage", "naics", "parent_name", "parent_name_norm",
                    "parent_uei", "dollars", "n_rows", "current_cedar_uid",
                    "fy_min", "fy_max"])
        for (uei, nm, st, city, cage, naics, pn, pu, d, nr, cu, y0, y1) in rows:
            w.writerow([uei, nm, norm(nm), "|".join(toks(nm)), st, city,
                        cage, naics, pn, norm(pn), pu,
                        f"{d or 0:.2f}", nr, cu, y0 or "", y1 or ""])

    # ---- entities: one row per (cedar_uid, name variant) ----
    ent = []
    spine_meta = {}
    with SPINE.open(encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            uid = (r.get("cedar_uid") or "").strip()
            if not uid:
                continue
            spine_meta[uid] = {
                "tribe_id": (r.get("tribe_id") or "").strip(),
                "canonical_name": r.get("canonical_name", ""),
                "entity_class": r.get("entity_class", ""),
                "state": (r.get("state") or "").strip().upper(),
                "city": (r.get("city") or "").strip().upper(),
                "website": r.get("entity_website", ""),
            }
            seen = set()
            for src, nm in [("canonical", r.get("canonical_name", "")),
                            ("fr_official", r.get("fr_official_name", ""))] + \
                           [("spine_alias", a) for a in (r.get("aliases") or "").split(";")]:
                k = norm(nm)
                if k and k not in seen:
                    seen.add(k)
                    ent.append((uid, nm, src))
    if ALIASES.exists():
        with ALIASES.open(encoding="utf-8", errors="replace", newline="") as f:
            for r in csv.DictReader(f):
                uid = (r.get("cedar_uid") or "").strip()
                nm = r.get("alias_name", "")
                atype = (r.get("alias_type") or "").strip()
                if not (uid and norm(nm)) or uid not in spine_meta:
                    continue
                # ENTITY_MATCH_RULES: a single-token alias_type='brand' row is
                # a fragment of a company name, not a name. 503 refuses all 104.
                if atype == "brand" and len(norm(nm).split()) == 1:
                    continue
                ent.append((uid, nm, "alias:" + (atype or "?")))

    with (OUT / "entities.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["unique_id", "cedar_uid", "name_raw", "name_norm",
                    "name_tokens", "state", "city", "entity_class",
                    "tribe_id", "name_source", "website"])
        seen_key = set()
        i = 0
        for uid, nm, src in ent:
            key = (uid, norm(nm))
            if key in seen_key:
                continue
            seen_key.add(key)
            m = spine_meta[uid]
            i += 1
            w.writerow([f"E{i:06d}", uid, nm, norm(nm), "|".join(toks(nm)),
                        m["state"], m["city"], m["entity_class"],
                        m["tribe_id"], src, m["website"]])
    log(f"  entities:    {i:,} name records over {len(spine_meta):,} cedar_uid")

    # ---- truth: positives ----
    q = f"""select l.identifier uei, l.cedar_uid,
                   any_value(l.legal_business_name) legal_name,
                   any_value(l.canonical_name) owner_name,
                   any_value(l.attribution_method) method
            from led l
            where l.identifier_type='UEI' and l.confidence_tier='A'
              and l.attribution_method in {RULED!r}
              and coalesce(l.cedar_uid,'')<>''
            group by 1,2"""
    pos = con.sql(q.replace("'", "'").replace('("', "('").replace('")', "')")).fetchall() \
        if False else con.sql(f"""
            select l.identifier, l.cedar_uid,
                   any_value(l.legal_business_name),
                   any_value(l.canonical_name),
                   any_value(l.attribution_method)
            from led l
            where l.identifier_type='UEI' and l.confidence_tier='A'
              and l.attribution_method in {tuple(RULED)}
              and coalesce(l.cedar_uid,'')<>''
            group by 1,2""").fetchall()
    have = {r[0] for r in con.sql("select uei from contractors").fetchall()}
    known_uid = set(spine_meta)
    kept, drop_nc, drop_ns = [], 0, 0
    for uei, uid, lbn, own, meth in pos:
        if uei not in have:
            drop_nc += 1
            continue
        if uid not in known_uid:
            drop_ns += 1
            continue
        kept.append((uei, uid, lbn, own, meth))

    # SORT BEFORE YOU SHUFFLE. `kept` arrives in whatever order DuckDB's
    # parallel hash aggregate emitted, which is NOT stable across runs, so a
    # seeded shuffle of it produced a DIFFERENT train/test partition every time
    # - and the incumbent's own held-out score moved with it (210/195 on one
    # run, 208/191 on the next, same bytes). A seeded RNG over an unordered
    # input is not reproducible; it only looks it.
    kept.sort(key=lambda r: r[0])
    rnd = random.Random(SEED)
    rnd.shuffle(kept)
    cut = int(len(kept) * 0.5)
    split = {u: ("train" if i < cut else "test") for i, (u, *_) in enumerate(kept)}
    # owner-disjoint variant: a whole cedar_uid falls on one side
    owners = sorted({uid for _, uid, *_ in kept})
    rnd2 = random.Random(SEED + 1)
    rnd2.shuffle(owners)
    ocut = int(len(owners) * 0.5)
    oside = {o: ("train" if i < ocut else "test") for i, o in enumerate(owners)}

    with (OUT / "truth.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["uei", "cedar_uid", "legal_name", "owner_name",
                    "attribution_method", "split", "owner_split"])
        for uei, uid, lbn, own, meth in kept:
            w.writerow([uei, uid, lbn, own, meth, split[uei], oside[uid]])
    log(f"  truth:       {len(kept):,} positive pairs "
        f"(train {cut:,} / test {len(kept)-cut:,}); "
        f"dropped {drop_nc} not-in-prime, {drop_ns} owner-not-in-spine")

    # ---- negatives: tier X UEI rows ----
    neg = con.sql("""select identifier, any_value(legal_business_name),
                            any_value(tier_rationale)
                     from led where identifier_type='UEI'
                       and confidence_tier='X' group by 1""").fetchall()
    with (OUT / "negatives.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["uei", "legal_name", "ruling", "in_prime"])
        for uei, lbn, why in neg:
            w.writerow([uei, lbn, why, "Y" if uei in have else "N"])
    log(f"  negatives:   {len(neg):,} tier-X UEI rulings "
        f"({sum(1 for u,_,_ in neg if u in have):,} present in prime)")
    log(f"  prep total {time.time()-t0:.1f}s")
    return 0


# ===================== the incumbent baseline =====================

def load_503():
    """Import 503_identity.py by path (a leading digit is not importable)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cedar_503", CODE / "503_identity.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cedar_503"] = mod
    spec.loader.exec_module(mod)
    return mod


def tribe_to_uid():
    m = {}
    with SPINE.open(encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            t = (r.get("tribe_id") or "").strip()
            u = (r.get("cedar_uid") or "").strip()
            if t and u:
                m[t] = u
    return m


def read(p):
    with Path(p).open(encoding="utf-8", errors="replace", newline="") as f:
        return list(csv.DictReader(f))


def cmd_baseline(args) -> int:
    """Run the INCUMBENT matcher (503_identity.resolve) on the held-out set."""
    mod = load_503()
    t2u = tribe_to_uid()
    truth = read(OUT / "truth.csv")
    contractors = {r["unique_id"]: r for r in read(OUT / "contractors.csv")}
    t0 = time.time()
    exact, gov, state_of = mod.build_index()
    log(f"  503 index built in {time.time()-t0:.1f}s")

    out = []
    t0 = time.time()
    for r in truth:
        c = contractors.get(r["uei"], {})
        filed = c.get("name_raw") or r["legal_name"]
        tid, why = mod.resolve(filed, exact, gov, state_of,
                               top_states=c.get("state", ""))
        pred = t2u.get(tid or "", "")
        out.append({**r, "filed_name": filed,
                    "baseline_tribe_id": tid or "",
                    "baseline_cedar_uid": pred,
                    "baseline_reason": why,
                    "baseline_correct": "1" if pred and pred == r["cedar_uid"] else "0"})
    dt = time.time() - t0

    neg = read(OUT / "negatives.csv")
    nout = []
    for r in neg:
        c = contractors.get(r["uei"], {})
        filed = c.get("name_raw") or r["legal_name"]
        tid, why = mod.resolve(filed, exact, gov, state_of,
                               top_states=c.get("state", ""))
        nout.append({**r, "filed_name": filed,
                     "baseline_cedar_uid": t2u.get(tid or "", ""),
                     "baseline_reason": why})

    with (OUT / "baseline_truth.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    with (OUT / "baseline_negatives.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(nout[0].keys()))
        w.writeheader()
        w.writerows(nout)

    for scope in ("test", "all"):
        rows = [r for r in out if scope == "all" or r["split"] == "test"]
        n = len(rows)
        proposed = [r for r in rows if r["baseline_cedar_uid"]]
        right = [r for r in proposed if r["baseline_correct"] == "1"]
        log(f"  BASELINE 503 [{scope}] n={n}  proposed={len(proposed)} "
            f"({100*len(proposed)/n:.1f}%)  correct={len(right)}  "
            f"precision={100*len(right)/max(1,len(proposed)):.1f}%  "
            f"recall={100*len(right)/n:.1f}%")
    fired = [r for r in nout if r["baseline_cedar_uid"]]
    log(f"  BASELINE 503 on {len(nout)} tier-X NEGATIVE rulings: "
        f"{len(fired)} would be linked anyway ({100*len(fired)/max(1,len(nout)):.1f}%)")
    log(f"  scored {len(out):,} names in {dt:.1f}s")
    return 0


# ===================== splink =====================

def cmd_splink(args) -> int:
    import pandas as pd
    from splink import Linker, SettingsCreator, DuckDBAPI, block_on
    import splink.comparison_level_library as cll
    import splink.comparison_library as cl
    import splink

    t_start = time.time()
    con_df = pd.read_csv(OUT / "contractors.csv", dtype=str,
                         keep_default_na=False)
    ent_df = pd.read_csv(OUT / "entities.csv", dtype=str, keep_default_na=False)
    truth = read(OUT / "truth.csv")
    truth_train = {r["uei"]: r["cedar_uid"] for r in truth if r["split"] == "train"}
    truth_test = {r["uei"]: r["cedar_uid"] for r in truth if r["split"] == "test"}

    # A model may not see a pair it will be scored on. The test UEIs are
    # withheld from the LABELS used to estimate m; they stay in the record
    # table because their presence is what makes the u-estimate honest.
    log(f"  contractors {len(con_df):,}  entity-name records {len(ent_df):,}")
    log(f"  labels: train {len(truth_train):,}  held-out test {len(truth_test):,}")

    for df in (con_df, ent_df):
        df["tok_arr"] = df["name_tokens"].apply(
            lambda s: [t for t in s.split("|") if t])
        df["first_tok"] = df["tok_arr"].apply(lambda a: a[0] if a else "")

    # Splink concatenates the two frames, so they must carry the SAME columns.
    # Everything else stays in lookup dicts below - a column splink does not
    # compare on has no business being in the model's input.
    MODEL_COLS = ["unique_id", "name_raw", "name_norm", "state", "city",
                  "tok_arr", "first_tok"]
    con_model = con_df[MODEL_COLS].copy()
    ent_model = ent_df[MODEL_COLS].copy()

    # --- comparisons ---
    # Name. Levels run strong -> weak. The bottom TWO levels are the ones the
    # UKB/Cherokee defect lives in: "shares one distinctive token" must be a
    # LOW-weight level, not a match.
    name_cmp = cl.CustomComparison(
        output_column_name="name",
        comparison_levels=[
            cll.NullLevel("name_norm"),
            cll.ExactMatchLevel("name_norm").configure(
                tf_adjustment_column="name_norm", tf_minimum_u_value=0.001),
            cll.JaroWinklerLevel("name_norm", 0.95),
            cll.CustomLevel(
                sql_condition=(
                    "list_has_all(tok_arr_l, tok_arr_r) "
                    "and len(tok_arr_r) >= 2 and len(tok_arr_l) > 0"),
                label_for_charts="entity tokens are a subset of filed, >=2 tokens"),
            cll.JaroWinklerLevel("name_norm", 0.88),
            cll.CustomLevel(
                sql_condition=(
                    "len(list_intersect(tok_arr_l, tok_arr_r)) >= 2"),
                label_for_charts=">=2 distinctive tokens shared"),
            cll.CustomLevel(
                sql_condition=(
                    "len(list_intersect(tok_arr_l, tok_arr_r)) >= 1"),
                label_for_charts="exactly 1 distinctive token shared"),
            cll.ElseLevel(),
        ],
    )
    state_cmp = cl.CustomComparison(
        output_column_name="state",
        comparison_levels=[
            cll.CustomLevel(sql_condition="state_l = '' or state_r = ''",
                            label_for_charts="state missing one side"),
            cll.ExactMatchLevel("state").configure(
                tf_adjustment_column="state"),
            cll.ElseLevel(),
        ],
    )
    city_cmp = cl.CustomComparison(
        output_column_name="city",
        comparison_levels=[
            cll.CustomLevel(sql_condition="city_l = '' or city_r = ''",
                            label_for_charts="city missing one side"),
            cll.ExactMatchLevel("city"),
            cll.ElseLevel(),
        ],
    )

    # CITY IS DELIBERATELY NOT A MODEL FEATURE. Only 2,088 of 7,186 entity
    # name records (29%) carry a city, so the "one side missing" level fires on
    # nearly every pair and estimate_m_from_pairwise_labels observed the exact
    # level zero times - splink said so, in a warning. A feature whose m cannot
    # be estimated contributes a default, which is a number that looks trained
    # and is not. City stays as EVIDENCE IN THE QUEUE ROW (the owner's rung 1
    # and rung 3) rather than as a weight in the model.
    #
    # BLOCKING. The exploding rule on tok_arr pairs any contractor with any
    # entity sharing ONE distinctive token. That is deliberately the widest
    # useful net: a pair sharing no token and no name similarity can only reach
    # the ElseLevel, so blocking it in would add cost and no recall. The
    # 86.4% ceiling measured in the docstring is the same fact from the other
    # side.
    settings = SettingsCreator(
        link_type="link_only",
        comparisons=[name_cmp, state_cmp],
        blocking_rules_to_generate_predictions=[
            block_on("name_norm"),
            {"blocking_rule": "l.tok_arr = r.tok_arr",
             "arrays_to_explode": ["tok_arr"]},
        ],
        retain_intermediate_calculation_columns=True,
        retain_matching_columns=True,
    )

    # THE PRIOR IS SET, NOT ESTIMATED FROM A BLOCKING RULE.
    #
    # `estimate_probability_two_random_records_match([block_on("name_norm")],
    # recall=0.5)` returned 8.69e-06 - one match in 115,077 pairs - and that is
    # wrong by more than an order of magnitude for THIS task. It assumes the
    # exact-name blocking rule catches half the true matches. It does not:
    # a subsidiary almost never files under its owner's exact name, which is
    # the whole reason this backlog exists. The under-estimate crushed every
    # posterior; nothing scored above 0.95 and the top band was empty.
    #
    # Set it from the data instead. prime_contracts currently attributes 3,216
    # of 12,491 UEIs; each attributed UEI's owner carries `names_per_owner`
    # name records, so the expected number of TRUE record pairs is the sum of
    # those, over the full cartesian. Note what this does and does not use:
    # it is a SCALE parameter taken from how many contractors have an owner at
    # all - it is not a label, and it says nothing about WHICH owner.
    ent_by_uid = defaultdict(list)
    for _, e in ent_df.iterrows():
        ent_by_uid[e["cedar_uid"]].append(e["unique_id"])
    attributed = con_df[con_df["current_cedar_uid"] != ""]["current_cedar_uid"]
    expected_pairs = sum(len(ent_by_uid.get(u, [])) or 1 for u in attributed)
    total_pairs = len(con_df) * len(ent_df)
    prior = expected_pairs / total_pairs
    log(f"  prior: {len(attributed):,} attributed UEIs -> {expected_pairs:,} "
        f"expected true record pairs / {total_pairs:,} = {prior:.3e} "
        f"(1 in {1/prior:,.0f})")

    settings.probability_two_random_records_match = prior
    db_api = DuckDBAPI()
    linker = Linker([con_model, ent_model], settings, db_api=db_api,
                    input_table_aliases=["contractor", "entity"])

    # --- training ---
    t0 = time.time()
    # THIS MODEL IS NOT REPRODUCIBLE RUN TO RUN, AND ENLARGING THE SAMPLE DOES
    # NOT FIX IT. Measured 2026-09-02 on byte-identical inputs:
    #
    #   max_pairs=5e6   (5 runs)  precision at p>=0.95: 79.2 - 85.4%
    #                             top-1 recall:         51.6 - 55.1%
    #   max_pairs=1e8   (3 runs)  precision at p>=0.95: 82.2 - 91.1%
    #                             top-1 recall:         51.6 - 53.6%
    #
    # 1e8 exceeds the 89,760,326 pairs that exist, so "sample the whole space"
    # is not available through this API - it still samples, and `seed=` does not
    # determinise it. Cost of the larger sample: u estimation 1.7s -> 45s, for
    # no reduction in spread. Default is therefore back to 5e6; override with
    # CEDAR_SPLINK_U_PAIRS to re-measure.
    #
    # CONSEQUENCE, and it is the one that decides the verdict: a FIXED
    # probability threshold does not mean the same thing tomorrow as today. Any
    # confidence band cut on raw `match_probability` inherits a several-point
    # swing that has nothing to do with the data.
    u_pairs = int(os.environ.get("CEDAR_SPLINK_U_PAIRS", 5_000_000))
    linker.training.estimate_u_using_random_sampling(max_pairs=u_pairs,
                                                     seed=SEED)
    log(f"  u sampled over max_pairs={u_pairs:,}")
    log(f"  u estimated in {time.time()-t0:.1f}s")

    # m from the owner's OWN adjudications, train half only.
    #
    # ONE LABEL PER (uei, owner), NOT ONE PER NAME RECORD. The first draft
    # labelled the contractor against EVERY name its owner carries. For an
    # owner with ten aliases that is one informative pair and nine pairs whose
    # comparison vector is the bottom level - and estimate_m_from_pairwise_
    # labels dutifully learned that "no distinctive token in common" is a
    # frequent signature of a TRUE match. It is not; it is a signature of an
    # alias that happens not to be the one the filer used. Label the name
    # record the filer actually resembles: highest comparison level, ties
    # broken by token overlap then by name length.
    def level_of(cname, ctoks, ename, etoks):
        if cname == ename:
            return (5, 0, 0)
        inter = len(set(ctoks) & set(etoks))
        subset = 1 if (etoks and set(etoks) <= set(ctoks) and len(etoks) >= 2) else 0
        return (4 if subset else (3 if inter >= 2 else (2 if inter else 0)),
                inter, -abs(len(cname) - len(ename)))

    cinfo = con_df.set_index("unique_id")
    einfo = ent_df.set_index("unique_id")
    lab = []
    label_levels = Counter()
    for uei, uid in truth_train.items():
        cands = ent_by_uid.get(uid, [])
        if not cands:
            continue
        c = cinfo.loc[uei]
        best = max(cands, key=lambda e: level_of(
            c["name_norm"], c["tok_arr"],
            einfo.loc[e]["name_norm"], einfo.loc[e]["tok_arr"]))
        label_levels[level_of(c["name_norm"], c["tok_arr"],
                              einfo.loc[best]["name_norm"],
                              einfo.loc[best]["tok_arr"])[0]] += 1
        lab.append({"source_dataset_l": "contractor", "unique_id_l": uei,
                    "source_dataset_r": "entity", "unique_id_r": best,
                    "clerical_match_score": 1.0})
    log(f"  label comparison-level census (5=exact .. 0=no shared token): "
        f"{dict(sorted(label_levels.items(), reverse=True))}")
    lab_df = pd.DataFrame(lab)
    lab_df.to_csv(OUT / "labels_train.csv", index=False)
    log(f"  m-training labels: {len(lab_df):,} pairs from {len(truth_train):,} "
        f"ruled UEIs")
    t0 = time.time()
    try:
        labels_tbl = linker.table_management.register_labels_table(lab_df)
        linker.training.estimate_m_from_pairwise_labels(labels_tbl)
        m_route = "estimate_m_from_pairwise_labels (owner rulings, train half)"
    except Exception as exc:                                   # pragma: no cover
        log(f"  !! label-based m failed ({exc}); falling back to EM")
        linker.training.estimate_parameters_using_expectation_maximisation(
            block_on("name_norm"))
        m_route = "expectation maximisation (label route failed)"
    log(f"  m estimated in {time.time()-t0:.1f}s via {m_route}")

    model = linker.misc.save_model_to_json()
    (OUT / "model.json").write_text(json.dumps(model, indent=1),
                                    encoding="utf-8")
    # Print the learned weights. A model whose parameters are not on the record
    # is a model nobody can argue with.
    log("\n  --- learned parameters (m, u, Bayes factor per level) ---")
    for c in model["comparisons"]:
        log(f"  {c['output_column_name']}:")
        for lv in c["comparison_levels"]:
            m_, u_ = lv.get("m_probability"), lv.get("u_probability")
            if m_ is None or u_ in (None, 0):
                log(f"    {lv.get('label_for_charts'):<52} m={m_} u={u_}")
            else:
                log(f"    {lv.get('label_for_charts'):<52} "
                    f"m={m_:.4g} u={u_:.4g} BF={m_/u_:>12,.1f}")

    # --- predict ---
    t0 = time.time()
    preds = linker.inference.predict(threshold_match_probability=0.001)
    pdf = preds.as_pandas_dataframe()
    t_predict = time.time() - t0
    log(f"  predict: {len(pdf):,} scored pairs in {t_predict:.1f}s")

    ent_uid = dict(zip(ent_df["unique_id"], ent_df["cedar_uid"]))
    ent_name = dict(zip(ent_df["unique_id"], ent_df["name_raw"]))
    ent_cls = dict(zip(ent_df["unique_id"], ent_df["entity_class"]))
    ent_st = dict(zip(ent_df["unique_id"], ent_df["state"]))
    pdf["cedar_uid"] = pdf["unique_id_r"].map(ent_uid)
    pdf["entity_name"] = pdf["unique_id_r"].map(ent_name)
    pdf["entity_class"] = pdf["unique_id_r"].map(ent_cls)
    pdf["entity_state"] = pdf["unique_id_r"].map(ent_st)

    # collapse to one row per (uei, cedar_uid): an entity has many name records
    # and the best-scoring one is the entity's score.
    best = (pdf.sort_values("match_probability", ascending=False)
              .drop_duplicates(["unique_id_l", "cedar_uid"]))
    best.to_csv(OUT / "scored_pairs.csv", index=False)
    log(f"  collapsed to {len(best):,} (uei, cedar_uid) candidate pairs")
    log(f"  TOTAL splink wall clock {time.time()-t_start:.1f}s")
    return 0


# ===================== evaluation =====================

BANDS_FILE = OUT / "bands.json"


def _load_scored():
    import pandas as pd
    return pd.read_csv(OUT / "scored_pairs.csv", dtype={"unique_id_l": str},
                       low_memory=False)


def cmd_evaluate(args) -> int:
    import pandas as pd
    df = _load_scored()
    truth = read(OUT / "truth.csv")
    test = {r["uei"]: r["cedar_uid"] for r in truth if r["split"] == "test"}
    train = {r["uei"]: r["cedar_uid"] for r in truth if r["split"] == "train"}
    neg = {r["uei"] for r in read(OUT / "negatives.csv") if r["in_prime"] == "Y"}

    # top-1 candidate per contractor
    top = (df.sort_values("match_probability", ascending=False)
             .drop_duplicates(["unique_id_l"]))
    top = top.set_index("unique_id_l")

    def curve(pool, label):
        rows = []
        for thr in [0.999, 0.99, 0.95, 0.9, 0.8, 0.7, 0.5, 0.3, 0.1,
                    0.05, 0.01, 0.001]:
            tp = fp = miss = 0
            for uei, gold in pool.items():
                if uei not in top.index:
                    miss += 1
                    continue
                r = top.loc[uei]
                if float(r["match_probability"]) < thr:
                    miss += 1
                elif r["cedar_uid"] == gold:
                    tp += 1
                else:
                    fp += 1
            n = len(pool)
            rows.append({"threshold": thr, "n": n, "tp": tp, "fp": fp,
                         "no_call": miss,
                         "precision": round(100*tp/max(1, tp+fp), 1),
                         "recall": round(100*tp/max(1, n), 1)})
        log(f"\n  === {label} (n={len(pool)}) ===")
        log("  thr      tp    fp  nocall   prec%   rec%")
        for r in rows:
            log(f"  {r['threshold']:<7} {r['tp']:>4}  {r['fp']:>4}  "
                f"{r['no_call']:>5}   {r['precision']:>5}  {r['recall']:>5}")
        return rows

    c_test = curve(test, "SPLINK held-out TEST")
    c_train = curve(train, "SPLINK TRAIN (leakage reference, not a result)")

    # TOP-K RECALL. Under the owner's reframe the queue shows CANDIDATES, so
    # "the right entity is somewhere in the shortlist" is the metric that
    # decides whether adjudication is cheap. Top-1 accuracy is the metric for
    # an autonomous matcher, which is explicitly not what is wanted.
    ranked = defaultdict(list)
    for _, r in df.sort_values("match_probability", ascending=False).iterrows():
        ranked[r["unique_id_l"]].append((r["cedar_uid"],
                                         float(r["match_probability"])))
    log("\n  === TOP-K RECALL, held-out test (is the true owner in the "
        "shortlist at all?) ===")
    topk = {}
    for k in (1, 2, 3, 5, 10):
        hit = sum(1 for u, g in test.items()
                  if any(c == g for c, _ in ranked.get(u, [])[:k]))
        topk[k] = round(100 * hit / len(test), 1)
        log(f"  top-{k:<3} {hit:>4}/{len(test)}  {topk[k]:>5}%")
    ceiling = sum(1 for u, g in test.items()
                  if any(c == g for c, _ in ranked.get(u, [])))
    log(f"  anywhere in candidate set: {ceiling}/{len(test)} "
        f"{100*ceiling/len(test):.1f}%   <- the blocking ceiling")

    # WHAT DO THE FALSE POSITIVES LOOK LIKE? A precision number cannot tell
    # you whether the errors are UKB/Cherokee-class. The rows can.
    log("\n  === top-1 FALSE POSITIVES at p>=0.5, held-out test ===")
    con_df = None
    import pandas as _pd
    con_df = _pd.read_csv(OUT / "contractors.csv", dtype=str,
                          keep_default_na=False).set_index("unique_id")
    fps = []
    for uei, gold in test.items():
        if uei not in top.index:
            continue
        r = top.loc[uei]
        if float(r["match_probability"]) >= 0.5 and r["cedar_uid"] != gold:
            gold_rank = next((i + 1 for i, (c, _) in enumerate(ranked[uei])
                              if c == gold), None)
            fps.append({
                "uei": uei,
                "contractor": con_df.loc[uei]["name_raw"],
                "state": con_df.loc[uei]["state"],
                "p": round(float(r["match_probability"]), 4),
                "splink_said": r["entity_name"],
                "truth_is": gold,
                "truth_rank_in_candidates": gold_rank or "ABSENT",
                "dollars": con_df.loc[uei]["dollars"],
            })
    fps.sort(key=lambda x: -x["p"])
    with (OUT / "false_positives.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fps[0].keys()))
        w.writeheader()
        w.writerows(fps)
    for x in fps[:25]:
        log(f"  p={x['p']:<7} {x['contractor'][:40]:<40} {x['state']:<3} -> "
            f"{x['splink_said'][:34]:<34} (truth rank "
            f"{x['truth_rank_in_candidates']})")
    log(f"  {len(fps)} false positives at p>=0.5 -> "
        f"{OUT/'false_positives.csv'}")

    # negatives: what does splink do with UEIs the owner ruled NOT native
    nrows = []
    for thr in [0.999, 0.99, 0.95, 0.9, 0.8, 0.5, 0.1]:
        fired = sum(1 for u in neg if u in top.index
                    and float(top.loc[u]["match_probability"]) >= thr)
        nrows.append({"threshold": thr, "fired": fired, "n": len(neg)})
    log(f"\n  === SPLINK vs {len(neg)} tier-X NEGATIVE rulings ===")
    for r in nrows:
        log(f"  thr {r['threshold']:<7} would link {r['fired']:>3} / {r['n']}"
            f"  ({100*r['fired']/max(1,r['n']):.1f}%)")

    # HEAD TO HEAD, on the same held-out rows, plus the UNION - the question
    # the reframe actually asks: does splink SURFACE anything the incumbent
    # misses, at a confidence the owner could triage?
    base = {r["uei"]: r for r in read(OUT / "baseline_truth.csv")
            if r["split"] == "test"}
    log("\n  === HEAD TO HEAD on the held-out test set ===")
    b_prop = [u for u, r in base.items() if r["baseline_cedar_uid"]]
    b_right = [u for u in b_prop if base[u]["baseline_correct"] == "1"]
    log(f"  incumbent 503     : proposed {len(b_prop):>3}  correct "
        f"{len(b_right):>3}  precision {100*len(b_right)/max(1,len(b_prop)):.1f}%"
        f"  recall {100*len(b_right)/len(base):.1f}%")
    h2h = []
    for thr in (0.95, 0.5, 0.3, 0.1, 0.001):
        s_prop = {u for u in test
                  if u in top.index and float(top.loc[u]["match_probability"]) >= thr}
        s_right = {u for u in s_prop if top.loc[u]["cedar_uid"] == test[u]}
        # rows the incumbent declined that splink gets right
        rescued = s_right - set(b_prop)
        # rows the incumbent got right that splink would overwrite wrongly
        broken = {u for u in s_prop - s_right if u in set(b_right)}
        h2h.append({"threshold": thr, "splink_proposed": len(s_prop),
                    "splink_correct": len(s_right),
                    "rescued_from_incumbent_no_call": len(rescued),
                    "would_break_an_incumbent_correct": len(broken)})
        log(f"  splink p>={thr:<6}: proposed {len(s_prop):>3}  correct "
            f"{len(s_right):>3}  RESCUED (503 said nothing) {len(rescued):>3}"
            f"  WOULD BREAK a 503 correct {len(broken):>3}")

    json.dump({"test": c_test, "train": c_train, "negatives": nrows,
               "top_k_recall": topk, "head_to_head": h2h,
               "n_false_positives_at_0.5": len(fps)},
              (OUT / "eval.json").open("w", encoding="utf-8"), indent=1)
    return 0


# ===================== the three collision cases =====================

# The three named pairs, keyed by cedar_uid -> the state that decides them.
# Verified against data/spine/cedar_entity_spine.csv on 2026-09-02.
COLLISION_PAIRS = [
    {"CE-00150-XS": "WI",   # Ho-Chunk Nation of Wisconsin
     "CE-001C8-GH": "NE"},  # Winnebago Tribe of Nebraska (owns Ho-Chunk Inc)
    {"CE-0014B-TW": "NC",   # Eastern Cherokee (Eastern Band, NC)
     "CE-00134-BX": "OK",   # Cherokee Nation (OK)
     "CE-001BS-HA": "OK"},  # United Keetoowah Band (OK) - the $181.9M merge
    {"CE-001A9-CA": "FL",   # Seminole Tribe of Florida
     "CE-001AA-J3": "OK"},  # The Seminole Nation of Oklahoma
]

COLLISIONS = [
    ("Ho-Chunk Inc", "Ho-Chunk Nation of Wisconsin",
     "Ho-Chunk Inc is the WINNEBAGO TRIBE OF NEBRASKA's holding company. "
     "A link to Ho-Chunk Nation (WI) is disqualifying."),
    ("Eastern Band of Cherokee Indians", "Cherokee Nation (Oklahoma)",
     "Two distinct federally recognized tribes, NC and OK. Also United "
     "Keetoowah Band, OK - the $181,881,441.37 / 820-row merge."),
    ("The Seminole Nation of Oklahoma", "Seminole Tribe of Florida",
     "Two distinct federally recognized tribes, OK and FL."),
]


def cmd_collisions(args) -> int:
    import pandas as pd
    df = _load_scored()
    ent = pd.read_csv(OUT / "entities.csv", dtype=str, keep_default_na=False)
    con_df = pd.read_csv(OUT / "contractors.csv", dtype=str,
                         keep_default_na=False)
    bands = json.loads(BANDS_FILE.read_text()) if BANDS_FILE.exists() else \
        {"accept": 0.99, "reject": 0.5}

    log("\n  === THE THREE NAMED COLLISION CASES ===")
    log(f"  bands in force: auto-accept >= {bands['accept']}, "
        f"adjudicate {bands['reject']}-{bands['accept']}, "
        f"auto-reject < {bands['reject']}")
    rep = []
    probe = ["HO CHUNK", "CHEROKEE", "SEMINOLE", "KEETOOWAH"]
    for word in probe:
        # every contractor whose name carries the token
        cands = con_df[con_df["name_norm"].str.contains(
            word, regex=False, na=False)]
        for _, c in cands.iterrows():
            sub = df[df["unique_id_l"] == c["unique_id"]]
            if sub.empty:
                continue
            sub = sub.sort_values("match_probability", ascending=False).head(4)
            tops = [(r["entity_name"], r["cedar_uid"],
                     round(float(r["match_probability"]), 4))
                    for _, r in sub.iterrows()]
            band = ("AUTO_ACCEPT" if tops[0][2] >= bands["accept"]
                    else "ADJUDICATE" if tops[0][2] >= bands["reject"]
                    else "AUTO_REJECT")
            rep.append({"token": word, "contractor": c["name_raw"],
                        "uei": c["unique_id"], "state": c["state"],
                        "dollars": c["dollars"],
                        "current_cedar_uid": c["current_cedar_uid"],
                        "band": band,
                        "top_candidates": "; ".join(
                            f"{n} [{u}] p={p}" for n, u, p in tops)})
    with (OUT / "collisions.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rep[0].keys()))
        w.writeheader()
        w.writerows(rep)
    for r in rep:
        log(f"  [{r['band']:<11}] {r['token']:<9} {r['contractor'][:44]:<44} "
            f"{r['state']:<3} -> {r['top_candidates'][:110]}")
    log(f"  wrote {OUT/'collisions.csv'} ({len(rep)} rows)")
    return 0


# ===================== verify =====================

def cmd_verify(args) -> int:
    """Invariants. Exits 1 on any breach. Named, so the reader knows WHICH."""
    fails = []

    def check(name, ok, detail=""):
        log(f"  [{'PASS' if ok else 'FAIL'}] {name}  {detail}")
        if not ok:
            fails.append(name)

    # I1. No pilot output may sit in data/clean, data/spine or dist.
    stray = [p for p in (ROOT / "data" / "clean").glob("*splink*")] + \
            [p for p in (ROOT / "data" / "spine").glob("*splink*")]
    check("I1_no_writes_outside_interim", not stray, f"{len(stray)} stray")

    # I2. Held-out test UEIs must not appear in the m-training labels.
    if (OUT / "labels_train.csv").exists() and (OUT / "truth.csv").exists():
        lab = {r["unique_id_l"] for r in read(OUT / "labels_train.csv")}
        test = {r["uei"] for r in read(OUT / "truth.csv") if r["split"] == "test"}
        leak = lab & test
        check("I2_no_test_leakage_into_labels", not leak,
              f"{len(leak)} leaked UEIs")
    else:
        check("I2_no_test_leakage_into_labels", False, "inputs missing")

    # I3. Every truth owner cedar_uid exists in the entities table.
    if (OUT / "entities.csv").exists():
        known = {r["cedar_uid"] for r in read(OUT / "entities.csv")}
        bad = {r["cedar_uid"] for r in read(OUT / "truth.csv")} - known
        check("I3_truth_owner_in_spine", not bad, f"{len(bad)} unknown uid")
    else:
        check("I3_truth_owner_in_spine", False, "entities.csv missing")

    # I4. THE DISQUALIFIER, stated by cedar_uid and not by word.
    #     For each named collision pair, an AUTO_ACCEPT link may not send a
    #     contractor to the member of the pair whose state DISAGREES with the
    #     contractor's, when the other member's state agrees. That is exactly
    #     the shape of the UKB/Cherokee merge and of Ho-Chunk Inc -> Wisconsin.
    if (OUT / "collisions.csv").exists():
        bad = []
        for r in read(OUT / "collisions.csv"):
            if r["band"] != "AUTO_ACCEPT":
                continue
            top_uid = re.search(r"\[(CE-[0-9A-Z-]+)\]", r["top_candidates"])
            if not top_uid:
                continue
            got, st = top_uid.group(1), r["state"]
            for pair in COLLISION_PAIRS:
                if got not in pair:
                    continue
                other = [u for u in pair if u != got]
                if pair[got] != st and any(pair[o] == st for o in other):
                    bad.append(f"{r['contractor']} ({st}) -> {got} "
                               f"[{pair[got]}] while a same-state member exists")
            # AND: state cannot separate Cherokee Nation from the United
            # Keetoowah Band - both are Oklahoma. So the second clause is
            # state-free: if the top TWO candidates are two different members
            # of one collision pair, the model is choosing between two
            # federally recognized tribes and may never auto-accept.
            uids = re.findall(r"\[(CE-[0-9A-Z-]+)\]", r["top_candidates"])[:2]
            if len(uids) == 2 and uids[0] != uids[1]:
                for pair in COLLISION_PAIRS:
                    if uids[0] in pair and uids[1] in pair:
                        bad.append(f"{r['contractor']}: top-2 are two members "
                                   f"of one collision pair ({uids[0]}/{uids[1]})")
        check("I4_no_autoaccept_collision_merge", not bad, f"{bad[:3]}")
    else:
        check("I4_no_autoaccept_collision_merge", False, "collisions.csv missing")

    # I5. Fixture: the checker must FIRE on a synthetic violation.
    if args.selftest:
        log("\n  -- selftest: injecting a synthetic violation of I2 --")
        p = OUT / "labels_train.csv"
        backup = p.read_text(encoding="utf-8")
        test = [r["uei"] for r in read(OUT / "truth.csv")
                if r["split"] == "test"][:1]
        with p.open("a", encoding="utf-8", newline="") as f:
            f.write(f"contractor,{test[0]},entity,E000001,1.0\n")
        sub = argparse.Namespace(selftest=False)
        rc = cmd_verify(sub)
        p.write_text(backup, encoding="utf-8")
        if rc == 0:
            log("  !! SELFTEST FAILED: I2 did not fire on an injected leak")
            fails.append("I5_selftest_did_not_fire")
        else:
            log("  selftest OK: I2 fired on the injected leak, then restored")
        rc2 = cmd_verify(argparse.Namespace(selftest=False))
        if rc2 != 0:
            log("  !! restore did not clear the injected violation")
            fails.append("I5_restore_failed")

        # I4 PASSES TRIVIALLY WHILE THE AUTO_ACCEPT BAND IS EMPTY, and an
        # invariant that has never had anything to refuse is not known to work.
        # Drop the accept cut to 0.5 - which the held-out curve says is NOT an
        # auto-accept grade - rebuild the collision table, and require I4 to
        # fire on the Cherokee Nation / United Keetoowah top-2 pairs.
        log("\n  -- selftest: lowering the accept cut to 0.5 so I4 has "
            "something to refuse --")
        keep = BANDS_FILE.read_text(encoding="utf-8") if BANDS_FILE.exists() \
            else '{"accept": 0.999, "reject": 0.1}'
        BANDS_FILE.write_text('{"accept": 0.5, "reject": 0.1}', encoding="utf-8")
        try:
            cmd_collisions(argparse.Namespace())
            rc3 = cmd_verify(argparse.Namespace(selftest=False))
            if rc3 == 0:
                log("  !! SELFTEST FAILED: I4 did not fire at accept=0.5")
                fails.append("I5_I4_selftest_did_not_fire")
            else:
                log("  selftest OK: I4 fired at accept=0.5")
        finally:
            BANDS_FILE.write_text(keep, encoding="utf-8")
            cmd_collisions(argparse.Namespace())
        if cmd_verify(argparse.Namespace(selftest=False)) != 0:
            log("  !! restore did not clear the I4 violation")
            fails.append("I5_I4_restore_failed")

    if fails:
        log(f"\n  VERIFY FAILED: {', '.join(fails)}")
        return 1
    log("\n  verify: all invariants hold")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("prep", "baseline", "splink", "evaluate", "collisions"):
        sub.add_parser(name)
    v = sub.add_parser("verify")
    v.add_argument("--selftest", action="store_true")
    q = sub.add_parser("queue")
    q.add_argument("--accept", type=float, default=None)
    q.add_argument("--reject", type=float, default=None)
    a = sub.add_parser("all")
    args = ap.parse_args()

    fns = {"prep": cmd_prep, "baseline": cmd_baseline, "splink": cmd_splink,
           "evaluate": cmd_evaluate, "collisions": cmd_collisions,
           "verify": cmd_verify}
    if args.cmd == "queue":
        return cmd_queue(args)
    if args.cmd == "all":
        for k in ("prep", "baseline", "splink", "evaluate", "collisions"):
            log(f"\n===== {k} =====")
            rc = fns[k](argparse.Namespace())
            if rc:
                return rc
        return cmd_verify(argparse.Namespace(selftest=True))
    return fns[args.cmd](args)


# ===================== the adjudication queue =====================

def cmd_queue(args) -> int:
    """The owner adjudication queue - a FIRST-CLASS output.

    Carries what the owner's ladder needs, in the row, so he is not
    re-researching from scratch:
      rung 1 address   -> contractor city/state AND the entity's state
      rung 2 website   -> the entity's own site from the spine
      rung 3 the address itself -> other UEIs at the same city+state, and
                                   whether any of them is already keyed
      rung 4 CAGE      -> the contractor's CAGE, as a pointer to the next name
      rung 5 news      -> left to the owner; a link is the whole requirement
      rung 6 STOP      -> `unresolved` is a legitimate answer and the form says so
    """
    import pandas as pd
    bands = json.loads(BANDS_FILE.read_text()) if BANDS_FILE.exists() else {}
    accept = args.accept if args.accept is not None else bands.get("accept", 0.99)
    reject = args.reject if args.reject is not None else bands.get("reject", 0.50)
    BANDS_FILE.write_text(json.dumps({"accept": accept, "reject": reject},
                                     indent=1), encoding="utf-8")

    df = _load_scored()
    con_df = pd.read_csv(OUT / "contractors.csv", dtype=str,
                         keep_default_na=False)
    ent = pd.read_csv(OUT / "entities.csv", dtype=str, keep_default_na=False)
    site = dict(zip(ent["cedar_uid"], ent["website"]))
    truth_uei = {r["uei"] for r in read(OUT / "truth.csv")}
    negs = {r["uei"] for r in read(OUT / "negatives.csv")}

    # rung 3: co-located UEIs, and whether any is already keyed
    at = defaultdict(list)
    for _, c in con_df.iterrows():
        if c["city"] and c["state"]:
            at[(c["city"], c["state"])].append(
                (c["unique_id"], c["name_raw"], c["current_cedar_uid"]))

    top = (df.sort_values("match_probability", ascending=False)
             .drop_duplicates(["unique_id_l"]))
    second = (df.sort_values("match_probability", ascending=False)
                .groupby("unique_id_l").nth(1))
    sec = {}
    try:
        for _, r in second.reset_index().iterrows():
            sec[r["unique_id_l"]] = (r["entity_name"],
                                     float(r["match_probability"]))
    except Exception:
        pass

    cinfo = con_df.set_index("unique_id")
    rows = []
    for _, r in top.iterrows():
        uei = r["unique_id_l"]
        p = float(r["match_probability"])
        if uei in truth_uei or uei in negs:
            continue                       # already ruled; not a question
        c = cinfo.loc[uei]
        if c["current_cedar_uid"]:
            continue                       # already attributed in prime
        band = ("AUTO_ACCEPT" if p >= accept
                else "ADJUDICATE" if p >= reject else "AUTO_REJECT")
        if band == "AUTO_REJECT":
            continue
        nb = [(n, u) for i, n, u in at.get((c["city"], c["state"]), [])
              if i != uei][:6]
        keyed = [f"{n} [{u}]" for n, u in nb if u]
        s = sec.get(uei)
        rows.append({
            "band": band,
            "match_probability": round(p, 5),
            "runner_up": f"{s[0]} p={s[1]:.4f}" if s else "",
            "margin_over_runner_up": round(p - s[1], 5) if s else "",
            "uei": uei,
            "contractor_name": c["name_raw"],
            "contractor_city": c["city"],
            "contractor_state": c["state"],
            "cage_code": c["cage"],
            "declared_parent_name": c["parent_name"],
            "declared_parent_uei": c["parent_uei"],
            "naics": c["naics"],
            "prime_dollars": c["dollars"],
            "fy_range": f"{c['fy_min']}-{c['fy_max']}",
            "proposed_cedar_uid": r["cedar_uid"],
            "proposed_entity_name": r["entity_name"],
            "proposed_entity_class": r["entity_class"],
            "proposed_entity_state": r["entity_state"],
            "state_agrees": "Y" if (c["state"] and c["state"] == r["entity_state"])
                            else ("?" if not r["entity_state"] else "N"),
            "rung2_entity_website": site.get(r["cedar_uid"], ""),
            "rung3_other_ueis_at_this_address": "; ".join(n for n, _ in nb),
            "rung3_already_keyed_at_this_address": "; ".join(keyed),
            "owner_ruling": "",
            "owner_ruling_options": "ACCEPT | REFUSE | REPOINT:<cedar_uid> | UNRESOLVED",
            "owner_note": "",
        })
    rows.sort(key=lambda r: -float(r["prime_dollars"] or 0))
    REVIEW.mkdir(exist_ok=True)
    p = REVIEW / f"splink_pilot_adjudication_queue_{TODAY}.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    ca = sum(1 for r in rows if r["band"] == "AUTO_ACCEPT")
    log(f"  queue: {len(rows):,} rows -> {p}")
    log(f"    AUTO_ACCEPT {ca:,}   ADJUDICATE {len(rows)-ca:,}")
    log(f"    dollars in queue: "
        f"${sum(float(r['prime_dollars'] or 0) for r in rows)/1e9:.2f}B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
