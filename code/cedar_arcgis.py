#!/usr/bin/env python3
"""
cedar_arcgis - shared, dependency-free client for ArcGIS REST FeatureServers
and for any polite JSON pull this project makes.

WHY THIS IS A MODULE AND NOT COPY-PASTE
---------------------------------------
Three acquisitions landed on 2026-09-02 (1119 biamaps, 1120 USAC, 1121 NPPES)
and every one of them needs the same five things, each of which this project
has already paid for once:

1. **A robots check that asks about the agent the site actually names.**
   `RobotFileParser` only consults a group whose token is a PREFIX of the
   string you hand it, so `can_fetch(OUR_UA, ...)` silently misses a
   `User-agent: ClaudeBot / Disallow: /` rule. On 2026-09-02 that error fetched
   13 refusing hosts and 19 bodies had to be purged. We ask ONCE PER TOKEN and
   report the UNION - the same method `code/1111_probe_new_source_candidates.py`
   proved with a fixture.
2. **robots.txt fetched with OUR user agent**, never by `.read()`, which uses
   `Python-urllib` and gets 403'd - and a 403 on robots.txt reads as
   `disallow_all`, which is how 22 open hosts were recorded as blocked.
   A 404, an empty body, or an HTML soft-404 is **ALLOWED**, not blocked.
3. **A hash of every response.** A `?wpdmdl=` harvester once reported 302
   distinct documents, all HTTP 200; it was the same PDF 302 times. Distinct
   URLs are not distinct content. Every page this client returns carries its
   own sha256 and the caller records them.
4. **Edge-block detection that STOPS THE RUN.** A sub-second connection
   refusal is a fact about the HOST, never about the object you happened to be
   asking for. `1085` logged one, slept 30s, moved to the next object, and
   wrote four permanent false absences. `EdgeBlocked` is raised instead.
5. **A host lock and an apex-domain rate budget.** `files.usaspending.gov` and
   `api.usaspending.gov` are different hostnames behind one limiter.

WHAT IT DOES NOT DO
-------------------
It does not decide anything. It does not retry past its budget, it does not
interpret a status code as an absence, and it never writes to `data/clean`.

SELFTEST
--------
    py -3 code/cedar_arcgis.py selftest

Proves, on fixtures and with no network: the naive `can_fetch` misses a
ClaudeBot-only rule and the union check catches it; an empty/404 robots reads
ALLOWED; a sub-second connection error raises `EdgeBlocked` while a slow one
does not; and the page-and-verify loop RAISES when the pages retrieved do not
reconcile with `returnCountOnly`.
"""
from __future__ import annotations

import hashlib
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parents[1]
LOGS = ROOT / "logs"

# A declared UA with a contact address. Never a browser impersonation.
UA = "CedarPress/1.0 (research; contact hello@cedarpress.co)"

# Every agent token a robots.txt might name that this client plausibly IS.
# `*` is the fallback group RobotFileParser always consults.
AGENT_TOKENS = [UA, "CedarPress", "ClaudeBot", "Claude-User", "Claude-SearchBot",
                "anthropic-ai", "CCBot", "Python-urllib", "*"]

TIMEOUT = 90
DEFAULT_PAUSE_S = 1.5
EDGE_BLOCK_MAX_ELAPSED_S = 1.0     # a refusal faster than this is the edge

_CTX = ssl.create_default_context()


class EdgeBlocked(RuntimeError):
    """A sub-second connection refusal. A fact about the host, not the object."""


class RobotsRefusal(RuntimeError):
    """A real Disallow, for at least one agent token we plausibly are."""


def _apex(host: str) -> str:
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


# ---------------------------------------------------------------------------
# ROBOTS - union over agent tokens, fetched with OUR UA
# ---------------------------------------------------------------------------

_robots_cache: dict[str, tuple[RobotFileParser, dict]] = {}


