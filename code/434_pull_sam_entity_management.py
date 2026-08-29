#!/usr/bin/env python3
"""
Cedar Press - 434: SAM.gov Entity Management pull, one measured call at a time.

WHY THIS EXISTS, AND WHY IT IS NOT AUTOMATED
--------------------------------------------
SAM entity management is the only exact CAGE/UEI route we have into the entity
universe, and (per the standing brief) the route several datasets need for
EIN <-> UEI. The quota is either 10/day or 1,000/day and WE DO NOT KNOW WHICH -
the org role request may or may not have landed. Until that is MEASURED, every
call is potentially 10% of the day's budget, so this tool issues exactly ONE
call per invocation, logs it, prints the answer, and stops.

    py -3 code/434_pull_sam_entity_management.py status
    py -3 code/434_pull_sam_entity_management.py get <PATH> k=v k=v ...
    py -3 code/434_pull_sam_entity_management.py download <URL_FROM_RESPONSE> <OUTNAME>

WHAT IT REFUSES / ENFORCES (all from docs/API_MANUALS_AND_QUIRKS.md sec.1)
--------------------------------------------------------------------------
- **Branches on the response body's `error.code`, not the HTTP status.** Auth
  status codes are inconsistent across the SAM family (403 documented, 401 and
  404 measured, 400 on the Extracts route). A 404 is probably a wrong route,
  not a bad key.
- **Stops dead on quota exhaustion** (HTTP 429 / OVER_RATE_LIMIT / WSO2
  "Message throttled out" code 900804). Retrying burns the whole day.
- **One poller per host.** Claims logs/_HOSTLOCK_api.sam.gov.json and refuses to
  run if another live process holds it.
- **Never writes a half file.** Downloads go to `.part` then rename.
- **Logs EVERY call** to logs/sam_entity_calls.jsonl with the key redacted, so
  the day's spend is auditable and the rate limit is measurable after the fact.
- `emailId` is a BOOLEAN (`YES`/`NO`), not an address, and is REDUNDANT - the
  download URL is already in the response body. Enforced here: an emailId value
  that is not YES/NO is refused pre-flight, at zero quota cost.
- Any returned download URL contains the literal `REPLACE_WITH_API_KEY`, which
  `download` substitutes.
- Reads the env file with `utf-8-sig`. A BOM defeated `startswith()` before.

WHAT IT DOES NOT DO
-------------------
It does not classify, attribute, or promote anything. A SAM business-type code
is a self-certification and is a RECALL NET to find candidates, never a
determination of Native ownership. Nothing here may set or upgrade an ownership
assertion.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
RAW = CEDAR / "data" / "raw" / "external" / "sam_entity_management"
LOG = CEDAR / "logs" / "sam_entity_calls.jsonl"
LOCK = CEDAR / "logs" / "_HOSTLOCK_api.sam.gov.json"
ENV_FILES = [
    CEDAR / ".env.local",
    Path(r"C:\Users\esm247\Desktop\dissertation\data\tribal_federal_spending\.env.local"),
]
UA = {"User-Agent": "Cedar Press research pull (elijahsamsonmoreno@gmail.com)"}

# Quota-exhaustion signatures. HTTP 429 is the api.data.gov gateway shape;
# 900804 / "Message throttled out" is the WSO2 shape api.sam.gov actually
# returned on 2026-08-12. Both are stop-work.
THROTTLE_MARKS = ("OVER_RATE_LIMIT", "900804", "Message throttled out",
                  "exceeded your quota")


def now():
    return datetime.now(timezone.utc).isoformat()


def key():
    v = None
    for f in ENV_FILES:
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = line.strip()
            for name in ("SAM_API_KEY=", "SAM_GOV_API_KEY="):
                if line.startswith(name):
                    cand = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if cand and (v is None):
                        v = cand
        if v:
            break
    if not v:
        v = os.environ.get("SAM_API_KEY") or os.environ.get("SAM_GOV_API_KEY")
    if not v:
        raise SystemExit("no SAM key found - see docs/API_KEYS.md")
    if len(v) != 40:
        raise SystemExit(
            f"REFUSED: key is {len(v)} chars, expected 40. This is the "
            "concatenated-env-file defect - one variable per line, no BOM.")
    return v


def redact(url, k):
    return url.replace(k, "REDACTED")


def logcall(rec):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


# ---------------------------------------------------------------- host lock

def lock_holder_alive(pid):
    try:
        import subprocess
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Get-Process -Id {pid} -ErrorAction SilentlyContinue | "
             "Select-Object -ExpandProperty Id"],
            capture_output=True, text=True, timeout=30).stdout.strip()
        return out.isdigit()
    except Exception:
        return False


def claim():
    if LOCK.exists():
        try:
            d = json.loads(LOCK.read_text(encoding="utf-8"))
        except Exception:
            d = {}
        if d.get("active") and lock_holder_alive(d.get("pid", -1)):
            raise SystemExit(
                f"REFUSED: api.sam.gov is held by pid {d.get('pid')} "
                f"({d.get('script')}) since {d.get('claimed_at')}. "
                "One poller per host. Append to its queue instead.")
    LOCK.write_text(json.dumps({
        "host": "api.sam.gov",
        "pid": os.getpid(),
        "script": "code/434_pull_sam_entity_management.py",
        "claimed_at": now(),
        "active": True,
        "queue": [],
        "policy": "ONE call per invocation, human-driven; stop dead on 429/900804",
        "note": "entity management pull + rate-limit measurement (role landed?)",
    }, indent=1), encoding="utf-8")


def release(result, issued):
    if not LOCK.exists():
        return
    try:
        d = json.loads(LOCK.read_text(encoding="utf-8"))
    except Exception:
        return
    if d.get("pid") != os.getpid():
        return
    d.update({"active": False, "released": now(),
              "requests_issued": issued, "result": result})
    LOCK.write_text(json.dumps(d, indent=1), encoding="utf-8")


# ---------------------------------------------------------------- the call

def error_code(body):
    """Branch on the BODY's error code, never on the HTTP status."""
    try:
        d = json.loads(body)
    except Exception:
        m = re.search(r"<h1>([A-Z_]+)</h1>", body or "")
        return m.group(1) if m else ""
    for path in (("error", "code"), ("code",), ("errorCode",)):
        cur = d
        for p in path:
            cur = cur.get(p) if isinstance(cur, dict) else None
        if isinstance(cur, str) and cur:
            return cur
    return ""


