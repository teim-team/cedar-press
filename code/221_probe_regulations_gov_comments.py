"""221 — regulations.gov comment dockets, measured against KNOWN Cedar entities.

WHY THIS SOURCE, SPECIFICALLY
    `docs/LOBBYING_EXPANSION_RECONCILIATION.md` refuses to build
    `position_on_native_issue` because it would be "a characterisation we would
    be authoring, published under our name, about a named organisation", and
    prescribes the replacement schema:

        lda_position_reported   the filing's own "position" text, verbatim
        bill_id                 what they lobbied on
        tribal_position_on_bill where a tribe publicly stated one
        alignment               DERIVED per (org, rule): SAME | OPPOSED |
                                NO_TRIBAL_POSITION_FOUND

    "Build the fact, not the verdict."

    A regulations.gov PUBLIC SUBMISSION is that fact in its purest available
    form: a named organisation, on a dated federal rulemaking docket, saying in
    its own words what it wants.  The `ADMINISTRATIVE_COMMENT` member of the
    project's own AdvocacyChannel enum has had no source behind it.  This is it.

    It is also the only channel in the enum where the TRIBE is the speaker.  The
    27,796 LDA filings record who was hired; a comment records what the tribe
    itself said, over its own signature.

STATUS BEFORE THIS SCRIPT: regulations.gov was NEVER TOUCHED by Cedar Press.
    Repo-wide, the only mention is `docs/FEDERAL_ACTIONS_BUILD_LOG_2026-08-05.md`
    saying a value lives "on regulations.gov, not in this field".  No puller, no
    host lock, no raw directory.

WHAT IT MEASURES
    * reachability and the real page ceiling of the v4 API
    * per-entity comment counts across a stratified Cedar sample
    * a VERIFIED sample: one comment fetched in detail, whose `organization`
      or title names the entity, quoted verbatim with its docket and URL

VERIFICATION, NOT ASSERTION
    A search hit is only a hit on TEXT.  A comment counts as ATTRIBUTED here
    only when the comment's own `organization` field or its `title` names the
    entity.  `highlightedContent` matching alone is recorded as
    `TEXT_MENTION_ONLY` — a rule about a tribe is not a comment BY that tribe,
    and conflating them is the same error shape as
    `docs/LOBBYING_EXPANSION_RECONCILIATION.md` warns of throughout.

WHAT IT REFUSES
    * No shared table is touched.  Output stages under review/ and
      data/raw/external/untapped_2026-08-26/.
    * ONE poller; claims logs/_HOSTLOCK_api.regulations.gov.json.
    * Honest User-Agent.  RUN_DEADLINE.  Stop on consecutive refusals.
    * It writes NO position verdict of any kind.  It records the speaker, the
      docket, the date and the text, and stops there.

py -3 code/221_probe_regulations_gov_comments.py sample
py -3 code/221_probe_regulations_gov_comments.py detail
"""
import csv, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error
import collections, datetime, pathlib

csv.field_size_limit(10 ** 8)
ROOT = pathlib.Path(r"C:\Users\esm247\Desktop\Cedar Press")
OUT = ROOT / "data" / "raw" / "external" / "untapped_2026-08-26"
REVIEW = ROOT / "review"
LOGS = ROOT / "logs"
OUT.mkdir(parents=True, exist_ok=True)

SCRIPT = "221_probe_regulations_gov_comments.py"
HOST = "api.regulations.gov"
API = "https://api.regulations.gov/v4"
# api.data.gov key, account esmclaude@gmail.com, recorded in
# dissertation/docs/API_KEYS.md.  One api.data.gov key is valid across every
# api.data.gov-fronted service; regulations.gov is one, as api.fac.gov is.
KEY = os.environ.get("API_DATA_GOV_KEY", "xAmmmCQ05iWdMTWfhvBeSgul008UxCUfSsdZRbex")
UA = ("CedarPress-research/1.0 (+https://cedarpress.co; "
      "elijahsamsonmoreno@gmail.com)")
GAP = 1.2
DEADLINE_S = 40 * 60
MAX_CONSEC_REFUSALS = 3
START = time.time()
TODAY = "2026-08-26"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"


def log(m):
    try:
        print(m, flush=True)
    except UnicodeEncodeError:
        print(m.encode("ascii", "replace").decode(), flush=True)


def squash(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).strip()


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
                  f"{MAX_CONSEC_REFUSALS} consecutive refusals",
        "key": "api.data.gov key (value not recorded here)",
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


