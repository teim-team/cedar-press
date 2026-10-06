"""SHARD-E: the ANC shareholder-communication channels, and whether they carry
deal content.

Output: data/staging/tribe_harvest/shard_e/newsletters.jsonl

WHY THIS IS A DEALS SOURCE. An ANC shareholder newsletter and an ANC annual
report announce ACQUISITIONS, new subsidiaries and joint ventures in the
corporation's own words, months before any federal file shows the change. This
file records the CHANNEL - name, format, where it lives, how deep the archive
goes - and SAMPLES the three most recent issues for deal content. It deliberately
does NOT harvest every back issue.

Two channels, not one:

  * the corporation's own site (a newsletter, a newsroom, a report library);
  * the Alaska DBS STAR portal, which holds every filing an ANCSA corporation
    with 500+ shareholders must make under AS 45.55.139. That is a STATUTORY
    channel, it reaches corporations that have no website at all, and Cedar
    already holds its index (data/clean/ancsa_filings_index.csv, 19,269
    documents). For a village corporation with no site, the portal is often the
    ONLY shareholder-communication channel that exists.

ABSENCE IS RECORDED. A corporation with no findable newsletter gets a row saying
so, with what was probed.

NO NETWORK - reads this shard's own probe results and the portal index.
"""
from __future__ import annotations

import collections
import csv
import io
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
H = ROOT / "data" / "staging" / "tribe_harvest" / "shard_e"
OUT = H / "newsletters.jsonl"
RAW = H / "raw"
csv.field_size_limit(10_000_000)

DEAL_RE = re.compile(
    r"(?i)\b(acquir\w+|acquisition|merger|merged|joint venture|divest\w*|"
    r"purchase(?:d)? (?:the |all |100)|new subsidiary|has been formed|"
    r"wholly[- ]owned subsidiary|majority (?:interest|stake))\b")


