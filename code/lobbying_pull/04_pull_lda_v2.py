"""
Cedar Press Dataset 4 (Native Influence / Lobbying) -- LDA pull, v2.

WHY v2 EXISTS
-------------
v1 (`01_pull_lda_filings.py`) ran 216 keyword sweeps against /filings/ and
paginated each one in full. That is correct but wasteful: the 204 specific-name
keywords overlap the 12 broad keywords almost completely, and every overlapping
page costs a throttled request. v1 was still on keyword 1 of 216 after 35 minutes.

v2 keeps every guarantee of v1 (append-only raw file, dedupe on filing_uuid,
per-page progress checkpoint, resume from wherever it stopped) and adds a
client-first discovery stage that makes the redundancy EXACTLY computable
instead of guessed:

  Stage 1  FILINGS sweep, broad keywords only (12). Bulk-efficient: 25 filings
           per request, little overlap between the broad terms themselves.
  Stage 2  CLIENTS sweep, all keywords (216) against /clients/. The client
           roster is one to two orders of magnitude smaller than the filing
           roster, so this is cheap. It yields the exact client_id set each
           keyword resolves to -- using the API's own matcher, not a local
           re-implementation of its tokenizer.
  Stage 3  Per-client_id FILINGS fetch for every client in the Stage-2 universe
           that is NOT in the client set of a COMPLETED Stage-1 keyword.

The Stage-3 coverage test is exact, and this is the load-bearing claim:
if client C is returned by /clients/?client_name=K, and K's /filings/ sweep ran
to completion, then every filing of C was returned by that sweep -- because both
endpoints apply the same client_name filter. So Stage 3 only has to fetch the
clients the broad nets provably never touched (Cherokee Nation, Koniag, NCAI,
Kamehameha Schools -- names carrying no generic Native token).

MEASURED API BEHAVIOR (2026-08-05)
----------------------------------
  * lda.senate.gov was SUNSET 2026-07-31 (RFC 8594 Sunset header in its own
    OpenAPI spec). Successor host is lda.gov. Both still answer today; this
    script uses the successor.
  * page_size is capped SERVER-SIDE at 25. Requesting 100 returns 25.
  * throttle is 15 requests/minute anonymous (documented; re-measured today:
    13 requests succeeded in 12.3s, the 14th returned 429 Retry-After 33).
    120/min requires a registered API key, which is a user-mediated signup.
  * client_name is a token-PREFIX match, not a substring match.
  * default ordering is ascending by filing date, which is why an interrupted
    sweep looks like a truncated year range rather than a random sample.

ZERO FABRICATION: every line written to raw_filings.jsonl is a filing object as
returned by the API, with two underscore-prefixed provenance keys added
(_pull_keyword / _pull_source, _pull_dt).

Output:
  raw_filings.jsonl        append-only, one filing JSON per line
  clients_universe.jsonl   append-only, one client JSON per line
  pull_progress.json       per-keyword filings sweep state
  client_progress.json     per-keyword clients sweep state
  clientfetch_progress.json per-client_id filings fetch state
"""
import json
import time
import sys
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
RAW_PATH = OUT_DIR / "raw_filings.jsonl"
CLIENTS_PATH = OUT_DIR / "clients_universe.jsonl"
PROGRESS_PATH = OUT_DIR / "pull_progress.json"
CLIENT_PROGRESS_PATH = OUT_DIR / "client_progress.json"
CLIENTFETCH_PROGRESS_PATH = OUT_DIR / "clientfetch_progress.json"

API_ROOT = "https://lda.gov/api/v1"
FILINGS_API = f"{API_ROOT}/filings/"
CLIENTS_API = f"{API_ROOT}/clients/"
PAGE_SIZE = 25
USER_AGENT = "cedar-press-lobbying/2.0 (research; contact elijahsamsonmoreno@gmail.com)"

