"""368 - WHICH SIDE OF THE `v.` IS THE PARENT ON?

THE QUESTION THIS ANSWERS, AND WHY IT IS WORTH REQUESTS
--------------------------------------------------------
`code/367` established that a docket's `party` array puts a subsidiary and a
corporate parent in one caption.  It does NOT say what side each is on, and
that difference decides the answer:

    Novotny v. Delaware Nation Economic Development Authority LLC
    W.D. Okla. 5:18-cv-00200, docket 6501295
    party: Kenneth W Novotny | Indigenous Technologies LLC
           | Delaware Nation Economic Development Authority LLC | KNWEBS Inc

If KNWEBS Inc is a **defendant beside** the Delaware Nation entity, the two are
on one side and a corporate-family reading is live.  If KNWEBS is a
**plaintiff with Novotny**, the two are ADVERSE and the caption is evidence of
a commercial dispute, not of ownership.  Cedar already attributes
`INDIGENOUS TECHNOLOGIES, LLC` (Chickasha OK, $371.5M) to **Delaware Nation**,
so the side KNWEBS sits on is worth **$167,179,488** on its own.

The same question decides three more:
    16069152  US v. Hawaiian Native Corp.  (S.D. Cal. 3:18-cv-02849)
              the whole Dawson family as co-defendants, ~$1.06B unattributed
    71537478  Modoc Nation v. Shah         (10th Cir. 24-5135)
              RED CEDAR ENTERPRISES, INC. beside MODOC NATION, against a
              Cedar ledger row pointing at Paiute of Utah, $265.3M
    68142331  Ray v. Tanaq Government Services (N.D. Ga. 1:24-cv-00056)
              operating company + village corporation, ANCSA rule 1

WHAT A ROLE DOES AND DOES NOT PROVE
-----------------------------------
Alignment is not ownership either.  Co-defendants are joined as joint
employers, as alter egos, as sureties, as successors, and because a plaintiff
named everyone.  `Michaud v. Manu Kai, LLC` lists **31 parties including
"Doe Holding Companies 1020"** - that caption is a plaintiff fishing, and the
presence of ITT / Exelis / Vectrus / Harris on it shows the common thread is a
Navy CONTRACT, not a corporate parent.

So this script produces a ROLE, and the typing vocabulary stays honest:

    NAMED_AS_PARENT              the record names one as the other's parent
    CO_PARTY_ALIGNED             same side of the v.
    CO_DEFENDANT_ONLY            both defendants, relationship unstated
    CO_PARTY_ADVERSE             opposite sides - evidence AGAINST a simple
                                 parent/subsidiary reading at that date
    ALLEGED_IN_COMPLAINT         an allegation is not a finding
    STIPULATED / COURT_FOUND     the strong forms

Only STIPULATED, COURT_FOUND and a NAMED_AS_PARENT off a Rule 7.1 corporate
disclosure are ownership evidence.  Everything else is a RELATIONSHIP and is
staged as one.

BUDGET
------
Shares `366`'s ledger, host lock and caps (5/min, 50/hr, 125/day).  A docket's
party list is ONE request via `/api/rest/v4/parties/?docket=<id>`, and that is
the cheapest form of this answer available.

py -3 code/368_courtlistener_party_roles_and_docs.py roles --max 8
py -3 code/368_courtlistener_party_roles_and_docs.py show      # 0 requests
"""
import argparse
import csv
import datetime
import importlib.util
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVIEW = ROOT / "review"
TODAY = "2026-08-26"

_ARGV = list(sys.argv)
spec = importlib.util.spec_from_file_location(
    "cl366", ROOT / "code" / "366_courtlistener_ownership_adjudication.py")
cl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cl)
sys.argv = _ARGV
log = cl.log

PARTIES = "https://www.courtlistener.com/api/rest/v4/parties/"
OUT = REVIEW / f"courtlistener_party_roles_{TODAY}.csv"

