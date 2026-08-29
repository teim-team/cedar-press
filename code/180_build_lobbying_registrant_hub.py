#!/usr/bin/env python3
"""
Cedar Press - 180: the LOBBYING REGISTRANT as a first-class hub.

WHY THIS EXISTS
---------------
Elijah, 2026-08-26:

    "for lobbying, it's probably worth adding the firm that was hired to lobby,
     and maybe we can get more info on them from IRS 990 or other sources. The
     non-Native lobbying firm who isn't a tribe will have more data than the
     tribe, and we can link them to Native entities."

`data/clean/native_entity_lobbying_disclosures.csv` already carries
`registrant_id`, `registrant_name` and `registrant_state` on all 27,796 rows.
They are bare strings on a filing. Nothing in this project has ever treated the
registrant as an ENTITY, so nobody can ask:

    - which firms represent Indian Country before the federal government
    - how concentrated that representation is
    - which of those firms are themselves Native

`registrant_id` is a stable federal identifier issued by the Senate Office of
Public Records / Clerk of the House LDA system. It is the key here, never the
name: three registrant_ids in this corpus carry more than one name over time
(a rename is not a new firm).

WHAT THIS SCRIPT WRITES
-----------------------
    data/clean/lobbying_registrants.csv
        one row per registrant_id observed anywhere in the Native LDA corpus

    data/clean/lobbying_registrant_client_relationships.csv
        one row per (registrant_id, client_id) - who represents whom, over
        what period, on what issues

    data/clean/lobbying_registrant_concentration.csv
        the concentration measures, overall and per filing year, plus the
        reverse measure (how many firms each Native entity uses)

    review/lobbying_registrant_data_quality_2026-08-26.csv
        registrants that must not be read as ordinary firms

TWO SOURCES, AND THE DIFFERENCE BETWEEN THEM MATTERS
----------------------------------------------------
1. `code/lobbying_pull/raw_filings.jsonl` - 39,448 filings, the FULL pulled
   corpus including the 11,652 whose client never matched a Native entity. It
   carries the registrant's own LDA record: description, street address, city,
   state, zip, contact name, `house_registrant_id`, and the per-activity
   lobbyist roster with `covered_position`. The keyed CSV drops all of it.

2. `data/clean/native_entity_lobbying_disclosures.csv` - 27,796 filings that
   matched, 26,955 of them keyed to a Native entity.

**The corpus is a KEYWORD PULL, not a registrant's book of business.** Every
`*_corpus` count in the hub is a FLOOR on that firm's practice: it counts only
the filings this project's Native keyword nets caught. A firm with 800 filings
here may have 8,000 in LDA. `n_clients_corpus` is NOT the firm's client count
and the column name says `_corpus` for that reason. Only the `*_native_*`
columns are statements about Indian Country work.

THE SPEND FIGURE IS DEDUPLICATED, AND THE NAIVE SUM IS 6.3% TOO BIG
--------------------------------------------------------------------
An LDA amendment RESTATES a quarter; a termination report covers the final
quarter. Summing `spend_usd` over filings therefore counts the same money
twice on 2,269 of 24,384 (registrant, client, year, period) cells:

    naive sum over filings                 $685.8M
    per-cell maximum                       $650.4M
    per-cell latest-posted filing          $645.0M   <- published

The published figure takes the value from the filing with the latest
`dt_posted` in each cell, because an amendment SUPERSEDES what it amends. All
three are written to the hub so the choice is visible and reversible.

CAVEATS THAT TRAVEL WITH EVERY DOLLAR HERE
------------------------------------------
- LDA income/expenses is a good-faith estimate **rounded to $10,000**. Never
  print it to the dollar.
- 11,145 of 26,955 keyed filings (41.3%) report NO dollar figure at all
  (`spend_basis = none_reported`). The source file carries them as 0. A zero in
  this dataset is "reported nothing", not "spent nothing".
- Income and expenses are either/or: outside registrants report income,
  self-filers report expenses. 122 expense rows against 15,688 income rows is
  correct, not a gap.

WHAT THIS SCRIPT REFUSES TO DO
------------------------------
- It never runs `resolve_entity`. Every entity link on every row is INHERITED
  verbatim from the keyed disclosure row that already carried it, together with
  that row's `attribution_method` and `match_confidence`. Sweeping 653 firm
  names for tribes is detection, which AGENTS.md forbids containment for, and
  it is how "READ & STEVENS, INC. -> Stevens Village" happens.
- It never writes `position_on_native_issue`, or any other characterisation of
  a firm's stance. `docs/LOBBYING_EXPANSION_RECONCILIATION.md` settled that.
- It drops the 841 rows the organisation-type guard (script 65) already
  withdrew - 333 of them SALT RIVER PROJECT, an Arizona public power and
  irrigation district that is not the Salt River Pima-Maricopa Indian
  Community. Those filings stay in the corpus counts and out of every Native
  count, and `n_filings_org_type_barred` says so per registrant.

Zero network calls. Reads shared tables and writes only its own outputs.
"""

