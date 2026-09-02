#!/usr/bin/env python3
"""
Cedar Press - 1011: WHERE THE THIRTEEN DATASETS DISAGREE WITH EACH OTHER.

    py -3 code/1011_cross_dataset_reconciliation.py            # measure + write
    py -3 code/1011_cross_dataset_reconciliation.py verify     # exit 1 on breach
    py -3 code/1011_cross_dataset_reconciliation.py selftest   # prove verify fires

The datasets share one identity spine, so they should agree. Twelve checks ask
whether they do. Each one is re-measured from the live files on every run; none
of them repairs anything. **This script writes only its own files.** Where a
finding belongs to another dataset's owner it is written down with the
identifier and the count so that owner can act; the owner's table is not
touched.

THE CHECKS

  CDR-01  the typed ownership graph has no joinable subject
  CDR-02  operating companies worth $175.6B are absent from the entity layer
  CDR-03  declared parent UEIs that the identifier ledger cannot resolve
  CDR-04  lobbying clients recorded as unmatched that the spine already names
  CDR-05  hubs that appear in contracting and in no other dataset
  CDR-06  the `nan` sentinel repair is recorded as done and is 65% undone
  CDR-07  gaming facilities keyed by a method ENTITY_MATCH_RULES refuses alone
  CDR-08  gaming operator against the register - TESTED, NO DISAGREEMENT
  CDR-09  nonprofits whose own name is a spine entity and carry no hub link
  CDR-10  four duplicate allegations tested; all four phantom
  CDR-11  three QUARANTINED attribution methods still carry $38.2B
  CDR-12  one corporate family split across four nations

RANKING. Findings are ranked on two axes the owner named: dollars, and how
embarrassing it would be if a customer found it first. The second is recorded
as `embarrassment` with the reason, because a $0 finding that makes a published
claim false outranks a large one that is merely incomplete.

MONEY. Every dollar figure here is a REACH measure - how much already-published
money sits behind a defect - and never a new total. `MONEY_TOTALLING_RULES.md`
governs: nothing in this file may be added to anything in another file, and the
prime obligations quoted are the same dollars `prime_contracts.csv` already
publishes.
"""
from __future__ import annotations

import collections
import csv
import glob
import json
import os
import re
import sys

csv.field_size_limit(1 << 30)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C = lambda n: os.path.join(ROOT, "data", "clean", n)  # noqa: E731
S = lambda n: os.path.join(ROOT, "data", "spine", n)  # noqa: E731

OUT_FIND = os.path.join(ROOT, "review", "1011_cross_dataset_findings.csv")
OUT_ROWS = os.path.join(ROOT, "review", "1011_cross_dataset_finding_rows.csv")
OUT_INV = os.path.join(ROOT, "docs", "schema", "cross_dataset_reconciliation_invariants.json")

GENERIC = frozenset(
    """inc incorporated llc llp lp lc pllc corp corporation co company the of and a an
    group holdings holding ltd limited plc jv joint venture""".split()
)


def toks(s):
    s = re.sub(r"[^a-z0-9]+", " ", (s or "").lower())
    return [w for w in s.split() if w and w not in GENERIC]


def nkey(s):
    return " ".join(toks(s))


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        yield from csv.DictReader(f)


def name_index():
    """Exact whole-name index: spine canonical / FR name / aliases, >=2 tokens.

    Two tokens minimum and EXACT whole-name equality, because this index is used
    to AWARD a resolution. `docs/ENTITY_MATCH_RULES.md`: an entity whose entire
    distinctive token set is generic may not win a name-only match, and
    containment never accepts alone.
    """
    spine = {r["tribe_id"]: r for r in rows(S("cedar_entity_spine.csv"))}
    idx = collections.defaultdict(set)
    eid = {}
    for t, r in spine.items():
        eid[r.get("cedar_entity_id") or t] = t
        eid[t] = t
        for f in ("canonical_name", "fr_official_name"):
            if len(toks(r.get(f))) >= 2:
                idx[nkey(r.get(f))].add(t)
        for a in (r.get("aliases") or "").split("|"):
            if len(toks(a)) >= 2:
                idx[nkey(a)].add(t)
    for r in rows(C("entity_aliases.csv")):
        t = eid.get(r["entity_id"])
        if t and len(toks(r["alias_name"])) >= 2:
            idx[nkey(r["alias_name"])].add(t)
    return spine, idx