def get(path, params, purpose):
    k = key()
    if "emailId" in params and params["emailId"] not in ("YES", "NO"):
        raise SystemExit("REFUSED pre-flight (0 quota): emailId must be YES or NO. "
                         "It is a boolean, not an address.")
    q = dict(params)
    q["api_key"] = k
    url = f"https://api.sam.gov/{path.lstrip('/')}?" + urllib.parse.urlencode(q)
    status, body = 0, ""
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180)
        status = r.getcode()
        body = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
    except Exception as e:
        # A transport failure is NOT an HTTP fact. Recorded as 0, stop-work.
        status, body = 0, f"{type(e).__name__}: {e}"

    ec = error_code(body)
    throttled = (status == 429) or any(m in body for m in THROTTLE_MARKS)

    # A call costs an irreplaceable resource. Keep the WHOLE body, always,
    # .part then rename - a truncated console print has lost one already.
    RAW.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", purpose)[:80]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bp = RAW / f"response_{stamp}_{safe}.json"
    bp.with_suffix(".json.part").write_text(body, encoding="utf-8")
    bp.with_suffix(".json.part").rename(bp)

    rec = {"utc": now(), "purpose": purpose, "url": redact(url, k),
           "http_status": status, "error_code": ec,
           "body_head": body[:400], "request_sent": True,
           "charged_quota": status != 0, "throttled": throttled}
    logcall(rec)
    return status, ec, body, throttled


def today_spend():
    if not LOG.exists():
        return []
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("utc", "").startswith(day):
            out.append(d)
    return out


# ---------------------------------------------------------------- commands

def cmd_status():
    sp = today_spend()
    print(f"UTC day {datetime.now(timezone.utc):%Y-%m-%d}: "
          f"{sum(1 for r in sp if r.get('charged_quota'))} charged calls logged "
          f"by this script")
    for r in sp:
        print(f"  {r['utc'][11:19]}  {r['http_status']:>3} {r.get('error_code',''):<18} "
              f"{r['purpose']}")
    print(f"\nextracts on disk: {RAW}")
    if RAW.exists():
        for f in sorted(RAW.iterdir()):
            print(f"  {f.name:60s} {f.stat().st_size:>12,}")
    else:
        print("  (directory does not exist yet)")


def cmd_get(argv):
    path = argv[0]
    params = {}
    purpose = f"get:{path}"
    for a in argv[1:]:
        if a.startswith("purpose="):
            purpose = a.split("=", 1)[1]
            continue
        k, v = a.split("=", 1)
        params[k] = v
    claim()
    issued = 0
    try:
        status, ec, body, thr = get(path, params, purpose)
        issued = 1
        print(f"HTTP {status}   error.code={ec!r}   throttled={thr}")
        if thr:
            print("\nSTOP-WORK: quota exhausted. Do not retry today.")
            print(body[:600])
            release("throttled", issued)
            return
        print("\n--- body head ---")
        print(body[:3000])
    finally:
        if LOCK.exists():
            release("completed", issued)


def cmd_download(argv):
    url, outname = argv[0], argv[1]
    k = key()
    url = url.replace("REPLACE_WITH_API_KEY", k)
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / outname
    part = dest.with_suffix(dest.suffix + ".part")
    claim()
    issued = 0
    try:
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=900)
            issued = 1
            with open(part, "wb") as fh:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    fh.write(chunk)
            part.rename(dest)
            logcall({"utc": now(), "purpose": f"download:{outname}",
                     "url": redact(url, k), "http_status": r.getcode(),
                     "error_code": "", "body_head": "",
                     "request_sent": True, "charged_quota": True,
                     "bytes": dest.stat().st_size})
            print(f"OK  {dest}  {dest.stat().st_size:,} bytes")
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")
            except Exception:
                pass
            issued = 1
            logcall({"utc": now(), "purpose": f"download:{outname}",
                     "url": redact(url, k), "http_status": e.code,
                     "error_code": error_code(body), "body_head": body[:400],
                     "request_sent": True, "charged_quota": True})
            print(f"HTTP {e.code}  {body[:600]}")
            if "specified key does not exist" in body or "S3" in body:
                print("\nNOTE: that 404 is S3's, about an object not yet WRITTEN. "
                      "The token is still live - poll again later, do not resubmit.")
            if part.exists():
                part.unlink()
    finally:
        if LOCK.exists():
            release("completed", issued)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        cmd_status()
    elif cmd == "get":
        cmd_get(sys.argv[2:])
    elif cmd == "download":
        cmd_download(sys.argv[2:])
    else:
        raise SystemExit(__doc__)