import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CEDAR / "code"))
# 2026-08-26: this script tested `org_type_barred` alone, so the 471 filings
# withdrawn by 350_withdraw_false_lobbying_attributions.py - Santa Rosa County
# FL, Santa Rosa Junior College, Coeur d'Alene MINING, BBEDC, BBAHC - would
# have been re-imported as native-keyed on the next run. A consumer that tests
# for ONE SPELLING of a correction is blind to the next one. The predicate is
# declared once, in cedar_domain, and every mark is read there.
from cedar_domain import lobbying_attribution_withdrawn   # noqa: E402

CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
RAW_JSONL = CEDAR / "code" / "lobbying_pull" / "raw_filings.jsonl"
DISCLOSURES = CLEAN / "native_entity_lobbying_disclosures.csv"

HUB = CLEAN / "lobbying_registrants.csv"
RELS = CLEAN / "lobbying_registrant_client_relationships.csv"
CONC = CLEAN / "lobbying_registrant_concentration.csv"
DQ = REVIEW / "lobbying_registrant_data_quality_2026-08-26.csv"

TODAY = date.today().isoformat()
SCRIPT = "180_build_lobbying_registrant_hub.py"

csv.field_size_limit(min(sys.maxsize, 2147483647))


def log(m=""):
    print(m, flush=True)


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def write_csv(path, rows, fields):
    """`.part` then rename - an interruption must not look like a completion."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    with open(part, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    if path.exists():
        bak = path.with_name(path.name + f".bak_{TODAY}_pre_{SCRIPT}")
        if not bak.exists():
            bak.write_bytes(path.read_bytes())
            log(f"  backed up -> {bak.name}")
    os.replace(part, path)


def j(vals, sep="|"):
    return sep.join(str(v) for v in vals if str(v).strip())


def top_counter(c, n=6):
    return j(f"{k}:{v}" for k, v in c.most_common(n) if str(k).strip())


def to_int(x, d=0):
    try:
        return int(float(x))
    except Exception:
        return d


def to_f(x, d=0.0):
    try:
        v = float(x)
        return d if v != v else v
    except Exception:
        return d


# ---------------------------------------------------------------------------
# 1. the registrant's own LDA record, and everything the keyed CSV drops
# ---------------------------------------------------------------------------

def read_raw():
    """Per registrant: LDA record, corpus footprint, lobbyists, covered posts.

    `contact_telephone` is deliberately NOT carried forward. It is on the
    public filing, it has no analytic use here, and a dataset should not
    republish a contact detail it does not need. `contact_name` IS carried: a
    named LDA contact is a person acting in a public professional capacity,
    the same standard under which this project publishes a WAVES visitee.
    """
    regs, footprint = {}, defaultdict(lambda: {
        "filings": 0, "clients": {}, "years": [], "issues": Counter(),
        "gov": Counter(), "lobbyists": set(), "lob_rows": 0, "covered": 0,
        "covered_text": Counter(), "self_filed": 0,
    })
    if not RAW_JSONL.exists():
        log(f"  !! {RAW_JSONL} absent - corpus columns will be blank")
        return regs, footprint

    n = 0
    with open(RAW_JSONL, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            n += 1
            r = d.get("registrant") or {}
            rid = r.get("id")
            if rid is None:
                continue
            rid = str(rid)
            prev = regs.get(rid)
            # keep the record from the most recently updated registrant blob
            if prev is None or (r.get("dt_updated") or "") >= (prev.get("dt_updated") or ""):
                regs[rid] = r
            f = footprint[rid]
            f["filings"] += 1
            c = d.get("client") or {}
            if c.get("id") is not None:
                f["clients"][str(c["id"])] = c.get("name")
                if (c.get("name") or "").strip().upper() == (r.get("name") or "").strip().upper():
                    f["self_filed"] += 1
            y = to_int(d.get("filing_year"), 0)
            if y:
                f["years"].append(y)
            for a in d.get("lobbying_activities") or []:
                code = (a.get("general_issue_code") or "").strip()
                if code:
                    f["issues"][code] += 1
                for g in a.get("government_entities") or []:
                    nm = g.get("name") if isinstance(g, dict) else g
                    if nm:
                        f["gov"][str(nm)] += 1
                for lo in a.get("lobbyists") or []:
                    f["lob_rows"] += 1
                    lid = (lo.get("lobbyist") or {}).get("id")
                    if lid is not None:
                        f["lobbyists"].add(str(lid))
                    cp = (lo.get("covered_position") or "").strip()
                    if cp and cp.upper().replace(".", "") not in (
                            "N/A", "NA", "NONE", "-", "NOT APPLICABLE", ""):
                        f["covered"] += 1
                        f["covered_text"][cp] += 1
    log(f"  raw corpus: {n:,} filings, {len(regs)} distinct registrants")
    return regs, footprint


# ---------------------------------------------------------------------------
# 2. the keyed Native side
# ---------------------------------------------------------------------------

def dedup_period_spend(rows):
    """{(rid, client_id, year, period): (latest_posted, max, n_filings)}.

    An amendment restates the period it amends, so a sum over filings counts
    the same money twice. The published value is the one on the filing with the
    latest dt_posted in the cell.
    """
    cells = defaultdict(list)
    for r in rows:
        k = (r["registrant_id"], r["client_id"], r["filing_year"],
             r["filing_period"])
        cells[k].append(r)
    out = {}
    for k, rs in cells.items():
        def posted(x):
            s = (x.get("dt_posted") or "")[:19]
            try:
                return datetime.fromisoformat(s)
            except Exception:
                return datetime.min
        rs_sorted = sorted(rs, key=posted)
        latest = to_f(rs_sorted[-1].get("spend_usd"))
        mx = max(to_f(x.get("spend_usd")) for x in rs)
        out[k] = (latest, mx, len(rs))
    return out


def main():
    log("=== Cedar Press 180: lobbying registrant hub ===\n")

    regs, foot = read_raw()

    disc = read_csv(DISCLOSURES)
    log(f"  disclosures: {len(disc):,} rows")
    barred = [r for r in disc if lobbying_attribution_withdrawn(r)]
    live = [r for r in disc if not lobbying_attribution_withdrawn(r)]
    keyed = [r for r in live if (r.get("entity_id") or "").strip()]
    log(f"    withdrawn attributions (65 org-type + 350 false-attribution): "
        f"{len(barred):,}")
    log(f"    live: {len(live):,}   keyed to a Native entity: {len(keyed):,}")

    cells = dedup_period_spend(keyed)
    naive = sum(to_f(r.get("spend_usd")) for r in keyed)
    latest_total = sum(v[0] for v in cells.values())
    max_total = sum(v[1] for v in cells.values())
    log(f"    spend  naive ${naive/1e6:,.1f}M · per-cell max "
        f"${max_total/1e6:,.1f}M · latest-posted ${latest_total/1e6:,.1f}M")

    # ---------------- relationship grain: (registrant, client) --------------
    pair = defaultdict(lambda: {
        "filings": 0, "years": set(), "issues": Counter(), "gov": Counter(),
        "spend_latest": 0.0, "spend_max": 0.0, "spend_naive": 0.0,
        "no_dollar": 0, "urls": [], "terminations": set(),
        "methods": Counter(), "confidences": Counter(), "aliases": Counter(),
        "self_filed": 0, "periods": set(),
    })
    meta = {}
    for r in live:
        rid, cid = r["registrant_id"], r["client_id"]
        p = pair[(rid, cid)]
        p["filings"] += 1
        y = to_int(r.get("filing_year"))
        if y:
            p["years"].add(y)
        p["periods"].add((r.get("filing_year"), r.get("filing_period")))
        for c in (r.get("lobbying_issues_codes") or "").split("|"):
            if c.strip():
                p["issues"][c.strip()] += 1
        for g in (r.get("government_entities") or "").split("|"):
            if g.strip():
                p["gov"][g.strip()] += 1
        p["spend_naive"] += to_f(r.get("spend_usd"))
        if (r.get("spend_basis") or "") == "none_reported":
            p["no_dollar"] += 1
        if r.get("filing_url"):
            p["urls"].append((r.get("dt_posted") or "", r["filing_url"]))
        if (r.get("termination_date") or "").strip():
            p["terminations"].add(r["termination_date"])
        if (r.get("self_filed") or "") == "1":
            p["self_filed"] += 1
        if (r.get("attribution_method") or "").strip():
            p["methods"][r["attribution_method"]] += 1
        if (r.get("match_confidence") or "").strip():
            p["confidences"][r["match_confidence"]] += 1
        if (r.get("matched_alias") or "").strip():
            p["aliases"][r["matched_alias"]] += 1
        meta[(rid, cid)] = {
            "registrant_name": r.get("registrant_name"),
            "registrant_state": r.get("registrant_state"),
            "client_name": r.get("client_name"),
            "client_state": r.get("client_state"),
            "entity_id": r.get("entity_id"),
            "canonical_name": r.get("canonical_name"),
            "entity_type": r.get("entity_type"),
            "entity_state": r.get("entity_state"),
        }
    for (rid, cid, yr, per), (lat, mx, _n) in cells.items():
        pair[(rid, cid)]["spend_latest"] += lat
        pair[(rid, cid)]["spend_max"] += mx

    rel_rows = []
    for (rid, cid), p in sorted(pair.items(),
                               key=lambda kv: -kv[1]["filings"]):
        m = meta[(rid, cid)]
        yrs = sorted(p["years"])
        urls = sorted(p["urls"])
        # A tier is INHERITED. The relationship carries the WEAKEST confidence
        # seen on any filing in the pair, never the best one, and the modal
        # attribution_method that produced it.
        conf_order = ["withdrawn_org_type", "withdrawn_false_attribution",
                      "low", "medium", "high"]
        confs = [c for c in conf_order if p["confidences"].get(c)]
        rel_rows.append({
            "registrant_id": rid,
            "registrant_name": m["registrant_name"],
            "registrant_state": m["registrant_state"],
            "client_id": cid,
            "client_name": m["client_name"],
            "client_state_on_filing": m["client_state"],
            "native_entity_id": m["entity_id"] or "",
            "native_entity_canonical_name": m["canonical_name"] or "",
            "native_entity_class": m["entity_type"] or "",
            "native_entity_state": m["entity_state"] or "",
            "client_is_keyed_native": "1" if (m["entity_id"] or "") else "0",
            "entity_link_confidence_inherited": confs[0] if confs else "",
            "entity_link_confidence_all": top_counter(p["confidences"], 4),
            "entity_link_attribution_method_inherited":
                p["methods"].most_common(1)[0][0] if p["methods"] else "",
            "entity_link_matched_alias":
                p["aliases"].most_common(1)[0][0] if p["aliases"] else "",
            "n_filings": p["filings"],
            "n_reporting_periods": len(p["periods"]),
            "first_filing_year": yrs[0] if yrs else "",
            "last_filing_year": yrs[-1] if yrs else "",
            "n_distinct_filing_years": len(yrs),
            "engagement_span_years": (yrs[-1] - yrs[0] + 1) if yrs else "",
            "self_filed_n": p["self_filed"],
            "spend_reported_usd": round(p["spend_latest"], 2),
            "spend_sensitivity_percell_max_usd": round(p["spend_max"], 2),
            "spend_sensitivity_naive_sum_usd": round(p["spend_naive"], 2),
            "n_filings_reporting_no_dollar": p["no_dollar"],
            "issue_codes": top_counter(p["issues"], 10),
            "n_distinct_issue_codes": len(p["issues"]),
            "government_entities_lobbied": top_counter(p["gov"], 10),
            "termination_dates": j(sorted(p["terminations"])),
            "first_filing_url": urls[0][1] if urls else "",
            "last_filing_url": urls[-1][1] if urls else "",
            "source": "Senate LDA filings API (lda.senate.gov), via "
                      "code/lobbying_pull",
            "built_by_script": SCRIPT,
            "built_date": TODAY,
        })
    rel_fields = list(rel_rows[0].keys())
    write_csv(RELS, rel_rows, rel_fields)
    log(f"\n  wrote {RELS.name}: {len(rel_rows):,} registrant-client pairs")

    # ---------------- hub grain: registrant -------------------------------
    by_reg = defaultdict(list)
    for r in rel_rows:
        by_reg[r["registrant_id"]].append(r)
    # `n_filings_org_type_barred` is a REGISTERED, DOCUMENTED column and it
    # means the script-65 org-type guard specifically. It keeps that meaning:
    # widening a column's contents while keeping its name is how
    # `prime_contracts.extent_competed` became two vocabularies. The 350
    # withdrawals are counted separately and reported in the run log.
    barred_by_reg = Counter(r["registrant_id"] for r in barred
                            if (r.get("org_type_barred") or "").strip())
    withdrawn_other = Counter(r["registrant_id"] for r in barred
                              if not (r.get("org_type_barred") or "").strip())
    if withdrawn_other:
        log(f"    of those, {sum(withdrawn_other.values()):,} filings across "
            f"{len(withdrawn_other)} registrant(s) were withdrawn as FALSE "
            f"ATTRIBUTIONS (script 350), not by the org-type guard. They are "
            f"excluded from every native metric and are NOT counted in "
            f"`n_filings_org_type_barred`, which keeps its documented meaning.")

    all_rids = set(regs) | set(by_reg) | set(barred_by_reg) | set(withdrawn_other)
    hub_rows = []
    for rid in sorted(all_rids, key=lambda x: (-sum(
            p["n_filings"] for p in by_reg.get(x, [])), x)):
        rec = regs.get(rid, {})
        f = foot.get(rid)
        pairs = by_reg.get(rid, [])
        nat = [p for p in pairs if p["client_is_keyed_native"] == "1"]
        yrs_n = [to_int(p["first_filing_year"]) for p in pairs if p["first_filing_year"]] + \
                [to_int(p["last_filing_year"]) for p in pairs if p["last_filing_year"]]
        issues = Counter()
        gov = Counter()
        for p in pairs:
            for tok in (p["issue_codes"] or "").split("|"):
                if ":" in tok:
                    k, v = tok.rsplit(":", 1)
                    issues[k] += to_int(v)
            for tok in (p["government_entities_lobbied"] or "").split("|"):
                if ":" in tok:
                    k, v = tok.rsplit(":", 1)
                    gov[k] += to_int(v)
        names = {rec.get("name")} | {p["registrant_name"] for p in pairs}
        names = sorted(x for x in names if x)
        cyrs = sorted(f["years"]) if f and f["years"] else []
        hub_rows.append({
            "registrant_id": rid,
            "registrant_name": names[-1] if names else "",
            "registrant_name_variants": j(names, ";"),
            "n_name_variants": len(names),
            "house_registrant_id": rec.get("house_registrant_id") or "",
            "registrant_description_lda_verbatim": (rec.get("description") or "").strip(),
            "registrant_city": rec.get("city") or "",
            "registrant_state": rec.get("state") or "",
            "registrant_zip": rec.get("zip") or "",
            "registrant_country": rec.get("country") or "",
            "registrant_street": rec.get("address_1") or "",
            "registrant_lda_contact_name": rec.get("contact_name") or "",
            "registrant_record_updated": (rec.get("dt_updated") or "")[:10],

            # corpus footprint - a FLOOR on the firm's practice, not its book
            "n_filings_corpus": (f["filings"] if f else 0),
            "n_clients_corpus": (len(f["clients"]) if f else 0),
            "first_filing_year_corpus": cyrs[0] if cyrs else "",
            "last_filing_year_corpus": cyrs[-1] if cyrs else "",

            # the Native side
            "n_filings_native_clients": sum(p["n_filings"] for p in nat),
            "n_native_clients": len(nat),
            "n_distinct_native_entities": len(
                {p["native_entity_id"] for p in nat if p["native_entity_id"]}),
            "native_entity_classes": top_counter(
                Counter(p["native_entity_class"] for p in nat
                        if p["native_entity_class"]), 6),
            "n_clients_in_corpus_not_keyed_native": len(pairs) - len(nat),
            "n_filings_org_type_barred": barred_by_reg.get(rid, 0),
            "first_filing_year_native": min(
                (to_int(p["first_filing_year"]) for p in nat
                 if p["first_filing_year"]), default=""),
            "last_filing_year_native": max(
                (to_int(p["last_filing_year"]) for p in nat
                 if p["last_filing_year"]), default=""),

            "spend_reported_usd": round(sum(p["spend_reported_usd"] for p in pairs), 2),
            "spend_sensitivity_percell_max_usd": round(
                sum(p["spend_sensitivity_percell_max_usd"] for p in pairs), 2),
            "spend_sensitivity_naive_sum_usd": round(
                sum(p["spend_sensitivity_naive_sum_usd"] for p in pairs), 2),
            "n_filings_reporting_no_dollar": sum(
                p["n_filings_reporting_no_dollar"] for p in pairs),

            "issue_codes": top_counter(issues, 10),
            "n_distinct_issue_codes": len(issues),
            "share_filings_issue_IND_pct": (
                round(100 * issues.get("IND", 0) / sum(issues.values()), 1)
                if sum(issues.values()) else ""),
            "government_entities_lobbied": top_counter(gov, 10),

            # the revolving door, in the filers' own words
            "n_distinct_lobbyists_corpus": (len(f["lobbyists"]) if f else 0),
            "n_lobbyist_rows_corpus": (f["lob_rows"] if f else 0),
            "n_lobbyist_rows_with_covered_position": (f["covered"] if f else 0),
            "covered_positions_verbatim_top": (
                top_counter(f["covered_text"], 3) if f else ""),

            "self_filed_filings_corpus": (f["self_filed"] if f else 0),
            "is_self_filer": "1" if (f and f["self_filed"]) else "0",
            "serves_native_entities": "1" if nat else "0",

            # 182 fills these; declared here so the schema is stable
            "native_ownership_status": "",
            "native_ownership_basis": "",
            "native_ownership_evidence_quote": "",
            "native_ownership_evidence_url": "",
            "native_ownership_evidence_tier": "",
            "native_ownership_entity_id": "",
            "native_ownership_routes": "",
            "n_ownership_routes": "",

            "data_quality_flag": "",
            "source": "Senate LDA filings API (lda.senate.gov) registrant "
                      "record and filings, via code/lobbying_pull",
            "built_by_script": SCRIPT,
            "built_date": TODAY,
        })

    # ---- data-quality flags: registrants that are not ordinary firms ------
    dq_rows = []
    for h in hub_rows:
        flags = []
        # A registrant whose ONLY client is itself is not a hired firm.
        if h["is_self_filer"] == "1" and h["n_clients_corpus"] <= 1:
            flags.append("SELF_FILER_NOT_A_HIRED_FIRM")
        if h["n_filings_org_type_barred"] and not h["n_filings_native_clients"]:
            flags.append("ALL_FILINGS_WITHDRAWN_BY_ORG_TYPE_GUARD")
        if h["n_filings_corpus"] <= 1:
            flags.append("SINGLE_FILING_IN_CORPUS")
        if flags:
            h["data_quality_flag"] = j(flags, ";")
            dq_rows.append({
                "registrant_id": h["registrant_id"],
                "registrant_name": h["registrant_name"],
                "registrant_city": h["registrant_city"],
                "registrant_state": h["registrant_state"],
                "flags": h["data_quality_flag"],
                "n_filings_corpus": h["n_filings_corpus"],
                "n_clients_corpus": h["n_clients_corpus"],
                "lda_description": h["registrant_description_lda_verbatim"],
                "lda_contact": h["registrant_lda_contact_name"],
                "reading": "A flag here is a property of the registration, "
                           "not a judgement about the registrant.",
                "built_by_script": SCRIPT,
                "built_date": TODAY,
            })

    hub_fields = list(hub_rows[0].keys())
    write_csv(HUB, hub_rows, hub_fields)
    log(f"  wrote {HUB.name}: {len(hub_rows):,} registrants")
    if dq_rows:
        write_csv(DQ, dq_rows, list(dq_rows[0].keys()))
        log(f"  wrote {DQ.name}: {len(dq_rows):,} flagged registrations")

    # ---------------- concentration ---------------------------------------
    conc_rows = []

    def shares(items, key):
        """items: list of dicts; key: numeric field. -> ordered desc list."""
        v = sorted((to_f(i[key]) for i in items), reverse=True)
        tot = sum(v)
        return v, tot

    def add_scope(scope, scope_value, pairs_in_scope):
        by_r = defaultdict(lambda: {"f": 0.0, "s": 0.0})
        by_e = defaultdict(set)
        for p in pairs_in_scope:
            by_r[p["registrant_id"]]["f"] += to_f(p["n_filings"])
            by_r[p["registrant_id"]]["s"] += to_f(p["spend_reported_usd"])
            if p["native_entity_id"]:
                by_e[p["native_entity_id"]].add(p["registrant_id"])
        if not by_r:
            return
        fv = sorted((x["f"] for x in by_r.values()), reverse=True)
        sv = sorted((x["s"] for x in by_r.values()), reverse=True)
        ft, st = sum(fv), sum(sv)
        row = {
            "scope": scope,
            "scope_value": scope_value,
            "n_registrants": len(by_r),
            "n_registrant_client_pairs": len(pairs_in_scope),
            "n_native_entities": len(by_e),
            "total_filings": int(ft),
            "total_spend_reported_usd": round(st, 2),
        }
        for n in (1, 3, 5, 10, 20, 50):
            row[f"top{n}_share_filings_pct"] = (
                round(100 * sum(fv[:n]) / ft, 2) if ft else "")
            row[f"top{n}_share_spend_pct"] = (
                round(100 * sum(sv[:n]) / st, 2) if st else "")
        row["hhi_filings"] = (
            round(sum((x / ft) ** 2 for x in fv) * 10000, 1) if ft else "")
        row["hhi_spend"] = (
            round(sum((x / st) ** 2 for x in sv) * 10000, 1) if st else "")
        # the reverse measure - how many firms does an entity use?
        nfirms = sorted(len(v) for v in by_e.values())
        row["entities_using_exactly_one_registrant"] = sum(
            1 for x in nfirms if x == 1)
        row["entities_using_5_or_more_registrants"] = sum(
            1 for x in nfirms if x >= 5)
        row["median_registrants_per_entity"] = (
            nfirms[len(nfirms) // 2] if nfirms else "")
        row["max_registrants_per_entity"] = nfirms[-1] if nfirms else ""
        row["hhi_reading"] = (
            "HHI is on a 0-10,000 scale over registrant shares within the "
            "scope. The US DOJ/FTC horizontal merger thresholds (1,500 / "
            "2,500) are quoted only as a familiar yardstick; a market for "
            "federal lobbying representation is not a merger market and no "
            "antitrust conclusion is asserted.")
        row["denominator_reading"] = (
            "Shares are of THIS CORPUS - filings whose client keyed to a "
            "Native entity - never of a firm's whole practice.")
        row["built_by_script"] = SCRIPT
        row["built_date"] = TODAY
        conc_rows.append(row)

    nat_pairs = [p for p in rel_rows if p["client_is_keyed_native"] == "1"]
    add_scope("ALL", "all_years", nat_pairs)

    # A (registrant, client) pair spans years, so a per-year scope has to be
    # rebuilt at the FILING grain rather than sliced off the pair table.
    per_year = defaultdict(list)
    yr_pair = defaultdict(lambda: {"n_filings": 0, "spend_reported_usd": 0.0,
                                   "native_entity_id": "",
                                   "registrant_id": ""})
    for r in keyed:
        k = (r["filing_year"], r["registrant_id"], r["client_id"])
        yr_pair[k]["n_filings"] += 1
        yr_pair[k]["registrant_id"] = r["registrant_id"]
        yr_pair[k]["native_entity_id"] = r.get("entity_id") or ""
    for (rid, cid, yr, period), (lat, mx, _n) in cells.items():
        k = (yr, rid, cid)
        if k in yr_pair:
            yr_pair[k]["spend_reported_usd"] += lat
    for (yr, rid, cid), v in yr_pair.items():
        per_year[yr].append(v)
    for yr in sorted(per_year):
        add_scope("FILING_YEAR", yr, per_year[yr])
    for cls in sorted({p["native_entity_class"] for p in nat_pairs
                       if p["native_entity_class"]}):
        add_scope("NATIVE_ENTITY_CLASS", cls,
                  [p for p in nat_pairs if p["native_entity_class"] == cls])

    conc_fields = list(conc_rows[0].keys())
    write_csv(CONC, conc_rows, conc_fields)
    log(f"  wrote {CONC.name}: {len(conc_rows):,} scopes")

    # ---------------- verify by RE-READING, never by the run log ----------
    log("\n-- verification (re-read from disk) --")
    for p in (HUB, RELS, CONC):
        rows = read_csv(p)
        log(f"  {p.name:<52} {len(rows):>7,} rows  "
            f"{len(rows[0]) if rows else 0} cols")

    hub2 = read_csv(HUB)
    rel2 = read_csv(RELS)
    top = sorted(hub2, key=lambda r: -to_int(r["n_filings_native_clients"]))[:12]
    log("\n-- who represents Indian Country, by filings on Native clients --")
    log(f"  {'registrant':<50}{'filings':>8}{'clients':>9}"
        f"{'entities':>9}{'$M':>9}")
    for h in top:
        log(f"  {h['registrant_name'][:48]:<50}"
            f"{to_int(h['n_filings_native_clients']):>8,}"
            f"{to_int(h['n_native_clients']):>9,}"
            f"{to_int(h['n_distinct_native_entities']):>9,}"
            f"{to_f(h['spend_reported_usd'])/1e6:>9,.1f}")

    allc = [r for r in read_csv(CONC) if r["scope"] == "ALL"][0]
    log("\n-- concentration, all years, Native-keyed filings --")
    for k in ("n_registrants", "n_native_entities", "total_filings",
              "top1_share_filings_pct", "top3_share_filings_pct",
              "top5_share_filings_pct", "top10_share_filings_pct",
              "top20_share_filings_pct", "top10_share_spend_pct",
              "hhi_filings", "hhi_spend",
              "entities_using_exactly_one_registrant",
              "median_registrants_per_entity",
              "max_registrants_per_entity"):
        log(f"  {k:<44} {allc[k]}")
    log(f"  total_spend_reported_usd                     "
        f"${to_f(allc['total_spend_reported_usd'])/1e6:,.1f}M")
    log(f"\n  pairs: {len(rel2):,}   registrants: {len(hub2):,}")
    log("\ndone.")


if __name__ == "__main__":
    main()