def get(path, params):
    params = dict(params)
    url = f"{API}/{path}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "X-Api-Key": KEY, "User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.status, json.loads(r.read().decode("utf-8", "replace")), url


def cohorts():
    rows = list(csv.DictReader(SPINE.open(encoding="utf-8-sig")))
    by = collections.defaultdict(list)
    for r in rows:
        by[r["entity_class"]].append(r)
    picks = []
    plan = [("Federally recognized tribe", 14),
            ("Intertribal Organization", 6),
            ("Alaska Native Regional Corporation", 4),
            ("Federally recognized Alaska Native Village", 3),
            ("Native Hawaiian Organization", 3),
            ("Tribal College or University", 2)]
    for cls, n in plan:
        pool = [r for r in by.get(cls, [])
                if len(r["canonical_name"].split()) >= 2]
        # longest names first: a two-token name like "Seminole" is a surname and
        # a county, and its search hits are dominated by neither.
        pool.sort(key=lambda r: -len(r["canonical_name"]))
        step = max(1, len(pool) // max(1, n))
        for r in pool[::step][:n]:
            picks.append(dict(cohort=cls, query_name=r["canonical_name"],
                              cedar_key=r["tribe_id"]))
    picks.append(dict(cohort="CONTROL_ABSENT",
                      query_name="Kwithluk Sentinel Holdings Incorporated",
                      cedar_key=""))
    return picks


def step_sample():
    picks = cohorts()
    log(f"{len(picks)} queries")
    if not claim_host("entity-keyed comment sample against known Cedar entities"):
        return 3
    rows, hits = [], []
    consec = 0
    state = {"queries_sent": 0, "http_ok": 0, "refused_by_host": [],
             "stopped_early": None}
    try:
        for p in picks:
            if time.time() - START > DEADLINE_S:
                state["stopped_early"] = "RUN_DEADLINE"
                break
            try:
                state["queries_sent"] += 1
                status, js, url = get("comments", {
                    "filter[searchTerm]": f'"{p["query_name"]}"',
                    "page[size]": 25, "sort": "-postedDate"})
                consec = 0
                state["http_ok"] += 1
            except urllib.error.HTTPError as e:
                consec += 1
                state["refused_by_host"].append([p["query_name"], e.code])
                log(f"  {p['query_name'][:45]:45s} HTTP {e.code}")
                if consec >= MAX_CONSEC_REFUSALS:
                    state["stopped_early"] = f"{consec} consecutive refusals"
                    break
                time.sleep(GAP * 5)
                continue
            except Exception as e:
                consec += 1
                state["refused_by_host"].append([p["query_name"], str(e)[:160]])
                if consec >= MAX_CONSEC_REFUSALS:
                    state["stopped_early"] = f"{consec} consecutive errors"
                    break
                time.sleep(GAP * 5)
                continue

            total = (js.get("meta") or {}).get("totalElements", 0)
            data = js.get("data") or []
            want = squash(p["query_name"])
            attributed = 0
            agencies = collections.Counter()
            for d in data:
                a = d.get("attributes") or {}
                title = a.get("title") or ""
                agencies[a.get("agencyId") or ""] += 1
                is_attr = want in squash(title) or squash(title) in want
                if is_attr:
                    attributed += 1
                hits.append(dict(
                    cohort=p["cohort"], query_name=p["query_name"],
                    cedar_key=p["cedar_key"],
                    comment_id=d.get("id"), agency_id=a.get("agencyId"),
                    document_type=a.get("documentType"),
                    title=title, posted_date=a.get("postedDate"),
                    withdrawn=a.get("withdrawn"),
                    highlighted_excerpt=re.sub(r"<[^>]+>", "",
                                               a.get("highlightedContent") or "")[:900],
                    attribution_class=("TITLE_NAMES_THE_ENTITY" if is_attr
                                       else "TEXT_MENTION_ONLY"),
                    comment_url=f"https://www.regulations.gov/comment/{d.get('id')}",
                    retrieved_date=TODAY))
            rows.append(dict(
                cohort=p["cohort"], query_name=p["query_name"],
                cedar_key=p["cedar_key"], http_status=status,
                comments_matching_total=total,
                page1_returned=len(data),
                page1_title_names_the_entity=attributed,
                page1_distinct_agencies=len(agencies),
                page1_top_agencies="|".join(f"{k}:{v}" for k, v in agencies.most_common(5)),
                query_url=url, retrieved_date=TODAY))
            log(f"  {p['cohort'][:26]:26s} {p['query_name'][:38]:38s} "
                f"comments={total:<7} titled={attributed:<3} "
                f"agencies={len(agencies)}")
            time.sleep(GAP)
    finally:
        release_host("comment sample complete", {"queries_sent": state["queries_sent"]})

    def write(path, data):
        tmp = str(path) + ".part"
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)
        os.replace(tmp, path)

    if rows:
        write(REVIEW / "regulations_gov_comment_sample_2026-08-26.csv", rows)
    if hits:
        write(REVIEW / "regulations_gov_comment_hits_2026-08-26.csv", hits)
    (OUT / "_221_state.json").write_text(json.dumps(state, indent=1), encoding="utf-8")
    log(f"wrote {len(rows)} query rows / {len(hits)} comment rows")
    return 0


