"""219 — CourtListener / RECAP, measured against KNOWN Cedar entities.

WHY THIS IS NOT A DUPLICATE OF `139_build_litigation_positions.py`
    139 uses CourtListener, but by HAND: it hardcodes five Brackeen docket rows
    and a West Flagler block, each typed out with its URL.  It carries no query,
    no sweep and no entity keying, and it says so itself —
        "RECAP coverage of this docket is PARTIAL. These are the amicus entries
         present in the free RECAP archive; the absence of an organisation here
         is NOT evidence it did not file."
    This script is the first ENTITY-KEYED sweep of the free v4 search API.

WHAT IT MEASURES, AND WHY EACH SAMPLE WAS CHOSEN
    Each cohort is picked to kill one specific hypothesis, per PULL_DISCIPLINE's
    "design your probes so their outcomes ELIMINATE explanations":

    ANCSA_OPCO      the operating companies in the 334
                    ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION defects.
                    Kills: "a complaint caption will not name the corporate
                    parent."  `docs/ANCSA_OWNERSHIP_RULING.md` rule 3 is an
                    exception that must be EVIDENCED, and a caption is evidence.
    ANCSA_PARENT    the village corporations themselves.  Kills: "the parent is
                    only ever a defendant under its subsidiary's name."
    GAMING          gaming tribes / authorities.  Kills: "revenue figures never
                    reach a federal docket" — the per-property revenue that
                    `docs/STATE_GAMING_PULL_LOG.md` types
                    `held_by_state_but_sealed`.
    CONTROL_ABSENT  a name constructed not to exist.  Kills: "the API returns
                    something for anything", which is the trap ProPublica's
                    organizations endpoint actually has (HTTP 200 +
                    "Unknown Organization" for EIN 999999999, measured today).

VERIFICATION, NOT ASSERTION
    A hit counts as VERIFIED only when the queried name appears in the docket's
    own `party` array (case-folded, punctuation-stripped).  A hit whose name
    appears only in `caseName` is recorded as `NAME_IN_CAPTION_ONLY` and is a
    weaker thing.  Nothing here is written as a link into any shared table.

WHAT IT REFUSES
    * No shared table is touched.  Output is staged under review/ and
      data/raw/external/untapped_2026-08-26/.
    * ONE poller.  Claims logs/_HOSTLOCK_www.courtlistener.com.json.
    * Honest User-Agent.  `docs/LOBBYING_EXPANSION_RECONCILIATION.md` records a
      host that REFUSED a browser-shaped UA and served the honest one; do not
      "fix" a 403 by pretending to be Chrome.
    * RUN_DEADLINE and stop-on-first-refusal-when-nothing-has-landed.

py -3 code/219_probe_courtlistener_recap.py sample
py -3 code/219_probe_courtlistener_recap.py report
"""
import csv, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error
import collections, datetime, pathlib

csv.field_size_limit(10 ** 8)
ROOT = pathlib.Path(r"C:\Users\esm247\Desktop\Cedar Press")
OUT = ROOT / "data" / "raw" / "external" / "untapped_2026-08-26"
REVIEW = ROOT / "review"
LOGS = ROOT / "logs"
OUT.mkdir(parents=True, exist_ok=True)

SCRIPT = "219_probe_courtlistener_recap.py"
HOST = "www.courtlistener.com"
API = "https://www.courtlistener.com/api/rest/v4/search/"
UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
TOKEN = os.environ.get("COURTLISTENER_TOKEN", "")   # optional; anon works
GAP = 2.5
DEADLINE_S = 45 * 60
MAX_CONSEC_REFUSALS = 3
START = time.time()
TODAY = "2026-08-26"

SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
DEFECTS = REVIEW / "identifier_one_to_many_defects_2026-08-26.csv"
FACILITIES = ROOT / "data" / "clean" / "gaming_facilities.csv"


def log(m):
    try:
        print(m, flush=True)
    except UnicodeEncodeError:
        print(m.encode("ascii", "replace").decode(), flush=True)


def norm(s):
    return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())


def squash(s):
    return re.sub(r"\s+", " ", norm(s)).strip()


# --------------------------------------------------------------- host lock
def claim_host(note):
    p = LOGS / f"_HOSTLOCK_{HOST}.json"
    if p.exists():
        cur = json.loads(p.read_text(encoding="utf-8"))
        if cur.get("active"):
            log(f"HOSTLOCK held by {cur.get('script')}; queued and exiting")
            cur.setdefault("queue", []).append({"script": f"code/{SCRIPT}", "note": note})
            p.write_text(json.dumps(cur, indent=1), encoding="utf-8")
            return False
    p.write_text(json.dumps({
        "host": HOST, "pid": os.getpid(), "script": f"code/{SCRIPT}",
        "started": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "active": True, "queue": [], "note": note,
        "policy": f"sequential, single stream, >={GAP}s gap, stop after "
                  f"{MAX_CONSEC_REFUSALS} consecutive refusals, "
                  f"RUN_DEADLINE {DEADLINE_S}s",
    }, indent=1), encoding="utf-8")
    return True