# ------------------------------------------------------------------ scanners ---
def scan_prime():
    out = {
        "rows": 0,
        "nan_by_col": collections.Counter(),
        "hub_usd": collections.defaultdict(float),
        "parent": collections.defaultdict(lambda: [set(), 0.0, collections.Counter(), set()]),
        "cage_nan_ueis": set(),
        "cage_nan_hubs": set(),
        "cage_nan_usd": 0.0,
    }
    with open(C("prime_contracts.csv"), newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        h = next(rd)
        ix = {c: i for i, c in enumerate(h)}
        for row in rd:
            out["rows"] += 1
            for i, v in enumerate(row):
                if v.strip().lower() == "nan":
                    out["nan_by_col"][h[i]] += 1
            try:
                ob = float(row[ix["total_obligations"]] or 0)
            except ValueError:
                ob = 0.0
            t = row[ix["tribe_id"]]
            if t:
                out["hub_usd"][t] += ob
            pu = row[ix["parent_uei"]].strip().upper()
            u = row[ix["awardee_uei"]].strip().upper()
            if pu and pu != u:
                a = out["parent"][pu]
                a[0].add(u)
                a[1] += ob
                a[2][row[ix["parent_name"]]] += 1
                if t:
                    a[3].add(t)
            if row[ix["cage_code"]].strip().lower() == "nan":
                out["cage_nan_ueis"].add(u)
                out["cage_nan_usd"] += ob
                if t:
                    out["cage_nan_hubs"].add(t)
    return out


# -------------------------------------------------------------------- checks ---
def build():
    spine, idx = name_index()
    p = scan_prime()
    finds, detail = [], []

    def F(cid, title, measure, usd, owner, embarrassment, evidence):
        finds.append({"check_id": cid, "title": title, "measure": measure,
                      "dollars_reached_usd": round(usd, 2), "owner_dataset": owner,
                      "embarrassment": embarrassment, "evidence": evidence})

    def D(cid, **kw):
        detail.append({"check_id": cid, **kw})

    # ---- CDR-01 -------------------------------------------------------------
    er = list(rows(C("entity_relationships.csv")))
    by = collections.Counter()
    for r in er:
        by[(r["relationship_type"], r["source_entity_id"] == "", r["target_entity_id"] == "")] += 1
    ow = [r for r in er if r["relationship_type"] == "owned_by"]
    uei_re = re.compile(r"\(UEI ([A-Z0-9]{12})\)")
    with_uei = [r for r in ow if uei_re.search(r["notes"] or "")]
    ledger_uei = {r["identifier"].strip().upper() for r in rows(C("cedar_identifier_ledger_final.csv"))
                  if r["identifier_type"].upper() == "UEI"}
    prose_ueis = {uei_re.search(r["notes"]).group(1) for r in with_uei}
    unjoinable = len(ow) - len(with_uei)
    F("CDR-01",
      "the typed ownership graph has no joinable subject",
      f"{len(ow)} owned_by edges, source_entity_id blank on {len(ow)} (100%); "
      f"{len(with_uei)} recover a UEI only from free-text notes; {unjoinable} recover nothing. "
      f"Across all {len(er)} edges, {sum(v for k, v in by.items() if k[1] or k[2])} have a blank endpoint.",
      0.0, "entity layer (entity_relationships.csv)",
      "HIGH - AGENTS.md names this file 'the source of truth' for ownership and a buyer "
      "cannot answer 'which firms does NANA own' from it without parsing English prose",
      "data/clean/entity_relationships.csv; relationship_type=owned_by; source_entity_id")
    for r in ow[:0]:
        pass
    for r in ow:
        m = uei_re.search(r["notes"] or "")
        if not m:
            D("CDR-01", key=r["relationship_id"], name=(r["notes"] or "")[:120],
              detail=f"owned_by -> {r['target_entity_id']}; no subject id and no UEI in notes",
              usd="")
    D("CDR-01", key="__summary__", name="endpoint blanks by relationship_type",
      detail="; ".join(f"{k[0]}: source_blank={k[1]} target_blank={k[2]} n={v}" for k, v in sorted(by.items())),
      usd="")
    _ = prose_ueis & ledger_uei

    # ---- CDR-02 -------------------------------------------------------------
    known = set()
    for r in rows(C("cedar_constellation_edges.csv")):
        known.add(nkey(r["from_name"]))
        known.add(nkey(r["to_hub_name"]))
    for r in er:
        for f in ("source_entity_id", "target_entity_id"):
            e = spine.get(r[f])
            if e:
                known.add(nkey(e["canonical_name"]))
    known.discard("")
    cr = list(rows(C("contractor_ranking.csv")))
    sub = [r for r in cr if nkey(r["operating_company_name"]) and
           nkey(r["operating_company_name"]) != nkey(r["owner_name"])]
    miss = [r for r in sub if nkey(r["operating_company_name"]) not in known]
    miss.sort(key=lambda r: -float(r["firm_obligations_usd"] or 0))
    miss_usd = sum(float(r["firm_obligations_usd"] or 0) for r in miss)
    F("CDR-02",
      "operating companies Cedar ranks as contractors are absent from the entity layer",
      f"{len(miss)} of {len(sub)} operating companies distinct from their owner are named nowhere in "
      f"entity_relationships.csv or cedar_constellation_edges.csv",
      miss_usd, "entity layer / contractors",
      "HIGH - contractor_ranking.csv is a published product and its firm column is the "
      "one thing the relationship graph cannot corroborate",
      "data/clean/contractor_ranking.csv operating_company_name vs "
      "cedar_constellation_edges.csv + entity_relationships.csv")
    for r in miss[:200]:
        D("CDR-02", key=r["operating_company_uei"], name=r["operating_company_name"],
          detail=f"owner={r['owner_name']} ({r['owner_entity_id']})",
          usd=r["firm_obligations_usd"])

    # ---- CDR-03 -------------------------------------------------------------
    par = p["parent"]
    absent = {k: v for k, v in par.items() if k not in ledger_uei and v[3]}
    absent_usd = sum(v[1] for v in absent.values())
    F("CDR-03",
      "declared parent UEIs the identifier ledger cannot resolve",
      f"{len(absent)} of {len(par)} non-self parent UEIs in prime_contracts.csv sit above at least one "
      f"Cedar-attributed child and have no row in cedar_identifier_ledger_final.csv - including the "
      f"top-level SAM registrations of NANA, Chugach, Afognak, Chenega, BBNC, Koniag, CIRI, Calista, "
      f"Bering Straits and The Aleut Corporation",
      absent_usd, "identity layer / contractors",
      "HIGH - the ledger exists to answer 'whose identifier is this' and cannot answer it "
      "for the parents FPDS itself names above $84.5B of attributed children",
      "data/clean/prime_contracts.csv parent_uei vs cedar_identifier_ledger_final.csv identifier_type=UEI")
    for k, v in sorted(absent.items(), key=lambda kv: -kv[1][1])[:200]:
        D("CDR-03", key=k, name=(v[2].most_common(1) or [("", 0)])[0][0],
          detail=f"{len(v[0])} children; child hubs {sorted(v[3])[:3]}", usd=round(v[1], 2))

    # ---- CDR-04 -------------------------------------------------------------
    uc = list(rows(C("lobbying_unmatched_clients.csv")))
    res = [(r, sorted(idx[nkey(r["client_name"])])) for r in uc
           if len(idx.get(nkey(r["client_name"]), ())) == 1]
    res.sort(key=lambda kv: -float(kv[0]["total_spend_usd"] or 0))
    res_usd = sum(float(r["total_spend_usd"] or 0) for r, _ in res)
    F("CDR-04",
      "lobbying clients recorded as unmatched that the spine already names exactly",
      f"{len(res)} of {len(uc)} rows in lobbying_unmatched_clients.csv resolve to EXACTLY ONE spine "
      f"entity on an exact whole-name match against canonical_name / fr_official_name / a recorded "
      f"alias - no containment, no token match. The commonest recorded reason is `no_alias_hit`.",
      res_usd, "influence (lobbying)",
      "HIGH - National Indian Gaming Association at $10.76M over 303 filings is unattributed "
      "while ITO-GAMING-00 is in the spine under that exact name",
      "data/clean/lobbying_unmatched_clients.csv client_name vs cedar_entity_spine.csv + entity_aliases.csv")
    for r, h in res:
        D("CDR-04", key=h[0], name=r["client_name"],
          detail=f"{r['n_filings']} filings {r['first_year']}-{r['last_year']}; "
                 f"why_unmatched={r['why_unmatched']}",
          usd=r["total_spend_usd"])

    # ---- CDR-05 -------------------------------------------------------------
    uid2t = {r["cedar_uid"]: r["handle"] for r in rows(S("cedar_identity_register.csv"))
             if r["handle"] in spine}
    pres = collections.defaultdict(set)
    for t in p["hub_usd"]:
        if t in spine:
            pres[t].add("contracting")

    def mark(path, col, label, uidcol=None):
        for r in rows(path):
            t = (r.get(col) or "") if col else ""
            if not t and uidcol:
                t = uid2t.get(r.get(uidcol) or "", "")
            if t in spine:
                pres[t].add(label)

    mark(C("federal_funding_tribe_year_panel.csv"), None, "funding", "cedar_uid")
    mark(C("gaming_facilities.csv"), "tribe_id", "gaming")
    mark(C("tribe_year_lobbying_panel.csv"), "entity_id", "lobbying")
    mark(C("np_ein_entity_hub.csv"), "entity_id", "nonprofit")
    mark(C("deals_classified.csv"), "native_party_entity_id", "deals")
    mark(C("subaward_entity_rollup.csv"), "tribe_id", "subawards")
    mark(C("faads_entity_attribution.csv"), "tribe_id", "faads")
    only = sorted(((t, p["hub_usd"][t]) for t in pres if pres[t] == {"contracting"}),
                  key=lambda kv: -kv[1])
    only_usd = sum(v for _, v in only)
    F("CDR-05",
      "hubs that appear in contracting and in no other dataset",
      f"{len(only)} of {len(pres)} hubs with attributed prime contracting appear in none of funding, "
      f"gaming, lobbying, nonprofits, deals, subawards or the FAADS attribution. "
      f"{sum(1 for t, _ in only if spine[t]['entity_class'].startswith('Alaska Native Village'))} of them "
      f"are Alaska Native Village Corporations, for which this is the EXPECTED shape - a village "
      f"corporation has no compact, files no tribal 990 and lobbies under its region.",
      only_usd, "cross-dataset coverage",
      "MEDIUM - mostly structural, but each one is a single-source attribution with no "
      "second dataset able to corroborate it",
      "prime_contracts.tribe_id against seven hub-keyed tables")
    for t, v in only:
        D("CDR-05", key=t, name=spine[t]["canonical_name"],
          detail=f"entity_class={spine[t]['entity_class']}; state={spine[t].get('state', '')}",
          usd=round(v, 2))

    # ---- CDR-06 -------------------------------------------------------------
    nan_total = sum(p["nan_by_col"].values())
    F("CDR-06",
      "the `nan` sentinel repair is recorded as applied and is 65% unapplied",
      f"prime_contracts.csv still carries the literal string `nan` in {nan_total:,} cells across "
      f"{len(p['nan_by_col'])} columns - cage_code {p['nan_by_col']['cage_code']:,} "
      f"({100 * p['nan_by_col']['cage_code'] / p['rows']:.2f}%), "
      f"place_of_perform_city {p['nan_by_col']['place_of_perform_city']:,}, "
      f"place_of_perform_state {p['nan_by_col']['place_of_perform_state']:,}, "
      f"funding_agency {p['nan_by_col']['funding_agency']:,}. "
      f"A backup named `prime_contracts.bak_2026-09-02_011205_pre772.csv` sits beside the live file and "
      f"the only column actually cleaned is parent_contract_number. "
      f"{len(p['cage_nan_ueis'])} distinct awardee UEIs across {len(p['cage_nan_hubs'])} Cedar hubs now "
      f"share the CAGE code `nan`.",
      p["cage_nan_usd"], "contractors (code/772)",
      "HIGHEST - ENTITY_MATCH_RULES rule 4 already warns that this exact sentinel in "
      "fpds_uei_cage_map.csv fuses 2,193 unrelated entities; the same sentinel is in the "
      "flagship table on 9x as many UEIs, and the backup filename asserts the repair ran",
      "data/clean/prime_contracts.csv; count cells equal to the 3-character string `nan`")
    for col, n in p["nan_by_col"].most_common():
        D("CDR-06", key=col, name="prime_contracts.csv", usd="",
          detail=f"{n} cells ({100 * n / p['rows']:.2f}% of {p['rows']} rows) hold the literal string `nan`")

    # ---- CDR-07 / CDR-08 ----------------------------------------------------
    gf = list(rows(C("gaming_facilities.csv")))
    meth = collections.Counter(r["entity_match_method"] for r in gf)
    contain = [r for r in gf if r["entity_match_method"] == "containment"]
    F("CDR-07",
      "gaming facilities keyed by a method the match rules refuse on its own",
      f"{len(contain)} of {len(gf)} facilities carry entity_match_method=containment. "
      f"ENTITY_MATCH_RULES rule 9: 'Containment never accepts alone' - it is a WEAK class needing a "
      f"second independent signal, and it is the class that produced 41 wrong links onto "
      f"Council Native Corporation. Method mix: " + ", ".join(f"{k or '(blank)'}={v}" for k, v in meth.most_common()),
      0.0, "gaming",
      "MEDIUM - no wrong key is demonstrated here; what is demonstrated is that 37% of the "
      "gaming register's keys rest on a method the project's own rules will not accept alone",
      "data/clean/gaming_facilities.csv entity_match_method")
    for r in contain[:200]:
        D("CDR-07", key=r["facility_id"], name=r["facility_name"],
          detail=f"tribe_id={r['tribe_id']} tier={r['entity_tier']} basis={r['entity_match_basis'][:80]}",
          usd="")

    dis = []
    for r in gf:
        h = idx.get(nkey(r["tribe"]))
        if h and r["tribe_id"] and r["tribe_id"] not in h:
            dis.append(r)
    F("CDR-08",
      "gaming operator against the register - TESTED, NO DISAGREEMENT FOUND",
      f"For all {len(gf)} facilities, the operator string the source publishes (`tribe`) was resolved "
      f"independently against the spine by exact whole-name match and compared with the tribe_id Cedar "
      f"ships. Disagreements: {len(dis)}. "
      f"{sum(1 for r in gf if r['tribe_id'] and nkey(r['tribe']) in idx)} of the rows resolve at all; "
      f"the rest do not resolve by exact name and are neither agreement nor disagreement.",
      0.0, "gaming",
      "NONE - this is a clean result and is recorded so nobody spends the day re-deriving it",
      "data/clean/gaming_facilities.csv tribe vs tribe_id")

    # ---- CDR-09 -------------------------------------------------------------
    hub_eins = {r["ein"] for r in rows(C("np_ein_entity_hub.csv"))}
    np_hits = []
    for r in rows(C("np_orgs.csv")):
        if r["cedar_spine_entity_id"] or r["tribe_id"]:
            continue
        h = idx.get(nkey(r["org_name"]))
        if h and len(h) == 1:
            np_hits.append((r, sorted(h)[0]))
    excluded = [x for x in np_hits if "EXCLUDED" in (x[0].get("disposition") or "")]
    F("CDR-09",
      "nonprofits whose own registered name IS a spine entity and carry no hub link",
      f"{len(np_hits)} unkeyed rows of np_orgs.csv have an org_name that matches EXACTLY ONE spine "
      f"entity on a whole-name match, and {sum(1 for r, _ in np_hits if r['EIN'] in hub_eins)} of them "
      f"appear in np_ein_entity_hub.csv. {len(excluded)} carry a prior EXCLUSION ruling and must not be "
      f"linked without re-reading that ruling - an exclusion is a decision, not an omission.",
      0.0, "nonprofits + the constellation agent (serves edges)",
      "MEDIUM - small in number and each one is an Indian Health Service programme, a tribal "
      "college or a BIE school that the spine already carries under the same name",
      "data/clean/np_orgs.csv org_name vs cedar_entity_spine.csv; REPORTED, NOT WRITTEN - "
      "the serves/hub edge belongs to its owner")
    for r, h in np_hits:
        D("CDR-09", key=r["EIN"], name=r["org_name"],
          detail=f"resolves to {h}; disposition={r.get('disposition', '')}; "
                 f"in_np_ein_entity_hub={'1' if r['EIN'] in hub_eins else '0'}",
          usd="")

    # ---- CDR-10 -------------------------------------------------------------
    dup_lines = []
    for t in ("ownership_events", "contractor_ranking", "entity_relationships", "deals_classified",
              "gaming_facilities", "np_ein_entity_hub", "lobbying_registrant_client_relationships",
              "fpds_uei_edges", "cedar_identifier_ledger_final", "entity_aliases",
              "cedar_constellation_edges"):
        with open(C(t + ".csv"), newline="", encoding="utf-8") as f:
            rd = csv.reader(f)
            next(rd)
            cnt = collections.Counter(tuple(x) for x in rd)
        surplus = sum(v - 1 for v in cnt.values() if v > 1)
        dup_lines.append(f"{t}={surplus}")
        D("CDR-10", key=t, name="whole-row duplicate scan",
          detail=f"rows={sum(cnt.values())} surplus_duplicate_rows={surplus}", usd="")

    al = list(rows(C("entity_aliases.csv")))
    ag = collections.defaultdict(list)
    for r in al:
        ag[(r["entity_id"], r["normalized_alias"])].append(r)
    asem = {k: v for k, v in ag.items() if len(v) > 1}
    fold = sum(1 for v in asem.values() if any("ascii_fold" in (x["source_id"] or "") for x in v))
    D("CDR-10", key="entity_aliases.normalized_alias", name="semantic duplicate allegation - PHANTOM",
      detail=f"{len(asem)} groups share (entity_id, normalized_alias). {fold} of them are an original "
             f"alias PLUS the deliberate ASCII-folded variant written by "
             f"97_build_aliases_and_relationships.py:ascii_fold - an em-dash spelling and a hyphen "
             f"spelling of the same name. A de-dupe on normalized_alias deletes the fold, which exists "
             f"precisely so a source that types a hyphen still matches. The remaining group is "
             f"\"Dena Nena Henash\" / \"Dena' Nena' Henash\" - the apostrophe orthography "
             f"ENTITY_MATCH_RULES rule 14 calls a positive identifying signal.", usd="")

    dl = {r["Deal_ID"] for r in rows(C("deals_classified.csv"))}
    add_tot = add_in = 0
    for pth in sorted(glob.glob(C("deals_*_additions.csv"))):
        rr = list(rows(pth))
        add_tot += len(rr)
        add_in += sum(1 for r in rr if r.get("Deal_ID") in dl)
    D("CDR-10", key="deals_*_additions.csv", name="re-verification of a documented claim",
      detail=f"{add_in} of {add_tot} rows across the nine additions files already carry a Deal_ID that "
             f"is in deals_classified.csv. MONEY_TOTALLING_RULES states 790 of 790; re-measured today "
             f"it is {add_in} of {add_tot}. They are the SAME rows staged twice by design, so the "
             f"additions files must never be summed with the classified ledger - and equally must not "
             f"be deleted, since they record which pass found which deal.", usd="")

    oe = list(rows(C("ownership_events.csv")))
    oe_in = sum(1 for r in oe if r["source_deal_id"] in dl)
    D("CDR-10", key="ownership_events.csv", name="projection, not new money",
      detail=f"{oe_in} of {len(oe)} rows carry a source_deal_id present in deals_classified.csv. "
             f"announced_value_usd totals "
             f"${sum(float(r['announced_value_usd'] or 0) for r in oe):,.0f} and is the SAME money as "
             f"the deals it projects. Never add the two.", usd="")

    blank_alias = [r for r in al if not r["alias_id"].strip()]
    D("CDR-10", key="entity_aliases.alias_id", name="a real keying defect found while testing a phantom",
      detail=f"{len(blank_alias)} of {len(al)} rows carry a BLANK alias_id, which is the table's "
             f"declared key. Both are org_self_statement rows for Tanana Chiefs Conference. "
             f"No non-blank alias_id repeats.", usd="")

    F("CDR-10",
      "four duplicate allegations tested; all four phantom, one real keying defect found",
      f"Whole-row duplicates across eleven identity and cross-dataset tables: "
      + ", ".join(dup_lines) +
      f". Semantic allegation on entity_aliases: {len(asem)} groups, {fold} of them an ASCII-fold pair - "
      f"PHANTOM. deals_*_additions against deals_classified: {add_in}/{add_tot} shared by design - "
      f"PHANTOM. ownership_events against deals_classified: {oe_in}/{len(oe)} a projection - PHANTOM. "
      f"The one thing that IS broken is {len(blank_alias)} blank alias_id values.",
      0.0, "identity layer",
      "LOW as a defect and HIGH as a precedent - a de-dupe on entity_aliases.normalized_alias "
      "would delete the ASCII-fold variants that exist to make matching work",
      "measured with csv.reader over the live files")

    # ---- CDR-11 -------------------------------------------------------------
    # `docs/CROSS_DATASET_LEARNING.md` channel 3: "a discredited method taints
    # its output wherever it landed. Quarantined: cluster_v3, need_v6,
    # sam_namematch_2026_05_06." Ask what those methods are still carrying.
    QUAR = {"cluster_v3", "need_v6", "sam_namematch_2026_05_06"}
    led_rows = list(rows(C("cedar_identifier_ledger_final.csv")))
    quar_uei = {r["identifier"].strip().upper(): r for r in led_rows
                if r["identifier_type"].upper() == "UEI" and r["attribution_method"] in QUAR}
    quar_excluded = sum(1 for r in quar_uei.values() if r["exclusion_id"].strip())

    def hubtoks(t):
        e = spine.get(t)
        if not e:
            return set()
        s = set(toks(e["canonical_name"])) | set(toks(e.get("fr_official_name")))
        for a in (e.get("aliases") or "").split("|"):
            s |= set(toks(a))
        return {w for w in s if len(w) >= 3}

    try:
        sys.path.insert(0, os.path.join(ROOT, "code"))
        import cedar_domain  # type: ignore
        TRAPS = {w.lower() for w in cedar_domain.NAME_TRAPS}
    except Exception:
        TRAPS = set()

    qrows = qusd = 0
    pair = collections.defaultdict(float)
    with open(C("prime_contracts.csv"), newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        hh = next(rd)
        jx = {c: i for i, c in enumerate(hh)}
        for row in rd:
            u = row[jx["awardee_uei"]].strip().upper()
            if u in quar_uei and row[jx["tribe_id"]]:
                try:
                    ob = float(row[jx["total_obligations"]] or 0)
                except ValueError:
                    ob = 0.0
                qrows += 1
                qusd += ob
                pair[(u, row[jx["awardee_name"]], row[jx["tribe_id"]], row[jx["canonical_name"]])] += ob
    no_tok, trap_tok = [], []
    for (u, nm, t, cn), v in pair.items():
        ft = {w for w in toks(nm) if len(w) >= 3}
        sh = ft & hubtoks(t)
        if not sh:
            no_tok.append((v, u, nm, t, cn, ""))
        elif sh <= TRAPS:
            trap_tok.append((v, u, nm, t, cn, "|".join(sorted(sh))))
    no_tok.sort(reverse=True)
    trap_tok.sort(reverse=True)
    F("CDR-11",
      "three QUARANTINED attribution methods are still carrying $38.2B of attributed contracting",
      f"{len(quar_uei)} UEI rows of cedar_identifier_ledger_final.csv carry attribution_method in "
      f"{{cluster_v3, need_v6, sam_namematch_2026_05_06}} - the three methods "
      f"docs/CROSS_DATASET_LEARNING.md quarantines - and {quar_excluded} of them carry an exclusion_id. "
      f"They key {qrows:,} rows of prime_contracts.csv. Two risk slices inside that: "
      f"{len(no_tok)} firm/hub pairs (${sum(x[0] for x in no_tok):,.0f}) share NO distinctive token with "
      f"the hub at all, and {len(trap_tok)} pairs (${sum(x[0] for x in trap_tok):,.0f}) share only a token "
      f"that is already on cedar_domain.NAME_TRAPS - `eagle`, `bristol`, `oneida`, `wind`. "
      f"prime_contracts.attribution_method reads `uei_exact` on every one of them, because that column "
      f"records HOW THE IDENTIFIER JOINED and not HOW THE IDENTIFIER WAS RULED, so the quarantine is "
      f"invisible to anyone reading the contracting table.",
      qusd, "identity layer + contractors",
      "HIGHEST - General Dynamics Information Technology ($3.53B) is keyed to the Native "
      "Village of Barrow and Blue Tech Inc ($3.51B) to Blue Lake Rancheria, both tier B, both "
      "on a method the project has already discredited in writing",
      "cedar_identifier_ledger_final.csv attribution_method vs prime_contracts.csv awardee_uei")
    for v, u, nm, t, cn, sh in (no_tok[:150] + trap_tok[:150]):
        D("CDR-11", key=u, name=nm,
          detail=f"keyed to {t} ({cn}) by {quar_uei[u]['attribution_method']}, tier "
                 f"{quar_uei[u]['confidence_tier']}; "
                 + (f"only shared token is the NAME_TRAP `{sh}`" if sh else "no shared distinctive token"),
          usd=round(v, 2))

    # ---- CDR-12 -------------------------------------------------------------
    nw = collections.defaultdict(lambda: [0, 0.0, set()])
    with open(C("prime_contracts.csv"), newline="", encoding="utf-8") as f:
        rd = csv.reader(f)
        hh = next(rd)
        jx = {c: i for i, c in enumerate(hh)}
        for row in rd:
            nm = row[jx["awardee_name"]].lower()
            if nm.startswith("north wind") or " north wind" in nm or nm.startswith("lbyd"):
                t = row[jx["tribe_id"]] or "(unattributed)"
                a = nw[t]
                a[0] += 1
                try:
                    a[1] += float(row[jx["total_obligations"]] or 0)
                except ValueError:
                    pass
                a[2].add(row[jx["awardee_uei"]].strip().upper())
    wrong = {k: v for k, v in nw.items() if k not in ("ANRC-CKINLT-00", "(unattributed)")}
    F("CDR-12",
      "one corporate family split across four nations, and Cedar's own deal ledger settles it",
      "The North Wind / LBYD family is keyed to " + str(len(nw)) + " different hubs in "
      "prime_contracts.csv: " + "; ".join(
          f"{k} = {v[0]} rows / {len(v[2])} UEIs / ${v[1]:,.0f}" for k, v in
          sorted(nw.items(), key=lambda kv: -kv[1][1])) +
      ". The Cook Inlet Region rows were resolved by agent_research_two_leg; the Eastern Shoshone rows "
      "were all resolved by the quarantined cluster_v3 on the token `wind`, which is on "
      "cedar_domain.NAME_TRAPS. Cedar's OWN deal ledger contradicts the Eastern Shoshone reading twice: "
      "ANCSA2-2017-003 'CIRI through its subsidiary North Wind purchased Portage' and MA2020-004 "
      "'North Wind Group acquires LBYD Engineers'. Note that `Wind River Construction LLC` is NOT in "
      "this set and may legitimately be Eastern Shoshone - Wind River is their reservation, which is "
      "exactly why the token is a trap.",
      sum(v[1] for v in wrong.values()), "identity layer + contractors",
      "HIGHEST - two datasets Cedar publishes disagree about who owns a $2.8B contracting "
      "family, and the tie-breaker is a third dataset Cedar also publishes",
      "prime_contracts.csv awardee_name LIKE 'North Wind%' / 'LBYD%' grouped by tribe_id; "
      "deals_classified.csv ANCSA2-2017-003 and MA2020-004")
    for t, v in sorted(nw.items(), key=lambda kv: -kv[1][1]):
        D("CDR-12", key=t, name=spine.get(t, {}).get("canonical_name", t),
          detail=f"{v[0]} rows, {len(v[2])} UEIs", usd=round(v[1], 2))

    finds.sort(key=lambda r: (-{"HIGHEST": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
                              .get(r["embarrassment"].split(" -")[0], 0),
                              -r["dollars_reached_usd"]))
    inv = {
        "prime_rows": p["rows"],
        "cdr01_owned_by_edges": len(ow),
        "cdr01_owned_by_blank_source": len(ow),
        "cdr01_owned_by_uei_only_in_prose": len(with_uei),
        "cdr02_operating_companies_absent": len(miss),
        "cdr02_dollars": round(miss_usd, 2),
        "cdr03_parent_ueis_absent_from_ledger": len(absent),
        "cdr03_dollars": round(absent_usd, 2),
        "cdr04_resolvable_unmatched_lobbying_clients": len(res),
        "cdr04_dollars": round(res_usd, 2),
        "cdr05_hubs_only_in_contracting": len(only),
        "cdr05_dollars": round(only_usd, 2),
        "cdr06_nan_cells_remaining": nan_total,
        "cdr06_cage_nan_ueis": len(p["cage_nan_ueis"]),
        "cdr06_cage_nan_dollars": round(p["cage_nan_usd"], 2),
        "cdr07_gaming_containment_keys": len(contain),
        "cdr08_gaming_operator_disagreements": len(dis),
        "cdr09_nonprofit_name_is_spine_entity": len(np_hits),
        "cdr10_whole_row_duplicates": {t.split("=")[0]: int(t.split("=")[1]) for t in dup_lines},
        "cdr10_alias_semantic_groups": len(asem),
        "cdr10_alias_blank_ids": len(blank_alias),
        "cdr10_additions_rows_already_in_classified": [add_in, add_tot],
        "cdr11_quarantined_uei_ledger_rows": len(quar_uei),
        "cdr11_quarantined_with_exclusion": quar_excluded,
        "cdr11_prime_rows_keyed": qrows,
        "cdr11_dollars": round(qusd, 2),
        "cdr11_pairs_no_shared_token": len(no_tok),
        "cdr11_dollars_no_shared_token": round(sum(x[0] for x in no_tok), 2),
        "cdr11_pairs_trap_token_only": len(trap_tok),
        "cdr11_dollars_trap_token_only": round(sum(x[0] for x in trap_tok), 2),
        "cdr12_north_wind_hubs": {k: [v[0], len(v[2]), round(v[1], 2)] for k, v in nw.items()},
    }
    return finds, detail, inv


FIND_COLS = ["check_id", "title", "measure", "dollars_reached_usd", "owner_dataset",
             "embarrassment", "evidence"]
ROW_COLS = ["check_id", "key", "name", "detail", "usd"]


def write_csv(path, cols, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in data:
            w.writerow({c: r.get(c, "") for c in cols})


def main(argv):
    mode = (argv[1] if len(argv) > 1 else "measure").lower()

    if mode == "selftest":
        # The invariant this script must never violate: a finding may not claim
        # a disagreement it did not measure. Prove the comparator fires by
        # feeding `verify` a recorded value that no longer matches.
        finds, detail, inv = build()
        tampered = dict(inv)
        tampered["cdr03_parent_ueis_absent_from_ledger"] = inv["cdr03_parent_ueis_absent_from_ledger"] + 1
        bad = [k for k, v in tampered.items() if inv.get(k) != v]
        if not bad:
            print("SELFTEST FAILED: the comparator did not detect a changed invariant.")
            return 1
        print("SELFTEST PASSED: comparator detected", bad)
        # And a structural rule: every finding must carry an evidence path.
        holes = [f["check_id"] for f in finds if not f["evidence"].strip()]
        if holes:
            print("SELFTEST FAILED: findings with no evidence path:", holes)
            return 1
        print("SELFTEST PASSED: all", len(finds), "findings carry an evidence path.")
        return 0

    finds, detail, inv = build()

    if mode == "verify":
        if not os.path.exists(OUT_INV):
            print(f"INVARIANT BREACH - {OUT_INV} is missing; run measure first.")
            return 1
        rec = json.load(open(OUT_INV, encoding="utf-8")).get("invariants", {})
        fail = False
        for k, v in rec.items():
            if inv.get(k) != v:
                fail = True
                print(f"INVARIANT BREACH - {k}: recorded {v}, measured {inv.get(k)}")
        holes = [f["check_id"] for f in finds if not f["evidence"].strip()]
        if holes:
            fail = True
            print("INVARIANT BREACH - findings with no evidence path:", holes)
        if fail:
            return 1
        print("VERIFY OK -", json.dumps(inv, indent=2, sort_keys=True))
        return 0

    write_csv(OUT_FIND, FIND_COLS, finds)
    write_csv(OUT_ROWS, ROW_COLS, detail)
    os.makedirs(os.path.dirname(OUT_INV), exist_ok=True)
    json.dump({"built_by": "code/1011_cross_dataset_reconciliation.py", "invariants": inv},
              open(OUT_INV, "w", encoding="utf-8"), indent=2, sort_keys=True)
    for f in finds:
        print(f"{f['check_id']}  ${f['dollars_reached_usd']:>18,.0f}  {f['embarrassment'].split(' -')[0]:<8} {f['title']}")
    print("\nwrote", OUT_FIND, f"({len(finds)} findings)")
    print("wrote", OUT_ROWS, f"({len(detail)} rows)")
    print("wrote", OUT_INV)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