def fold(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    s = re.sub(r"\b(inc|incorporated|corporation|corp|ltd|limited|llc|company|"
               r"the|native|association)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    slice_ = json.loads((H / "_slice.json").read_text(encoding="utf-8"))
    probes = [json.loads(l) for l in (H / "_probe_results.jsonl").open(encoding="utf-8")]

    # ---- statutory channel: the Alaska DBS STAR portal, per corporation
    portal = collections.defaultdict(list)
    for r in csv.DictReader((ROOT / "data/clean/ancsa_filings_index.csv")
                            .open(encoding="utf-8-sig")):
        portal[fold(r["corporation_name"])].append(r)

    recs = []
    by_uid = collections.defaultdict(list)
    for p in probes:
        if p.get("cedar_uid"):
            by_uid[p["cedar_uid"]].append(p)

    for e in slice_:
        key = fold(e["canonical_name"])
        mine = by_uid.get(e["cedar_uid"], [])

        # --- self-published channel
        chan = [p for p in mine
                if str(p.get("http_status")).isdigit() and 200 <= int(p["http_status"]) < 400
                and (p.get("url_type") in ("newsletter", "shareholder", "annual_report")
                     or (p.get("signals") or {}).get("newsletter"))]
        for p in chan:
            txt = ""
            rf = p.get("raw_file", "")
            if rf.endswith(".html") and (RAW / (rf[:-5] + ".txt")).exists():
                txt = (RAW / (rf[:-5] + ".txt")).read_text(encoding="utf-8")
            dates = re.findall(r"\b(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01])/(20\d\d)\b", txt)
            issues = re.findall(
                r"(?im)^([A-Z][A-Za-z’' .&-]{2,48}\s+[–-]\s+"
                r"(?:Winter|Spring|Summer|Fall|Autumn|Annual Meeting)\s*20\d\d)\s*$", txt)
            deal_hits = DEAL_RE.findall(txt)
            recs.append({
                "cedar_uid": e["cedar_uid"], "canonical_name": e["canonical_name"],
                "entity_class": e["entity_class"],
                "channel_type": p.get("url_type"),
                "channel_name": (issues[0].split("–")[0].strip() if issues
                                 else (p.get("title") or "")[:80]),
                "format": "html index" + (" listing PDF/article issues" if issues else ""),
                "url": p["url"], "http_status": p["http_status"],
                "issues_listed": len(issues),
                "issues_sample": issues[:6],
                "archive_years_observed": sorted(set(dates))[:12],
                "archive_depth": ("%s issues listed on one page" % len(issues)) if issues
                                 else "no discrete issue list parsed from the index page",
                "carries_deal_content": ("yes" if deal_hits else
                                         ("unknown" if not txt else "not on the index page")),
                "deal_terms_on_index": sorted(set(x.lower() for x in deal_hits))[:12],
                "retrieved_date": p.get("checked_date"),
                "note": "channel discovered by shard-E probe; index page only, "
                        "back issues deliberately not harvested",
            })

        # --- statutory channel
        docs = portal.get(key, [])
        if docs:
            years = sorted({d["period_covered"] for d in docs if d.get("period_covered")})
            kinds = collections.Counter(d["document_type"] for d in docs)
            recs.append({
                "cedar_uid": e["cedar_uid"], "canonical_name": e["canonical_name"],
                "entity_class": e["entity_class"],
                "channel_type": "statutory shareholder filings",
                "channel_name": "Alaska DBS STAR ANCSA portal (AS 45.55.139)",
                "format": "PDF, per-document, searchable by corporation and year",
                "url": "https://portal.akdbsstar.us/StarWebPortal/page/ANCSA/portal.aspx",
                "http_status": "on file (index harvested 2026-08-05)",
                "issues_listed": len(docs),
                "issues_sample": [d["document_description"][:90] for d in docs[:5]],
                "archive_years_observed": years[:1] + years[-1:] if years else [],
                "archive_depth": "%d documents, %s-%s" % (
                    len(docs), years[0] if years else "?", years[-1] if years else "?"),
                "carries_deal_content": "yes",
                "deal_terms_on_index": sorted(kinds)[:6],
                "retrieved_date": "2026-08-05",
                "note": "the only shareholder-communication channel that reaches an "
                        "ANC with no website; ANCSA annual reports carry the "
                        "acquisitions note (docs/DEALS_ANC_REPORTS_BUILD_LOG.md)",
            })

        # --- the WordPress media library: every uploaded PDF in one request.
        # docs/HIDDEN_DATA_TECHNIQUES.md technique 3. This is where the annual
        # reports and newsletter back issues actually live, and one call is
        # gentler on the server than crawling the archive.
        for p in mine:
            if "/wp-json/wp/v2/media" not in p.get("url", ""):
                continue
            rf = p.get("raw_file", "")
            body = ""
            cands = []
            if rf:
                cands.append(RAW / rf)
                if rf.endswith(".html"):
                    cands.append(RAW / (rf[:-5] + ".txt"))
            for cand in cands:
                if cand.is_file():
                    body = cand.read_text(encoding="utf-8", errors="replace")
                    break
            # WP REST escapes every slash: "https:\/\/host\/...pdf". Unescape
            # before matching or the whole media library reads as empty.
            body = body.replace("\\/", "/")
            pdfs = sorted(set(re.findall(r'(https?://[^"\s\\]+?\.pdf)', body)))
            named = [u for u in pdfs
                     if re.search(r"(?i)(annual[-_ ]?report|newsletter|shareholder|"
                                  r"proxy|report|news)", u)]
            recs.append({
                "cedar_uid": e["cedar_uid"], "canonical_name": e["canonical_name"],
                "entity_class": e["entity_class"],
                "channel_type": "wp-json media library",
                "channel_name": "WordPress REST media (application/*)",
                "format": "JSON index of uploaded files; PDFs retrievable directly",
                "url": p["url"], "http_status": p["http_status"],
                "issues_listed": len(pdfs),
                "issues_sample": named[:8] or pdfs[:8],
                "archive_years_observed": sorted(set(re.findall(r"/(20\d\d)/", " ".join(pdfs))))[:14],
                "archive_depth": "%d PDFs in one request (per_page=100 cap)" % len(pdfs),
                "carries_deal_content": "likely" if named else "unknown",
                "deal_terms_on_index": sorted(set(x.lower() for x in DEAL_RE.findall(body)))[:12],
                "retrieved_date": p.get("checked_date"),
                "note": "technique 3, docs/HIDDEN_DATA_TECHNIQUES.md; back issues "
                        "indexed, deliberately not downloaded",
            })

        # --- the three most recent issues actually sampled for deal content
        for p in mine:
            if p.get("url_type") != "newsletter":
                continue
            if "most recent issues sampled" not in (p.get("note") or ""):
                continue
            rf = p.get("raw_file", "")
            txt = ""
            if rf.endswith(".html") and (RAW / (rf[:-5] + ".txt")).exists():
                txt = (RAW / (rf[:-5] + ".txt")).read_text(encoding="utf-8")
            hits = DEAL_RE.findall(txt)
            ctx = []
            for m in DEAL_RE.finditer(txt):
                ctx.append(re.sub(r"\s+", " ", txt[max(0, m.start() - 110):m.end() + 150]))
            recs.append({
                "cedar_uid": e["cedar_uid"], "canonical_name": e["canonical_name"],
                "entity_class": e["entity_class"],
                "channel_type": "newsletter issue (sampled)",
                "channel_name": (p.get("title") or "")[:80],
                "format": "html article", "url": p["url"],
                "http_status": p["http_status"],
                "issues_listed": 1, "issues_sample": [],
                "archive_years_observed": [],
                "archive_depth": "one issue, sampled",
                "carries_deal_content": "yes" if hits else "no",
                "deal_terms_on_index": sorted(set(x.lower() for x in hits))[:12],
                "deal_context": ctx[:5],
                "retrieved_date": p.get("checked_date"),
                "note": "one of the three most recent issues, sampled for deal "
                        "content; the archive was NOT harvested",
            })

        if not chan and not docs:
            recs.append({
                "cedar_uid": e["cedar_uid"], "canonical_name": e["canonical_name"],
                "entity_class": e["entity_class"],
                "channel_type": "none found", "channel_name": "", "format": "",
                "url": "", "http_status": "NO_CHANNEL_FOUND",
                "issues_listed": 0, "issues_sample": [], "archive_years_observed": [],
                "archive_depth": "none",
                "carries_deal_content": "n/a",
                "deal_terms_on_index": [],
                "retrieved_date": "2026-09-01",
                "note": ("no self-published newsletter reachable and not among the 60 "
                         "corporations in the Alaska DBS STAR portal index. The portal "
                         "reaches ANCSA corporations with 500+ shareholders; absence "
                         "here is a fact about the DISCLOSURE THRESHOLD, not about the "
                         "corporation."),
            })

    with OUT.open("w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    c = collections.Counter(r["channel_type"] for r in recs)
    print("records", len(recs))
    for k, v in c.most_common():
        print("   %-32s %d" % (k, v))
    print("with deal content:", sum(1 for r in recs if r["carries_deal_content"] == "yes"))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