# Every docket here is one Cedar question with a dollar figure behind it.
# Ordered by what the answer is worth.
DOCKETS = [
    ("16069152", "3:18-cv-02849", "S.D. Cal.",
     "United States of America v. Hawaiian Native Corp.",
     "which side is each Dawson entity on, and is Hawaiian Native Corp named as their parent?",
     "1060500000", "DAWSON_FAMILY"),
    ("71537478", "24-5135", "10th Cir.",
     "Modoc Nation v. Shah",
     "is RED CEDAR ENTERPRISES, INC. aligned with MODOC NATION? Cedar's ledger says Paiute of Utah via cluster_v3",
     "265300000", "RED_CEDAR_VS_PAIUTE_OF_UTAH"),
    ("6501295", "5:18-cv-00200", "W.D. Okla.",
     "Novotny v. Delaware Nation Economic Development Authority LLC",
     "is KNWEBS Inc a defendant BESIDE the Delaware Nation entity, or a plaintiff AGAINST it?",
     "167179488", "KNWEBS_ONE_OF_THE_SEVEN"),
    ("68142331", "1:24-cv-00056", "N.D. Ga.",
     "Ray v. Tanaq Government Services",
     "operating company + village corporation as co-defendants - ANCSA rule 1, second independent case",
     "91800000", "ANCSA_RULE_1_CORROBORATION"),
    ("61576080", "5:21-cv-01119", "W.D. Okla.",
     "Huliau v. KWN Assets LLC",
     "Hui Huliau (an NHO) against KNWEBS' principal - what are the roles and the dates?",
     "167179488", "KNWEBS_ONE_OF_THE_SEVEN"),
    ("13318768", "1:15-cv-00438", "D. Haw.",
     "Michaud v. Manu Kai, LLC",
     "are Manu Kai, Ke'aki Technologies and Akimeka co-DEFENDANTS, and is any parent named?",
     "760581490", "MANU_KAI_ONE_OF_THE_SEVEN"),
    ("13566135", "5:15-cv-00102", "W.D. Okla.",
     "Southwind Construction Services LLC v. Ross Group Construction Corporation",
     "FCA case - which side are Red Cedar Enterprises and Pentacon on?",
     "110923113", "SOUTHWIND_ONE_OF_THE_SEVEN"),
]

COLS = ["docket_id", "docket_number", "court_short", "case_name", "cedar_question",
        "usd_at_stake", "tag", "party_name", "party_types_verbatim",
        "role_raw", "date_terminated", "extra_info", "attorneys_verbatim",
        "n_parties_retrieved", "source_reported_count", "retrieved_vs_reported",
        "docket_url", "relationship_type", "relationship_basis", "retrieved_date"]


def fetch_parties(docket_id, led):
    """One request.  Returns (ok, list_of_party_dicts_or_error, reported_count)."""
    url = PARTIES + "?" + urllib.parse.urlencode({"docket": docket_id})
    while cl.spent_counts(led)[2] >= cl.PER_MIN:
        time.sleep(2)
    led["requests"].append({
        "t": time.time(),
        "iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "target": f"parties docket={docket_id}", "url": cl.redact(url),
        "status": "SENT"})
    cl.save_spend(led)
    try:
        status, hdrs, js = cl.cl_get(url)
        led["requests"][-1]["status"] = status
        led["requests"][-1]["reported_count"] = js.get("count")
        led["requests"][-1]["retrieved"] = len(js.get("results") or [])
        cl.save_spend(led)
        return True, js, js.get("count")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = cl.redact(e.read().decode("utf-8", "replace"))[:300]
        except Exception:
            pass
        led["requests"][-1]["status"] = f"HTTP {e.code}"
        led["requests"][-1]["body"] = body
        cl.save_spend(led)
        return False, f"HTTP {e.code} {body}", None
    except Exception as e:
        led["requests"][-1]["status"] = f"ERR {cl.redact(str(e))[:120]}"
        cl.save_spend(led)
        return False, cl.redact(str(e)), None


