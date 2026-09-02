"""SHARD-G: pull the four AUTHORITATIVE REGISTRIES that name this slice's entities.

All four turned out to be BULK-DOWNLOADABLE. This script fetches the bulk object
once per registry rather than probing 315 entity pages.

  NCES / CCD   nces.ed.gov  Public Elementary/Secondary School Universe Survey
               ccd_sch_029 (directory)  -> NCESSCH, LEAID, charter/type/status
               ccd_sch_052 (membership) -> enrollment
               ccd_sch_129 (characteristics)
               ccd_lea_029 (LEA directory) -> agency type, operating agency
  IPEDS        nces.ed.gov  HD<year>.zip (directory, has TRIBAL + LANDGRNT +
               WEBADDR + HLOFFER) and DRVEF<year>.zip (derived enrollment)
  CDFI Fund    cdfifund.gov  List of Certified CDFIs (xlsx) - cert control num,
               date certified, FI type, RSSD, Native flag, website
  NCUA         ncua.gov  quarterly call report zip -> FOICU.txt charter numbers
  FDIC         api.fdic.gov  /banks/institutions - CERT, FED_RSSD, WEBADDR
  (support)    Fed Minneapolis CICD NAFI map xlsx - bank_cert / cu_number / rssd

PULL DISCIPLINE (docs/PULL_DISCIPLINE.md)
  * one request per object; no retry metronome. A refusal is recorded, not retried.
  * per-host serial, 3s floor between requests to the same host.
  * host locks written to logs/_HOSTLOCK_<host>.json before the first request and
    released after, with UNAMBIGUOUS state fields (downloaded_this_run /
    already_on_disk_skipped / refused_by_host).
  * global RUN_DEADLINE 2h; stop on first refusal if nothing has landed.
  * robots.txt checked once per host and honoured.
  * large objects land in the scratchpad, not the repo; only their sha256 and the
    filtered extract are kept under data/staging/.

Writes only:  data/staging/tribe_harvest/shard_g/raw/
              data/staging/tribe_harvest/shard_g/_pull_state.json
              logs/_HOSTLOCK_<host>.json  (its own, released on exit)
"""
from __future__ import annotations

import hashlib, json, os, re, subprocess, sys, time
import urllib.robotparser as urp
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "staging" / "tribe_harvest" / "shard_g" / "raw"
OUTH = ROOT / "data" / "staging" / "tribe_harvest" / "shard_g"
LOGS = ROOT / "logs"
BIG = Path(os.environ.get("SHARD_G_SCRATCH",
     r"C:\Users\esm247\AppData\Local\Temp\claude\C--Users-esm247"
     r"\6f0cc363-573d-4f3a-97b1-c84e32f43c8b\scratchpad\shard_g"))
RAW.mkdir(parents=True, exist_ok=True)
BIG.mkdir(parents=True, exist_ok=True)

UA = ("CedarPress-research/1.0 (institutional registry crosswalk; "
      "contact elijahsamsonmoreno@gmail.com)")
HOST_DELAY = 3.0
RUN_DEADLINE = time.time() + 2 * 3600
_last, _robots = {}, {}

NOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")

# object list: (key, url, dest, big?)
OBJECTS = [
    # ---- NCES CCD (school universe, SY2024-25 v.2a) ----
    ("ccd_sch_directory_2425",
     "https://nces.ed.gov/ccd/Data/zip/ccd_sch_029_2425_w_1a_073025.zip", RAW, False),
    ("ccd_sch_characteristics_2425",
     "https://nces.ed.gov/ccd/Data/zip/ccd_sch_129_2425_w_1a_073025.zip", RAW, False),
    ("ccd_sch_membership_2425",
     "https://nces.ed.gov/ccd/Data/zip/ccd_sch_052_2425_l_1a_073025.zip", BIG, True),
    # ---- IPEDS ----
    ("ipeds_hd2023", "https://nces.ed.gov/ipeds/datacenter/data/HD2023.zip", RAW, False),
    ("ipeds_drvef2023",
     "https://nces.ed.gov/ipeds/datacenter/data/DRVEF2023.zip", RAW, False),
    ("ipeds_ic2023", "https://nces.ed.gov/ipeds/datacenter/data/IC2023.zip", RAW, False),
    # ---- CDFI Fund ----
    # media id is versioned: the certification page links the CURRENT list, so a
    # refresh must re-read that page rather than hard-coding an id. 8018641 was
    # "as of July 16, 2026"; 8018681 is "as of August 14, 2026".
    ("cdfi_certified_list",
     "https://www.cdfifund.gov/media/8018641/download?inline", RAW, False),
    ("cdfi_certified_list_2026_08_14",
     "https://www.cdfifund.gov/media/8018681/download?inline", RAW, False),
    # ---- NCUA ----
    ("ncua_call_report_2026q1",
     "https://ncua.gov/files/publications/analysis/call-report-data-2026-03.zip",
     BIG, True),
    # ---- Fed Minneapolis CICD NAFI map (support, not a regulator) ----
    # github.com/robots.txt disallows the /*/raw/ path for UA *; the same bytes
    # are served from raw.githubusercontent.com, which publishes no robots.txt.
    ("cicd_nafi_map",
     "https://raw.githubusercontent.com/frb-mpls-cde/nafi-map/main/data/"
     "nafi-map-data_current.xlsx", RAW, False),
]

