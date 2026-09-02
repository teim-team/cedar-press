#!/usr/bin/env python3
"""
Cedar Press - SHARD F, step 6: map the PUBLICATION CHANNELS, do not harvest them.

The owner's scope, taken literally: map the channel now, leave the archive for
its own dataset later. So this records, per organisation:

    channel_type    news / newsletter archive / press releases / policy blog /
                    annual report / email signup
    format          html | pdf | email
    archive_depth   earliest and latest dated item actually SEEN on the page
    cadence         observed median gap between dated items, in days.
                    Labelled `observed_*`, never asserted as an editorial
                    schedule, unless the page states one in words - in which
                    case the words go in `stated_cadence` with a quote.
    3 most recent items, with dates and links
    deal_content    whether those items carry deal / economic-development
                    language, with the matched terms and a quote

`observed_median_gap_days` from three items is a weak estimate and is reported
with `n_dates_observed` so nobody mistakes it for a schedule.

Output: data/staging/tribe_harvest/shard_f/newsletters.jsonl
"""
import html, json, os, re, statistics, sys, time
import urllib.parse
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shard_f_fetch as F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f")
OUT = os.path.join(SH, "newsletters.jsonl")
TODAY = time.strftime("%Y-%m-%d")

CHANNEL_PAT = [
    (re.compile(r"newsletter\s+archive|past\s+(news)?letters?|bulletin\s+archive", re.I),
     "newsletter_archive", 10),
    (re.compile(r"\bnewsletters?\b", re.I), "newsletter", 9),
    (re.compile(r"press\s+releases?|newsroom|media\s+(centre|center|releases)", re.I),
     "press_releases", 8),
    (re.compile(r"annual\s+reports?", re.I), "annual_report", 8),
    (re.compile(r"policy\s+blog|policy\s+updates?|legislative\s+updates?", re.I),
     "policy_publication", 8),
    (re.compile(r"\bpublications?\b|\breports?\b", re.I), "publications", 6),
    (re.compile(r"^\s*news\s*$|latest\s+news|news\s+(and\s+)?(events|updates)", re.I),
     "news", 6),
    (re.compile(r"\bblog\b", re.I), "blog", 5),
    (re.compile(r"subscribe|sign\s*up\s+for\s+our", re.I), "email_signup", 4),
]

DEAL = re.compile(
    r"\b(acquisi?tion|acquired|acquires|merger|joint venture|"
    r"partnership agreement|memorandum of understanding|\bmou\b|groundbreaking|"
    r"broke ground|purchase(d)? (of|the)|investment|invests|contract award|"
    r"awarded a contract|8\(a\)|economic development|new casino|resort|"
    r"broadband|fiber|energy project|solar|land[- ]into[- ]trust|"
    r"lease agreement|opens? (a )?new|expansion|revenue sharing|compact)\b",
    re.I,
)

DATE_PATS = [
    (re.compile(r"\b(20[012]\d)-(\d{2})-(\d{2})\b"), lambda m: (int(m[1]), int(m[2]), int(m[3]))),
    (re.compile(r"\b(January|February|March|April|May|June|July|August|September|"
                r"October|November|December)\s+(\d{1,2}),?\s+(20[012]\d)\b", re.I),
     lambda m: (int(m[3]), _MON[m[1].lower()[:3]], int(m[2]))),
    (re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+"
                r"(\d{1,2}),?\s+(20[012]\d)\b", re.I),
     lambda m: (int(m[3]), _MON[m[1].lower()[:3]], int(m[2]))),
    (re.compile(r"\b(\d{1,2})/(\d{1,2})/(20[012]\d)\b"),
     lambda m: (int(m[3]), int(m[1]), int(m[2]))),
    (re.compile(r"\b(January|February|March|April|May|June|July|August|September|"
                r"October|November|December)\s+(20[012]\d)\b", re.I),
     lambda m: (int(m[2]), _MON[m[1].lower()[:3]], 1)),
]
_MON = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7,
        "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

STATED = re.compile(
    r"\b(daily|weekly|bi-?weekly|fortnightly|monthly|bi-?monthly|quarterly|"
    r"semi-?annual|annual)\b[^.]{0,60}(newsletter|bulletin|update|digest|report)"
    r"|(newsletter|bulletin|update|digest)[^.]{0,40}\b(daily|weekly|bi-?weekly|"
    r"monthly|bi-?monthly|quarterly|annual)\b", re.I)


def all_dates(text):
    out = []
    for pat, f in DATE_PATS:
        for m in pat.finditer(text):
            try:
                y, mo, d = f(m)
                dt = date(y, mo, min(d, 28))
                if date(2000, 1, 1) <= dt <= date(2027, 12, 31):
                    out.append(dt)
            except Exception:
                pass
    return out


def recent_items(h, base):
    """(date, title, url) for dated links on the page, newest first."""
    items = []
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', h, re.S | re.I):
        href = html.unescape(m.group(1))
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))).strip()
        if len(txt) < 8:
            continue
        ctx = h[max(0, m.start() - 400):m.end() + 400]
        ds = all_dates(re.sub(r"<[^>]+>", " ", ctx)) or all_dates(href)
        if not ds:
            continue
        items.append((max(ds), txt[:180], urllib.parse.urljoin(base, href)))
    seen, out = set(), []
    for d, t, u in sorted(items, key=lambda x: x[0], reverse=True):
        if u in seen:
            continue
        seen.add(u)
        out.append((d, t, u))
    return out


