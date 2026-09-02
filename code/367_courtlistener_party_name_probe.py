"""367 - aim the request at the PARTY ARRAY, not at the full text.

WHY THIS EXISTS
---------------
`code/366` spends one request per name on the plain full-text RECAP search
(`type=r&q="<name>"`).  Measured on the first 12 requests, that is wasteful in
a very specific way: of 57 evidence rows, **44 are `NAME_IN_DOCUMENT_TEXT_ONLY`**
- the name appears somewhere in a scanned filing and the docket has nothing to
do with our firm.  `Southwind Construction Company` returned nine dockets and
not one names it as a party; `Tc&S/F-W` returned a habeas petition.

At 5 requests/minute and 125/day, a query that returns mostly rejects is the
expensive kind of mistake.  CourtListener's RECAP search exposes a
**`party_name`** filter that matches against the docket's party array itself -
the exact predicate `366` applies AFTER the fact, applied BEFORE the request is
answered.

THE PROBE IS DESIGNED TO ELIMINATE EXPLANATIONS, PER PULL_DISCIPLINE
--------------------------------------------------------------------
The first request is `party_name=Manu Kai`, and it is chosen because
**`366` already proved the answer**: Manu Kai, LLC is a VERIFIED_PARTY on
D. Haw. 1:15-cv-00438 and 1:15-cv-00321.  Three outcomes, three different
conclusions, one request:

    >=2 dockets, both Michaud       the filter WORKS -> use it for everything
    the same 7 as the plain query   the filter is IGNORED -> a 200 that means
                                    nothing; fall back to `366`'s route
    HTTP 400                        the parameter does not exist here

A 200 is not proof a parameter was honoured.  `PULL_DISCIPLINE.md` records
`recipient_type_names` on USAspending returning HTTP 200 with an empty set for
a bogus value, and `docs/BLOCKED_SOURCE_BYPASS_2026-08-26.md` records a
RealFile widget answering 200 + `files: []` for a MISMATCHED PAIR of legal
parameters.  So the probe is a name whose answer we already hold.

A CONTROL RUNS ON THIS ROUTE TOO
--------------------------------
`366`'s control (`Kwithluk Sentinel Holdings Incorporated`) was run against
`q=`.  A filter is a different code path and inherits nothing from that result,
so `party_name=` gets its own control.

BUDGET
------
Shares `366`'s ledger file, its host lock and its caps.  The two scripts can
never be run concurrently because the second one to start queues on the lock
and exits.

py -3 code/367_courtlistener_party_name_probe.py probe          # 2 requests
py -3 code/367_courtlistener_party_name_probe.py ask --max 20
py -3 code/367_courtlistener_party_name_probe.py questions      # 0 requests
"""
import argparse
import csv
import datetime
import importlib.util
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVIEW = ROOT / "review"
TODAY = "2026-08-26"

_ARGV = list(sys.argv)                      # 366 is imported for its metering,
spec = importlib.util.spec_from_file_location(   # its host lock and its redactor.
    "cl366", ROOT / "code" / "366_courtlistener_ownership_adjudication.py")
cl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cl)                 # its argparse runs only under __main__
sys.argv = _ARGV

OUT = REVIEW / f"courtlistener_party_evidence_{TODAY}.csv"
QUESTIONS = REVIEW / f"courtlistener_questions_{TODAY}.csv"
log = cl.log


def cl_party_get(party_name, extra=None):
    params = {"type": "r", "party_name": party_name}
    if extra:
        params.update(extra)
    return cl.SEARCH + "?" + urllib.parse.urlencode(params)