# Interval-based pacing (start-of-request to start-of-request). A fixed
# post-request sleep silently loses the ~1.2s request latency.
BASE_INTERVAL = 4.30    # ~14.0 req/min against a 15/min ceiling
MAX_INTERVAL = 12.0

# The broad nets. These get FULL /filings/ sweeps in Stage 1.
BROAD_KEYWORDS = [
    "tribe",
    "tribal",
    "pueblo",
    "rancheria",
    "band of",
    "indian community",
    "indian nation",
    "alaska native",
    "native hawaiian",
    "village corporation",
    "regional corporation",
    "intertribal",
]

# Specific names. These get /clients/ sweeps only (Stage 2); any client they
# surface that the broad nets did not cover is fetched by client_id (Stage 3).
SPECIFIC_NAMES = [
    "cherokee nation", "navajo nation", "chickasaw nation",
    "choctaw nation", "muscogee", "seminole nation", "osage nation",
    "mohegan", "mashantucket pequot", "narragansett",
    "oneida indian", "oneida nation", "ho-chunk", "stockbridge-munsee",
    "saginaw chippewa", "sault ste. marie", "little traverse",
    "lac du flambeau", "lac courte oreilles", "menominee",
    "puyallup", "tulalip", "yakama", "colville",
    "muckleshoot", "lummi", "swinomish",
    "salish", "cocopah", "havasupai", "hualapai", "yavapai",
    "white mountain apache", "san carlos apache", "jicarilla apache",
    "mescalero", "fort sill", "tohono o'odham", "akimel",
    "salt river", "ak-chin", "gila river", "pascua yaqui",
    "fort mojave", "colorado river indian",
    "ute mountain", "southern ute", "uintah", "skull valley",
    "shoshone", "arapaho", "northern cheyenne",
    "fort belknap", "fort peck", "blackfeet",
    "sisseton-wahpeton", "spirit lake", "turtle mountain",
    "three affiliated", "mandan", "hidatsa", "arikara",
    "rosebud sioux", "oglala sioux", "cheyenne river sioux", "standing rock",
    "lower brule", "crow creek", "yankton sioux", "santee sioux",
    "winnebago", "ponca",
    "kickapoo", "potawatomi", "sac and fox", "sac & fox",
    "absentee shawnee", "eastern shawnee",
    "delaware nation", "wyandotte",
    "modoc", "peoria",
    "quapaw", "tonkawa", "kaw nation", "pawnee",
    "kiowa", "comanche", "wichita", "caddo nation",
    "alabama-coushatta", "coushatta", "tunica", "chitimacha",
    "jena band",
    "passamaquoddy", "penobscot", "houlton", "mi'kmaq", "micmac",
    "wampanoag", "aquinnah",
    "saint regis mohawk", "st regis mohawk", "mohawk", "tuscarora",
    "seneca nation", "cayuga", "onondaga", "tonawanda",
    "lumbee", "catawba",
    "miccosukee",
    "oklahoma seminole",
    "burns paiute",
    "warm springs", "umatilla", "siletz", "grand ronde", "coquille",
    "cow creek", "coos",
    "nez perce", "kalispel", "coeur d'alene", "kootenai", "shoshone-bannock",
    "northwestern band", "duckwater", "moapa", "las vegas paiute",
    "pyramid lake", "walker river", "fallon", "fort independence",
    "bishop", "big pine", "lone pine", "timbisha",
    "morongo", "soboba", "pala", "pauma", "rincon",
    "san manuel", "san pasqual", "santa rosa", "santa ynez",
    "sycuan", "viejas", "barona", "manzanita", "campo",
    "torres-martinez", "twenty-nine palms", "augustine",
    "pechanga", "agua caliente", "cabazon",
    "yurok", "hoopa", "karuk", "tolowa",
    "round valley", "pinoleville",
    "sherwood valley", "manchester", "stewarts point",
    "cher-ae heights", "blue lake", "robinson",
    "rumsey", "yocha dehe",
    "shingle springs", "miwok", "ione band",
    "buena vista",
    "tule river",
    "hopi", "zuni", "havasu",
    # ANC regional + village
    "calista", "doyon", "sealaska", "ahtna", "asrc",
    "arctic slope regional", "bering straits", "bristol bay",
    "chugach", "cook inlet", "ciri", "koniag", "nana",
    "aleut corporation", "afognak", "alutiiq", "ukpeagvik", "olgoonik",
    "goldbelt", "huna totem", "kuskokwim", "tanana chiefs",
    # NHO orgs
    "kamehameha schools", "office of hawaiian affairs",
    "alu like", "papa ola lokahi", "alakaina", "nakupuna",
    # Intertribal / consortia
    "national congress of american indians", "ncai",
    "national indian gaming",
    "alaska federation of natives",
    "native american rights fund", "narf",
    "national council of urban indian",
    "indian land tenure",
    "indian health board",
    "self-governance",
]