def main():
    resolved = F.load_resolved()
    only = set(sys.argv[1:]) or None
    fh = open(OUT, "a", encoding="utf-8")
    n_chan = n_deal = 0
    targets = [u for u in resolved if only is None or u in only]

    for i, uid in enumerate(targets, 1):
        r = resolved[uid]
        home = r["final_url"] or r["url"]
        hrec = F.fetch(home)
        hh = F.read_raw(hrec)
        if not hh:
            fh.write(json.dumps({
                "org_cedar_uid": uid, "org_name": r["canonical_name"],
                "org_website": home, "channel_type": "",
                "note": f"homepage not retrievable ({hrec['http_status']}); no channel mapped",
                "retrieved_date": TODAY}, ensure_ascii=False) + "\n")
            continue
        base = hrec.get("final_url") or home
        host = urllib.parse.urlsplit(base).netloc.lower().replace("www.", "")

        picked = {}
        for u, t in F.links_of(hh, base):
            hu = urllib.parse.urlsplit(u).netloc.lower().replace("www.", "")
            if hu != host:
                continue
            path = urllib.parse.urlsplit(u).path.replace("-", " ").replace("/", " ")
            for pat, kind, w in CHANNEL_PAT:
                if pat.search(t) or pat.search(path):
                    if kind not in picked or w > picked[kind][1]:
                        picked[kind] = (u, w, t.strip())
                    break

        wrote = 0
        for kind, (u, w, anchor) in sorted(picked.items(), key=lambda kv: -kv[1][1])[:4]:
            prec = F.fetch(u)
            ph = F.read_raw(prec)
            rec = {
                "org_cedar_uid": uid,
                "org_handle": r["handle"],
                "org_name": r["canonical_name"],
                "org_entity_class": r["entity_class"],
                "org_website": base,
                "channel_type": kind,
                "channel_url": prec.get("final_url") or u,
                "channel_anchor_text": anchor,
                "http_status": prec["http_status"],
                "format": "",
                "archive_earliest": "",
                "archive_latest": "",
                "n_dates_observed": 0,
                "observed_median_gap_days": "",
                "stated_cadence": "",
                "stated_cadence_quote": "",
                "recent_items": [],
                "deal_content": False,
                "deal_terms": [],
                "deal_quote": "",
                "retrieved_date": TODAY,
                "note": "",
            }
            if prec["http_status"] == 200 and ph:
                text = F.to_text(ph)
                ds = sorted(set(all_dates(text)))
                items = recent_items(ph, prec.get("final_url") or u)
                npdf = len(re.findall(r'href="[^"]+\.pdf', ph, re.I))
                rec["format"] = ("pdf" if npdf >= 3 else
                                 "email" if kind == "email_signup" else "html")
                if ds:
                    rec["archive_earliest"] = ds[0].isoformat()
                    rec["archive_latest"] = ds[-1].isoformat()
                    rec["n_dates_observed"] = len(ds)
                    if len(ds) >= 3:
                        gaps = [(b - a).days for a, b in zip(ds, ds[1:]) if (b - a).days > 0]
                        if gaps:
                            rec["observed_median_gap_days"] = int(statistics.median(gaps))
                sm = STATED.search(text)
                if sm:
                    rec["stated_cadence"] = sm.group(0)[:80]
                    q = text[max(0, sm.start() - 80):sm.end() + 80]
                    rec["stated_cadence_quote"] = re.sub(r"\s+", " ", q).strip()[:300]
                top = items[:3]
                rec["recent_items"] = [
                    {"date": d.isoformat(), "title": t, "url": uu} for d, t, uu in top
                ]
                blob = " ".join(t for _, t, _ in top) + " " + text[:6000]
                terms = sorted({m.group(0).lower() for m in DEAL.finditer(blob)})
                if terms:
                    rec["deal_content"] = True
                    rec["deal_terms"] = terms[:10]
                    m = DEAL.search(blob)
                    rec["deal_quote"] = re.sub(
                        r"\s+", " ", blob[max(0, m.start() - 120):m.end() + 160]).strip()[:400]
                    n_deal += 1
            else:
                rec["note"] = "channel page did not return 200"
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            wrote += 1
        if wrote == 0:
            fh.write(json.dumps({
                "org_cedar_uid": uid, "org_handle": r["handle"],
                "org_name": r["canonical_name"], "org_entity_class": r["entity_class"],
                "org_website": base, "channel_type": "none_found",
                "note": "homepage read; no newsletter/news/press/publication link found",
                "retrieved_date": TODAY}, ensure_ascii=False) + "\n")
        else:
            n_chan += 1
        fh.flush()
        print(f"[{i:3d}/{len(targets)}] {wrote} channels  {r['canonical_name'][:56]}")

    fh.close()
    print(f"\norganisations with >=1 channel: {n_chan}/{len(targets)}   "
          f"channel-pages with deal content: {n_deal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
