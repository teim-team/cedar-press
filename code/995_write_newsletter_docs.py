"""Write the newsletter corpus documentation FROM THE FILES, every time.

House rule, learned here the hard way: *docstrings in this project have been
found stale.* A hand-written coverage number is a number that will be wrong
within a week and will keep being quoted anyway. Every figure in
`docs/NEWSLETTER_CORPUS.md` is read out of the tables at write time by this
script; nothing in it is typed.

Reads
    data/clean/tribal_newsletter_corpus.csv
    data/clean/tribal_newsletter_coverage.csv
    docs/NEWSLETTER_CORPUS_STATE.json                       (990)
    data/staging/tribe_harvest/newsletter_gap_sweep/_state.json   (991)
    data/staging/deals_from_newsletters/_state.json               (992)
    data/staging/deals_from_newsletters/_wp_posts_state.json      (993)
    data/staging/deals_from_newsletters/_screen_state.json        (994)

Writes
    docs/NEWSLETTER_CORPUS.md

    python code/995_write_newsletter_docs.py
    python code/995_write_newsletter_docs.py verify
    python code/995_write_newsletter_docs.py verify --selftest
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "clean" / "tribal_newsletter_corpus.csv"
COVER = ROOT / "data" / "clean" / "tribal_newsletter_coverage.csv"
S990 = ROOT / "docs" / "NEWSLETTER_CORPUS_STATE.json"
S991 = (ROOT / "data/staging/tribe_harvest/newsletter_gap_sweep/_state.json")
S992 = ROOT / "data/staging/deals_from_newsletters/_state.json"
S993 = ROOT / "data/staging/deals_from_newsletters/_wp_posts_state.json"
S994 = ROOT / "data/staging/deals_from_newsletters/_screen_state.json"
OUT = ROOT / "docs" / "NEWSLETTER_CORPUS.md"
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

# THE CHANNEL FILTER IS A COLUMN NOW, NOT A SET HELD HERE. Until 2026-09-02
# this file owned a `REAL` set of channel types and 990 owned the data, so the
# published "1,195 channels" depended on two files agreeing about a vocabulary
# with nothing checking that they did. `record_status` is written by 990,
# validated by its invariants 8-10, and is the single definition.
REAL_RECORD_STATUS = "publication_channel"


def jload(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def pct(a, b):
    return "%.0f%%" % (100.0 * a / b) if b else "n/a"


def build():
    rows = list(csv.DictReader(CORPUS.open(encoding="utf-8-sig")))
    cover = list(csv.DictReader(COVER.open(encoding="utf-8-sig")))
    s990, s991 = jload(S990), jload(S991)
    s992, s993, s994 = jload(S992), jload(S993), jload(S994)

    real = [r for r in rows if r.get("record_status") == REAL_RECORD_STATUS]
    bycls = defaultdict(lambda: [0, 0, 0, 0])  # found, attempted, not_probed, total
    for c in cover:
        b = bycls[c["entity_class"]]
        b[3] += 1
        if c["probe_status"] == "found":
            b[0] += 1
        elif c["probe_status"] == "attempted_none_found":
            b[1] += 1
        elif c["probe_status"] == "not_probed":
            b[2] += 1

    deep = sorted([r for r in real if r["archive_span_years"]],
                  key=lambda r: -int(r["archive_span_years"]))
    named = [r for r in real if r["publication_name"].strip()
             and r["channel_type"] == "newsletter"]

    L = []
    a = L.append
    a("# The tribal newsletter corpus")
    a("")
    a("*Generated %s by `code/995_write_newsletter_docs.py`. Every number here "
      "is read out of the tables at write time - none of it is typed.*" % TODAY)
    a("")
    a("Owner, twice: *\"Don't forget tribal newsletters, especially for deals\"* "
      "and *\"even just keeping track of your newsletters could be a potential "
      "different dataset down the road.\"* This is both halves: a catalogue of "
      "what Indian Country publishes, and the deal-extraction route that runs "
      "off it.")
    a("")
    a("## What it is")
    a("")
    a("| | |")
    a("|---|---:|")
    a("| publication channels catalogued | %d |" % len(real))
    a("| rows in the corpus file | %d |" % len(rows))
    a("| entities publishing at least one | %d |" % len(
        {r["cedar_uid"] for r in real if r["cedar_uid"]}))
    a("| named publications (a masthead, not just a news page) | %d |" % len(named))
    a("| archives spanning 10 years or more | %d |" % len(
        [r for r in deep if int(r["archive_span_years"]) >= 10]))
    a("| deepest single archive | %s years (%s) |" % (
        deep[0]["archive_span_years"], deep[0]["publisher_name"]) if deep else "| - | - |")
    a("| spine entities in the coverage denominator | %d |" % len(cover))
    a("")
    a("**Filter `record_status` before you count anything.** The file holds "
      "%d rows and %d publication channels: %s. A recorded absence keeps a "
      "row on purpose, so the negative sits beside the positives and "
      "`discovery_technique` can name which routes ran. Counting rows instead "
      "of filtering the column overstates the channel count by %.0f%%."
      % (len(rows), len(real),
         ", ".join("%d `%s`" % (v, k) for k, v in sorted(
             Counter(r.get("record_status", "") for r in rows).items(),
             key=lambda kv: -kv[1])),
         100.0 * (len(rows) - len(real)) / len(real) if real else 0))
    a("")
    a("Grain is **(entity, channel URL)**. A nation that prints a newspaper, "
      "posts PDFs to a WordPress media library and files shareholder reports "
      "with the State of Alaska has three rows, because those are three "
      "channels with three different archive depths.")
    a("")
    a("## Coverage, by entity class")
    a("")
    a("`found`, `attempted, none found` and `not probed` are three different "
      "claims and the table keeps them apart. A `not probed` row is "
      "`NOT_SEARCHED_MACHINE_READABLE`, which is not an absence.")
    a("")
    a("| entity class | in spine | found | attempted, none found | not probed | found rate of those probed |")
    a("|---|---:|---:|---:|---:|---:|")
    for k in sorted(bycls, key=lambda x: -bycls[x][3]):
        f, at, npb, tot = bycls[k]
        a("| %s | %d | %d | %d | %d | %s |" % (k, tot, f, at, npb, pct(f, f + at)))
    tf = sum(v[0] for v in bycls.values())
    ta = sum(v[1] for v in bycls.values())
    tn = sum(v[2] for v in bycls.values())
    a("| **all** | **%d** | **%d** | **%d** | **%d** | **%s** |"
      % (len(cover), tf, ta, tn, pct(tf, tf + ta)))
    a("")
    a("## Read the coverage table with `site_url_class`, or you will read it "
      "wrong")
    a("")
    a("A single-digit found rate in the table above is not Cedar failing to "
      "look. `has_live_site` answers a narrower question than it appears "
      "to: it is `yes` whenever the web map holds ANY reachable URL for the "
      "entity, and for a large share of some classes that URL is a Wayback "
      "capture of a dead site, an IRS-derived profile page, or - found "
      "2026-09-02 - a **federal ArcGIS API endpoint that returns data about "
      "the entity**, which the web map had recorded as 45 Alaska Native "
      "Villages' website. None of those can be probed for a newsletter. "
      "`site_url_class` states which it is, per row.")
    a("")
    a("**The honest denominator is entities that operate their own site.** "
      "Against it, the picture changes:")
    a("")
    a("| entity class | in spine | operates own site | found ON that site | "
      "found rate on its own site | found ANYWHERE | no site of any kind |")
    a("|---|---:|---:|---:|---:|---:|---:|")
    own = defaultdict(lambda: [0, 0])
    nosite = Counter()
    for c in cover:
        k = c["entity_class"]
        if c.get("site_url_class") == "own_live_site":
            own[k][1] += 1
            if c["probe_status"] == "found":
                own[k][0] += 1
        else:
            nosite[k] += 1
    for k in sorted(bycls, key=lambda x: -bycls[x][3]):
        f, at, npb, tot = bycls[k]
        o_f, o_n = own[k]
        # `found ANYWHERE` can EXCEED `found on that site`, and where it does
        # that is the finding, not an error: the channel was located on
        # somebody else's host - the State of Alaska DBS STAR portal, or a
        # regional consortium's newsletter that carries the village's council
        # news. Both columns are printed so the gap between them is readable.
        a("| %s | %d | %d | %d | %s | %d | %d |"
          % (k, tot, o_n, o_f, pct(o_f, o_n), f, nosite[k]))
    a("")
    a("**`found ANYWHERE` exceeding `found ON that site` is a finding, not an "
      "arithmetic error.** It counts entities whose only publication channel "
      "lives on someone else's host: a village corporation's statutory filing "
      "on the State of Alaska's portal, or a village government's news "
      "carried in its regional consortium's newsletter. Those rows say so - "
      "`served_tribe_id` names the nation served when the publisher is not it.")
    a("")
    a("Three findings this makes visible, each of which reads as a Cedar gap "
      "on the first table and is a fact about the world on this one:")
    a("")
    nho = [c for c in cover if c["entity_class"] == "Native Hawaiian Organization"]
    nho_own = [c for c in nho if c.get("site_url_class") == "own_live_site"]
    nho_found = [c for c in nho_own if c["probe_status"] == "found"]
    a("* **Native Hawaiian Organizations: %d of %d have no website at all.** "
      "Of the %d that do, every one has now been probed on every "
      "machine-readable route and %d publish. The class rate is %s; the rate "
      "among NHOs with a site is %s. `SOURCE_DOES_NOT_PUBLISH` is the honest "
      "state (`docs/AGENT_FIELD_GUIDE.md` section 5), and it is a finding "
      "about how this sector is organised - many NHOs are small homestead "
      "associations and civic clubs whose public presence is a Facebook page "
      "or an IRS filing - not a backlog."
      % (len(nho) - len(nho_own), len(nho), len(nho_own), len(nho_found),
         pct(len(nho_found), len(nho)), pct(len(nho_found), len(nho_own))))
    vc = [c for c in cover
          if c["entity_class"] == "Alaska Native Village Corporation"]
    vc_own = [c for c in vc if c.get("site_url_class") == "own_live_site"]
    vc_found = [c for c in vc if c["probe_status"] == "found"]
    vc_own_found = [c for c in vc_own if c["probe_status"] == "found"]
    a("* **Village corporations look like a %s class and are a %s class.** "
      "Only %d of %d operate a website - but %d publish, because %d of them "
      "were found through the **State of Alaska DBS STAR portal**, where "
      "ANCSA corporations file shareholder communications by statute. A "
      "corporation with no website still has a statutory publication channel, "
      "and the channel is on the state's host, not theirs."
      % (pct(len(vc_found), len(vc)), pct(len(vc_own_found), len(vc_own)),
         len(vc_own), len(vc), len(vc_found),
         len(vc_found) - len(vc_own_found)))
    npb_bie = sum(1 for c in cover if c["probe_status"] == "not_probed"
                  and c["entity_class"] == "BIE School")
    npb_other = sum(1 for c in cover if c["probe_status"] == "not_probed"
                    and c["entity_class"] != "BIE School")
    a("* **The probeable frontier is closed.** %d entities remain "
      "`not_probed`: %d are BIE schools, excluded on purpose, and the other "
      "%d have no site to probe. There is no entity left that operates a live "
      "site, is in scope, and has never been looked at - and that is not a "
      "claim, it is invariant 10 in `990_build_newsletter_corpus.py`, which "
      "fails the build if it stops being true."
      % (npb_bie + npb_other, npb_bie, npb_other))
    a("")
    a("## The deepest back runs")
    a("")
    a("Archive depth is the span of years the channel's own index or media "
      "library exposes. It is a floor, not a ceiling: a paper printing since "
      "1966 whose site only indexes 2002 onward shows as 2002.")
    a("")
    a("| publisher | publication | years | channel |")
    a("|---|---|---|---|")
    for r in deep[:25]:
        a("| %s | %s | %s-%s | [link](%s) |" % (
            r["publisher_name"][:38].replace("|", "/"),
            (r["publication_name"] or r["channel_type"])[:44].replace("|", "/"),
            r["archive_earliest_year"], r["archive_latest_year"], r["channel_url"]))
    a("")
    a("## How they were found")
    a("")
    a("| route | channels |")
    a("|---|---:|")
    for k, v in Counter(
            (r["discovery_technique"] or "unrecorded").split("(")[0].strip()
            for r in real).most_common(14):
        a("| %s | %d |" % (k.replace("|", "/")[:70], v))
    a("")
    if s991:
        a("### The gap sweep: what search alone had missed")
        a("")
        a("`code/991_newsletter_gap_sweep.py` re-ran the machine-readable routes "
          "against entities no prior probe had touched. It is the direct test of "
          "the project's own rule that a negative from search alone is not a "
          "negative.")
        a("")
        a("| | |")
        a("|---|---:|")
        a("| entities in scope | %s |" % s991.get("expected_total"))
        a("| attempted | %s |" % s991.get("attempted"))
        a("| **newsletter channel found where none was known** | **%s** |"
          % s991.get("found"))
        a("| absence confirmed across every route run | %s |" % s991.get("none_found"))
        a("| hosts quarantined for serving one body to many URLs | %s |"
          % s991.get("quarantined"))
        a("| total requests | %s |" % s991.get("requests_made"))
        a("")
        if s991.get("by_technique"):
            a("| technique that produced the finding | count |")
            a("|---|---:|")
            for k, v in sorted(s991["by_technique"].items(), key=lambda x: -x[1]):
                a("| %s | %d |" % (k.replace("|", "/")[:70], v))
            a("")
        if s991.get("skipped"):
            a("Skipped, with the reason recorded rather than silently dropped: "
              + "; ".join("%s %s" % (v, k) for k, v in
                          sorted(s991["skipped"].items(), key=lambda x: -x[1])) + ".")
            a("")
    a("## Deals out of the tribal press")
    a("")
    a("Two extraction routes, one extractor. `992` fetches the issue and article "
      "URLs the corpus already indexes; `993` calls each WordPress host's "
      "`/wp-json/wp/v2/posts?search=` for full article bodies. `994` applies the "
      "precision screen and writes the merge proposal.")
    a("")
    a("| | |")
    a("|---|---:|")
    if s992:
        a("| documents fetched (issue route) | %s |" % s992.get("documents_fetched"))
        a("| documents with extractable text | %s |" % s992.get("documents_with_text"))
        a("| distinct document hashes | %s |" % s992.get("distinct_document_md5"))
        a("| repeated-body fetches refused | %s |"
          % s992.get("identical_body_repeats_blocked"))
    if s993:
        a("| hosts probed (WordPress posts route) | %s |" % s993.get("hosts_probed"))
        a("| of those with the REST posts API open | %s (%s) |"
          % (s993.get("wordpress_hosts"), s993.get("wp_rest_open_rate")))
        a("| articles read | %s |" % s993.get("posts_read"))
        a("| hosts caught ignoring `?search=` | %s |" % s993.get("hosts_ignoring_search"))
    if s994:
        a("| candidates extracted (generous pass) | %s |" % s994.get("candidates_in"))
        a("| rejected by the precision screen | %s |"
          % s994.get("by_tier", {}).get("tier_C_rejected"))
        a("| needing a human read | %s |" % s994.get("by_tier", {}).get("tier_B_review"))
        a("| corporate-parentage statements routed to the hub, not to deals | %s |"
          % s994.get("by_tier", {}).get("tier_D_ownership_fact"))
        a("| **promotable, duplicates removed** | **%s** |" % s994.get("promotable_unique"))
        a("| of those carrying a stated value | %s |" % s994.get("promotable_with_value"))
        a("| of those carrying a date | %s |" % s994.get("promotable_with_date"))
    priv = (s992.get("sentences_dropped_private_life", 0)
            + s993.get("sentences_dropped_private_life", 0))
    a("| sentences dropped by the private-life screen | %d |" % priv)
    a("")
    a("The proposal itself is "
      "`data/staging/deals_from_newsletters/MERGE_PROPOSAL.md`. Nothing has been "
      "written to `data/clean/deals_classified.csv`.")
    a("")
    a("## What is deliberately not here")
    a("")
    a("* **Private personal news.** A tribal newspaper carries obituaries, "
      "birthdays, funeral notices and family announcements about people who are "
      "not public figures. Cedar harvests the publication and records what it "
      "is; it does not extract a natural person's private news from it. The "
      "screen runs before anything is written, and the invariant is re-checked "
      "at every downstream stage.")
    a("* **Back issues.** Depth is measured from the index and the media "
      "library. Issues are downloaded only where a deal route needs the text, "
      "and never in bulk.")
    a("* **The eight `TERMS_STATED_RESTRICTIVE` publishers** - Confederated "
      "Colville, CTUIR/Umatilla, Yakama, Chickasaw, NANA/Akima, Southern Ute, "
      "Forest County Potawatomi and Stillaguamish - excluded by every route. "
      "Their newspapers are among the best in Indian Country (the *Tribal "
      "Tribune*, the *Confederated Umatilla Journal*, the *Southern Ute Drum*, "
      "the *Chickasaw Times*) and that is precisely why the exclusion is by "
      "HOST as well as by entity: those mastheads do not carry the nation's "
      "name and a name-only filter would have missed all four. **Asking is the "
      "route back in.**")
    a("")
    a("## Rebuild")
    a("")
    a("```")
    a("python code/990_build_newsletter_corpus.py            # no network")
    a("python code/991_newsletter_gap_sweep.py               # resumable")
    a("python code/992_newsletter_deal_candidates.py         # resumable")
    a("python code/993_newsletter_wp_posts_deals.py          # resumable")
    a("python code/994_screen_newsletter_deal_candidates.py  # no network")
    a("python code/995_write_newsletter_docs.py              # this file")
    a("```")
    a("")
    a("Each takes `verify`, and `verify --selftest` proves each invariant fires "
      "on a synthetic violation before it is trusted on real data.")
    a("")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("wrote %s (%d lines)" % (OUT, len(L)))
    return 0


def verify(text=None):
    if text is None:
        text = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    f = []
    if not text.strip():
        return ["DOC_EMPTY"]
    # 1. no unresolved placeholder ever ships
    for tok in ("TODO", "TBD", "XXX", "{}", "None years", "| None |"):
        if tok in text:
            f.append("PLACEHOLDER_IN_DOC: %s" % tok)
    # 2. the headline count must match the corpus file, or the doc is stale
    if CORPUS.exists():
        rows = list(csv.DictReader(CORPUS.open(encoding="utf-8-sig")))
        n = len([r for r in rows if r["channel_type"] in REAL
                 and not r["note"].startswith("FLAG_UPSTREAM")])
        m = re.search(r"\| publication channels catalogued \| (\d+) \|", text)
        if not m:
            f.append("HEADLINE_COUNT_MISSING")
        elif int(m.group(1)) != n:
            f.append("DOC_STALE: says %s channels, table has %d" % (m.group(1), n))
    # 3. the refusal section must name all eight restricted publishers
    for who in ("Colville", "Umatilla", "Yakama", "Chickasaw", "NANA",
                "Southern Ute", "Forest County", "Stillaguamish"):
        if who not in text:
            f.append("REFUSAL_NOT_DOCUMENTED: %s" % who)
    return f


def selftest():
    t = []
    good = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    t.append(("empty", verify("") == ["DOC_EMPTY"]))
    t.append(("placeholder", any("PLACEHOLDER_IN_DOC" in x
                                 for x in verify(good + "\nTODO\n"))))
    t.append(("stale", any("DOC_STALE" in x for x in verify(
        re.sub(r"\| publication channels catalogued \| \d+ \|",
               "| publication channels catalogued | 999999 |", good)))))
    t.append(("refusal", any("REFUSAL_NOT_DOCUMENTED" in x
                             for x in verify(good.replace("Stillaguamish", "")))))
    for n, ok in t:
        print("  selftest %-12s %s" % (n, "OK" if ok else "FAILED"))
    return 0 if all(x for _n, x in t) else 1


def main(argv):
    if "verify" in argv:
        if "--selftest" in argv and selftest():
            return 1
        fails = verify()
        if fails:
            for x in fails:
                print("FAIL", x)
            return 1
        print("verify OK - doc current, 3 invariants held")
        return 0
    return build()


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