def log(msg):
    print(msg, flush=True)


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1), encoding="utf-8")
    tmp.replace(path)


class Throttle:
    def __init__(self):
        self.interval = BASE_INTERVAL
        self.n_429 = 0
        self.last = 0.0

    def wait(self):
        gap = self.interval - (time.time() - self.last)
        if gap > 0:
            time.sleep(gap)
        self.last = time.time()

    def penalize(self, retry_after):
        self.n_429 += 1
        self.ok_streak = 0
        self.interval = min(MAX_INTERVAL, self.interval + 0.25)
        time.sleep(max(5, retry_after) + 2)
        self.last = time.time()

    def reward(self):
        """
        Decay the interval back toward BASE after sustained success.

        Without this the pacer is a ratchet: a burst of 429s (another process on
        the same IP, a transient server mood) permanently slows the rest of a
        multi-hour run even after the contention is gone. Observed live -- 15
        429s early in Stage 3 left the pace pinned at 10.5 req/min against a
        14 req/min ceiling for the remaining 460 clients. Recovery is slow
        enough (one step per 40 clean requests) that it cannot re-provoke the
        throttle it just backed away from.
        """
        self.ok_streak = getattr(self, "ok_streak", 0) + 1
        if self.ok_streak >= 40 and self.interval > BASE_INTERVAL:
            self.interval = max(BASE_INTERVAL, self.interval - 0.15)
            self.ok_streak = 0


def fetch(url, throttle, max_retries=10):
    """GET with 429 / 5xx / transport retry. Returns parsed JSON or None."""
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode("utf-8"))
            throttle.reward()
            return data
        except urllib.error.HTTPError as e:
            if e.code == 429:
                try:
                    ra = int(e.headers.get("Retry-After"))
                except (TypeError, ValueError):
                    ra = 30
                log(f"    429; sleeping {ra + 2}s (interval now {throttle.interval:.2f}s)")
                throttle.penalize(ra)
                continue
            if e.code in (500, 502, 503, 504):
                log(f"    HTTP {e.code}; retry {attempt + 1}/{max_retries}")
                time.sleep(5 + attempt * 5)
                continue
            log(f"    HTTP {e.code} (fatal for this URL): {url}")
            return None
        except Exception as e:
            log(f"    {type(e).__name__}: {str(e)[:120]}; retry {attempt + 1}/{max_retries}")
            time.sleep(5 + attempt * 5)
    log(f"    RETRIES EXHAUSTED: {url}")
    return None


def qurl(api, **params):
    return f"{api}?{urllib.parse.urlencode(params)}"