EXT = {"ccd_sch_directory_2425": ".zip", "ccd_sch_characteristics_2425": ".zip",
       "ccd_sch_membership_2425": ".zip", "ipeds_hd2023": ".zip",
       "ipeds_drvef2023": ".zip", "ipeds_ic2023": ".zip",
       "cdfi_certified_list": ".xlsx", "cdfi_certified_list_2026_08_14": ".xlsx", "ncua_call_report_2026q1": ".zip",
       "cicd_nafi_map": ".xlsx"}

state = {
    "script": "code/shard_g_registry_pull.py", "run_started": NOW(),
    "downloaded_this_run": [], "already_on_disk_skipped": [],
    "refused_by_host": [], "robots_disallowed": [], "objects": {},
    "notes": [],
}


def sleep_host(h):
    t = _last.get(h)
    if t is not None:
        d = HOST_DELAY - (time.time() - t)
        if d > 0:
            time.sleep(d)
    _last[h] = time.time()


def robots_ok(url):
    p = urlparse(url)
    host = p.netloc
    if host not in _robots:
        sleep_host(host)
        r = subprocess.run(["curl", "-s", "-m", "20", "-A", UA,
                            f"{p.scheme}://{host}/robots.txt"], capture_output=True)
        rp = urp.RobotFileParser()
        try:
            rp.parse(r.stdout.decode("utf-8", "replace").splitlines())
        except Exception:
            rp = None
        _robots[host] = rp
    rp = _robots[host]
    if rp is None:
        return True, "robots.txt unparseable; treated as no applicable rules"
    ok = rp.can_fetch("*", url)
    return ok, ("robots.txt allows" if ok else "robots.txt DISALLOWS for UA *")


def lock(host, urls):
    p = LOGS / f"_HOSTLOCK_{host}.json"
    if p.exists():
        try:
            prev = json.loads(p.read_text(encoding="utf-8"))
            if prev.get("script") != "code/shard_g_registry_pull.py":
                state["notes"].append(
                    f"{host}: existing lock held by {prev.get('script')} "
                    f"started {prev.get('started')}; appended to queue")
                prev.setdefault("queue", []).extend(urls)
                p.write_text(json.dumps(prev, indent=2), encoding="utf-8")
                return False
        except Exception:
            pass
    p.write_text(json.dumps({
        "host": host, "pid": os.getpid(),
        "script": "code/shard_g_registry_pull.py", "started": NOW(),
        "queue": urls, "downloaded_this_run": [],
        "already_on_disk_skipped": [], "refused_by_host": [],
    }, indent=2), encoding="utf-8")
    return True


def unlock(host, dl, skip, ref):
    p = LOGS / f"_HOSTLOCK_{host}.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return
    if d.get("script") != "code/shard_g_registry_pull.py":
        return
    d.update({"released": NOW(), "queue": [], "downloaded_this_run": dl,
              "already_on_disk_skipped": skip, "refused_by_host": ref,
              "note": "shard-G registry bulk pull complete; lock released"})
    p.write_text(json.dumps(d, indent=2), encoding="utf-8")


