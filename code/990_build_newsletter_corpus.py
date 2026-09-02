"""Consolidate every scattered newsletter probe into ONE tribal-press corpus.

Owner, twice: *"Don't forget tribal newsletters, especially for deals"* and
*"even just keeping track of your newsletters could be a potential different
dataset down the road."*

WHAT THIS FIXES. Nine shards each invented their own newsletter schema and wrote
it to their own staging directory, so nobody could answer "which nations publish
a newspaper and how deep does the back run go?" without reading nine files with
nine sets of column names:

    data/staging/tribe_harvest/shard_{a,b,c,d,e,f,g,h}/newsletters*.jsonl
    data/staging/np_harvest/newsletters_shard_i.jsonl
    data/staging/tribe_harvest/newsletter_gap_sweep/gap_sweep.jsonl   (991)
    data/staging/cedar_web_map.csv          (url_type in newsletter/
                                             press_release/annual_report)

This script reads all eleven, normalizes them onto one schema, and writes two
tables. It does NOT fetch anything - no network - so it is safe to re-run.

    data/clean/tribal_newsletter_corpus.csv     one row per publication channel
    data/clean/tribal_newsletter_coverage.csv   one row per spine entity:
                                                found / attempted_none_found /
                                                not_probed

WHY TWO TABLES. `docs/PUBLICATION_POLICY.md` and the coverage ledger both insist
that "attempted, none found" and "untouched" are different claims. The corpus
carries only channels that exist; the coverage table carries the denominator, so
a false absence cannot hide in a row count.

GRAIN of the corpus is (cedar_uid, channel_url). A nation that publishes a
newspaper AND a shareholder newsletter AND posts PDFs to a WordPress media
library gets three rows, because those are three channels with three different
archive depths.

PRIVACY. A tribal newsletter carries obituaries, birthdays, health notices and
family announcements. This corpus records the PUBLICATION - its name, cadence,
archive depth and URL - and never a natural person's news. No row here contains
issue body text.

TERMS. Eight publishers are `TERMS_STATED_RESTRICTIVE` and are excluded by every
route (docs/PUBLICATION_POLICY.md). Any inherited row that names one of their
hosts is dropped here and counted in the verify report, so the exclusion is
enforced at the consolidation seam as well as at the fetch seam.

    python code/990_build_newsletter_corpus.py
    python code/990_build_newsletter_corpus.py verify
    python code/990_build_newsletter_corpus.py verify --selftest
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
HARVEST = ROOT / "data" / "staging" / "tribe_harvest"
NPH = ROOT / "data" / "staging" / "np_harvest"
WEBMAP = ROOT / "data" / "staging" / "cedar_web_map.csv"
SWEEP = (ROOT / "data" / "staging" / "tribe_harvest" / "newsletter_gap_sweep"
         / "gap_sweep.jsonl")
CLEAN = ROOT / "data" / "clean"
OUT_CORPUS = CLEAN / "tribal_newsletter_corpus.csv"
OUT_COVER = CLEAN / "tribal_newsletter_coverage.csv"
OUT_STATE = ROOT / "docs" / "NEWSLETTER_CORPUS_STATE.json"
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

# --- the eight refusals, as HOSTS. Names alone are not enough: Colville's paper
# is tribaltribune.com and Southern Ute's is sudrum.com, neither of which
# contains the nation's name.
RESTRICTIVE_HOSTS = {
    "colvilletribes.com", "tribaltribune.com", "colvillecasinos.com",
    "ctuir.org", "wildhorseresort.com",
    "yakama.com", "yakama.org", "legendscasino.com",
    "chickasaw.net", "chickasawtimes.net", "chickasawbusinessnetwork.com",
    "nana.com", "akima.com",
    "southernute-nsn.gov", "sudrum.com", "skyutecasino.com",
    "fcpotawatomi.com", "potawatomi.com", "paysbig.com", "cartercasino.com",
    "stillaguamish.com", "angelofthewinds.com",
}
RESTRICTIVE_UIDS = {
    "CE-0013K-5M",  # Confederated Colville
    "CE-001BT-Q3",  # CTUIR / Umatilla
    "CE-001CC-8N",  # Confederated Yakama
    "CE-00135-HP",  # The Chickasaw Nation
    "CE-0007G-30",  # NANA / Akima
    "CE-001AX-4Y",  # Southern Ute
    "CE-0014H-YJ",  # Forest County Potawatomi
    "CE-001AY-AQ",  # Stillaguamish
}

FIELDS = [
    "newsletter_id", "cedar_uid", "tribe_id", "publisher_name", "entity_class",
    "state", "publication_name", "channel_type", "channel_url", "channel_host",
    "format", "issue_cadence", "archive_earliest_year", "archive_latest_year",
    "archive_span_years", "archive_depth_n_issues", "archive_depth_basis",
    "back_issues_open", "business_content", "business_content_terms",
    "n_recent_issue_urls", "recent_issue_urls", "discovery_technique",
    "http_status", "retrieved_date", "source_shard", "served_tribe_id", "note",
]
COVER_FIELDS = [
    "cedar_uid", "tribe_id", "canonical_name", "entity_class", "state",
    "has_live_site", "site_url", "probe_status", "n_channels",
    "best_channel_type", "best_channel_url", "archive_earliest_year",
    "archive_latest_year", "probed_by", "note",
]

# channel_type vocabulary, normalized. Everything maps into one of these.
CT = {
    "newsletter": "newsletter", "newsletter_archive": "newsletter",
    "news": "news_page", "news_page": "news_page", "blog": "news_page",
    "press_release": "press_release", "press_releases": "press_release",
    "publications": "publications", "policy_publication": "publications",
    "annual_report": "annual_report", "corporate": "news_page",
    "shareholder": "shareholder_communication",
    "subsidiary_list": "publications",
    "statutory shareholder filings": "statutory_filings",
    "wp-json media library": "wp_media_library",
    "newsletter issue (sampled)": "newsletter_issue",
    "email_signup": "email_signup",
    "none found": "none_found", "none_found": "none_found",
}


# Shard I built a "tribe-serving nonprofit" slice by name matching, and a city
# called Peoria, a valley called Mohawk and a county called Fond du Lac all
# match. An astronomical society is not a tribal publication.
PLACE_COLLISION = re.compile(
    r"(?i)\b(astronomical|cycling club|audubon|shakespeare|"
    r"congress of parents|symphony|garden club|rotary|kiwanis|"
    r"quilt|genealog\w+|historical society|humane society|little league|"
    r"wastewater recycling)\b")


def host_of(u):
    """Host, or the sentinel URL_MALFORMED when the string is not a URL.

    Flag, never delete. One inherited row carries `hhttps://...` - a typo in an
    upstream harvest, not something this script may silently repair, and not
    something it may silently drop either. It keeps its row, gets the sentinel,
    and stays visible to whoever owns shard I.
    """
    u = (u or "").strip()
    if not u:
        return ""
    m = re.match(r"(?i)^https?://([^/:]+)", u)
    if not m:
        return "URL_MALFORMED"
    return m.group(1).lower().lstrip("www.").strip()


def restricted(uid, url):
    if uid in RESTRICTIVE_UIDS:
        return True
    h = host_of(url)
    if not h or h == "URL_MALFORMED":
        return False
    return any(h == d or h.endswith("." + d) for d in RESTRICTIVE_HOSTS)


def nid(uid, url):
    """Deterministic id. Same inputs, same id, every run."""
    return "NLTR-%s-%s" % (uid or "NOUID",
                           hashlib.md5((url or "").encode("utf-8")).hexdigest()[:8])


def yr(v):
    try:
        n = int(str(v)[:4])
    except (TypeError, ValueError):
        return ""
    return str(n) if 1850 <= n <= 2100 else ""


def years_from(seq):
    out = []
    for v in seq or []:
        y = yr(v)
        if y:
            out.append(int(y))
    return (str(min(out)), str(max(out))) if out else ("", "")


def joinu(items, n=3):
    xs = []
    for it in (items or [])[:n]:
        if isinstance(it, dict):
            u = it.get("url") or it.get("issue_url") or ""
        else:
            u = str(it)
        if u:
            xs.append(u)
    return xs


def blank():
    return {k: "" for k in FIELDS}


def rows_from(path):
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def collect(spine_by_uid):
    """Return (corpus_rows, probed_uids -> set of shard names)."""
    recs = []
    probed = defaultdict(set)

    def stamp(r, uid, shard, url):
        e = spine_by_uid.get(uid, {})
        r["cedar_uid"] = uid
        r["tribe_id"] = r["tribe_id"] or e.get("tribe_id", "")
        r["publisher_name"] = r["publisher_name"] or e.get("canonical_name", "")
        r["entity_class"] = r["entity_class"] or e.get("entity_class", "")
        r["state"] = e.get("state", "")
        r["source_shard"] = shard
        r["channel_url"] = url
        r["channel_host"] = host_of(url)
        r["newsletter_id"] = nid(uid, url)
        if uid:
            probed[uid].add(shard)
        return r

    # ---------- shard A ----------
    for d in rows_from(HARVEST / "shard_a" / "newsletters.jsonl"):
        uid, url = d.get("cedar_uid", ""), d.get("final_url") or d.get("source_url", "")
        r = blank()
        r["publication_name"] = d.get("page_title", "")
        r["channel_type"] = CT.get(d.get("url_type", ""), d.get("url_type", ""))
        r["format"] = d.get("format", "")
        r["issue_cadence"] = "; ".join(d.get("cadence_language") or [])
        r["archive_earliest_year"] = yr(d.get("years_mentioned_min"))
        r["archive_latest_year"] = yr(d.get("years_mentioned_max"))
        r["archive_depth_n_issues"] = str(d.get("n_pdf_links") or 0)
        r["archive_depth_basis"] = "PDF issue links counted on the channel page"
        r["back_issues_open"] = "no" if d.get("login_required_language") else "uncertain"
        terms = d.get("business_content_signal") or []
        r["business_content"] = "yes" if terms else "unknown"
        r["business_content_terms"] = "; ".join(terms)
        r["recent_issue_urls"] = " | ".join(joinu(d.get("pdf_issue_links")))
        r["discovery_technique"] = "rendered page link (shard A probe)"
        r["http_status"] = str(d.get("http_status", ""))
        r["retrieved_date"] = d.get("as_of_date", "")
        r["note"] = "channel-page signal only; issue bodies not read"
        recs.append(stamp(r, uid, "shard_a", url))

    # ---------- shard B ----------
    for d in rows_from(HARVEST / "shard_b" / "newsletters.jsonl"):
        uid, url = d.get("cedar_uid", ""), d.get("channel_url", "")
        r = blank()
        r["publication_name"] = d.get("publication_name", "")
        r["channel_type"] = "newsletter"
        r["format"] = d.get("format", "")
        r["issue_cadence"] = d.get("issue_cadence") or ""
        lo, hi = years_from(d.get("archive_depth_years_seen_on_page"))
        r["archive_earliest_year"], r["archive_latest_year"] = lo, hi
        note = d.get("archive_depth_note") or ""
        m = re.search(r"(\d+)\s+issue", note)
        r["archive_depth_n_issues"] = m.group(1) if m else ""
        r["archive_depth_basis"] = note
        bi = d.get("back_issues_downloadable_without_login")
        r["back_issues_open"] = {True: "yes", False: "no"}.get(bi, "uncertain")
        r["business_content"] = {"no extractable text": "unknown"}.get(
            d.get("business_content_finding", ""), d.get("business_content_finding", "") or "unknown")
        r["recent_issue_urls"] = " | ".join(joinu(d.get("sampled_issues")))
        r["discovery_technique"] = "hand-verified tribal newspaper (shard B)"
        r["http_status"] = str(d.get("http_status", ""))
        r["retrieved_date"] = d.get("checked_date", "")
        r["note"] = d.get("publisher_note", "")
        recs.append(stamp(r, uid, "shard_b", url))

    # ---------- shard C ----------
    for d in rows_from(HARVEST / "shard_c" / "newsletters.jsonl"):
        uid, url = d.get("cedar_uid", ""), d.get("channel_url", "")
        r = blank()
        r["publication_name"] = d.get("publication_name", "")
        r["channel_type"] = CT.get(d.get("url_type", ""), d.get("url_type", ""))
        fmt = d.get("format")
        r["format"] = "; ".join(fmt) if isinstance(fmt, list) else (fmt or "")
        r["issue_cadence"] = "; ".join(d.get("issue_cadence_stated") or [])
        r["archive_earliest_year"] = yr(d.get("archive_earliest_year_linked"))
        r["archive_latest_year"] = yr(d.get("archive_latest_year_linked"))
        r["archive_depth_n_issues"] = str(d.get("n_dated_items_linked") or 0)
        r["archive_depth_basis"] = "dated items linked on the channel page"
        r["back_issues_open"] = "no" if d.get("back_issues_need_login") else "yes"
        terms = d.get("business_content_signal_terms") or {}
        r["business_content"] = "yes" if d.get("carries_business_or_econdev_content") else "no"
        r["business_content_terms"] = "; ".join(sorted(terms))
        r["recent_issue_urls"] = " | ".join(joinu(d.get("recent_items_sampled")))
        r["discovery_technique"] = "rendered page + hidden-endpoint sweep (shard C)"
        r["retrieved_date"] = d.get("harvested_date", "")
        r["note"] = d.get("assessment_basis", "")
        recs.append(stamp(r, uid, "shard_c", url))

    # ---------- shard D ----------
    for d in rows_from(HARVEST / "shard_d" / "newsletters.jsonl"):
        uid, url = d.get("cedar_uid", ""), d.get("channel_url", "")
        r = blank()
        r["publication_name"] = d.get("publication_name", "")
        r["channel_type"] = CT.get(d.get("channel_type", ""), d.get("channel_type", ""))
        r["format"] = d.get("format", "")
        r["issue_cadence"] = d.get("issue_cadence") or ""
        r["archive_earliest_year"] = yr(d.get("archive_depth_earliest_year"))
        r["archive_latest_year"] = yr(d.get("archive_depth_latest_year"))
        r["archive_depth_n_issues"] = str(d.get("n_issue_links_on_page") or 0)
        r["archive_depth_basis"] = d.get("cadence_basis") or "issue links counted on the channel page"
        r["back_issues_open"] = str(d.get("back_issues_downloadable_without_login", "")).lower()
        r["business_content"] = {"CHANNEL_PAGE_SIGNAL_ONLY": "unknown"}.get(
            d.get("carries_business_content", ""), str(d.get("carries_business_content", "")).lower())
        r["business_content_terms"] = d.get("business_content_basis", "")
        r["recent_issue_urls"] = " | ".join(joinu(d.get("recent_issue_urls")))
        r["discovery_technique"] = "shard D web probe"
        r["http_status"] = str(d.get("http_status", ""))
        r["retrieved_date"] = d.get("checked_date", "")
        r["note"] = "outcome=%s" % d.get("outcome", "")
        recs.append(stamp(r, uid, "shard_d", url))

    # ---------- shard E (ANCs) ----------
    for d in rows_from(HARVEST / "shard_e" / "newsletters.jsonl"):
        uid, url = d.get("cedar_uid", ""), d.get("url", "")
        r = blank()
        r["publication_name"] = d.get("channel_name", "")
        r["channel_type"] = CT.get(d.get("channel_type", ""), d.get("channel_type", ""))
        r["entity_class"] = d.get("entity_class", "")
        r["format"] = d.get("format", "")
        lo, hi = years_from(d.get("archive_years_observed"))
        r["archive_earliest_year"], r["archive_latest_year"] = lo, hi
        r["archive_depth_n_issues"] = str(d.get("issues_listed") or 0)
        r["archive_depth_basis"] = d.get("archive_depth", "")
        r["business_content"] = {"not on the index page": "no", "n/a": "unknown",
                                 "likely": "unknown"}.get(
            d.get("carries_deal_content", ""), d.get("carries_deal_content", ""))
        r["business_content_terms"] = "; ".join(d.get("deal_terms_on_index") or [])
        r["discovery_technique"] = ("Alaska DBS STAR portal (AS 45.55.139)"
                                    if r["channel_type"] == "statutory_filings"
                                    else "shard E ANC probe")
        r["http_status"] = str(d.get("http_status", ""))
        r["retrieved_date"] = d.get("retrieved_date", "")
        r["note"] = d.get("note", "")
        recs.append(stamp(r, uid, "shard_e", url))

    # ---------- shard F (orgs) ----------
    for d in rows_from(HARVEST / "shard_f" / "newsletters.jsonl"):
        uid, url = d.get("org_cedar_uid", ""), d.get("channel_url", "")
        r = blank()
        r["publication_name"] = d.get("channel_anchor_text", "")
        r["channel_type"] = CT.get(d.get("channel_type", ""), d.get("channel_type", ""))
        r["entity_class"] = d.get("org_entity_class", "")
        r["publisher_name"] = d.get("org_name", "")
        r["tribe_id"] = d.get("org_handle", "")
        r["format"] = d.get("format", "")
        r["issue_cadence"] = d.get("stated_cadence") or (
            "observed median gap %s days" % d["observed_median_gap_days"]
            if d.get("observed_median_gap_days") is not None else "")
        r["archive_earliest_year"] = yr(d.get("archive_earliest"))
        r["archive_latest_year"] = yr(d.get("archive_latest"))
        r["archive_depth_n_issues"] = str(d.get("n_dates_observed") or 0)
        r["archive_depth_basis"] = "distinct dates observed on the channel page"
        r["business_content"] = "yes" if d.get("deal_content") else "unknown"
        r["business_content_terms"] = "; ".join(d.get("deal_terms") or [])
        r["recent_issue_urls"] = " | ".join(joinu(d.get("recent_items")))
        r["discovery_technique"] = "shard F org web probe"
        r["http_status"] = str(d.get("http_status", ""))
        r["retrieved_date"] = d.get("retrieved_date", "")
        r["note"] = d.get("note", "")
        recs.append(stamp(r, uid, "shard_f", url))

    # ---------- shard G (TCUs, CDFIs) ----------
    for d in rows_from(HARVEST / "shard_g" / "newsletters.jsonl"):
        uid, url = d.get("cedar_uid", ""), d.get("channel_url", "")
        r = blank()
        r["channel_type"] = "news_page" if url else "none_found"
        r["entity_class"] = d.get("entity_class", "")
        r["format"] = d.get("format", "")
        r["issue_cadence"] = d.get("cadence", "")
        items = d.get("recent_items") or []
        lo, hi = years_from([re.search(r"(\d{4})", str(i.get("date", "")) or "").group(1)
                             if re.search(r"(\d{4})", str(i.get("date", "")) or "") else ""
                             for i in items])
        r["archive_earliest_year"], r["archive_latest_year"] = lo, hi
        r["archive_depth_n_issues"] = str(d.get("archive_depth") or "")
        r["archive_depth_basis"] = d.get("archive_depth_basis", "")
        r["business_content"] = {"undetermined": "unknown"}.get(
            d.get("economic_content", ""), d.get("economic_content", ""))
        r["business_content_terms"] = "; ".join(d.get("economic_terms") or [])
        r["recent_issue_urls"] = " | ".join(joinu(items))
        r["discovery_technique"] = d.get("technique") or d.get("channel") or ""
        r["http_status"] = str(d.get("http_status", ""))
        r["retrieved_date"] = d.get("checked_date", "")
        r["note"] = d.get("note", "")
        recs.append(stamp(r, uid, "shard_g", url))

    # ---------- shard H (NHOs, individually-owned firms) ----------
    for d in rows_from(HARVEST / "shard_h" / "newsletters.jsonl"):
        uid = d.get("cedar_uid", "")
        url = d.get("archive_url", "")
        r = blank()
        r["publication_name"] = d.get("newsletter_name", "")
        r["channel_type"] = "newsletter" if d.get("has_newsletter") else "none_found"
        r["entity_class"] = d.get("entity_class", "")
        r["format"] = d.get("format", "")
        r["issue_cadence"] = d.get("cadence", "")
        dep = d.get("archive_depth") or {}
        r["archive_depth_n_issues"] = str(dep.get("n_issues_linked_on_index", "")) if dep else ""
        r["archive_depth_basis"] = "issues linked on the index page"
        r["business_content"] = "yes" if d.get("business_or_econdev_content") else "unknown"
        r["business_content_terms"] = d.get("business_content_basis", "")
        r["recent_issue_urls"] = " | ".join(joinu(d.get("recent_issues")))
        r["discovery_technique"] = "; ".join(d.get("techniques_used") or []) or d.get("evidence", "")
        r["http_status"] = str(d.get("site_http_status", ""))
        r["retrieved_date"] = d.get("checked_date", "")
        r["note"] = d.get("evidence", "")
        recs.append(stamp(r, uid, "shard_h", url))

    # ---------- shard I (tribe-serving nonprofits) ----------
    # These are NOT spine entities. The `tribe_id` on the record is the tribe
    # SERVED, not the publisher, so keying them to that tribe's cedar_uid would
    # attribute a mission school's parent newsletter to a sovereign nation.
    # They land with cedar_uid empty and served_tribe_id filled.
    for d in rows_from(NPH / "newsletters_shard_i.jsonl"):
        url = d.get("final_url") or d.get("newsletter_url") or ""
        r = blank()
        r["publisher_name"] = d.get("org_name", "")
        r["entity_class"] = "Tribe-serving nonprofit (EIN %s)" % d.get("EIN", "")
        r["served_tribe_id"] = d.get("tribe_id", "")
        r["channel_type"] = "newsletter"
        ch = d.get("channel")
        r["format"] = "; ".join(ch) if isinstance(ch, list) else (ch or "")
        r["issue_cadence"] = d.get("cadence_evidence", "")
        r["archive_depth_n_issues"] = str(d.get("archive_depth_links_on_page") or "")
        r["archive_depth_basis"] = str(d.get("archive_depth") or "")
        lo, hi = years_from(d.get("archive_years_named_on_page"))
        r["archive_earliest_year"], r["archive_latest_year"] = lo, hi
        r["business_content"] = "unknown"
        r["recent_issue_urls"] = " | ".join(joinu(d.get("three_most_recent_issue_links")))
        r["discovery_technique"] = "shard I nonprofit probe"
        r["http_status"] = str(d.get("http_status", ""))
        r["retrieved_date"] = d.get("retrieved_date", "")
        r["note"] = d.get("harvest_limit", "")
        r["cedar_uid"] = ""
        r["source_shard"] = "shard_i"
        r["channel_url"] = url
        r["channel_host"] = host_of(url)
        r["newsletter_id"] = nid("EIN%s" % d.get("EIN", ""), url)
        recs.append(r)

    # ---------- the gap sweep (991): entities no shard ever probed ----------
    # These are the 104 nations, villages and corporations whose newsletter was
    # invisible to every earlier pass because every earlier pass read the
    # rendered page. Most of these were found in `/wp-json/wp/v2/media`.
    if SWEEP.exists():
        for line in SWEEP.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            uid = d["cedar_uid"]
            if d["outcome"] not in ("FOUND", "NONE_FOUND"):
                probed[uid].add("gap_sweep")
                continue
            if not d.get("found"):
                probed[uid].add("gap_sweep")
                r = blank()
                r["channel_type"] = "none_found"
                r["entity_class"] = d["entity_class"]
                r["discovery_technique"] = "; ".join(d.get("route_coverage") or [])
                r["retrieved_date"] = d["checked_date"]
                r["archive_depth_basis"] = ""
                r["business_content"] = "unknown"
                r["note"] = d.get("note", "")[:600]
                recs.append(stamp(r, uid, "gap_sweep", ""))
                continue
            for f in d["found"]:
                r = blank()
                r["publication_name"] = f.get("title", "")
                r["channel_type"] = {"issue_pdf": "newsletter",
                                     "feed": "news_page",
                                     "channel_index": "news_page"}.get(f["kind"], "newsletter")
                r["entity_class"] = d["entity_class"]
                r["format"] = {"issue_pdf": "PDF issue", "feed": "RSS/Atom XML"}.get(
                    f["kind"], "HTML page")
                lo, hi = years_from(d.get("archive_years") or [])
                r["archive_earliest_year"], r["archive_latest_year"] = lo, hi
                r["archive_depth_n_issues"] = str(d.get("wp_total_media") or "")
                r["archive_depth_basis"] = f.get("archive_depth", "") or (
                    "X-WP-Total on the media index" if d.get("wp_total_media") else
                    "URL located; depth not measured")
                terms = d.get("business_signal_terms") or []
                r["business_content"] = "yes" if terms else "unknown"
                r["business_content_terms"] = "; ".join(terms)
                r["recent_issue_urls"] = " | ".join(f.get("example_item_urls") or [])
                r["discovery_technique"] = f.get("technique", "")
                r["http_status"] = "200"
                r["retrieved_date"] = d["checked_date"]
                note = d.get("attribution_caution", "")
                if d.get("refused_paths"):
                    note += (" %d further URLs on this host were REFUSED: they sit "
                             "under an admin or staging path."
                             % len(d["refused_paths"]))
                r["note"] = note.strip()
                recs.append(stamp(r, uid, "gap_sweep", f["url"]))

    # ---------- the web map, for entities no shard newsletter file reached ----
    seen_uid_url = {(r["cedar_uid"], r["channel_url"]) for r in recs}
    already = set(probed)
    for m in csv.DictReader(WEBMAP.open(encoding="utf-8-sig")):
        if m["url_type"] not in ("newsletter", "press_release", "annual_report"):
            continue
        st = m.get("http_status", "")
        if not (st.isdigit() and 200 <= int(st) < 400):
            continue
        uid, url = m["cedar_uid"], m["url"]
        if uid in already or (uid, url) in seen_uid_url:
            continue
        r = blank()
        r["channel_type"] = CT.get(m["url_type"], m["url_type"])
        r["publisher_name"] = m.get("canonical_name", "")
        r["entity_class"] = m.get("entity_class", "")
        r["discovery_technique"] = "cedar_web_map (%s)" % m.get("shard", "")
        r["http_status"] = st
        r["retrieved_date"] = m.get("checked_date", "")
        r["archive_depth_basis"] = "URL only; depth not measured"
        r["business_content"] = "unknown"
        r["note"] = (m.get("evidence", "") or "")[:600]
        recs.append(stamp(r, uid, "web_map:" + m.get("shard", ""), url))

    return recs, probed


def build():
    spine = list(csv.DictReader(SPINE.open(encoding="utf-8-sig")))
    by_uid = {r["cedar_uid"]: r for r in spine}
    recs, probed = collect(by_uid)

    dropped = [r for r in recs if restricted(r["cedar_uid"], r["channel_url"])]
    recs = [r for r in recs if not restricted(r["cedar_uid"], r["channel_url"])]

    # de-duplicate on (cedar_uid, channel_url); keep the richest row
    def richness(r):
        return sum(1 for k in FIELDS if str(r.get(k, "")).strip())
    best = {}
    for r in recs:
        k = (r["cedar_uid"], r["channel_url"], r["source_shard"] if not r["channel_url"] else "")
        if k not in best or richness(r) > richness(best[k]):
            best[k] = r
    recs = list(best.values())

    for r in recs:
        lo, hi = r["archive_earliest_year"], r["archive_latest_year"]
        r["archive_span_years"] = str(int(hi) - int(lo) + 1) if lo and hi else ""
        r["n_recent_issue_urls"] = str(len([x for x in r["recent_issue_urls"].split(" | ") if x]))
        if r["source_shard"] == "shard_i" and PLACE_COLLISION.search(r["publisher_name"]):
            r["note"] = ("FLAG_UPSTREAM: this publisher reached the corpus through "
                         "shard I's tribe-serving-nonprofit slice, but its name is "
                         "a PLACE-NAME COLLISION (Peoria IL, Wichita KS, Mohawk "
                         "Valley NY, Seminole FL, Fond du Lac WI), not a Native "
                         "organisation. Kept and flagged for the shard-I owner; it "
                         "is not counted as a Native publication. " + r["note"])[:1100]
        if r["channel_host"] == "URL_MALFORMED":
            r["note"] = ("FLAG: channel_url is not a parseable URL as harvested "
                         "upstream; kept, not repaired. " + r["note"])[:1100]

    recs.sort(key=lambda r: (r["publisher_name"].lower(), r["channel_type"], r["channel_url"]))

    CLEAN.mkdir(parents=True, exist_ok=True)
    # Flush per record, not at the end. A buffered shard map nearly lost 1,159
    # rows once; this file is cheap enough to write a line at a time.
    with OUT_CORPUS.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in recs:
            w.writerow(r)
            f.flush()

    # ---- coverage ledger, one row per spine entity
    live_site, site_url = {}, {}
    for m in csv.DictReader(WEBMAP.open(encoding="utf-8-sig")):
        st = m.get("http_status", "")
        if st.isdigit() and 200 <= int(st) < 400:
            live_site[m["cedar_uid"]] = True
            site_url.setdefault(m["cedar_uid"], m["url"])
    by_ent = defaultdict(list)
    for r in recs:
        if r["cedar_uid"]:
            by_ent[r["cedar_uid"]].append(r)

    REAL = {"newsletter", "news_page", "press_release", "publications",
            "annual_report", "shareholder_communication", "statutory_filings",
            "wp_media_library", "newsletter_issue"}
    cover = []
    for e in spine:
        uid = e["cedar_uid"]
        mine = [r for r in by_ent.get(uid, []) if r["channel_type"] in REAL]
        if uid in RESTRICTIVE_UIDS:
            status = "excluded_terms_stated_restrictive"
        elif mine:
            status = "found"
        elif uid in probed:
            status = "attempted_none_found"
        else:
            status = "not_probed"
        mine.sort(key=lambda r: (r["channel_type"] != "newsletter",
                                 -(int(r["archive_span_years"]) if r["archive_span_years"] else 0)))
        lo = min([r["archive_earliest_year"] for r in mine if r["archive_earliest_year"]], default="")
        hi = max([r["archive_latest_year"] for r in mine if r["archive_latest_year"]], default="")
        cover.append({
            "cedar_uid": uid, "tribe_id": e.get("tribe_id", ""),
            "canonical_name": e.get("canonical_name", ""),
            "entity_class": e.get("entity_class", ""), "state": e.get("state", ""),
            "has_live_site": "yes" if live_site.get(uid) else "no",
            "site_url": site_url.get(uid, ""),
            "probe_status": status, "n_channels": str(len(mine)),
            "best_channel_type": mine[0]["channel_type"] if mine else "",
            "best_channel_url": mine[0]["channel_url"] if mine else "",
            "archive_earliest_year": lo, "archive_latest_year": hi,
            "probed_by": ";".join(sorted(probed.get(uid, []))),
            "note": ("TERMS_STATED_RESTRICTIVE - excluded by every route "
                     "(docs/PUBLICATION_POLICY.md)" if status ==
                     "excluded_terms_stated_restrictive" else
                     ("no machine-readable route run yet; this is "
                      "NOT_SEARCHED_MACHINE_READABLE, not an absence"
                      if status == "not_probed" else "")),
        })
    with OUT_COVER.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COVER_FIELDS)
        w.writeheader()
        for r in cover:
            w.writerow(r)
            f.flush()

    st = {
        "script": "code/990_build_newsletter_corpus.py", "run_date": TODAY,
        "corpus_rows": len(recs),
        "corpus_entities": len({r["cedar_uid"] for r in recs if r["cedar_uid"]}),
        "restrictive_rows_dropped": len(dropped),
        "restrictive_hosts_seen": sorted({host_of(r["channel_url"]) for r in dropped
                                          if r["channel_url"]}),
        "spine_entities": len(spine),
        "by_probe_status": dict(Counter(c["probe_status"] for c in cover)),
        "by_channel_type": dict(Counter(r["channel_type"] for r in recs)),
        "by_source_shard": dict(Counter(r["source_shard"] for r in recs)),
        "found_by_entity_class": dict(Counter(
            c["entity_class"] for c in cover if c["probe_status"] == "found")),
        "not_probed_with_live_site": sum(
            1 for c in cover if c["probe_status"] == "not_probed" and c["has_live_site"] == "yes"),
        "shard_i_place_name_collisions_flagged": sum(
            1 for r in recs if r["note"].startswith("FLAG_UPSTREAM")),
        "archive_depth_10y_plus": sum(
            1 for r in recs if r["archive_span_years"] and int(r["archive_span_years"]) >= 10),
        "deepest_archives": sorted(
            [(int(r["archive_span_years"]), r["publisher_name"], r["publication_name"],
              r["archive_earliest_year"] + "-" + r["archive_latest_year"], r["channel_url"])
             for r in recs if r["archive_span_years"]], reverse=True)[:20],
    }
    OUT_STATE.write_text(json.dumps(st, indent=2), encoding="utf-8")
    print(json.dumps(st, indent=2)[:4000])
    return 0


# ------------------------------------------------------------------ verify
def verify(rows=None, cover=None):
    """Invariants. Returns a list of failures; empty means pass."""
    if rows is None:
        rows = list(csv.DictReader(OUT_CORPUS.open(encoding="utf-8-sig")))
    if cover is None:
        cover = list(csv.DictReader(OUT_COVER.open(encoding="utf-8-sig")))
    f = []

    # 1. no TERMS_STATED_RESTRICTIVE publisher, by uid or by host, anywhere
    bad = [r for r in rows if restricted(r["cedar_uid"], r["channel_url"])]
    if bad:
        f.append("RESTRICTIVE_SOURCE_PRESENT: %d rows, e.g. %s" %
                 (len(bad), bad[0]["channel_url"]))

    # 2. newsletter_id unique
    ids = Counter(r["newsletter_id"] for r in rows)
    dup = [k for k, v in ids.items() if v > 1]
    if dup:
        f.append("DUPLICATE_NEWSLETTER_ID: %d, e.g. %s" % (len(dup), dup[0]))

    # 3. every row with a channel_url carries a host or the explicit sentinel.
    #    A silently EMPTY host is the failure; URL_MALFORMED is a flag, and a
    #    flag that is visible has done its job.
    nohost = [r for r in rows if r["channel_url"] and not r["channel_host"]]
    if nohost:
        f.append("UNPARSEABLE_HOST: %d rows" % len(nohost))

    # 4. archive years ordered and in range
    bady = [r for r in rows if r["archive_earliest_year"] and r["archive_latest_year"]
            and int(r["archive_earliest_year"]) > int(r["archive_latest_year"])]
    if bady:
        f.append("ARCHIVE_YEARS_INVERTED: %d rows" % len(bady))

    # 5. the coverage denominator must equal the spine exactly
    spine_n = sum(1 for _ in csv.DictReader(SPINE.open(encoding="utf-8-sig")))
    if len(cover) != spine_n:
        f.append("COVERAGE_DENOMINATOR_DRIFT: %d rows vs %d spine entities"
                 % (len(cover), spine_n))

    # 6. no entity may be BOTH found and not_probed, and a `found` entity must
    #    actually have a corpus row (the false-absence guard, run backwards)
    have = {r["cedar_uid"] for r in rows if r["cedar_uid"]}
    ghost = [c for c in cover if c["probe_status"] == "found" and c["cedar_uid"] not in have]
    if ghost:
        f.append("FOUND_WITHOUT_A_CORPUS_ROW: %d, e.g. %s" %
                 (len(ghost), ghost[0]["canonical_name"]))

    # 7. no issue-body text may leak into the corpus. The privacy invariant.
    #    Any single field over 1,200 chars is body text, not metadata.
    longf = [(r["newsletter_id"], k) for r in rows for k in r
             if len(str(r[k] or "")) > 1200]
    if longf:
        f.append("POSSIBLE_BODY_TEXT_IN_CORPUS: %d fields, e.g. %s"
                 % (len(longf), longf[0]))
    return f


def selftest():
    """Prove each invariant fires on a synthetic violation."""
    ok = []
    base = dict.fromkeys(FIELDS, "")
    base.update(newsletter_id="NLTR-X-1", cedar_uid="CE-TEST", channel_url="https://a.org/n",
                channel_host="a.org", archive_earliest_year="2001",
                archive_latest_year="2020", channel_type="newsletter")
    cov = [{"cedar_uid": "CE-TEST", "probe_status": "found", "canonical_name": "T"}]
    spine_n = sum(1 for _ in csv.DictReader(SPINE.open(encoding="utf-8-sig")))
    pad = [{"cedar_uid": "CE-%d" % i, "probe_status": "not_probed",
            "canonical_name": "p"} for i in range(spine_n - 1)]

    r = dict(base); r.update(channel_url="https://www.sudrum.com/x", channel_host="sudrum.com")
    ok.append(("restrictive", any("RESTRICTIVE" in x for x in verify([r], cov + pad))))
    r1, r2 = dict(base), dict(base)
    r2["channel_url"] = "https://a.org/other"
    ok.append(("dup_id", any("DUPLICATE_NEWSLETTER_ID" in x for x in verify([r1, r2], cov + pad))))
    r = dict(base); r["channel_host"] = ""
    ok.append(("nohost", any("UNPARSEABLE_HOST" in x for x in verify([r], cov + pad))))
    r = dict(base); r["archive_earliest_year"], r["archive_latest_year"] = "2020", "2001"
    ok.append(("inverted", any("ARCHIVE_YEARS_INVERTED" in x for x in verify([r], cov + pad))))
    ok.append(("denominator", any("COVERAGE_DENOMINATOR_DRIFT" in x
                                  for x in verify([dict(base)], cov))))
    ok.append(("ghost", any("FOUND_WITHOUT_A_CORPUS_ROW" in x for x in verify(
        [], [{"cedar_uid": "CE-ZZ", "probe_status": "found", "canonical_name": "G"}]
        + pad + [cov[0]]))))
    r = dict(base); r["note"] = "x" * 1300
    ok.append(("body_text", any("POSSIBLE_BODY_TEXT" in x for x in verify([r], cov + pad))))

    for name, fired in ok:
        print("  selftest %-14s %s" % (name, "FIRES" if fired else "DID NOT FIRE"))
    return 0 if all(f for _, f in ok) else 1


def main(argv):
    if "verify" in argv:
        if "--selftest" in argv:
            rc = selftest()
            if rc:
                return 1
        fails = verify()
        if fails:
            for x in fails:
                print("FAIL", x)
            return 1
        rows = sum(1 for _ in csv.DictReader(OUT_CORPUS.open(encoding="utf-8-sig")))
        print("verify OK - %d corpus rows, 7 invariants held" % rows)
        return 0
    return build()


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
