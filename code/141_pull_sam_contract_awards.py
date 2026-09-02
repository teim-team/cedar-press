#!/usr/bin/env python3
"""
Cedar Press - 141: pull FY2000-2007 prime contracts from SAM Contract Awards.

WHY THIS EXISTS
---------------
The USAspending static archive begins at FY2008. FY2000-2007 has no route
through it, and those years in `prime_contracts.csv` came from a BGOV export
that was FILTERED at download time - measured cost, missing ENTITIES rather
than wrong dollars.

SAM's Contract Awards API serves them. Confirmed 2026-08-12:
    fiscalYear=2000 -> totalRecords 591,754
    fiscalYear=2007 -> totalRecords 4,112,136

THE OPTIMISATION THAT MAKES THIS FIT IN THE QUOTA
--------------------------------------------------
We are on the 10 requests/day tier (confirmed by HTTP 429 at call ten). Pulling
year by year would cost 8 calls per business-type variant - 32 calls, four days.

But the limit counts REQUESTS, not records, and the async extract returns up to
**1,000,000 records per call**. `dateSigned` accepts a RANGE. The Native slice
is ~1.40% of a fiscal year (measured: awardeeBusinessTypeName=INDIAN returned
57,537 of 4,112,136 for FY2007).

So the whole FY2000-2007 span is roughly 140k records - comfortably under the
ceiling. **One extract covers all eight years.** Four business-type variants =
four calls for the entire backfill, not thirty-two.

WHY FOUR VARIANTS
-----------------
`awardeeBusinessTypeName` is a partial match. "INDIAN" catches "Indian Tribe"
but will MISS Alaska Native corporations and Native Hawaiian organisations whose
business-type strings contain no such word. Untested at the time of writing -
the variant probe is call 1-3 of the run and its result decides whether the
remaining variants are needed.

The socio-economic flags (indianTribeFederallyRecognized, triballyOwnedFirm,
alaskanNativeCorporationOwnedFirm...) do NOT filter - both returned HTTP 400,
"the search parameter does not exist". They are OUTPUT fields only.

WHAT IT REFUSES
---------------
- **Never hardcodes a stamp or assumes a path.** A 404 from api.sam.gov means an
  invalid key, NOT a wrong endpoint - measured: every path 404s without a valid
  key, including ones that exist.
- **Stops on the first 429** and reports remaining quota. Burning the day's
  budget on retries is the failure mode this file exists to avoid.
- **Writes raw, does not merge.** Reconciliation against the 42,322 verified
  FY2012 archive rows happens in a separate step, before any of this is trusted.
- A SAM socio-economic flag is a firm's SELF-CERTIFICATION. Measured on the
  first record returned: Goldbelt Raven LLC, an ANC subsidiary, certifies
  alaskanNativeCorporationOwnedFirm = NO. Evidence toward tier B, never
  automatic tier A. `awardeeUltimateParentUniqueEntityId` is far stronger.

D&B LICENSING - carried on every row
------------------------------------
D&B Open Data (legal business name, street, city, state, ZIP, country) may not
be disseminated IN BULK, and it attaches to all base award notices dated before
2022-04-04 - i.e. 100% of this pull. Contract facts publish; the entity name and
address fields do not, in bulk. Every row carries `source_system = SAM_CONTRACT_AWARDS`
so the question is answerable per field later.

THE `format` / `emailId` PAIR (measured 2026-08-13, cost 5 calls)
----------------------------------------------------------------
    format=csv with no emailId
    -> 400 "Parameters 'format' and 'emailId' must both be supplied for
       successful emailing of the download link."

The docs state only the converse, so `emailId` was read as optional. It is not.
The pair is now built in ONE place (`extract_params`) and enforced in ANOTHER
(`check_params`, pre-flight, costs zero quota). Neither can be edited away
without the other catching it.

    py -3 code/141_pull_sam_contract_awards.py probe     # 3 calls: variant test
    py -3 code/141_pull_sam_contract_awards.py canary    # ONE call, proves shape
    py -3 code/141_pull_sam_contract_awards.py extract   # the remaining variants
    py -3 code/141_pull_sam_contract_awards.py status    # spend so far, no calls

SAM_API_KEY must be set. There is no key on this machine as of 2026-08-26 -
see docs/API_KEYS.md.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
RAW = CEDAR / "data" / "raw" / "contracts" / "sam_contract_awards"
LOG = CEDAR / "logs" / "141_sam_calls.jsonl"
BASE = "https://api.sam.gov/contract-awards/v1/search"

# FY2000 begins 1999-10-01; FY2007 ends 2007-09-30.
SPAN = ("10/01/1999", "09/30/2007")

# Elijah, 2026-08-12: "add individual natives too so we can make more use of
# the download". Correct - `INDIAN` will not reliably catch a firm whose
# business-type string reads "American Indian Owned" without the word tribe.
#
# CRITICAL: these are kept in SEPARATE CLASSES and must never be summed into one
# "Native" total. Cedar Press holds tribally-owned and individually-Native-owned
# strictly apart - an individual Native business owner is not a tribal
# enterprise, and conflating them overstates tribal economic activity.
OWNERSHIP_VARIANTS = ["INDIAN", "ALASKAN NATIVE", "NATIVE HAWAIIAN", "TRIBAL"]
INDIVIDUAL_VARIANTS = ["AMERICAN INDIAN", "NATIVE AMERICAN"]
VARIANT_CLASS = {**{v: "ENTITY_OWNED" for v in OWNERSHIP_VARIANTS},
                 **{v: "INDIVIDUAL_NATIVE_OWNED" for v in INDIVIDUAL_VARIANTS}}
VARIANTS = OWNERSHIP_VARIANTS + INDIVIDUAL_VARIANTS

# `emailId` IS A YES/NO FLAG, NOT AN ADDRESS. Measured 2026-08-26, one call:
#
#   emailId=<an email address>  ->  400 "Parameter 'emailId' must be either
#                                        YES or NO."
#
# The name says "Id", and the 2026-08-13 error said the pair is needed "for
# successful emailing of the download link", so it read unmistakably as an
# address. It is not. The link goes to the address on the SAM account; this
# parameter only chooses WHETHER to send it.
#
# YES, deliberately: the response body carries the download URL, but an
# accepted job whose token is lost is a wasted call out of ten. The email is a
# second copy of that token at no extra quota cost.
EMAIL_LINK = (os.environ.get("SAM_EMAIL_LINK") or "YES").strip().upper()

DAILY_QUOTA = 10          # non-federal user with no SAM role
# 6 variants means probe(5) + extract(6) = 11 calls, one over. The probe is what
# gets trimmed: a variant returning 0 costs an extract we never needed, but a
# variant we never probed still gets extracted. Probes run in priority order and
# stop at the quota, leaving the extract stage to spend what remains.
RUN_DEADLINE_MIN = 45

# Written only after an extract submission is ACCEPTED. `extract` refuses to run
# until it exists, so the first call of any day is always a single canary.
CANARY_OK = RAW / "_canary_accepted.json"


def key():
    k = os.environ.get("SAM_API_KEY", "").strip()
    if not k:
        sys.exit("SAM_API_KEY not set. export SAM_API_KEY=... before running.")
    return k


def spent_today():
    """Requests actually PUT ON THE WIRE today.

    Rows carrying `request_sent: false` are pre-flight refusals - the guard
    caught a malformed request and nothing left this machine, so no quota was
    spent. Older rows have no such field and are counted, which is correct:
    every one of them was a real request.
    """
    if not LOG.exists():
        return 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    n = 0
    for line in LOG.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if not rec.get("utc", "").startswith(today):
            continue
        if rec.get("request_sent") is False:
            continue
        if rec.get("charged_quota") is False:
            continue
        # Read-side rule for rows written before `charged_quota` existed. The
        # log is not rewritten - an invalid key genuinely has no quota bucket,
        # so the row is a true record of a request that cost nothing.
        if rec.get("http_status") == 401 and "API_KEY_INVALID" in (rec.get("note") or ""):
            continue
        n += 1
    return n


def redact(url):
    """Strip the api_key VALUE, keep every other parameter intact.

    The old version spliced the string by hand and dropped the `&` after
    REDACTED, producing `api_key=REDACTEDdateSigned=...` - which is what the
    2026-08-13 log lines look like. A log you cannot read the parameters off is
    the reason a missing `emailId` took a day to see.
    """
    head, _, qs = url.partition("?")
    if not qs:
        return url
    pairs = urllib.parse.parse_qsl(qs, keep_blank_values=True)
    safe = [(k, "REDACTED" if k == "api_key" else v) for k, v in pairs]
    return head + "?" + urllib.parse.urlencode(safe)


def record(purpose, url, status, note="", request_sent=True):
    # An invalid key has no subscription, so the gateway rejects it before any
    # throttle counter exists to increment. Measured 2026-08-26: 401
    # API_KEY_INVALID. That request left this machine but charged nothing, so
    # it must not eat one of the ten a VALID key would still have.
    charged = not (status == 401 and "API_KEY_INVALID" in (note or ""))
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "utc": datetime.now(timezone.utc).isoformat(),
            "purpose": purpose,
            "url": redact(url),
            "http_status": status,
            "note": note,
            "request_sent": request_sent,
            "charged_quota": charged if request_sent else False,
        }) + "\n")


def check_params(params):
    """Refuse a request the API is certain to reject. Costs zero quota.

    MEASURED 2026-08-13, cost 5 calls - the whole remaining daily budget:

        format=csv with no emailId
        -> HTTP 400 "Parameters 'format' and 'emailId' must both be supplied
           for successful emailing of the download link. Please re-submit your
           request with both parameters or none."

    A 400 costs a call exactly like a 200 does, so the pair is enforced HERE,
    before the socket opens, rather than trusted at each call site. An empty
    string counts as absent - `emailId=` is not supplying it.

    AND `emailId` must be YES or NO, measured 2026-08-26 at the cost of one
    call: an email address there returns 400 "Parameter 'emailId' must be
    either YES or NO." Both rules are checked because satisfying one while
    breaking the other still burns a call.
    """
    fmt = (params.get("format") or "").strip()
    eml = (params.get("emailId") or "").strip()
    if bool(fmt) != bool(eml):
        missing = "emailId" if fmt else "format"
        return (f"PREFLIGHT: 'format' and 'emailId' must BOTH be supplied or "
                f"NEITHER; '{missing}' is missing or empty. Not sending - a "
                f"malformed request costs a call exactly like a good one.")
    if eml and eml.upper() not in ("YES", "NO"):
        return (f"PREFLIGHT: emailId must be YES or NO, got {eml!r}. It is a "
                f"FLAG, not an address, despite the name. Not sending.")
    return None


def call(purpose, params, k):
    """One request. Every call is logged BEFORE the result is known, because a
    call that times out still spent quota."""
    bad = check_params(params)
    if bad:
        # Logged so the refusal is auditable, flagged so it is NOT counted
        # against the daily quota - nothing was sent.
        record(purpose, BASE + "?" + urllib.parse.urlencode(
            {"api_key": k, **params}), None, bad, request_sent=False)
        return None, (-1, bad)
    url = BASE + "?" + urllib.parse.urlencode({"api_key": k, **params})
    req = urllib.request.Request(url, headers={
        "User-Agent": "CedarPress/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = json.loads(r.read())
            record(purpose, url, r.status)
            return body, None
    except urllib.error.HTTPError as e:
        detail = e.read(400).decode("utf-8", "replace")
        record(purpose, url, e.code, detail[:200])
        return None, (e.code, detail)
    except Exception as e:
        record(purpose, url, 0, f"{type(e).__name__}: {e}")
        return None, (0, str(e))


def probe(k):
    """Calls 1-3: does each business-type variant match anything?

    Decides whether the extract needs one call or four. Uses limit=1 so it costs
    a request and returns a count, nothing more.
    """
    print("=== probe: business-type variants, FY2007 ===")
    print("  baseline FY2007 unfiltered = 4,112,136")
    print("  INDIAN already measured    =    57,537 (1.40%)\n")
    out = {}
    for v in VARIANTS[1:]:                      # INDIAN already known (57,537)
        if spent_today() >= DAILY_QUOTA:
            print("  QUOTA EXHAUSTED - stopping")
            break
        body, err = call(f"probe:{v}", {
            "fiscalYear": "2007", "limit": "1",
            "awardeeBusinessTypeName": v}, k)
        if err:
            print(f"  {v:18s} HTTP {err[0]}  {err[1][:90]}")
            if err[0] == 429:
                break
            continue
        t = body.get("totalRecords")
        out[v] = t
        print(f"  {v:18s} [{VARIANT_CLASS[v]:24s}] totalRecords={t}")
        time.sleep(3)
    print(f"\n  calls spent today: {spent_today()}/{DAILY_QUOTA}")
    return out


def dest_for(v):
    cls = VARIANT_CLASS[v]
    return RAW / f"sam_fy2000_2007_{cls.lower()}_{v.replace(' ', '_').lower()}.json"


def extract_params(v):
    """THE ONLY place an extract request is built.

    `format` and `emailId` are written as one literal pair so no future edit can
    separate them, and `check_params` refuses the request if anything does.
    `dateSigned` takes a RANGE, so this one call covers all of FY2000-2007.
    """
    return {
        "dateSigned": f"[{SPAN[0]},{SPAN[1]}]",
        "awardeeBusinessTypeName": v,
        "format": "csv",
        "emailId": EMAIL_LINK,
    }


def submit(v, k):
    """Submit ONE extract. Returns (ok, body_or_err)."""
    body, err = call(f"extract:{v}", extract_params(v), k)
    if err:
        return False, err
    dest = dest_for(v)
    tmp = dest.with_suffix(dest.suffix + ".part")
    tmp.write_text(json.dumps(body, indent=1), encoding="utf-8")
    tmp.replace(dest)                       # .part then rename - never a half file
    return True, body


def canary(k):
    """Spend exactly ONE call, on the first variant not already on disk.

    Five calls died on 2026-08-13 because six identical requests went out
    together and every one of them carried the same defect. Acceptance of the
    first is the only evidence that the other five are worth sending, so the
    canary is a SEPARATE INVOCATION and `extract` refuses to run without it.
    """
    RAW.mkdir(parents=True, exist_ok=True)
    todo = [v for v in VARIANTS if not dest_for(v).exists()]
    if not todo:
        print("  nothing to do - every variant already has a response on disk")
        return True
    if spent_today() >= DAILY_QUOTA:
        print("  QUOTA EXHAUSTED - not sending")
        return False
    v = todo[0]
    print(f"=== CANARY: one extract, variant {v!r} ===")
    print(f"  dateSigned [{SPAN[0]},{SPAN[1]}]  format=csv  emailId={EMAIL_LINK}")
    ok, res = submit(v, k)
    if not ok:
        code, detail = res
        print(f"  CANARY FAILED  HTTP {code}  {str(detail)[:300]}")
        if code == 401:
            print("  401 API_KEY_INVALID = the key is dead. Collect a new one:")
            print("  sam.gov > Workspace > Profile > Account Details > Public")
            print("  API Key (eye icon, one-time password to email). Do NOT")
            print("  follow the link in the rotation email. No quota was spent.")
        elif code == 404:
            print("  404 from api.sam.gov = BAD OR MISSING KEY, not a wrong path.")
        elif code == 403:
            print("  403 = key rejected.")
        elif code == 429:
            print("  429 = quota gone for the UTC day. Do not retry today.")
        print("  STOPPING. The remaining variants are NOT sent.")
        return False
    CANARY_OK.write_text(json.dumps({
        "utc": datetime.now(timezone.utc).isoformat(),
        "variant": v, "response": res}, indent=1), encoding="utf-8")
    print(f"  ACCEPTED -> {dest_for(v).name}")
    print(f"     {json.dumps(res)[:400]}")
    print(f"\n  calls spent today: {spent_today()}/{DAILY_QUOTA}")
    print("  Canary passed. Now run:  py -3 code/141_pull_sam_contract_awards.py extract")
    return True


def extract(k):
    """The REMAINING variants, after the canary has been accepted."""
    RAW.mkdir(parents=True, exist_ok=True)
    if not CANARY_OK.exists():
        sys.exit(
            "REFUSING: no accepted canary on record.\n"
            "  Run `py -3 code/141_pull_sam_contract_awards.py canary` first.\n"
            "  It spends ONE call and proves the request shape is accepted.\n"
            "  Five calls died on 2026-08-13 from skipping exactly this step.")
    t0 = time.time()
    print(f"=== extract: dateSigned {SPAN[0]} .. {SPAN[1]} ===")
    for v in VARIANTS:
        if spent_today() >= DAILY_QUOTA:
            print("  QUOTA EXHAUSTED - stopping cleanly")
            break
        if (time.time() - t0) / 60 > RUN_DEADLINE_MIN:
            print("  RUN DEADLINE reached - stopping cleanly")
            break
        dest = dest_for(v)
        if dest.exists():
            print(f"  {v:18s} already have {dest.name} - skip")
            continue
        ok, res = submit(v, k)
        if not ok:
            code, detail = res
            print(f"  {v:18s} HTTP {code}  {str(detail)[:160]}")
            # Only 403/404 are facts about the object; 429 is the day's budget.
            # Everything else is a fact about the moment - but a repeated
            # parameter error is not, so stop on 400 too rather than repeat it.
            if code in (400, 403, 404, 429):
                print("  stopping on first refusal - not repeating it five times")
                break
            continue
        print(f"  {v:18s} [{VARIANT_CLASS[v]:24s}] accepted -> {dest.name}")
        print(f"     {json.dumps(res)[:200]}")
        time.sleep(5)
    print(f"\n  calls spent today: {spent_today()}/{DAILY_QUOTA}")
    print("  NOTE: the extract returns a download URL containing the literal")
    print("  string REPLACE_WITH_API_KEY. Substitute the key, then GET it.")
    print("  Poll with a deadline; do NOT resubmit a job that is still building.")
    print("  D&B: every row here is a pre-2022-04-04 base award. Contract facts")
    print("  publish; legal name/street/city/state/ZIP do NOT, in bulk.")


def tokens():
    """Every accepted export token on disk, newest response wins.

    An accepted job whose token is lost is a wasted call out of ten, so the
    token is read back from the response file rather than held in memory.
    """
    out = []
    for v in VARIANTS:
        p = dest_for(v)
        if not p.exists():
            continue
        try:
            body = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        tok = body.get("exportToken")
        url = body.get("presignedUrl")
        if tok and url:
            out.append((v, tok, url))
    return out


def download(k, only=None):
    """Fetch the generated CSVs. SEPARATE QUOTA SPEND from the submissions.

    A submission is irreplaceable - it starts server-side work. A download is
    retryable tomorrow against the same token. So when the budget is short,
    submit everything and download what fits.
    """
    RAW.mkdir(parents=True, exist_ok=True)
    got = []
    for v, tok, url in tokens():
        if only and v not in only:
            continue
        csv_dest = RAW / (dest_for(v).stem + ".csv")
        if csv_dest.exists():
            print(f"  {v:18s} already downloaded - skip")
            continue
        if spent_today() >= DAILY_QUOTA:
            print("  QUOTA EXHAUSTED - remaining tokens stay valid for tomorrow")
            break
        real = url.replace("REPLACE_WITH_API_KEY", urllib.parse.quote(k, safe=""))
        req = urllib.request.Request(real, headers={
            "User-Agent": "CedarPress/1.0", "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=(300)) as r:
                data = r.read()
                record(f"download:{v}", real, r.status,
                       f"token={tok} bytes={len(data)}")
        except urllib.error.HTTPError as e:
            detail = e.read(400).decode("utf-8", "replace")
            record(f"download:{v}", real, e.code, f"token={tok} {detail[:200]}")
            print(f"  {v:18s} HTTP {e.code}  {detail[:160]}")
            # MEASURED 2026-08-26, and it is a trap worth naming. A file still
            # generating answers:
            #   HTTP 303 "Cannot proceed with download: The specified key does
            #             not exist. (Service: S3, Status Code: 404 ...)"
            # That 404 is S3's, about an object not yet WRITTEN. It is NOT
            # api.sam.gov saying anything about our request, and the standing
            # rule "only 404 and 403 are facts about the object" does not reach
            # it. Read literally it says "the export does not exist" and would
            # get a live token thrown away. The job is fine; it is not finished.
            if "specified key does not exist" in detail or e.code == 303:
                print("  NOT READY - still generating. Token kept, retry later.")
                print("  Do NOT resubmit: that discards accepted server work.")
                break
            if e.code in (403, 404, 429):
                print("  stopping - token kept, retry tomorrow")
                break
            continue
        except Exception as e:
            record(f"download:{v}", real, 0, f"token={tok} {type(e).__name__}: {e}")
            print(f"  {v:18s} transport failure: {type(e).__name__}: {e}")
            break
        # .part then rename - an interruption must not look like a completion.
        tmp = csv_dest.with_suffix(".csv.part")
        tmp.write_bytes(data)
        tmp.replace(csv_dest)
        rows = max(data.count(b"\n") - 1, 0)
        print(f"  {v:18s} {len(data):,} bytes  ~{rows:,} rows -> {csv_dest.name}")
        got.append((v, rows, len(data)))
        time.sleep(5)
    print(f"\n  calls spent today: {spent_today()}/{DAILY_QUOTA}")
    return got


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "status"
    print(f"  spent today: {spent_today()}/{DAILY_QUOTA}")
    if mode == "status":
        for v in VARIANTS:
            csv_dest = RAW / (dest_for(v).stem + ".csv")
            state = ("CSV " + f"{csv_dest.stat().st_size:,}b" if csv_dest.exists()
                     else "submitted" if dest_for(v).exists() else "-")
            print(f"    {v:18s} {state}")
        print(f"    canary accepted: {CANARY_OK.exists()}")
        print(f"    tokens held: {len(tokens())}")
        return
    k = key()
    if mode == "probe":
        probe(k)
    elif mode == "canary":
        canary(k)
    elif mode == "extract":
        extract(k)
    elif mode == "download":
        download(k, only=sys.argv[2:] or None)
    else:
        sys.exit("usage: probe | canary | extract | download [VARIANT...] | status")


if __name__ == "__main__":
    main()