def release_host(note, extra=None):
    p = LOGS / f"_HOSTLOCK_{HOST}.json"
    cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"host": HOST}
    cur.update(active=False,
               released=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               note=note)
    if extra:
        cur.update(extra)
    p.write_text(json.dumps(cur, indent=1), encoding="utf-8")


# --------------------------------------------------------------- cohorts
def build_cohorts():
    cohorts = []

    # ANCSA operating companies from the 334, top by observed dollars
    opco, parent_ids = [], set()
    if DEFECTS.exists():
        rows = [r for r in csv.DictReader(DEFECTS.open(encoding="utf-8-sig"))
                if r["defect_family"] == "ALASKA_VILLAGE_GOVERNMENT_VS_VILLAGE_CORPORATION"]
        rows.sort(key=lambda r: -float(r["usd_observed"] or 0))
        seen = set()
        for r in rows:
            nm = (r["observed_name"] or "").strip()
            k = squash(nm)
            if not nm or k in seen:
                continue
            seen.add(k)
            opco.append((nm, r["identifier"], r["usd_observed"], r["entities"]))
            for e in (r["entities"] or "").split("|"):
                if e.startswith("ANVC-"):
                    parent_ids.add(e)
            if len(opco) >= 20:
                break
    for nm, ident, usd, ents in opco:
        cohorts.append(dict(cohort="ANCSA_OPCO", query_name=nm,
                            cedar_key=ident, cedar_context=ents,
                            usd_context=usd))

    # ANCSA village corporations named as the parent in those defects
    spine = {r["tribe_id"]: r for r in csv.DictReader(SPINE.open(encoding="utf-8-sig"))}
    for eid in sorted(parent_ids)[:12]:
        r = spine.get(eid)
        if r:
            cohorts.append(dict(cohort="ANCSA_PARENT",
                                query_name=r["canonical_name"],
                                cedar_key=eid,
                                cedar_context=r["entity_class"], usd_context=""))

    # Gaming: tribes with the largest gaming presence we can name locally
    gaming = []
    if FACILITIES.exists():
        cnt = collections.Counter()
        nm = {}
        for r in csv.DictReader(FACILITIES.open(encoding="utf-8-sig")):
            t = (r.get("entity_id") or r.get("tribe_entity_id")
                 or r.get("tribe_id") or "").strip()
            if t:
                cnt[t] += 1
                nm.setdefault(t, r.get("tribe") or r.get("tribe_name") or "")
        for t, _ in cnt.most_common(40):
            sr = spine.get(t)
            name = (sr["canonical_name"] if sr else nm.get(t, "")).strip()
            if name:
                gaming.append((name, t))
            if len(gaming) >= 12:
                break
    for name, t in gaming:
        cohorts.append(dict(cohort="GAMING", query_name=name, cedar_key=t,
                            cedar_context="gaming facility operator",
                            usd_context=""))

    # Control: a name built so that a hit would mean the API matches anything
    cohorts.append(dict(cohort="CONTROL_ABSENT",
                        query_name="Kwithluk Sentinel Holdings Incorporated",
                        cedar_key="", cedar_context="constructed non-entity",
                        usd_context=""))
    return cohorts


# --------------------------------------------------------------- fetch
def cl_get(url):
    hdr = {"User-Agent": UA, "Accept": "application/json"}
    if TOKEN:
        hdr["Authorization"] = f"Token {TOKEN}"
    req = urllib.request.Request(url, headers=hdr)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status, json.loads(r.read().decode("utf-8", "replace"))