def step_roles(max_requests):
    rows = []
    done = set()
    if OUT.exists():
        for r in csv.DictReader(OUT.open(encoding="utf-8-sig")):
            rows.append(r)
            done.add(r["docket_id"])
    led = cl.load_spend()
    d, h, _ = cl.spent_counts(led)
    room = min(cl.PER_DAY - d, cl.PER_HOUR - h, max_requests)
    log(f"budget: {d}/{cl.PER_DAY} today, {h}/{cl.PER_HOUR} this hour -> room {room}")
    if room <= 0:
        log("no budget in this window; nothing sent")
        return 0
    todo = [t for t in DOCKETS if t[0] not in done][:room]
    if not todo:
        log("every docket already has recorded roles")
        return 0
    if not cl.claim_host("party roles on the dockets that decide a dollar figure"):
        return 3
    sent = 0
    stopped = None
    try:
        for (did, dnum, court, case, q, usd, tag) in todo:
            dd, hh, _ = cl.spent_counts(led)
            if dd >= cl.PER_DAY or hh >= cl.PER_HOUR:
                stopped = "CAP"
                break
            if sent:
                time.sleep(cl.GAP_S)
            ok, js, reported = fetch_parties(did, led)
            sent += 1
            if not ok:
                log(f"  docket {did} {case[:40]:40s} {str(js)[:60]}")
                if "429" in str(js):
                    stopped = "HTTP_429"
                    break
                continue
            (cl.RAW / f"parties_docket_{did}.json").write_text(
                cl.redact(json.dumps(js, indent=1)), encoding="utf-8")
            res = js.get("results") or []
            log(f"  docket {did} {case[:44]:44s} count={reported} page={len(res)}")
            for p in res:
                # party_types is a list of dicts carrying `name` (Defendant,
                # Plaintiff, ...), `date_terminated` and `extra_info`.
                pts = p.get("party_types") or []
                names = [str(t.get("name") or "") for t in pts]
                extra = " ; ".join(str(t.get("extra_info") or "") for t in pts
                                   if t.get("extra_info"))
                term = " ; ".join(str(t.get("date_terminated") or "") for t in pts
                                  if t.get("date_terminated"))
                attys = []
                for t in pts:
                    for a in (t.get("attorneys") or []):
                        nm = a.get("name") or ""
                        if nm:
                            attys.append(nm)
                rows.append({
                    "docket_id": did, "docket_number": dnum, "court_short": court,
                    "case_name": case, "cedar_question": q, "usd_at_stake": usd,
                    "tag": tag,
                    "party_name": p.get("name", ""),
                    "party_types_verbatim": " | ".join(names),
                    "role_raw": json.dumps(names),
                    "date_terminated": term,
                    "extra_info": extra,
                    "attorneys_verbatim": " | ".join(sorted(set(attys)))[:900],
                    "n_parties_retrieved": str(len(res)),
                    "source_reported_count": "" if reported is None else str(reported),
                    "retrieved_vs_reported": ("COMPLETE"
                                              if reported is not None and len(res) >= reported
                                              else "PARTIAL_PAGE_1_ONLY"),
                    "docket_url": f"https://www.courtlistener.com/docket/{did}/",
                    "relationship_type": "", "relationship_basis": "",
                    "retrieved_date": TODAY,
                })
                log(f"      {str(p.get('name'))[:52]:52s} :: {'/'.join(names)}"
                    f"{('  [' + extra[:60] + ']') if extra else ''}")
    finally:
        write(rows)
        d, h, _ = cl.spent_counts(led)
        cl.release_host(f"{sent} party-role request(s); {d}/{cl.PER_DAY} today",
                        {"downloaded_this_run": sent, "stopped_early": stopped,
                         "requests_today": d, "requests_this_hour": h})
    log(f"\n{sent} request(s). stopped_early={stopped}. "
        f"ledger {d}/{cl.PER_DAY} today, {h}/{cl.PER_HOUR} this hour.")
    return 0


def write(rows):
    seen, out = set(), []
    for r in rows:
        k = (r["docket_id"], r["party_name"], r["party_types_verbatim"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    out.sort(key=lambda r: (r["docket_id"], r["party_name"]))
    tmp = OUT.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in out:
            w.writerow({c: r.get(c, "") for c in COLS})
    tmp.replace(OUT)
    log(f"  wrote {len(out)} party-role row(s) -> {OUT.name}")


def step_show():
    if not OUT.exists():
        log("nothing recorded yet")
        return 0
    cur = None
    for r in csv.DictReader(OUT.open(encoding="utf-8-sig")):
        if r["docket_id"] != cur:
            cur = r["docket_id"]
            log(f"\n### {r['case_name']} | {r['court_short']} {r['docket_number']} "
                f"| docket {cur}")
            log(f"    Q: {r['cedar_question']}")
        log(f"    {r['party_name'][:56]:56s} :: {r['party_types_verbatim']}"
            f"{('  [' + r['extra_info'][:70] + ']') if r['extra_info'] else ''}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["roles", "show"])
    ap.add_argument("--max", type=int, default=8)
    a = ap.parse_args(_ARGV[1:])
    if a.stage == "roles":
        return step_roles(a.max)
    return step_show()


if __name__ == "__main__":
    sys.exit(main())
