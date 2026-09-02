"""SHARD-G: emit data/staging/tribe_web_map/shard_g.csv.

Runs in two modes and is SAFE TO RE-RUN:
  build  (default)  assemble candidate URLs from the registry crosswalk +
                    institution_facts + the spine, write the map with
                    http_status blank / pending. Zero network.
  probe             verify each distinct URL once (robots-honoured, rate limited)
                    and rewrite the map with the observed http_status.

Columns match the sibling shards exactly:
  tribe_id, cedar_uid, canonical_name, url_type, url, http_status, checked_date,
  evidence

url_type values used: institution | regulator_record | annual_report |
newsletter | leadership | procurement

Every entity in the 315-slice appears at least once. An entity with no URL gets a
row with url blank and evidence saying where we looked - absence is recorded, not
omitted.
"""
from __future__ import annotations

import csv, json, os, re, subprocess, sys, time
import urllib.robotparser as urp
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
OUTREG = ROOT / "data" / "staging" / "institution_registry"
OUTH = ROOT / "data" / "staging" / "tribe_harvest" / "shard_g"
MAPD = ROOT / "data" / "staging" / "tribe_web_map"
MAPD.mkdir(parents=True, exist_ok=True)
MAP = MAPD / "shard_g.csv"
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

FIELDS = ["tribe_id", "cedar_uid", "canonical_name", "url_type", "url",
          "http_status", "checked_date", "evidence"]

UA = ("CedarPress-research/1.0 (institutional web map; "
      "contact elijahsamsonmoreno@gmail.com)")
HOST_DELAY = 2.5
RUN_DEADLINE = time.time() + 2 * 3600
_last, _robots, _fails = {}, {}, {}