def step_sample():
    cohorts = build_cohorts()
    log(f"{len(cohorts)} queries across "
        f"{len(set(c['cohort'] for c in cohorts))} cohorts")
    if not claim_host("entity-keyed RECAP sample against known Cedar entities"):
        return 3

    rows, dockets = [], []
    consec = 0
    state = {"queries_sent": 0, "refused_by_host": [], "http_ok": 0,
             "stopped_early": None}
    try:
        for c in cohorts:
            if time.time() - START > DEADLINE_S:
                state["stopped_early"] = "RUN_DEADLINE"
                log("RUN_DEADLINE reached")
                break
            q = f'"{c["query_name"]}"'
            url = API + "?" + urllib.parse.urlencode({"q": q, "type": "r"})
            try:
                state["queries_sent"] += 1
                status, js = cl_get(url)
                consec = 0
                state["http_ok"] += 1
            except urllib.error.HTTPError as e:
                consec += 1
                state["refused_by_host"].append([c["query_name"], e.code])
                log(f"  {c['query_name'][:45]:45s} HTTP {e.code}")
                if consec >= MAX_CONSEC_REFUSALS:
                    state["stopped_early"] = f"{consec} consecutive refusals"
                    log("stop: consecutive refusals")
                    break
                time.sleep(GAP * 4)
                continue
            except Exception as e:
                consec += 1
                state["refused_by_host"].append([c["query_name"], str(e)[:160]])
                log(f"  {c['query_name'][:45]:45s} ERR {e}")
                if consec >= MAX_CONSEC_REFUSALS:
                    state["stopped_early"] = f"{consec} consecutive errors"
                    break
                time.sleep(GAP * 4)
                continue

            want = squash(c["query_name"])
            n_dockets = js.get("count", 0)
            n_docs = js.get("document_count", 0)
            verified = caption_only = 0
            avail = 0
            firms, attys, courts = set(), set(), set()
            for d in js.get("results", []):
                parties = [squash(p) for p in (d.get("party") or [])]
                hit_party = any(want in p or p in want for p in parties if p)
                hit_caption = want in squash(d.get("caseName") or "")
                if hit_party:
                    verified += 1
                elif hit_caption:
                    caption_only += 1
                for f in (d.get("firm") or []):
                    firms.add(f)
                for a in (d.get("attorney") or []):
                    attys.add(a)
                if d.get("court"):
                    courts.add(d["court"])
                for rd in (d.get("recap_documents") or []):
                    if rd.get("is_available"):
                        avail += 1
                dockets.append(dict(
                    cohort=c["cohort"], query_name=c["query_name"],
                    cedar_key=c["cedar_key"],
                    docket_id=d.get("docket_id"),
                    case_name=d.get("caseName"),
                    court=d.get("court"), court_id=d.get("court_id"),
                    docket_number=d.get("docketNumber"),
                    date_filed=d.get("dateFiled"),
                    date_terminated=d.get("dateTerminated"),
                    cause=d.get("cause"),
                    parties="|".join(d.get("party") or []),
                    firms="|".join(d.get("firm") or []),
                    attorneys="|".join(d.get("attorney") or []),
                    n_recap_documents=len(d.get("recap_documents") or []),
                    n_documents_available=sum(
                        1 for x in (d.get("recap_documents") or [])
                        if x.get("is_available")),
                    match_class=("VERIFIED_PARTY" if hit_party else
                                 "NAME_IN_CAPTION_ONLY" if hit_caption else
                                 "NAME_IN_DOCUMENT_TEXT_ONLY"),
                    docket_url="https://www.courtlistener.com"
                               + (d.get("docket_absolute_url") or ""),
                    retrieved_date=TODAY,
                ))
            rows.append(dict(
                cohort=c["cohort"], query_name=c["query_name"],
                cedar_key=c["cedar_key"], cedar_context=c["cedar_context"],
                usd_context=c["usd_context"],
                http_status=status,
                dockets_matching=n_dockets,
                documents_matching=n_docs,
                page1_verified_party=verified,
                page1_caption_only=caption_only,
                page1_documents_free_pdf=avail,
                distinct_firms_page1=len(firms),
                distinct_attorneys_page1=len(attys),
                distinct_courts_page1=len(courts),
                query_url=url, retrieved_date=TODAY))
            log(f"  {c['cohort']:14s} {c['query_name'][:42]:42s} "
                f"dockets={n_dockets:<5} docs={n_docs:<6} "
                f"verified_party={verified} free_pdf={avail}")
            time.sleep(GAP)
    finally:
        release_host("RECAP sample complete", {"queries_sent": state["queries_sent"]})

    def write(path, data, fields):
        tmp = str(path) + ".part"
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(data)
        os.replace(tmp, path)

    if rows:
        write(REVIEW / "courtlistener_recap_sample_2026-08-26.csv", rows,
              list(rows[0].keys()))
    if dockets:
        write(REVIEW / "courtlistener_recap_dockets_2026-08-26.csv", dockets,
              list(dockets[0].keys()))
    (OUT / "_219_state.json").write_text(json.dumps(state, indent=1),
                                         encoding="utf-8")
    log(f"wrote {len(rows)} query rows / {len(dockets)} docket rows")
    return 0


def step_report():
    p = REVIEW / "courtlistener_recap_sample_2026-08-26.csv"
    if not p.exists():
        log("no sample on disk; run `sample` first")
        return 1
    rows = list(csv.DictReader(p.open(encoding="utf-8-sig")))
    by = collections.defaultdict(list)
    for r in rows:
        by[r["cohort"]].append(r)
    for c, rs in sorted(by.items()):
        hit = sum(1 for r in rs if int(r["dockets_matching"]) > 0)
        ver = sum(1 for r in rs if int(r["page1_verified_party"]) > 0)
        dk = sum(int(r["dockets_matching"]) for r in rs)
        dc = sum(int(r["documents_matching"]) for r in rs)
        fp = sum(int(r["page1_documents_free_pdf"]) for r in rs)
        log(f"{c:16s} n={len(rs):<3} any_docket={hit:<3} verified_party={ver:<3} "
            f"dockets={dk:<6} documents={dc:<7} free_pdf_page1={fp}")
    return 0


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "sample"
    sys.exit({"sample": step_sample, "report": step_report}[stage]())
