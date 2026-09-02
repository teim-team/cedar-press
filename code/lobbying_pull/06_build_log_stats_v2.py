"""
Compute every figure quoted in docs/LOBBYING_BUILD_LOG_2026-08-05.md and write
them INTO the log, between the STATS BLOCK markers.

Read-only over the outputs of 04 (pull) and 05 (match). Nothing in the stats
block is typed by hand; re-running this script regenerates it from the files on
disk. Adds, over 03_build_log_stats.py:

  * distinct GOVERNMENT ENTITIES lobbied (the LD-2 agencies-contacted field),
    which is the field this dataset exists to expose at scale
  * top REGISTRANTS -- the firms that carry Native clients
  * the review-queue census

Usage:  py -3 06_build_log_stats_v2.py            (writes the log)
        py -3 06_build_log_stats_v2.py --stdout   (prints only)
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RAW = HERE / "raw_filings.jsonl"
CLIENTS = HERE / "clients_universe.jsonl"
PROGRESS = HERE / "pull_progress.json"
CLIENT_PROGRESS = HERE / "client_progress.json"
CLIENTFETCH = HERE / "clientfetch_progress.json"
CLEAN = ROOT / "data" / "clean"
DISC = CLEAN / "native_entity_lobbying_disclosures.csv"
PANEL = CLEAN / "tribe_year_lobbying_panel.csv"
UNM = CLEAN / "lobbying_unmatched_clients.csv"
REVIEW = ROOT / "review" / "lobbying_ambiguous_2026-08-05.csv"
LOG_MD = ROOT / "docs" / "LOBBYING_BUILD_LOG_2026-08-05.md"

START = "<!-- STATS BLOCK -->"
END = "<!-- END STATS BLOCK -->"

csv.field_size_limit(10_000_000)
OUT = []


def p(s=""):
    OUT.append(s)


def money(x):
    return f"${x:,.0f}"


def fl(x):
    try:
        return float(x or 0)
    except ValueError:
        return 0.0


def load_progress(path):
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


NAMED_SIX = [
    "HOPI TRIBE",
    "ONEIDA TRIBE OF INDIANS OF WISCONSIN",
    "ST REGIS MOHAWK TRIBE",
    "YUROK TRIBE",
    "MOHEGAN TRIBE OF CONNECTICUT",
    "CONFEDERATED TRIBES OF THE GRAND RONDE OF OREGON",
]


def _load_matcher(fname, modname):
    import importlib.util
    spec = importlib.util.spec_from_file_location(modname, HERE / fname)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def before_after():
    """
    Run the v1 and v2 client matchers over the SAME raw file and report both.

    This is the only honest form of a before/after: v1's published CSVs were a
    snapshot of a partial pull, so comparing them to v2's finished CSVs would
    conflate the retrieval fix with the matching fix. Here the input is
    identical and only the matcher differs.
    """
    try:
        v1 = _load_matcher("02_match_filings_to_tribes.py", "lda_match_v1")
        v2 = _load_matcher("05_match_filings_v2.py", "lda_match_v2")
    except Exception as e:                       # pragma: no cover
        p(f"## Matcher before/after\n\n- NOT COMPUTED: {type(e).__name__}: {e}")
        return

    clients = defaultdict(lambda: {"n": 0, "spend": 0.0})
    with RAW.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            name = ((r.get("client") or {}).get("name") or "").strip()
            inc, exp = r.get("income"), r.get("expenses")
            try:
                spend = float(inc) if inc not in (None, "", "null") and float(inc) > 0 \
                    else (float(exp) if exp not in (None, "", "null") else 0.0)
            except (TypeError, ValueError):
                spend = 0.0
            c = clients[name]
            c["n"] += 1
            c["spend"] += max(spend, 0.0)

    i1c, i1s = v1.build_canonical_index(), None
    i1s = v1.build_subsidiary_index(i1c)
    i2c = v2.build_canonical_index()
    i2s = v2.build_subsidiary_index(i2c)

    tot_f = sum(c["n"] for c in clients.values())
    tot_s = sum(c["spend"] for c in clients.values())
    res = {}
    stats = {}
    for tag, mod, ic, isub in (("v1", v1, i1c, i1s), ("v2", v2, i2c, i2s)):
        mf = mc = 0
        ms = 0.0
        r = {}
        for name, c in clients.items():
            m = mod.match_client(name, ic, isub)
            r[name] = m
            if m["entity_id"]:
                mc += 1
                mf += c["n"]
                ms += c["spend"]
        res[tag] = r
        stats[tag] = (mf, mc, ms)

    p("## Matcher before/after, same raw file")
    p()
    p(f"Both matchers run over the identical {tot_f:,} filings / {len(clients):,} "
      f"distinct client names on disk, so the only thing that differs is the "
      f"matching logic.")
    p()
    p("| | filings matched | of filings | distinct clients matched | of clients | spend attributed |")
    p("|---|---|---|---|---|---|")
    for tag, label in (("v1", "v1 (one-directional containment)"),
                       ("v2", "v2 (two-sided normalization + 7 guards)")):
        mf, mc, ms = stats[tag]
        p(f"| **{label}** | {mf:,} | {mf / max(tot_f, 1):.1%} | {mc:,} "
          f"| {mc / max(len(clients), 1):.1%} | {money(ms)} |")
    d_f = stats["v2"][0] - stats["v1"][0]
    d_c = stats["v2"][1] - stats["v1"][1]
    d_s = stats["v2"][2] - stats["v1"][2]
    p(f"| **change** | {d_f:+,} | {100 * d_f / max(tot_f, 1):+.1f} pp | {d_c:+,} "
      f"| {100 * d_c / max(len(clients), 1):+.1f} pp | {money(d_s)} |")
    p()

    # regressions: matched by v1, not by v2 -- each must be an intentional refusal
    reg = [(n, res["v1"][n], clients[n]) for n in clients
           if res["v1"][n]["entity_id"] and not res["v2"][n]["entity_id"]]
    p(f"- clients v1 matched that v2 now refuses: **{len(reg)}** "
      f"(each one is a guard firing, listed with its reason in the review queue)")
    for n, m, c in sorted(reg, key=lambda x: -x[2]["spend"])[:10]:
        p(f"  - `{n}` -> v1 said {m['entity_id']}; v2 says "
          f"`{res['v2'][n]['reason']}` ({money(c['spend'])})")
    p()
    p("### The six named clients")
    p()
    p("| client | v1 | v2 | v2 method |")
    p("|---|---|---|---|")
    for name in NAMED_SIX:
        if name not in clients:
            p(f"| `{name}` | *(not present under this exact spelling in the pull)* | | |")
            continue
        a, b = res["v1"][name], res["v2"][name]
        av = a["entity_id"] or f"`{a['reason']}`"
        bn = i2c.meta.get(b["entity_id"], {}).get("canonical_name", "") if b["entity_id"] else ""
        bv = f"{b['entity_id']} {bn}" if b["entity_id"] else f"`{b['reason']}`"
        p(f"| `{name}` | {av} | {bv} | `{b['method'] or ''}` |")
    p()


def main():
    years = defaultdict(int)
    n_raw = 0
    uuids = set()
    types = defaultdict(int)
    with RAW.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            n_raw += 1
            uuids.add(r.get("filing_uuid"))
            if r.get("filing_year"):
                years[int(r["filing_year"])] += 1
            types[r.get("filing_type_display") or "?"] += 1

    prog = load_progress(PROGRESS)
    cprog = load_progress(CLIENT_PROGRESS)
    fprog = load_progress(CLIENTFETCH)
    n_clients_universe = sum(1 for _ in CLIENTS.open(encoding="utf-8")) if CLIENTS.exists() else 0

    p("## Pull")
    p()
    p(f"- raw lines `{n_raw:,}`; unique `filing_uuid` **{len(uuids):,}**")
    if years:
        p(f"- filing years **{min(years)}-{max(years)}** ({len(years)} distinct years)")
    p(f"- Stage 1 broad-keyword `/filings/` sweeps complete: "
      f"{sum(1 for v in prog.values() if v.get('done'))}/{len(prog)}"
      + (f"; OPEN: {', '.join(k for k, v in prog.items() if not v.get('done'))}"
         if any(not v.get("done") for v in prog.values()) else ""))
    p(f"- Stage 2 `/clients/` sweeps complete: "
      f"{sum(1 for v in cprog.values() if v.get('done'))}/{len(cprog)}; "
      f"client universe **{n_clients_universe:,}** distinct LDA clients")
    p(f"- Stage 3 per-`client_id` fetches complete: "
      f"{sum(1 for v in fprog.values() if v.get('done'))}/{len(fprog)}")
    p("- filing types: " + ", ".join(
        f"`{k}` {v:,}" for k, v in sorted(types.items(), key=lambda x: -x[1])[:8]))
    p()

    disc = list(csv.DictReader(DISC.open(encoding="utf-8")))
    panel = list(csv.DictReader(PANEL.open(encoding="utf-8")))
    unm = list(csv.DictReader(UNM.open(encoding="utf-8")))
    review = list(csv.DictReader(REVIEW.open(encoding="utf-8"))) if REVIEW.exists() else []

    matched_spend = sum(fl(r["spend_usd"]) for r in disc)
    unm_spend = sum(fl(r["total_spend_usd"]) for r in unm)
    unm_filings = sum(int(r["n_filings"] or 0) for r in unm)
    n_total = len(disc) + unm_filings
    n_clients_matched = len(set(r["client_name"] for r in disc))

    by_method = defaultdict(int)
    for r in disc:
        by_method[r["attribution_method"]] += 1
    self_filed = sum(1 for r in disc if r["self_filed"] == "1")
    spend_basis = defaultdict(float)
    for r in disc:
        spend_basis[r["spend_basis"]] += fl(r["spend_usd"])

    p("## Match")
    p()
    p(f"- filings scored **{n_total:,}**")
    p(f"- matched **{len(disc):,}** ({len(disc) / max(n_total, 1):.1%} of filings) "
      f"to **{len(set(r['entity_id'] for r in disc)):,}** distinct canonical entities")
    p(f"- distinct client names: **{n_clients_matched + len(unm):,}** total, "
      f"**{n_clients_matched:,}** matched "
      f"({n_clients_matched / max(n_clients_matched + len(unm), 1):.1%}), "
      f"{len(unm):,} unmatched")
    p(f"- unmatched filings {unm_filings:,}")
    p(f"- panel rows (entity x year) **{len(panel):,}**")
    p(f"- matched spend **{money(matched_spend)}**; unmatched spend {money(unm_spend)}")
    p(f"- self-filed (registrant == client) filings {self_filed:,}")
    p("- spend basis: " + ", ".join(f"{k} {money(v)}" for k, v in
                                    sorted(spend_basis.items(), key=lambda x: -x[1])))
    p("- attribution methods: " + ", ".join(f"`{k}` {v:,}" for k, v in
                                            sorted(by_method.items(), key=lambda x: -x[1])))
    reasons = defaultdict(int)
    rclients = defaultdict(int)
    for r in unm:
        reasons[r["why_unmatched"]] += int(r["n_filings"] or 0)
        rclients[r["why_unmatched"]] += 1
    p("- unmatched reasons (filings / distinct clients): " + ", ".join(
        f"`{k}` {v:,}/{rclients[k]:,}" for k, v in sorted(reasons.items(), key=lambda x: -x[1])))
    p(f"- queued for a ruling in `review/lobbying_ambiguous_2026-08-05.csv`: "
      f"**{len(review):,}** clients, {money(sum(fl(r['total_spend_usd']) for r in review))} "
      f"of reported spend")
    p()

    # ---- government entities ----------------------------------------------
    agencies = defaultdict(int)
    ag_spend = defaultdict(float)
    ag_entities = defaultdict(set)
    for r in disc:
        for a in (r["government_entities"] or "").split("|"):
            if a:
                agencies[a] += 1
                ag_spend[a] += fl(r["spend_usd"])
                ag_entities[a].add(r["entity_id"])
    named = sum(1 for r in disc if r["government_entities"])
    p("## Government entities lobbied (LD-2 agencies-contacted, matched filings)")
    p()
    p(f"- **{len(agencies):,}** distinct government entities named across "
      f"{named:,} of {len(disc):,} matched filings "
      f"({named / max(len(disc), 1):.0%} name at least one)")
    p()
    p("| # | government entity | filings | Native entities contacting | spend on those filings |")
    p("|---|---|---|---|---|")
    for i, (a, n) in enumerate(sorted(agencies.items(), key=lambda x: (-x[1], x[0]))[:25], 1):
        p(f"| {i} | {a} | {n:,} | {len(ag_entities[a]):,} | {money(ag_spend[a])} |")
    p()

    # ---- registrants -------------------------------------------------------
    regs = defaultdict(lambda: {"n": 0, "spend": 0.0, "clients": set(), "yrs": set()})
    for r in disc:
        if not r["registrant_name"]:
            continue
        v = regs[r["registrant_name"]]
        v["n"] += 1
        v["spend"] += fl(r["spend_usd"])
        v["clients"].add(r["client_name"])
        if r["filing_year"]:
            v["yrs"].add(int(r["filing_year"]))
    p("## Registrants carrying Native clients")
    p()
    p(f"- **{len(regs):,}** distinct registrants filed on behalf of a matched Native entity")
    p()
    p("| # | registrant | filings | Native clients | reported spend | years |")
    p("|---|---|---|---|---|---|")
    for i, (r, v) in enumerate(sorted(regs.items(), key=lambda x: (-x[1]["n"], x[0]))[:25], 1):
        yrs = f"{min(v['yrs'])}-{max(v['yrs'])}" if v["yrs"] else ""
        p(f"| {i} | {r} | {v['n']:,} | {len(v['clients']):,} | {money(v['spend'])} | {yrs} |")
    p()

    # ---- top entities ------------------------------------------------------
    ent = defaultdict(lambda: {"spend": 0.0, "n": 0, "name": "", "type": "",
                               "regs": set(), "yrs": set()})
    for r in disc:
        e = ent[r["entity_id"]]
        e["spend"] += fl(r["spend_usd"])
        e["n"] += 1
        e["name"] = r["canonical_name"]
        e["type"] = r["entity_type"]
        if r["registrant_name"]:
            e["regs"].add(r["registrant_name"])
        if r["filing_year"]:
            e["yrs"].add(int(r["filing_year"]))
    p("## Top 25 matched entities by reported spend")
    p()
    p("| # | entity_id | entity | type | spend | filings | registrants | years |")
    p("|---|---|---|---|---|---|---|---|")
    for i, (eid, e) in enumerate(sorted(ent.items(), key=lambda x: -x[1]["spend"])[:25], 1):
        yrs = f"{min(e['yrs'])}-{max(e['yrs'])}" if e["yrs"] else ""
        p(f"| {i} | {eid} | {e['name']} | {e['type']} | {money(e['spend'])} "
          f"| {e['n']:,} | {len(e['regs'])} | {yrs} |")
    p()

    # ---- top unmatched -----------------------------------------------------
    unm_sorted = sorted(unm, key=lambda r: -fl(r["total_spend_usd"]))
    p("## Top 25 UNMATCHED clients by reported spend")
    p()
    p("| # | client | spend | filings | years | native token | why unmatched |")
    p("|---|---|---|---|---|---|---|")
    for i, r in enumerate(unm_sorted[:25], 1):
        p(f"| {i} | {r['client_name']} | {money(fl(r['total_spend_usd']))} "
          f"| {r['n_filings']} | {r['first_year']}-{r['last_year']} "
          f"| {r['native_token_hit']} | `{r['why_unmatched']}` |")
    nat = [r for r in unm_sorted if r["native_token_hit"] == "1"]
    p()
    p(f"- unmatched clients carrying Native tokens: **{len(nat):,}** "
      f"({money(sum(fl(r['total_spend_usd']) for r in nat))} of reported spend)")
    p()

    # ---- issue codes -------------------------------------------------------
    codes = defaultdict(int)
    for r in disc:
        for c in (r["lobbying_issues_codes"] or "").split("|"):
            if c:
                codes[c] += 1
    p("## Issue codes (matched filings)")
    p()
    p("- top issue codes: " + ", ".join(f"`{k}` {v:,}" for k, v in
                                        sorted(codes.items(), key=lambda x: -x[1])[:12]))
    p()

    # ---- by year -----------------------------------------------------------
    yr = defaultdict(float)
    cnt = defaultdict(int)
    ents_yr = defaultdict(set)
    for r in disc:
        if r["filing_year"]:
            y = int(r["filing_year"])
            yr[y] += fl(r["spend_usd"])
            cnt[y] += 1
            ents_yr[y].add(r["entity_id"])
    p("## Matched spend by year")
    p()
    p("| year | spend | filings | distinct entities |")
    p("|---|---|---|---|")
    for y in sorted(yr):
        p(f"| {y} | {money(yr[y])} | {cnt[y]:,} | {len(ents_yr[y])} |")

    before_after()

    block = "\n".join(OUT)
    if "--stdout" in sys.argv:
        print(block)
        return 0

    text = LOG_MD.read_text(encoding="utf-8")
    if START not in text:
        print(f"ERROR: {START} marker not found in {LOG_MD}")
        return 1
    head, _, rest = text.partition(START)
    tail = rest.partition(END)[2] if END in rest else "\n" + rest.lstrip("\n")
    LOG_MD.write_text(f"{head}{START}\n\n{block}\n\n{END}{tail}", encoding="utf-8")
    print(f"stats block written into {LOG_MD} ({len(block.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