def rows(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def clean_url(u):
    u = (u or "").strip().strip('"').rstrip(";,")
    if not u:
        return ""
    if u.lower() in ("n/a", "na", "none", "unavailable", "not applicable"):
        return ""
    if not u.startswith(("http://", "https://")):
        if re.match(r"^[a-z0-9.-]+\.[a-z]{2,}(/|$)", u, re.I):
            u = "https://" + u
        else:
            return ""
    p = urlparse(u)
    if not p.netloc or "." not in p.netloc:
        return ""
    return u


# --------------------------------------------------------------- build
def build():
    slice_rows = rows(OUTREG / "_slice.csv")
    facts = rows(OUTREG / "institution_facts.csv") if (
        OUTREG / "institution_facts.csv").exists() else []
    xw = rows(OUTREG / "registry_crosswalk.csv") if (
        OUTREG / "registry_crosswalk.csv").exists() else []

    # website candidates per entity, in source-priority order
    PRI = ["website_registry_nces", "website_registry_ipeds", "website_registry_cdfi",
           "website_registry_fdic", "website_registry_bie", "website_registry_cicd",
           "website_registry", "website_spine", "website_spine_note"]
    LABEL = {
        "website_registry_nces": "NCES CCD SY2024-25 school directory WEBSITE field",
        "website_registry_ipeds": "IPEDS HD2023 WEBADDR field",
        "website_registry_cdfi": "CDFI Fund certified-CDFI list Organization Website",
        "website_registry_fdic": "FDIC BankFind institutions API WEBADDR field",
        "website_registry_bie": "BIE school directory website field",
        "website_registry_cicd": ("Federal Reserve Bank of Minneapolis CICD "
                                 "Native American Financial Institutions map, "
                                 "website field"),
        "website_registry": "registry directory website field (2026-08-06 cache)",
        "website_spine": "cedar_entity_spine.csv entity_website",
        "website_spine_note": "cedar_entity_spine.csv reconciliation_note website=",
    }
    cand = {}
    for f in facts:
        if f["attribute"] not in PRI:
            continue
        u = clean_url(f["value"])
        if not u:
            continue
        cand.setdefault(f["cedar_uid"], {}).setdefault(u, []).append(f)

    out = []
    for r in slice_rows:
        uid = r["cedar_uid"]
        c = cand.get(uid, {})
        if c:
            # order candidates by attribute priority, dedupe on normalised url
            def key(u):
                attrs = [x["attribute"] for x in c[u]]
                return min(PRI.index(a) for a in attrs if a in PRI)
            seen = set()
            for u in sorted(c, key=key):
                k = u.rstrip("/").lower().replace("https://", "").replace(
                    "http://", "").replace("www.", "")
                if k in seen:
                    continue
                seen.add(k)
                srcs = c[u]
                best = min(srcs, key=lambda x: PRI.index(x["attribute"]))
                ev = (f"{LABEL.get(best['attribute'], best['attribute'])}; "
                      f"match_method={best['match_method']}"
                      f"{'/' + best['match_score'] if best.get('match_score') else ''}"
                      f"; source: {best['source_url']}")
                out.append({"tribe_id": r["tribe_id"], "cedar_uid": uid,
                            "canonical_name": r["canonical_name"],
                            "url_type": "institution", "url": u,
                            "http_status": "", "checked_date": "",
                            "evidence": ev})
        else:
            out.append({"tribe_id": r["tribe_id"], "cedar_uid": uid,
                        "canonical_name": r["canonical_name"],
                        "url_type": "institution", "url": "", "http_status": "",
                        "checked_date": TODAY,
                        "evidence": ("NO URL FOUND. Looked in: NCES CCD SY2024-25 "
                                     "directory WEBSITE; BIE school directory "
                                     "website; IPEDS HD2023 WEBADDR; CDFI Fund "
                                     "certified list Organization Website; FDIC "
                                     "BankFind WEBADDR; cedar_entity_spine "
                                     "entity_website and reconciliation_note. "
                                     "Blank rather than guessed.")})

    # regulator_record rows - a permanent, citable public record of the entity
    REG_URL = {
        "NCES_SCHOOL_ID": ("https://nces.ed.gov/ccd/schoolsearch/school_detail.asp?ID={v}",
                           "NCES Common Core of Data school detail record"),
        "IPEDS_UNITID": ("https://nces.ed.gov/collegenavigator/?id={v}",
                         "NCES College Navigator / IPEDS institution record"),
        "FDIC_CERT": ("https://banks.data.fdic.gov/bankfind-suite/bankfind/details/{v}",
                      "FDIC BankFind institution record"),
        "NCUA_CHARTER": ("https://mapping.ncua.gov/ResearchCreditUnion?ID={v}",
                         "NCUA Research a Credit Union record"),
    }
    for x in xw:
        spec = REG_URL.get(x["id_system"])
        if not spec:
            continue
        tmpl, label = spec
        v = x["id_value"].strip()
        if x["id_system"] == "IPEDS_UNITID":
            v = v.lstrip("0") or v
        out.append({"tribe_id": x["tribe_id"], "cedar_uid": x["cedar_uid"],
                    "canonical_name": x["canonical_name"],
                    "url_type": "regulator_record", "url": tmpl.format(v=v),
                    "http_status": "", "checked_date": "",
                    "evidence": (f"{label}, keyed on {x['id_system']}={x['id_value']} "
                                 f"captured from {x['source_url'].split(' ->')[0]}; "
                                 f"match_method={x['match_method']}")})

    # newsletter / periodical channels found by code/shard_g_newsletters.py
    nl = OUTH / "newsletters.jsonl"
    if nl.exists():
        for line in nl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if not d.get("channel_url"):
                continue
            out.append({
                "tribe_id": d.get("tribe_id", ""), "cedar_uid": d["cedar_uid"],
                "canonical_name": d["canonical_name"], "url_type": "newsletter",
                "url": d["channel_url"], "http_status": str(d.get("http_status", "")),
                "checked_date": d.get("checked_date", TODAY),
                "evidence": (
                    f"{d.get('channel','')} | {d.get('format','')} | archive_depth="
                    f"{d.get('archive_depth')} ({d.get('archive_depth_basis','')}) | "
                    f"cadence={d.get('cadence','')} | economic_content="
                    f"{d.get('economic_content','')}"
                    f"{' terms: ' + ', '.join(d.get('economic_terms') or []) if d.get('economic_terms') else ''}"
                    f" | technique: {d.get('technique','')}").strip()[:1200],
            })

    # carry forward any http_status already observed by a previous probe so a
    # rebuild never discards verification work
    prior = {}
    if MAP.exists():
        for p in rows(MAP):
            if p["http_status"]:
                prior[(p["cedar_uid"], p["url_type"],
                       p["url"].rstrip("/").lower())] = (p["http_status"],
                                                         p["checked_date"], p)
    for r in out:
        k = (r["cedar_uid"], r["url_type"], r["url"].rstrip("/").lower())
        if k in prior:
            r["http_status"], r["checked_date"] = prior[k][:2]

    # PRESERVE WHAT THIS REBUILD DOES NOT REGENERATE. A rebuild writer on a table
    # another stage enriches silently drops every row it does not know about -
    # the class-6 shape named in AGENTS.md, and it bit this file once already:
    # the first rebuild after the repair ladder deleted all 25 Wayback- and
    # variant-recovered URLs, because build() derives rows from the registry
    # facts and the ladder's finds are not in them. Any prior row that carries an
    # http_status was established by work, so it is carried forward.
    made = {(r["cedar_uid"], r["url_type"], r["url"].rstrip("/").lower())
            for r in out}
    carried = 0
    for k, (st, cd, row) in prior.items():
        if k not in made:
            out.append(dict(row))
            carried += 1
    if carried:
        print(f"carried forward {carried} prior verified row(s) this rebuild "
              f"does not regenerate", file=sys.stderr)

    # dedupe (cedar_uid, url_type, url)
    seen, ded = set(), []
    for r in out:
        k = (r["cedar_uid"], r["url_type"], r["url"].rstrip("/").lower())
        if k in seen:
            continue
        seen.add(k)
        ded.append(r)
    ded.sort(key=lambda r: (r["canonical_name"], r["url_type"], r["url"]))
    with open(MAP, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(ded)
    print(f"wrote {MAP.relative_to(ROOT)} rows={len(ded)} "
          f"entities={len({r['cedar_uid'] for r in ded})} "
          f"with_url={sum(1 for r in ded if r['url'])}", file=sys.stderr)


# --------------------------------------------------------------- probe
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
        r = subprocess.run(["curl", "-s", "-m", "15", "-A", UA,
                            f"{p.scheme}://{host}/robots.txt"], capture_output=True)
        rp = urp.RobotFileParser()
        try:
            body = r.stdout.decode("utf-8", "replace")
            if body.lstrip().startswith("<"):
                rp = None
            else:
                rp.parse(body.splitlines())
        except Exception:
            rp = None
        _robots[host] = rp
    rp = _robots[host]
    if rp is None:
        return True
    return rp.can_fetch("*", url)


def probe_one(url):
    host = urlparse(url).netloc
    if _fails.get(host, 0) >= 3:
        return "SKIP_HOST_BREAKER", ""
    if not robots_ok(url):
        return "ROBOTS_DISALLOWED", ""
    sleep_host(host)
    p = subprocess.run(["curl", "-s", "-L", "--max-redirs", "5", "-A", UA,
                        "-o", os.devnull, "--max-time", "35",
                        "-w", "%{http_code}|%{url_effective}", url],
                       capture_output=True, text=True)
    parts = (p.stdout or "").strip().split("|")
    code = parts[0] if parts else "0"
    eff = parts[1] if len(parts) > 1 else ""
    if code in ("0", "000"):
        _fails[host] = _fails.get(host, 0) + 1
        return "CONN_REFUSED", eff
    if code.startswith(("2", "3")):
        _fails[host] = 0
    else:
        _fails[host] = _fails.get(host, 0) + 1
    return code, eff


def probe():
    recs = rows(MAP)
    todo = [r for r in recs if r["url"] and not r["http_status"]]
    # one probe per distinct URL
    urls = []
    for r in todo:
        if r["url"] not in urls:
            urls.append(r["url"])
    print(f"probing {len(urls)} distinct urls for {len(todo)} rows", file=sys.stderr)
    res = {}
    for i, u in enumerate(urls):
        if time.time() > RUN_DEADLINE:
            print("RUN_DEADLINE reached; remaining rows left unprobed",
                  file=sys.stderr)
            break
        code, eff = probe_one(u)
        res[u] = (code, eff)
        if i % 25 == 0:
            print(f"  {i}/{len(urls)} {code} {u}", file=sys.stderr)
            _flush(recs, res)
    _flush(recs, res)
    ok = sum(1 for v in res.values() if str(v[0]).startswith("2"))
    print(json.dumps({"probed": len(res), "http_2xx": ok,
                      "non_2xx": len(res) - ok}, indent=2))


def _flush(recs, res):
    for r in recs:
        if r["url"] in res and not r["http_status"]:
            code, eff = res[r["url"]]
            r["http_status"] = str(code)
            r["checked_date"] = TODAY
            if eff and eff.rstrip("/") != r["url"].rstrip("/"):
                r["evidence"] = r["evidence"] + f" | resolved to {eff}"
    with open(MAP, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(recs)


# --------------------------------------------------------------- repair
def repair():
    """The alternative-route ladder, for URLs the probe could not reach.

    Rungs, in order, exactly as the shard brief specifies. The rung that worked
    is written into `evidence` so the next agent skips straight to it:
      1. scheme / www variants of the same host  (a dead http:// very often has a
         live https:// or www. twin - this is a typo, not a dead site)
      2. the Wayback Machine availability API, which is one JSON call per URL and
         is the documented, rate-tolerant way to ask "did this ever exist"
      3. nothing further is attempted here: the parent tribe's site, the PDF
         behind the page and Facebook are per-entity judgement calls and belong
         in a review queue, not an automated sweep.

    A URL that stays dead keeps its refusal code. A repaired URL is ADDED as a
    new row with url_type=institution and the original row is left in place with
    its refusal - the failure is evidence too.
    """
    recs = rows(MAP)
    BROKEN = {"CONN_REFUSED", "404", "400", "410", "500", "502", "503", "0"}
    todo = [r for r in recs
            if r["url"] and r["url_type"] == "institution"
            and r["http_status"] in BROKEN]
    print(f"repair ladder: {len(todo)} broken institution URLs", file=sys.stderr)
    existing = {(r["cedar_uid"], r["url"].rstrip("/").lower()) for r in recs}
    added, fixed_by = [], {}
    for i, r in enumerate(todo):
        if time.time() > RUN_DEADLINE:
            print("RUN_DEADLINE reached in repair", file=sys.stderr)
            break
        p = urlparse(r["url"])
        host = p.netloc
        variants = []
        alt_host = host[4:] if host.startswith("www.") else "www." + host
        for h in (host, alt_host):
            for sch in ("https", "http"):
                v = f"{sch}://{h}{p.path or '/'}"
                if v.rstrip("/").lower() != r["url"].rstrip("/").lower():
                    variants.append(v)
        got = None
        for v in dict.fromkeys(variants):
            code, eff = probe_one(v)
            if str(code).startswith("2"):
                got = (v, code, "rung 1: scheme/www variant of the same host")
                break
        if got is None:
            # rung 2: Wayback availability API
            sleep_host("archive.org")
            q = ("https://archive.org/wayback/available?url=" +
                 r["url"].replace("https://", "").replace("http://", ""))
            pr = subprocess.run(["curl", "-s", "-A", UA, "--max-time", "30", q],
                                capture_output=True, text=True)
            try:
                snap = (json.loads(pr.stdout or "{}")
                        .get("archived_snapshots", {}).get("closest", {}))
            except Exception:
                snap = {}
            if snap.get("available") and snap.get("url"):
                got = (snap["url"], "200_WAYBACK",
                       f"rung 2: Wayback Machine snapshot "
                       f"{snap.get('timestamp','')} - the origin is dead, the "
                       f"archived copy is not")
        if got:
            u, code, why = got
            k = (r["cedar_uid"], u.rstrip("/").lower())
            if k not in existing:
                existing.add(k)
                added.append({
                    "tribe_id": r["tribe_id"], "cedar_uid": r["cedar_uid"],
                    "canonical_name": r["canonical_name"],
                    "url_type": "institution", "url": u,
                    "http_status": str(code), "checked_date": TODAY,
                    "evidence": (f"RECOVERED by the alternative-route ladder, "
                                 f"{why}. The registry-named URL "
                                 f"{r['url']} returned {r['http_status']} on "
                                 f"{r['checked_date'] or TODAY}.")})
                fixed_by[why.split(":")[0]] = fixed_by.get(why.split(":")[0], 0) + 1
        if i % 10 == 0:
            print(f"  {i}/{len(todo)} {'FIXED' if got else 'still dead'} "
                  f"{r['canonical_name'][:40]}", file=sys.stderr)
            _write(recs + added)
    _write(recs + added)
    print(json.dumps({"broken_examined": len(todo), "recovered": len(added),
                      "by_rung": fixed_by}, indent=2))


def _write(recs):
    recs = sorted(recs, key=lambda r: (r["canonical_name"], r["url_type"],
                                       r["url"]))
    with open(MAP, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(recs)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "build"
    if mode == "build":
        build()
    elif mode == "probe":
        probe()
    elif mode == "repair":
        repair()
    else:
        sys.exit(f"unknown mode {mode}")