def spend_one(url, label, led):
    """Send exactly one metered request.  Returns (ok, json_or_error)."""
    while cl.spent_counts(led)[2] >= cl.PER_MIN:
        time.sleep(2)
    led["requests"].append({
        "t": time.time(),
        "iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "target": label, "url": cl.redact(url), "status": "SENT"})
    cl.save_spend(led)
    try:
        status, hdrs, js = cl.cl_get(url)
        led["requests"][-1]["status"] = status
        led["requests"][-1]["reported_count"] = js.get("count")
        led["requests"][-1]["retrieved"] = len(js.get("results") or [])
        cl.save_spend(led)
        return True, js
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = cl.redact(e.read().decode("utf-8", "replace"))[:400]
        except Exception:
            pass
        led["requests"][-1]["status"] = f"HTTP {e.code}"
        led["requests"][-1]["body"] = body
        cl.save_spend(led)
        return False, f"HTTP {e.code} {body}"
    except Exception as e:
        led["requests"][-1]["status"] = f"ERR {cl.redact(str(e))[:120]}"
        cl.save_spend(led)
        return False, cl.redact(str(e))


def step_probe():
    led = cl.load_spend()
    d, h, _ = cl.spent_counts(led)
    if min(cl.PER_DAY - d, cl.PER_HOUR - h) < 2:
        log("not enough budget for the 2-request probe")
        return 0
    if not cl.claim_host("party_name filter probe - 2 requests"):
        return 3
    try:
        # 1. the known-answer probe
        ok, js = spend_one(cl_party_get("Manu Kai"), "PROBE party_name=Manu Kai", led)
        if not ok:
            log(f"  party_name probe: {js}")
            log("  VERDICT: PARAMETER_REJECTED - stay on 366's q= route")
            return 0
        names = [r.get("caseName", "") for r in (js.get("results") or [])]
        cnt = js.get("count")
        log(f"  party_name=Manu Kai -> count={cnt}; page names: {names[:8]}")
        michaud = sum(1 for n in names if "michaud" in n.lower())
        if cnt is not None and cnt <= 4 and michaud >= 2:
            verdict = "FILTER_HONOURED"
        elif cnt == 7:
            verdict = "LOOKS_LIKE_THE_PLAIN_QUERY - filter probably IGNORED"
        else:
            verdict = f"AMBIGUOUS count={cnt} michaud_on_page={michaud}"
        log(f"  VERDICT: {verdict}")

        # 2. the control on THIS code path.  A filter is not the query it
        #    replaces and inherits none of its evidence.
        time.sleep(cl.GAP_S)
        ok2, js2 = spend_one(cl_party_get("Kwithluk Sentinel Holdings"),
                             "CONTROL_ABSENT party_name", led)
        if ok2:
            log(f"  CONTROL party_name=Kwithluk Sentinel Holdings -> "
                f"count={js2.get('count')}  (must be 0)")
        else:
            log(f"  CONTROL: {js2}")
        (cl.RAW / "_party_name_probe.json").write_text(
            cl.redact(json.dumps({"verdict": verdict, "probe": js,
                                  "control": js2 if ok2 else str(js2)}, indent=1)),
            encoding="utf-8")
    finally:
        d, h, _ = cl.spent_counts(led)
        cl.release_host(f"party_name probe; {d}/{cl.PER_DAY} today",
                        {"requests_today": d, "requests_this_hour": h})
    return 0


def load_questions():
    if not QUESTIONS.exists():
        log(f"{QUESTIONS.name} not present - write it first (see `questions`)")
        return []
    return [r for r in csv.DictReader(QUESTIONS.open(encoding="utf-8-sig"))
            if (r.get("party_name") or "").strip()]


def step_questions():
    qs = load_questions()
    log(f"{len(qs)} question(s) queued in {QUESTIONS.name}   (0 requests spent)")
    for q in qs:
        log(f"  [{q.get('priority','')}] {q['party_name'][:44]:44s} {q.get('question','')[:70]}")
    return 0


COLS = ["party_query", "priority", "cedar_key", "usd_at_stake", "question",
        "docket_id", "match_class", "case_name", "court", "docket_number",
        "date_filed", "cause", "suit_nature", "party_verbatim", "n_parties",
        "docket_url", "source_reported_count", "retrieved_this_page",
        "retrieved_vs_reported", "relationship_type", "relationship_basis",
        "retrieved_date"]


def step_ask(max_requests):
    qs = load_questions()
    if not qs:
        return 1
    rows = []
    done = set()
    if OUT.exists():
        for r in csv.DictReader(OUT.open(encoding="utf-8-sig")):
            rows.append(r)
            done.add(r["party_query"])
    led = cl.load_spend()
    d, h, _ = cl.spent_counts(led)
    room = min(cl.PER_DAY - d, cl.PER_HOUR - h, max_requests)
    log(f"budget: {d}/{cl.PER_DAY} today, {h}/{cl.PER_HOUR} this hour -> room {room}")
    if room <= 0:
        log("no budget in this window; nothing sent")
        return 0
    todo = [q for q in qs if q["party_name"] not in done][:room]
    if not todo:
        log("every queued question already has a recorded answer")
        return 0
    if not cl.claim_host("party_name aimed questions"):
        return 3
    sent = 0
    stopped = None
    try:
        for q in todo:
            if time.time() - cl.START > cl.RUN_DEADLINE_S:
                stopped = "RUN_DEADLINE"
                break
            dd, hh, _ = cl.spent_counts(led)
            if dd >= cl.PER_DAY:
                stopped = "PER_DAY"
                break
            if hh >= cl.PER_HOUR:
                stopped = "PER_HOUR"
                break
            if sent:
                time.sleep(cl.GAP_S)
            ok, js = spend_one(cl_party_get(q["party_name"]),
                               f"party_name={q['party_name']}", led)
            sent += 1
            if not ok:
                log(f"  {q['party_name'][:44]:44s} {js[:60]}")
                if "429" in str(js):
                    stopped = "HTTP_429"
                    break
                continue
            reported = js.get("count")
            results = js.get("results") or []
            want = cl.norm(q["party_name"])
            (cl.RAW / f"party_{re.sub(r'[^A-Za-z0-9]+','_',q['party_name'])[:60]}.json"
             ).write_text(cl.redact(json.dumps(js, indent=1)), encoding="utf-8")
            if not results:
                rows.append(mk(q, None, "NO_DOCKET_RETURNED", reported, 0))
            n_ver = 0
            for d0 in results:
                parties = [p for p in (d0.get("party") or []) if p]
                pn = [cl.norm(p) for p in parties]
                if any(want in p for p in pn):
                    mc = "VERIFIED_PARTY"
                    n_ver += 1
                elif any(w in p for p in pn for w in [want]) or want in cl.norm(d0.get("caseName")):
                    mc = "NAME_IN_CAPTION_ONLY"
                else:
                    mc = "FILTER_MATCHED_BUT_NAME_NOT_IN_PAGE_PARTY_ARRAY"
                rows.append(mk(q, d0, mc, reported, len(results)))
            log(f"  {q['party_name'][:44]:44s} count={reported:<5} "
                f"page={len(results):<3} verified={n_ver}")
    finally:
        write(rows)
        d, h, _ = cl.spent_counts(led)
        cl.release_host(f"{sent} aimed request(s); {d}/{cl.PER_DAY} today",
                        {"downloaded_this_run": sent, "stopped_early": stopped,
                         "requests_today": d, "requests_this_hour": h})
    log(f"\n{sent} request(s). stopped_early={stopped}. "
        f"ledger {d}/{cl.PER_DAY} today, {h}/{cl.PER_HOUR} this hour.")
    return 0


def mk(q, d0, match_class, reported, retrieved):
    d0 = d0 or {}
    parties = [p for p in (d0.get("party") or []) if p]
    return {
        "party_query": q["party_name"],
        "priority": q.get("priority", ""),
        "cedar_key": q.get("cedar_key", ""),
        "usd_at_stake": q.get("usd_at_stake", ""),
        "question": q.get("question", ""),
        "docket_id": str(d0.get("docket_id") or d0.get("id") or ""),
        "match_class": match_class,
        "case_name": d0.get("caseName", ""),
        "court": d0.get("court", "") or d0.get("court_id", ""),
        "docket_number": d0.get("docketNumber", ""),
        "date_filed": d0.get("dateFiled", "") or "",
        "cause": d0.get("cause", "") or "",
        "suit_nature": d0.get("suitNature", "") or "",
        "party_verbatim": " | ".join(parties),
        "n_parties": len(parties),
        "docket_url": ("https://www.courtlistener.com" + d0.get("docket_absolute_url", ""))
                      if d0.get("docket_absolute_url") else "",
        "source_reported_count": "" if reported is None else str(reported),
        "retrieved_this_page": str(retrieved),
        "retrieved_vs_reported": ("COMPLETE" if reported is not None and retrieved >= reported
                                  else "PARTIAL_PAGE_1_ONLY"),
        "relationship_type": "",
        "relationship_basis": "",
        "retrieved_date": TODAY,
    }


def write(rows):
    seen, out = set(), []
    for r in rows:
        k = (r["party_query"], r["docket_id"], r["match_class"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    out.sort(key=lambda r: (r["priority"], r["party_query"], r["docket_id"]))
    tmp = OUT.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in out:
            w.writerow({c: r.get(c, "") for c in COLS})
    tmp.replace(OUT)
    log(f"  wrote {len(out)} row(s) -> {OUT.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["probe", "ask", "questions"])
    ap.add_argument("--max", type=int, default=10)
    a = ap.parse_args(_ARGV[1:])
    if a.stage == "probe":
        return step_probe()
    if a.stage == "questions":
        return step_questions()
    return step_ask(a.max)


if __name__ == "__main__":
    sys.exit(main())
