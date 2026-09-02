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
py -3 code/221_probe_regulations_gov_comments.py harvest   # FULL-SPINE sweep

=== 2026-09-01: THE PROBE BECAME THE PULLER (stage `harvest`) ===

The 2026-08-26 probe answered the reachability question and stopped.  33
queries, 0 refusals, and no shared table touched.  This stage turns it into
the acquisition run the coverage mandate asks for.

WHAT WAS MEASURED BEFORE WRITING IT, and what each measurement forced:

  * `X-Ratelimit-Limit: 1000` per hour, per api.data.gov key.  This is the
    binding constraint on the whole channel and it is enforced in-process by
    a rolling 3,600s request window, not by a fixed sleep, because a fixed
    sleep cannot survive two runs inside one hour.
  * `page[size]=250` is honoured; `meta.totalPages`/`hasNextPage` are
    truthful; the documented ceiling is page 20 (5,000 records).
  * Response time is 0.5-6s warm, ~20s cold.  Cold-start latency is not a
    throttle and must not be read as one.
  * **The COMMENT SEARCH RESPONSE CARRIES NO `organization` FIELD.**  Its
    attributes are exactly: agencyId, documentType, highlightedContent,
    lastModifiedDate, objectId, postedDate, title, withdrawn.  The submitter's
    organisation lives ONLY on the per-comment detail endpoint, one request
    each.  That single fact decides the shape of this stage: search can
    produce CANDIDATES cheaply and can produce ATTRIBUTIONS only where the
    TITLE itself names the entity.
  * `"A" OR "B"` returns 0 results - searchTerm is a phrase, not a query
    language.  Queries cannot be batched, so the request budget is linear in
    the number of entities and there is no way around it.

WHAT IT WRITES, AND THE LINE BETWEEN THE TWO FILES

  data/clean/regulations_gov_comments.csv
      ATTRIBUTED only: the comment's own title names the entity.  scope
      `entity`, inclusion basis `named_entity`.
  data/clean/regulations_gov_entity_coverage.csv
      One row PER ENTITY QUERIED, including the ones that returned nothing.
      A zero here is a measured zero with its query URL, which is the whole
      point - "absence under a filter is a property of the filter"
      (docs/PULL_DISCIPLINE.md).
  review/regulations_gov_comment_candidates.csv
      TEXT_MENTION_ONLY.  A rulemaking that mentions a tribe is not a comment
      BY that tribe.  These are candidates for a ruling and they stay out of
      data/clean, per the sweep doctrine: a sweep produces candidates, never
      attributions.