def step_detail():
    """Fetch the FULL text of the comments whose title names the entity.

    The search response carries only `highlightedContent`, which is an excerpt
    chosen by the search engine.  The detail endpoint carries `comment` — the
    submitter's own words — plus `organization`, `docketId` and any attachment
    links.  That is the difference between a search snippet and a citable quote.
    """
    src = REVIEW / "regulations_gov_comment_hits_2026-08-26.csv"
    if not src.exists():
        log("run `sample` first")
        return 1
    hits = [h for h in csv.DictReader(src.open(encoding="utf-8-sig"))
            if h["attribution_class"] == "TITLE_NAMES_THE_ENTITY"]
    hits = hits[:int(os.environ.get("DETAIL_N", "25"))]
    log(f"fetching {len(hits)} comment details")
    if not claim_host("comment detail fetch"):
        return 3
    out = []
    consec = 0
    try:
        for h in hits:
            if time.time() - START > DEADLINE_S:
                break
            try:
                status, js, url = get(f"comments/{h['comment_id']}",
                                      {"include": "attachments"})
                consec = 0
            except Exception as e:
                consec += 1
                log(f"  {h['comment_id']} ERR {e}")
                if consec >= MAX_CONSEC_REFUSALS:
                    break
                time.sleep(GAP * 5)
                continue
            a = ((js.get("data") or {}).get("attributes") or {})
            body = re.sub(r"<[^>]+>", " ", a.get("comment") or "")
            body = re.sub(r"\s+", " ", body).strip()
            atts = [x for x in (js.get("included") or [])
                    if x.get("type") == "attachments"]
            nfiles = sum(len((x.get("attributes") or {}).get("fileFormats") or [])
                         for x in atts)
            out.append(dict(
                cedar_key=h["cedar_key"], query_name=h["query_name"],
                comment_id=h["comment_id"], docket_id=a.get("docketId"),
                agency_id=a.get("agencyId"),
                organization_as_filed=a.get("organization") or "",
                submitter_name=" ".join(
                    x for x in [a.get("firstName") or "", a.get("lastName") or ""] if x),
                submitter_type=a.get("category") or "",
                title=a.get("title"), posted_date=a.get("postedDate"),
                comment_on_document_id=a.get("commentOnDocumentId"),
                comment_text_verbatim=body[:6000],
                comment_text_chars=len(body),
                n_attachments=len(atts), n_attachment_files=nfiles,
                comment_url=f"https://www.regulations.gov/comment/{h['comment_id']}",
                docket_url=f"https://www.regulations.gov/docket/{a.get('docketId')}",
                api_url=url.split("&api_key")[0].split("?")[0],
                retrieved_date=TODAY,
                caveat=("Retrieved fact only. This row records WHO filed, on WHICH "
                        "docket, WHEN, and WHAT THEY WROTE. It asserts no position "
                        "label and no alignment; both are derived downstream from "
                        "two sourced positions, per "
                        "docs/LOBBYING_EXPANSION_RECONCILIATION.md.")))
            log(f"  {h['comment_id']:26s} org={(a.get('organization') or '-')[:38]:38s} "
                f"chars={len(body):<6} att={len(atts)}")
            time.sleep(GAP)
    finally:
        release_host("comment detail fetch complete")
    if out:
        path = REVIEW / "regulations_gov_comment_detail_2026-08-26.csv"
        tmp = str(path) + ".part"
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
            w.writeheader()
            w.writerows(out)
        os.replace(tmp, path)
        log(f"wrote {path} ({len(out)} rows)")
    return 0


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "sample"
    sys.exit({"sample": step_sample, "detail": step_detail}[stage]())