class Writer:
    """Append-only JSONL writer with a uuid/id dedupe set loaded from disk."""

    def __init__(self, path, key):
        self.path = path
        self.key = key
        self.seen = set()
        if path.exists():
            with path.open(encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        v = json.loads(line).get(key)
                    except json.JSONDecodeError:
                        continue
                    if v is not None:
                        self.seen.add(v)
        self.fh = path.open("a", encoding="utf-8")

    def write(self, records, provenance):
        n = 0
        for r in records:
            v = r.get(self.key)
            if v is None or v in self.seen:
                continue
            self.seen.add(v)
            r.update(provenance)
            self.fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
        if n:
            self.fh.flush()
        return n

    def close(self):
        self.fh.close()


def sweep(api, keyword, progress, writer, throttle, provenance_key, stats):
    """Paginate one keyword to exhaustion, checkpointing every page."""
    st = progress.setdefault(keyword, {"count": None, "next_page": 1, "done": False})
    if st.get("done"):
        return
    page = int(st.get("next_page") or 1)
    while True:
        throttle.wait()
        data = fetch(qurl(api, page_size=PAGE_SIZE, page=page, client_name=keyword), throttle)
        stats["n_req"] += 1
        if data is None:
            log(f"  [{keyword}] page {page}: unrecoverable; keyword left OPEN for resume")
            return
        if st.get("count") is None:
            st["count"] = data.get("count")
            log(f"  [{keyword}] count={st['count']} "
                f"({-(-(st['count'] or 0) // PAGE_SIZE)} pages)")
        results = data.get("results") or []
        writer.write(results, {provenance_key: keyword,
                               "_pull_dt": time.strftime("%Y-%m-%dT%H:%M:%S")})
        st["next_page"] = page + 1
        save_json(progress_path_for(api), progress)
        if page % 25 == 0:
            rate = stats["n_req"] / max(1e-9, (time.time() - stats["t0"]) / 60)
            log(f"  [{keyword}] page {page}/{-(-(st['count'] or 0) // PAGE_SIZE)} "
                f"| unique={len(writer.seen)} | {rate:.1f} req/min | 429s={throttle.n_429}")
        if not data.get("next") or not results:
            st["done"] = True
            save_json(progress_path_for(api), progress)
            log(f"  [{keyword}] DONE at page {page}; unique now {len(writer.seen)}")
            return
        page += 1


def progress_path_for(api):
    return PROGRESS_PATH if api == FILINGS_API else CLIENT_PROGRESS_PATH


def main():
    stats = {"n_req": 0, "t0": time.time()}
    throttle = Throttle()

    filings_progress = load_json(PROGRESS_PATH, {})
    clients_progress = load_json(CLIENT_PROGRESS_PATH, {})
    clientfetch_progress = load_json(CLIENTFETCH_PROGRESS_PATH, {})

    fw = Writer(RAW_PATH, "filing_uuid")
    cw = Writer(CLIENTS_PATH, "id")

    log(f"START {time.strftime('%Y-%m-%d %H:%M:%S')}  host={API_ROOT}")
    log(f"Resume: {len(fw.seen)} filing_uuids and {len(cw.seen)} client ids already on disk")

    all_keywords = []
    for k in BROAD_KEYWORDS + SPECIFIC_NAMES:
        k = k.strip()
        if k and k not in all_keywords:
            all_keywords.append(k)

    # ---------------- Stage 1: broad-keyword FILINGS sweeps ----------------
    log("\n########## STAGE 1 -- broad-keyword /filings/ sweeps ##########")
    for i, kw in enumerate(BROAD_KEYWORDS, 1):
        if filings_progress.get(kw, {}).get("done"):
            log(f"=== [1.{i}/{len(BROAD_KEYWORDS)}] {kw!r} already complete "
                f"(count={filings_progress[kw].get('count')})")
            continue
        st = filings_progress.get(kw, {})
        log(f"\n=== [1.{i}/{len(BROAD_KEYWORDS)}] {kw!r} from page {st.get('next_page', 1)} ===")
        sweep(FILINGS_API, kw, filings_progress, fw, throttle, "_pull_keyword", stats)

    # ---------------- Stage 2: all-keyword CLIENTS sweeps ----------------
    log("\n########## STAGE 2 -- /clients/ sweeps (client universe) ##########")
    for i, kw in enumerate(all_keywords, 1):
        if clients_progress.get(kw, {}).get("done"):
            continue
        log(f"\n=== [2.{i}/{len(all_keywords)}] {kw!r} ===")
        sweep(CLIENTS_API, kw, clients_progress, cw, throttle, "_client_keyword", stats)

    # ------- Stage 3: per-client_id fetch for clients the broad nets missed -------
    log("\n########## STAGE 3 -- per-client_id /filings/ fetch ##########")
    # Client ids provably covered by a COMPLETED broad filings sweep.
    covered = set()
    for kw in BROAD_KEYWORDS:
        if not filings_progress.get(kw, {}).get("done"):
            log(f"  NOTE: broad keyword {kw!r} did NOT complete; its clients are not "
                f"treated as covered, so they fall through to Stage 3.")
            continue
        with CLIENTS_PATH.open(encoding="utf-8") as f:
            for line in f:
                try:
                    c = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if c.get("_client_keyword") == kw:
                    covered.add(c.get("id"))

    universe = {}
    with CLIENTS_PATH.open(encoding="utf-8") as f:
        for line in f:
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue
            if c.get("id") is not None:
                universe[c["id"]] = c.get("name")

    todo = [cid for cid in universe if cid not in covered]
    log(f"  client universe: {len(universe)} | covered by completed broad sweeps: "
        f"{len(covered)} | to fetch by client_id: {len(todo)}")

    for i, cid in enumerate(sorted(todo), 1):
        st = clientfetch_progress.setdefault(str(cid), {"count": None, "next_page": 1, "done": False})
        if st.get("done"):
            continue
        page = int(st.get("next_page") or 1)
        while True:
            throttle.wait()
            data = fetch(qurl(FILINGS_API, page_size=PAGE_SIZE, page=page, client_id=cid), throttle)
            stats["n_req"] += 1
            if data is None:
                log(f"  [client {cid}] page {page}: unrecoverable; left OPEN")
                break
            if st.get("count") is None:
                st["count"] = data.get("count")
            results = data.get("results") or []
            fw.write(results, {"_pull_keyword": f"client_id:{cid}",
                               "_pull_dt": time.strftime("%Y-%m-%dT%H:%M:%S")})
            st["next_page"] = page + 1
            save_json(CLIENTFETCH_PROGRESS_PATH, clientfetch_progress)
            if not data.get("next") or not results:
                st["done"] = True
                save_json(CLIENTFETCH_PROGRESS_PATH, clientfetch_progress)
                break
            page += 1
        if i % 25 == 0:
            rate = stats["n_req"] / max(1e-9, (time.time() - stats["t0"]) / 60)
            log(f"  stage3 {i}/{len(todo)} clients | filings={len(fw.seen)} "
                f"| {rate:.1f} req/min | 429s={throttle.n_429}")

    fw.close()
    cw.close()
    elapsed = (time.time() - stats["t0"]) / 60
    log(f"\nFINISHED {time.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"  requests this run : {stats['n_req']} in {elapsed:.1f} min "
        f"({stats['n_req'] / max(elapsed, 1e-9):.1f} req/min); 429s={throttle.n_429}")
    log(f"  unique filing_uuids on disk : {len(fw.seen)}")
    log(f"  unique client ids on disk   : {len(cw.seen)}")

    open_f = [k for k in BROAD_KEYWORDS if not filings_progress.get(k, {}).get("done")]
    open_c = [k for k in all_keywords if not clients_progress.get(k, {}).get("done")]
    open_i = [k for k, v in clientfetch_progress.items() if not v.get("done")]
    if open_f or open_c or open_i:
        log(f"  INCOMPLETE -- filings kw: {open_f} | clients kw: {len(open_c)} "
            f"| client_ids: {len(open_i)}")
        sys.exit(2)
    log("  ALL STAGES COMPLETE")


if __name__ == "__main__":
    main()