PAGE BUDGET.  Page 1 is fetched for every entity.  Pages 2+ are fetched only
where page 1 produced at least one title-attributed hit - i.e. only where the
name has demonstrated that it finds the entity's OWN comments.  Without that
gate a two-token place name ("Bear River", 813 hits; "Blue Lake", 2,139)
spends the hour's budget on other people's comments about a lake.
"""
import csv, json, os, re, sys, time, urllib.parse, urllib.request, urllib.error
import collections, datetime, pathlib, subprocess

csv.field_size_limit(10 ** 8)
ROOT = pathlib.Path(__file__).resolve().parent.parent
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


def _pid_is_live(pid):
    """Is this PID a LIVE python process?

    PULL_DISCIPLINE.md is emphatic in both directions: `ps aux` cannot answer
    this on Windows and manufactures false confidence, while a check that
    counts log-watchers manufactures false blocks. So this selects `Name` as
    well as `ProcessId` and requires the image to be a python interpreter -
    the mirror-image guard the same doc prescribes.

    Returns True if live, False if verifiably dead, None if UNKNOWN. Unknown
    is treated as live by the caller: failing to start is recoverable, and
    stealing a lock from a running poller is not.
    """
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False        # a lock with no usable pid cannot own anything
    try:
        out = subprocess.run(
            ["wmic", "process", "where", f"ProcessId={pid}",
             "get", "Name,ProcessId", "/format:csv"],
            capture_output=True, text=True, timeout=30).stdout
    except Exception:
        return None         # cannot tell -> do not steal
    for line in out.splitlines():
        low = line.strip().lower()
        if not low or low.startswith("node,"):
            continue
        if str(pid) in low and any(
                img in low for img in ("python.exe", "pythonw.exe", "py.exe")):
            return True
    return False


def claim_host(note):
    p = LOGS / f"_HOSTLOCK_{HOST}.json"
    if p.exists():
        cur = json.loads(p.read_text(encoding="utf-8"))
        if cur.get("active"):
            # A KILLED POLLER MUST NOT BLOCK THE HOST FOREVER. Before this
            # check, stopping a harvest mid-run left `active: true` behind and
            # every later run exited 3 - the lock outlived the process it was
            # protecting, and the only way out was deleting a lock by hand,
            # which is exactly how a lock stops being trusted.
            live = _pid_is_live(cur.get("pid"))
            if live is False:
                log(f"HOSTLOCK held by dead pid {cur.get('pid')} "
                    f"({cur.get('script')}); reclaiming")
                cur["reclaimed_from_dead_pid"] = {
                    "pid": cur.get("pid"), "script": cur.get("script"),
                    "started": cur.get("started"),
                    "reclaimed_by": f"code/{SCRIPT}",
                    "reclaimed_at": datetime.datetime.now(
                        datetime.timezone.utc).isoformat(),
                    "evidence": "Win32_Process shows no live python "
                                "interpreter with that ProcessId"}
            else:
                log(f"HOSTLOCK held by {cur.get('script')} "
                    f"(pid {cur.get('pid')}, live={live}); queued and exiting")
                cur.setdefault("queue", []).append(
                    {"script": f"code/{SCRIPT}", "note": note})
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




# =====================================================================
# STAGE `harvest` -- the full-spine acquisition run (added 2026-09-01)
# =====================================================================

CLEAN = ROOT / "data" / "clean"
RAWH = ROOT / "data" / "raw" / "external" / "regulations_gov"
RAWH.mkdir(parents=True, exist_ok=True)
CLEAN.mkdir(parents=True, exist_ok=True)
HSTATE = RAWH / "_221_harvest_state.json"
RUN_DATE = datetime.date.today().isoformat()

# The api.data.gov ceiling, measured from X-Ratelimit-Limit on 2026-09-01.
RATE_LIMIT_PER_HOUR = 1000
RATE_BUDGET = 900              # leave headroom for a peer on the same key
RATE_WINDOW_S = 3600
HARVEST_GAP = 4.0              # 900/hr floor even if the window is empty
HARVEST_DEADLINE_S = 110 * 60
PAGE_SIZE = 250
MAX_PAGES = 4                  # 1,000 records; API ceiling is page 20


def _done_key(entity_id, name_source, capped):
    """The checkpoint key, and it CARRIES THE PAGE BUDGET when the budget bit.

    Defect class 4 - "a per-unit budget that can truncate and still mark
    COMPLETE" - is exactly the trap here: an entity whose search reports 12
    pages and whose read stopped at MAX_PAGES=4 is NOT done, and a resume
    keyed on the entity alone would never revisit it. So a CAPPED read is
    keyed `<entity>|<source>|p<MAX_PAGES>`: re-running with the same budget
    correctly skips it, and raising MAX_PAGES correctly re-opens it. A read
    that reached the source's own total is keyed `|pALL` and is done for
    good, whatever the budget is set to later.
    """
    return "%s|%s|%s" % (entity_id, name_source,
                         ("p%d" % MAX_PAGES) if capped else "pALL")

# Ordered most-likely-to-petition first, so a run cut short by the deadline
# has still covered the classes that do the petitioning.
CLASS_PRIORITY = [
    "Federally recognized tribe",
    "Intertribal Organization",
    "Federal-level constituency entity",
    "Federal-level self-governance consortium",
    "Alaska Native Regional Corporation",
    "Federally recognized Alaska Native Village",
    "State-recognized tribe",
    "Native Hawaiian Organization",
    "Tribal College or University",
    "Urban Indian Organization",
    "ANCSA Group Corporation",
    "Alaska Native Village Corporation",
    "Native Community Development Financial Institution",
    "Native Financial Institution",
    "State-level constituency entity",
    "Individually Native-owned business",
    "BIE School",
]

# ADR-010 scope. A coalition speaking for all of Indian Country is NOT an
# unresolved entity link; it is its own scope. These classes speak for a
# membership, so a comment they file is `indian_country`-scoped even though
# the FILER is a named Cedar entity -- both facts are recorded, in
# record_scope and in cedar_entity_id respectively.
COALITION_CLASSES = {
    "Intertribal Organization",
    "Federal-level constituency entity",
    "Federal-level self-governance consortium",
    "State-level constituency entity",
}

_RATE = []          # epoch seconds of every request this process has made


def _rate_wait():
    """Rolling-window limiter. A fixed sleep cannot survive two runs inside
    one hour; counting requests can."""
    now = time.time()
    while _RATE and now - _RATE[0] > RATE_WINDOW_S:
        _RATE.pop(0)
    if len(_RATE) >= RATE_BUDGET:
        nap = RATE_WINDOW_S - (now - _RATE[0]) + 1
        log("  rate window full (%d/%d); sleeping %.0fs"
            % (len(_RATE), RATE_BUDGET, nap))
        time.sleep(max(1, nap))
        return _rate_wait()
    if _RATE:
        gap = HARVEST_GAP - (now - _RATE[-1])
        if gap > 0:
            time.sleep(gap)
    _RATE.append(time.time())


def _get_rated(path, params):
    """get() plus the rate window and the X-Ratelimit-Remaining reading."""
    _rate_wait()
    params = dict(params)
    url = "%s/%s?%s" % (API, path, urllib.parse.urlencode(params))
    req = urllib.request.Request(url, headers={
        "X-Api-Key": KEY, "User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        remaining = r.headers.get("X-Ratelimit-Remaining")
        body = json.loads(r.read().decode("utf-8", "replace"))
    if remaining is not None and str(remaining).isdigit() and int(remaining) < 40:
        log("  !! X-Ratelimit-Remaining=%s; pausing 300s" % remaining)
        time.sleep(300)
    return body, url.split("&api_key")[0], remaining


def _oneline(v):
    """Collapse whitespace so one CSV record is one PHYSICAL line.

    regulations.gov titles and search excerpts carry raw newlines. A quoted
    field containing them is valid CSV, and `25_build_publication_layer.py`
    counts it correctly - but `27_build_dataset_manifests.py` counts PHYSICAL
    LINES, so the same 172-row table was published to buyers as "1,219 rows".
    Two shipped artefacts disagreeing about the size of one table is worse
    than either being wrong alone. Nothing of value is lost: an excerpt is a
    display string, and its line breaks are the search engine's, not the
    submitter's.
    """
    return re.sub(r"\s+", " ", str(v or "")).strip()


def _query_names():
    """One or two query names per spine entity, ordered by class priority.

    `canonical_name` is Cedar's name; `fr_official_name` is the Federal
    Register's. Where they differ the FR form is what an agency docket is
    most likely to print, so BOTH are queried and the coverage table records
    which one found what. One-token names are refused: a search for
    "Seminole" is a search for a county.
    """
    rows = list(csv.DictReader(SPINE.open(encoding="utf-8-sig")))
    order = {c: i for i, c in enumerate(CLASS_PRIORITY)}
    rows.sort(key=lambda r: (order.get(r["entity_class"], 99),
                             r["canonical_name"]))
    out = []
    for r in rows:
        seen = set()
        for src, nm in (("canonical_name", r.get("canonical_name") or ""),
                        ("fr_official_name", r.get("fr_official_name") or "")):
            nm = nm.strip()
            key = squash(nm)
            if not nm or len(nm.split()) < 2 or key in seen:
                continue
            seen.add(key)
            out.append(dict(cedar_entity_id=r["tribe_id"],
                            entity_class=r["entity_class"],
                            state=r.get("state") or "",
                            query_name=nm, query_name_source=src))
    return out


def _scope_for(entity_class):
    if entity_class in COALITION_CLASSES:
        return ("indian_country",
                "ADR-010: the filer is a named Cedar entity AND it advocates "
                "for a membership rather than for one tribe. cedar_entity_id "
                "names the filer; record_scope says who the filing is for.")
    return ("entity",
            "ADR-010: the comment's own title names one Cedar entity, which "
            "is the filer.")


def _derive_append(canonical, path):
    """The header an APPEND must use: the LIVE file's, verbatim.

    ADR-017 / `845` rule 17. A fixed literal header is bad enough in a
    wholesale rewrite - it deletes an in-place enricher's column. In an
    APPEND it is worse: the literal names 38 columns, the file carries 39,
    and every appended field past the 38th lands one column to the left.
    Nothing errors and the misalignment is invisible.

    So when the file already exists, the live header WINS - order and all.
    Extras the literal does not name (e.g. `cedar_uid`, added in place after
    the first harvest) come out blank on the appended rows, which is honest:
    the enricher runs last and will fill them. If the literal names a column
    the file does NOT have, appending cannot add it, so this raises rather
    than silently drop the values.
    """
    if not path.exists():
        return list(canonical)
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            live = next(csv.reader(fh), [])
    except OSError:
        return list(canonical)
    if not live:
        return list(canonical)
    missing = [c for c in canonical if c not in live]
    if missing:
        raise SystemExit(
            "REFUSING to append to %s: this run wants to write %d column(s) "
            "the file does not have (%s). Appending cannot add a column, and "
            "writing under the literal header would misalign every field past "
            "the first mismatch. Rebuild the file instead."
            % (path, len(missing), ", ".join(missing[:6])))
    return list(live)


def _append_csv(path, rows, fields):
    """Append-with-header. The harvest is resumable, so every write must be
    survivable by a process killed between entities."""
    if not rows:
        return
    new = not path.exists()
    fields = _derive_append(fields, path)
    with open(path, "w" if new else "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerows(rows)


CFIELDS = ["regulations_gov_comment_row_id", "comment_id", "agency_id",
           "document_type", "title", "posted_date", "posted_year",
           "withdrawn", "cedar_entity_id", "cedar_entity_name",
           "entity_class", "query_name", "query_name_source",
           "attribution_class", "attribution_basis", "record_scope",
           "record_scope_basis", "inclusion_basis", "matched_terms",
           "highlighted_excerpt", "event_class", "channel", "is_lobbying",
           "rule_basis", "comment_url", "query_url", "confidence_tier",
           "retrieved_date", "built_by_script"]

VFIELDS = ["cedar_entity_id", "cedar_entity_name", "entity_class", "state",
           "query_name", "query_name_source", "http_status",
           "comments_matching_total", "records_retrieved", "pages_fetched",
           "pages_available", "page_budget_exhausted",
           "title_attributed_rows", "text_mention_rows",
           "earliest_posted_date", "latest_posted_date",
           "distinct_agencies", "top_agencies", "coverage_status",
           "coverage_basis", "query_url", "retrieved_date",
           "built_by_script"]

QFIELDS = ["candidate_id", "comment_id", "agency_id", "posted_date", "title",
           "cedar_entity_id", "cedar_entity_name", "entity_class",
           "query_name", "highlighted_excerpt", "refusal_reason",
           "question_for_review", "YOUR_RULING", "comment_url",
           "retrieved_date", "built_by_script"]

RULE_BASIS_H = (
    "Retrieved fact only. This row records that a public submission on a "
    "federal rulemaking docket carries this entity's name in its TITLE, on "
    "this date, before this agency. It asserts no position, no alignment and "
    "no outcome. A regulations.gov comment is advocacy and is NOT LDA "
    "lobbying: is_lobbying=0 on every row.")


def step_harvest():
    picks = _query_names()
    st = {"done": [], "queries_sent": 0, "http_ok": 0,
          "refused_by_host": [], "already_done_skipped": 0,
          "stopped_early": None, "runs": []}
    if HSTATE.exists():
        st = json.loads(HSTATE.read_text(encoding="utf-8"))
        st.setdefault("runs", [])
        st.setdefault("refused_by_host", [])
    done = set(st.get("done") or [])
    # An entity is skipped only if it is done EITHER completely (`pALL`) or
    # at the page budget currently in force. Raising MAX_PAGES re-opens every
    # capped entity automatically - see `_done_key`.
    todo = [p for p in picks
            if _done_key(p["cedar_entity_id"], p["query_name_source"], False)
            not in done
            and _done_key(p["cedar_entity_id"], p["query_name_source"], True)
            not in done]
    st["already_done_skipped"] = len(picks) - len(todo)
    log("%d query names on the spine; %d not yet harvested"
        % (len(picks), len(todo)))
    if not todo:
        log("nothing to do -- harvest complete for every spine query name")
        return 0
    if not claim_host("full-spine regulations.gov comment harvest"):
        return 3

    spine = {r["tribe_id"]: r for r in
             csv.DictReader(SPINE.open(encoding="utf-8-sig"))}
    cpath = CLEAN / "regulations_gov_comments.csv"
    vpath = CLEAN / "regulations_gov_entity_coverage.csv"
    qpath = REVIEW / "regulations_gov_comment_candidates.csv"
    run_started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    consec = 0
    n_attr = n_cand = 0
    try:
        for p in todo:
            if time.time() - START > HARVEST_DEADLINE_S:
                st["stopped_early"] = "RUN_DEADLINE"
                log("RUN_DEADLINE reached -- checkpointed; re-run to resume")
                break
            ent = spine.get(p["cedar_entity_id"], {})
            cname = ent.get("canonical_name") or p["query_name"]
            want = squash(p["query_name"])
            scope, scope_basis = _scope_for(p["entity_class"])
            crows, qrows = [], []
            total = 0
            pages_avail = 0
            got = 0
            status = 200
            agencies = collections.Counter()
            dates = []
            qurl = ""
            page = 1
            while page <= MAX_PAGES:
                try:
                    st["queries_sent"] += 1
                    js, qurl, _rem = _get_rated("comments", {
                        "filter[searchTerm]": '"%s"' % p["query_name"],
                        "page[size]": PAGE_SIZE, "page[number]": page,
                        "sort": "-postedDate"})
                    st["http_ok"] += 1
                    consec = 0
                except urllib.error.HTTPError as e:
                    consec += 1
                    status = e.code
                    st["refused_by_host"].append([p["query_name"], page, e.code])
                    log("  %-45s HTTP %s" % (p["query_name"][:45], e.code))
                    if e.code == 429:
                        time.sleep(600)
                    break
                except Exception as e:
                    consec += 1
                    status = str(e)[:80]
                    st["refused_by_host"].append([p["query_name"], page,
                                                  str(e)[:160]])
                    break
                meta = js.get("meta") or {}
                total = meta.get("totalElements", 0) or 0
                pages_avail = meta.get("totalPages", 0) or 0
                data = js.get("data") or []
                got += len(data)
                for d in data:
                    a = d.get("attributes") or {}
                    title = _oneline(a.get("title"))
                    posted = (a.get("postedDate") or "")[:10]
                    agencies[a.get("agencyId") or ""] += 1
                    if posted:
                        dates.append(posted)
                    cid = d.get("id")
                    excerpt = _oneline(
                        re.sub(r"<[^>]+>", " ",
                               a.get("highlightedContent") or ""))[:900]
                    if want and want in squash(title):
                        crows.append(dict(
                            regulations_gov_comment_row_id="RGC-%s-%s"
                                % (p["cedar_entity_id"], cid),
                            comment_id=cid, agency_id=a.get("agencyId") or "",
                            document_type=a.get("documentType") or "",
                            title=title, posted_date=posted,
                            posted_year=posted[:4],
                            withdrawn=a.get("withdrawn"),
                            cedar_entity_id=p["cedar_entity_id"],
                            cedar_entity_name=cname,
                            entity_class=p["entity_class"],
                            query_name=p["query_name"],
                            query_name_source=p["query_name_source"],
                            attribution_class="TITLE_NAMES_THE_ENTITY",
                            attribution_basis=(
                                "The comment's own title, as regulations.gov "
                                "publishes it, contains the entity name that "
                                "was queried. The submitter's `organization` "
                                "field is NOT in the search response and is "
                                "retrieved only by stage `detail`."),
                            record_scope=scope,
                            record_scope_basis=scope_basis,
                            inclusion_basis="named_entity",
                            matched_terms=p["query_name"],
                            highlighted_excerpt=excerpt,
                            event_class="ADVOCACY",
                            channel="ADMINISTRATIVE_COMMENT",
                            is_lobbying="0",
                            rule_basis=RULE_BASIS_H,
                            comment_url="https://www.regulations.gov/comment/%s"
                                % cid,
                            query_url=qurl,
                            confidence_tier="B",
                            retrieved_date=RUN_DATE,
                            built_by_script="code/" + SCRIPT))
                    else:
                        qrows.append(dict(
                            candidate_id="RGQ-%s-%s"
                                % (p["cedar_entity_id"], cid),
                            comment_id=cid, agency_id=a.get("agencyId") or "",
                            posted_date=posted, title=title,
                            cedar_entity_id=p["cedar_entity_id"],
                            cedar_entity_name=cname,
                            entity_class=p["entity_class"],
                            query_name=p["query_name"],
                            highlighted_excerpt=excerpt,
                            refusal_reason="TEXT_MENTION_ONLY",
                            question_for_review=(
                                "The entity name appears in this comment's "
                                "TEXT but not in its title. Did this entity "
                                "FILE this comment, or does the comment "
                                "merely mention it?"),
                            YOUR_RULING="",
                            comment_url="https://www.regulations.gov/comment/%s"
                                % cid,
                            retrieved_date=RUN_DATE,
                            built_by_script="code/" + SCRIPT))
                if page == 1 and not crows:
                    break          # this name never finds its own filings
                if not meta.get("hasNextPage"):
                    break
                page += 1
            capped = got < total
            _append_csv(cpath, crows, CFIELDS)
            _append_csv(qpath, qrows, QFIELDS)
            n_attr += len(crows)
            n_cand += len(qrows)
            _append_csv(vpath, [dict(
                cedar_entity_id=p["cedar_entity_id"], cedar_entity_name=cname,
                entity_class=p["entity_class"], state=p["state"],
                query_name=p["query_name"],
                query_name_source=p["query_name_source"],
                http_status=status, comments_matching_total=total,
                records_retrieved=got, pages_fetched=min(page, MAX_PAGES),
                pages_available=pages_avail,
                page_budget_exhausted=("Y" if (pages_avail > MAX_PAGES
                                               and got < total) else "N"),
                title_attributed_rows=len(crows),
                text_mention_rows=len(qrows),
                earliest_posted_date=min(dates) if dates else "",
                latest_posted_date=max(dates) if dates else "",
                distinct_agencies=len(agencies),
                top_agencies="|".join("%s:%d" % (k, v)
                                      for k, v in agencies.most_common(8)),
                coverage_status=("NO_COMMENTS_MATCH_THIS_NAME" if total == 0
                                 else ("CAPPED" if capped else "FULL")),
                coverage_basis=(
                    "regulations.gov v4 /comments, exact-phrase searchTerm on "
                    "this name, whole available archive (the API applies no "
                    "date floor). CAPPED means this build's own 4-page budget "
                    "stopped short of totalElements, not that the source did."),
                query_url=qurl, retrieved_date=RUN_DATE,
                built_by_script="code/" + SCRIPT)], VFIELDS)
            done.add(_done_key(p["cedar_entity_id"], p["query_name_source"],
                               capped))
            if capped:
                # RETRIEVED vs SOURCE-REPORTED, named, per entity. A count of
                # "capped" is not actionable; the entity and the shortfall are.
                st.setdefault("capped_by_page_budget", []).append(
                    {"cedar_entity_id": p["cedar_entity_id"],
                     "query_name": p["query_name"],
                     "retrieved": got, "source_reported_total": total,
                     "pages_available": pages_avail,
                     "page_budget": MAX_PAGES})
            st["done"] = sorted(done)
            HSTATE.write_text(json.dumps(st, indent=1), encoding="utf-8")
            log("  %-24s %-38s total=%-6s attr=%-4d cand=%-4d%s [%d/%d]"
                % (p["entity_class"][:24], p["query_name"][:38], total,
                   len(crows), len(qrows),
                   (" CAPPED %d/%d" % (got, total)) if capped else "",
                   len(done), len(picks)))
            if consec >= MAX_CONSEC_REFUSALS:
                st["stopped_early"] = "%d consecutive refusals" % consec
                log("stopping: consecutive refusals -- this is a HOST fact")
                break
    finally:
        st["runs"].append({
            "started": run_started,
            "ended": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "queries_sent_cumulative": st["queries_sent"],
            "attributed_rows_this_run": n_attr,
            "candidate_rows_this_run": n_cand,
            "stopped_early": st.get("stopped_early")})
        HSTATE.write_text(json.dumps(st, indent=1), encoding="utf-8")
        release_host("harvest checkpointed", {
            "downloaded_this_run": st["queries_sent"] > 0,
            "already_on_disk_skipped": st["already_done_skipped"],
            "refused_by_host": st["refused_by_host"][-20:],
            "accepted_then_failed_server_side": []})
    # A kill between `_append_csv` and the checkpoint write can leave ONE
    # entity's rows on disk without its done-key, so a resume re-appends them.
    # The row ids are deterministic, so the repair is exact and idempotent.
    for path, key in ((cpath, "regulations_gov_comment_row_id"),
                      (qpath, "candidate_id")):
        log("  deduped %s: %d rows removed" % (path.name, _dedupe(path, key)))
    # The coverage table has no natural row id - its grain is one row per
    # (entity, query name source) - and it needs one, because a killed run
    # that is resumed re-reads the entity and appends a SECOND coverage row.
    # Measured 2026-09-01: a stopped run whose python outlived its shell
    # wrapper produced 51 coverage rows for 24 entities. Keep the LAST, which
    # is the most recent read of that entity.
    log("  deduped %s: %d rows removed"
        % (vpath.name, _dedupe(vpath, ("cedar_entity_id", "query_name_source"),
                               keep="last")))
    log("\nharvest: %d/%d query names done | +%d attributed | +%d candidates"
        % (len(done), len(picks), n_attr, n_cand))
    capped = st.get("capped_by_page_budget") or []
    if capped:
        log("  %d entities CAPPED by the %d-page budget - each is named in "
            "_221_harvest_state.json with retrieved vs source-reported, and "
            "each is keyed `p%d` so raising MAX_PAGES re-opens it:"
            % (len(capped), MAX_PAGES, MAX_PAGES))
        for c in capped[:10]:
            log("    %-40s %d of %d" % (c["query_name"][:40], c["retrieved"],
                                        c["source_reported_total"]))
    _harvest_codebook()
    return 0


def _dedupe(path, key, keep="first"):
    """Remove duplicate rows by a deterministic key.

    `key` is a column name or a tuple of them. `keep="first"` for an immutable
    row id; `keep="last"` where a later read supersedes an earlier one, as it
    does for the per-entity coverage row. Idempotent; a no-op on a clean file.
    """
    if not path.exists():
        return 0
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rd = csv.DictReader(fh)
        fields = rd.fieldnames or []
        rows = list(rd)
    cols = (key,) if isinstance(key, str) else tuple(key)
    # lint-ok: class5 - this is a SCHEMA guard, not an 'already done'
    # short-circuit: it returns 0 when the file does not carry the key
    # columns, which is a fact about the file, not a skipped unit of
    # work. The log-rewrite the detector pairs it with is line 358,
    # `_221_state.json`, which belongs to the unrelated `sample` stage.
    # The harvest's own state DOES merge and was checked: it is loaded
    # from HSTATE at the top of step_harvest, `queries_sent`/`http_ok`
    # accumulate across runs, and `done`, `runs`, `refused_by_host` and
    # `capped_by_page_budget` are appended to, never replaced. A second
    # run therefore cannot rewrite the counters to zero, which is the
    # 164 defect this class exists to catch.
    if any(c not in fields for c in cols):
        return 0
    if keep == "last":
        rows = list(reversed(rows))
    seen, kept = set(), []
    for r in rows:
        k = tuple(r.get(c) or "" for c in cols)
        if k in seen:
            continue
        seen.add(k)
        kept.append(r)
    if keep == "last":
        kept.reverse()
    keep_rows = kept
    removed = len(rows) - len(keep_rows)
    if removed:
        tmp = str(path) + ".part"
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(keep_rows)
        os.replace(tmp, path)
    return removed


def _harvest_codebook():
    sys.path.insert(0, str(ROOT / "code"))
    try:
        import cedar_codebook
    except Exception as e:                                  # pragma: no cover
        log("codebook fragment skipped: %s" % e)
        return
    D = {
        "regulations_gov_comment_row_id":
            "Deterministic key: RGC-<cedar_entity_id>-<comment_id>. One row "
            "per (entity, comment); a comment naming two entities yields two.",
        "comment_id": "regulations.gov comment id, e.g. EPA-HQ-OW-2023-0001-0042.",
        "agency_id": "regulations.gov agency acronym that owns the docket.",
        "document_type": "regulations.gov document type; 'Public Submission'.",
        "title": "Comment title, verbatim as regulations.gov publishes it.",
        "posted_date": "Date the agency posted the comment (YYYY-MM-DD).",
        "posted_year": "Calendar year of posted_date.",
        "withdrawn": "True where the agency withdrew the submission.",
        "cedar_entity_id": "Cedar spine tribe_id of the entity named in the title.",
        "cedar_entity_name": "Spine canonical name of that entity.",
        "entity_class": "Spine entity_class of that entity.",
        "query_name": "The exact phrase searched.",
        "query_name_source": "Which spine column supplied the phrase - "
                             "canonical_name or fr_official_name.",
        "attribution_class": "TITLE_NAMES_THE_ENTITY on every row in this "
                             "file. Text-only mentions are held in "
                             "review/regulations_gov_comment_candidates.csv.",
        "attribution_basis": "What the attribution rests on, in words.",
        "record_scope": "ADR-010 scope. `entity` for a single-tribe filer; "
                        "`indian_country` where the filer is a coalition "
                        "advocating for a membership.",
        "record_scope_basis": "Why that scope.",
        "inclusion_basis": "ADR-013 / C12 inclusion basis: named_entity.",
        "matched_terms": "The term whose match put this row in Cedar.",
        "highlighted_excerpt": "Search-engine excerpt, tags stripped. An "
                               "excerpt chosen by the search engine, NOT the "
                               "submitter's full text - stage `detail` "
                               "retrieves that.",
        "event_class": "cedar_domain EventClass: ADVOCACY.",
        "channel": "cedar_domain AdvocacyChannel: ADMINISTRATIVE_COMMENT.",
        "is_lobbying": "0 on every row. A rulemaking comment is advocacy and "
                       "is not LDA lobbying.",
        "rule_basis": "What this record does and does not assert.",
        "comment_url": "Public regulations.gov page for the comment.",
        "query_url": "The API query that returned it, minus the key.",
        "confidence_tier": "B. The title is the source's own field, but a "
                           "title match is a name match, not an identifier.",
        "retrieved_date": "Date of the request.",
        "built_by_script": "Producer.",
        "state": "Spine state.",
        "http_status": "HTTP status of the last request for this name.",
        "comments_matching_total": "meta.totalElements the API reported.",
        "records_retrieved": "Records this build actually read.",
        "pages_fetched": "Pages this build read (page[size]=250).",
        "pages_available": "meta.totalPages the API reported.",
        "page_budget_exhausted": "Y where this build's 4-page cap, not the "
                                 "source, stopped the read.",
        "title_attributed_rows": "Rows written to regulations_gov_comments.csv.",
        "text_mention_rows": "Rows written to the review candidate file.",
        "earliest_posted_date": "Earliest posted_date seen for this name.",
        "latest_posted_date": "Latest posted_date seen for this name.",
        "distinct_agencies": "Distinct agencyId values among retrieved rows.",
        "top_agencies": "agencyId:count, '|' separated, top 8.",
        "coverage_status": "NO_COMMENTS_MATCH_THIS_NAME | FULL | CAPPED.",
        "coverage_basis": "What the coverage claim rests on.",
    }

    def frag(ds, path, fields):
        if not path.exists():
            return
        rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
        n = len(rows)
        out = []
        for f in fields:
            filled = sum(1 for r in rows if str(r.get(f, "")).strip())
            out.append({"dataset": ds, "variable": f, "type": "text",
                        "units": "",
                        "pct_filled": round(100.0 * filled / n, 1) if n else 0.0,
                        "n_rows": n, "published": 1, "access_tier": "public",
                        "description": D.get(f, ""), "generated": RUN_DATE})
        cedar_codebook.write_fragment(ds, out)
        log("codebook fragment %s: %d variables over %d rows" % (ds, len(out), n))

    frag("04z_regulations_gov_comments",
         CLEAN / "regulations_gov_comments.csv", CFIELDS)
    frag("04z_regulations_gov_entity_coverage",
         CLEAN / "regulations_gov_entity_coverage.csv", VFIELDS)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "sample"
    sys.exit({"sample": step_sample, "detail": step_detail,
              "harvest": step_harvest}[stage]())