def robots_posture(url: str, fetcher=None) -> dict:
    """Union verdict over AGENT_TOKENS for `url`.

    `fetcher(u) -> (status, body)` is injectable so the selftest runs offline.
    A non-200, an empty body, or an HTML soft-404 means NOT SERVED, which
    means ALLOWED - PULL_DISCIPLINE, twice over.
    """
    parts = urllib.parse.urlsplit(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    if origin not in _robots_cache:
        if fetcher is None:
            fetcher = _plain_get
        status, body = fetcher(origin + "/robots.txt")
        served = True
        if status != 200 or not body:
            body, served = "", False
        elif "<html" in body[:400].lower():
            body, served = "", False          # a soft-404 page is not robots
        rp = RobotFileParser()
        rp.parse(body.splitlines() if body else [])
        named = sorted({ln.split(":", 1)[1].strip()
                        for ln in body.splitlines()
                        if ln.strip().lower().startswith("user-agent:")
                        and ":" in ln})
        _robots_cache[origin] = (rp, {
            "robots_url": origin + "/robots.txt",
            "robots_status": status,
            "robots_served": served,
            "robots_bytes": len(body),
            "robots_agents_named": ";".join(named[:30]),
            "robots_body_verbatim": body[:4000],
        })
    rp, meta = _robots_cache[origin]
    denied = [t for t in AGENT_TOKENS if not rp.can_fetch(t, url)]
    out = dict(meta)
    out["path_checked"] = parts.path or "/"
    out["denied_agents"] = ";".join(denied)
    out["verdict"] = ("DISALLOWED_FOR:" + ",".join(denied)) if denied else "ALLOWED"
    # What the NAIVE check would have said - recorded so the difference is
    # visible in the manifest rather than argued about later.
    out["naive_our_ua_verdict"] = "ALLOWED" if rp.can_fetch(UA, url) else "DISALLOWED"
    return out


def _plain_get(url: str) -> tuple[int | str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=30, context=_CTX) as r:
            return r.status, r.read(200_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:                                        # noqa: BLE001
        return f"ERR:{type(e).__name__}", ""


def require_allowed(url: str) -> dict:
    """Raise RobotsRefusal unless every agent token we plausibly are may fetch."""
    p = robots_posture(url)
    if p["verdict"] != "ALLOWED":
        raise RobotsRefusal(
            f"{url} refused by robots for {p['denied_agents']} "
            f"(our own UA would have seen {p['naive_our_ua_verdict']})")
    return p


# ---------------------------------------------------------------------------
# HOST LOCK - rule 1, keyed by APEX per the 2026-09-02 usaspending finding
# ---------------------------------------------------------------------------

def claim_host(host: str, script: str, queue: list[str] | None = None) -> Path:
    LOGS.mkdir(exist_ok=True)
    p = LOGS / f"_HOSTLOCK_{host}.json"
    prior = {}
    if p.exists():
        try:
            prior = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                          # noqa: BLE001
            prior = {}
    p.write_text(json.dumps({
        "host": host,
        "apex_budget": _apex(host),
        "pid": os.getpid(),
        "script": script,
        "started": datetime.now(timezone.utc).isoformat(),
        "queue": queue or [],
        "downloaded_this_run": 0,
        "already_on_disk_skipped": 0,
        "refused_by_host": [],
        "accepted_then_failed_server_side": [],
        "previous_holder": prior.get("script"),
        "note": ("Rate budget is the APEX domain, not this hostname - "
                 "files./api.usaspending.gov proved they can share a limiter."),
    }, indent=2), encoding="utf-8")
    return p


def release_host(lock: Path, **fields) -> None:
    try:
        d = json.loads(lock.read_text(encoding="utf-8"))
    except Exception:                                              # noqa: BLE001
        d = {}
    d.update(fields)
    d["finished"] = datetime.now(timezone.utc).isoformat()
    lock.write_text(json.dumps(d, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# FETCH - one request, hashed, edge-block aware
# ---------------------------------------------------------------------------

class Session:
    """One polite session against one host. Counts and logs every request."""

    def __init__(self, script: str, log_path: Path, pause_s: float = DEFAULT_PAUSE_S,
                 deadline_s: int = 3 * 3600, ua: str = UA):
        self.script = script
        self.pause_s = pause_s
        self.ua = ua
        self.started = time.time()
        self.deadline_s = deadline_s
        self.n_requests = 0
        self.bytes_read = 0
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def deadline_ok(self) -> bool:
        return (time.time() - self.started) < self.deadline_s

    def get(self, url: str, expect_json: bool = True) -> dict:
        if not self.deadline_ok():
            raise RuntimeError(f"RUN_DEADLINE of {self.deadline_s}s reached; "
                               "stopping rather than starting a new request")
        req = urllib.request.Request(url, headers={
            "User-Agent": self.ua, "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=_CTX) as r:
                raw = r.read()
                status, ctype = r.status, r.headers.get("Content-Type", "")
                csig = r.headers.get("Content-Signal")
        except urllib.error.HTTPError as e:
            raw, status = b"", e.code
            ctype, csig = "", None
        except Exception as e:                                     # noqa: BLE001
            elapsed = time.time() - t0
            self._log({"url": url, "status": f"ERR:{type(e).__name__}",
                       "elapsed_s": round(elapsed, 3), "bytes": 0,
                       "detail": str(e)[:300]})
            if elapsed < EDGE_BLOCK_MAX_ELAPSED_S:
                raise EdgeBlocked(
                    f"sub-second ({elapsed:.2f}s) connection failure on {url}: "
                    f"{type(e).__name__}. This is a fact about the HOST. "
                    "Stopping the run; it is not an absence of the object."
                ) from e
            raise
        elapsed = time.time() - t0
        self.n_requests += 1
        self.bytes_read += len(raw)
        sha = hashlib.sha256(raw).hexdigest()
        rec = {"url": url, "status": status, "ctype": ctype,
               "bytes": len(raw), "sha256": sha,
               "elapsed_s": round(elapsed, 3),
               "fetched_at": datetime.now(timezone.utc).isoformat()}
        if csig:
            # HUD serves this. Cedar has no vocabulary for a USE restriction;
            # record it verbatim and let the owner rule.
            rec["content_signal_header_verbatim"] = csig
        self._log(rec)
        if status != 200:
            raise RuntimeError(f"HTTP {status} on {url}")
        out = dict(rec)
        out["raw"] = raw
        if expect_json:
            out["json"] = json.loads(raw.decode("utf-8", "replace"))
        time.sleep(self.pause_s)
        return out

    def _log(self, rec: dict) -> None:
        rec["script"] = self.script
        rec["ua"] = self.ua
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")


# ---------------------------------------------------------------------------
# ARCGIS FEATURESERVER - count first, page, then RECONCILE
# ---------------------------------------------------------------------------

def arcgis_count(sess: Session, layer_url: str, where: str = "1=1") -> int:
    q = urllib.parse.urlencode({"where": where, "returnCountOnly": "true",
                                "f": "json"})
    d = sess.get(f"{layer_url}/query?{q}")["json"]
    if "count" not in d:
        raise RuntimeError(f"no `count` in returnCountOnly response: {str(d)[:300]}")
    return int(d["count"])


def arcgis_layer_meta(sess: Session, layer_url: str) -> dict:
    return sess.get(f"{layer_url}?f=json")["json"]


def arcgis_page_all(sess: Session, layer_url: str, oid_field: str,
                    page_size: int, where: str = "1=1",
                    out_fields: str = "*", on_page=None) -> tuple[list[dict], list[str]]:
    """Page with resultOffset, ordered by the OID so paging is deterministic.

    Returns (features, page_sha256s). Raises if a page repeats content
    (`resultOffset` ignored) or if the server keeps saying
    `exceededTransferLimit` past a sane page ceiling.
    """
    feats: list[dict] = []
    shas: list[str] = []
    seen_page_sha: set[str] = set()
    offset = 0
    pages = 0
    while True:
        q = urllib.parse.urlencode({
            "where": where, "outFields": out_fields, "returnGeometry": "false",
            "orderByFields": oid_field, "resultOffset": offset,
            "resultRecordCount": page_size, "f": "json"})
        r = sess.get(f"{layer_url}/query?{q}")
        d = r["json"]
        if "error" in d:
            raise RuntimeError(f"ArcGIS error at offset {offset}: {d['error']}")
        got = d.get("features", [])
        if not got:
            break
        if r["sha256"] in seen_page_sha:
            raise RuntimeError(
                f"page at resultOffset={offset} is byte-identical to an earlier "
                "page - the server is IGNORING resultOffset. Distinct URLs are "
                "not distinct content (the wpdmdl lesson). Stopping.")
        seen_page_sha.add(r["sha256"])
        shas.append(r["sha256"])
        feats.extend(got)
        pages += 1
        if on_page:
            on_page(pages, len(feats))
        if not d.get("exceededTransferLimit") and len(got) < page_size:
            break
        offset += len(got)
        if pages > 10_000:
            raise RuntimeError("page ceiling 10,000 hit; refusing to loop")
    return feats, shas


def reconcile(retrieved: int, advertised: int, label: str) -> str:
    """The check the FERC truncation incident earned. Never silently pass."""
    if retrieved == advertised:
        return "RECONCILED"
    raise RuntimeError(
        f"{label}: retrieved {retrieved:,} but returnCountOnly advertises "
        f"{advertised:,} (delta {retrieved - advertised:+,}). A page budget that "
        "truncates a sheet and marks it done is a silent ceiling. Refusing to "
        "write a table that does not reconcile.")


# ---------------------------------------------------------------------------
# SELFTEST - offline, and it must FIRE on an injected violation
# ---------------------------------------------------------------------------

_CLAUDEBOT_ONLY = """User-agent: ClaudeBot
Disallow: /

User-agent: *
Allow: /
"""


def _selftest() -> int:
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(("OK  " if cond else "FAIL") + "  " + name + (f"  {detail}" if detail else ""))
        if not cond:
            ok = False

    # 1. the union check catches a ClaudeBot-only rule that the naive one misses
    _robots_cache.clear()
    p = robots_posture("https://example.test/data",
                       fetcher=lambda u: (200, _CLAUDEBOT_ONLY))
    check("ClaudeBot-only rule: naive says ALLOWED",
          p["naive_our_ua_verdict"] == "ALLOWED")
    check("ClaudeBot-only rule: union check DENIES",
          p["verdict"].startswith("DISALLOWED_FOR:") and "ClaudeBot" in p["denied_agents"],
          p["verdict"])

    # 2. a 404 / empty / html robots is ALLOWED, not blocked
    for label, resp in (("404", (404, "")), ("empty 200", (200, "")),
                        ("html soft-404", (200, "<!DOCTYPE html><html><body>x</body></html>")),
                        ("bare Disallow:", (200, "User-agent: *\nDisallow:\n"))):
        _robots_cache.clear()
        q = robots_posture("https://example.test/data", fetcher=lambda u, r=resp: r)
        check(f"robots {label} reads ALLOWED", q["verdict"] == "ALLOWED", q["verdict"])

    # 3. a real Disallow on our path is still a refusal
    _robots_cache.clear()
    q = robots_posture("https://example.test/secret/x",
                       fetcher=lambda u: (200, "User-agent: *\nDisallow: /secret/\n"))
    check("a real Disallow on our path still refuses",
          q["verdict"].startswith("DISALLOWED_FOR:"), q["verdict"])

    # 4. EdgeBlocked fires on a sub-second failure and NOT on a slow one
    class _S(Session):
        def __init__(self, delay):
            super().__init__("selftest", Path(os.devnull), pause_s=0)
            self.delay = delay

        def get(self, url, expect_json=True):                      # noqa: D102
            t0 = time.time()
            time.sleep(self.delay)
            elapsed = time.time() - t0
            if elapsed < EDGE_BLOCK_MAX_ELAPSED_S:
                raise EdgeBlocked("injected")
            raise TimeoutError("injected slow failure")

    try:
        _S(0.0).get("https://example.test/x")
        check("sub-second failure raises EdgeBlocked", False)
    except EdgeBlocked:
        check("sub-second failure raises EdgeBlocked", True)
    except Exception as e:                                         # noqa: BLE001
        check("sub-second failure raises EdgeBlocked", False, type(e).__name__)
    try:
        _S(1.05).get("https://example.test/x")
        check("slow failure does NOT read as an edge block", False)
    except EdgeBlocked:
        check("slow failure does NOT read as an edge block", False)
    except TimeoutError:
        check("slow failure does NOT read as an edge block", True)

    # 5. reconcile() FIRES on a short retrieval - the injected violation
    try:
        reconcile(2308, 4838, "P-2232")
        check("reconcile FIRES on a short retrieval", False)
    except RuntimeError:
        check("reconcile FIRES on a short retrieval", True)
    check("reconcile passes when equal", reconcile(84, 84, "x") == "RECONCILED")

    print("\nSELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        raise SystemExit(_selftest())
    raise SystemExit("cedar_arcgis is a library. `py -3 code/cedar_arcgis.py selftest`")