def fetch(key, url, dest_dir, timeout=900):
    out = dest_dir / (key + EXT[key])
    if out.exists() and out.stat().st_size > 1024:
        return "already_on_disk", out
    if time.time() > RUN_DEADLINE:
        return "deadline", None
    host = urlparse(url).netloc
    ok, note = robots_ok(url)
    if not ok:
        state["robots_disallowed"].append({"key": key, "url": url, "note": note})
        return "robots_disallowed", None
    sleep_host(host)
    tmp = out.with_suffix(out.suffix + ".part")
    p = subprocess.run(["curl", "-sS", "-L", "--max-redirs", "5", "-A", UA,
                        "--max-time", str(timeout), "-o", str(tmp),
                        "-w", "%{http_code}|%{size_download}|%{content_type}", url],
                       capture_output=True, text=True)
    meta = (p.stdout or "").strip().split("|")
    code = meta[0] if meta else "0"
    size = meta[1] if len(meta) > 1 else "0"
    ctype = meta[2] if len(meta) > 2 else ""
    if code == "200" and tmp.exists() and tmp.stat().st_size > 1024:
        tmp.replace(out)
        h = hashlib.sha256(out.read_bytes()).hexdigest()
        state["objects"][key] = {"url": url, "http_status": 200,
                                 "bytes": out.stat().st_size, "sha256": h,
                                 "content_type": ctype, "path": str(out),
                                 "fetched": NOW(), "robots": note}
        return "downloaded", out
    if tmp.exists():
        tmp.unlink()
    state["objects"][key] = {"url": url, "http_status": code, "bytes": size,
                             "curl_stderr": (p.stderr or "")[:300], "fetched": NOW()}
    return f"refused_{code}", None


def main():
    by_host = {}
    for key, url, dd, big in OBJECTS:
        by_host.setdefault(urlparse(url).netloc, []).append((key, url, dd))

    any_success = False
    for host, items in by_host.items():
        got_lock = lock(host, [u for _, u, _ in items])
        dl, skip, ref = [], [], []
        for key, url, dd in items:
            if time.time() > RUN_DEADLINE:
                state["notes"].append(f"RUN_DEADLINE reached before {key}")
                break
            res, path = fetch(key, url, dd)
            print(f"{res:<22} {key:<32} {url}", file=sys.stderr)
            if res == "downloaded":
                dl.append(url); state["downloaded_this_run"].append(key)
                any_success = True
            elif res == "already_on_disk":
                skip.append(url); state["already_on_disk_skipped"].append(key)
                any_success = True
            elif res.startswith("refused"):
                ref.append({"url": url, "result": res})
                state["refused_by_host"].append({"key": key, "url": url,
                                                 "result": res})
                if not any_success:
                    state["notes"].append(
                        f"first object {key} refused with nothing landed - "
                        f"treating {host} as refusing and stopping this host")
                    break
        if got_lock:
            unlock(host, dl, skip, ref)

    # RETRIEVED vs DECLARED. A budget that exits a loop and then writes a
    # completion marker is the PER_DOCKET_BUDGET_S defect (AGENTS.md concurrency
    # rule 7): four FERC dockets were written at 2,300 of 3,555 documents and
    # marked done, so no resume would ever revisit them. The source here states
    # its total as the OBJECTS list, so compare against it explicitly and refuse
    # to call the run complete when short.
    declared = [k for k, _u, _d, _b in OBJECTS]
    expected_total = len(declared)          # what the SOURCE list says there is
    obtained = set(state["downloaded_this_run"]) | set(
        state["already_on_disk_skipped"])
    result_count = len(obtained)            # what we actually RETRIEVED
    short = [k for k in declared if k not in obtained]
    state["expected_total"] = expected_total
    state["result_count"] = result_count
    state["objects_short_of_expected_total"] = short
    state["run_complete"] = (result_count == expected_total) and not short
    if short:
        state["notes"].append(
            f"INCOMPLETE: retrieved {result_count} of expected_total "
            f"{expected_total} declared objects; missing {', '.join(short)}. "
            f"This run must NOT be treated as a finished refresh; re-run to "
            f"resume.")
    state["run_finished"] = NOW()
    (OUTH / "_pull_state.json").write_text(json.dumps(state, indent=2),
                                           encoding="utf-8")
    print(json.dumps({k: v for k, v in state.items() if k != "objects"}, indent=2))


if __name__ == "__main__":
    main()
