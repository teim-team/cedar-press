#!/usr/bin/env python3
"""
1105 - take the tribal newsletter corpus through the shipping standard.

    py -3 code/1105_newsletter_corpus_ship.py codebook   # register both tables
    py -3 code/1105_newsletter_corpus_ship.py conserve   # C5 row conservation
    py -3 code/1105_newsletter_corpus_ship.py verify     # exit 1 on breach
    py -3 code/1105_newsletter_corpus_ship.py verify --selftest

NO NETWORK. Everything here reads files 990 and 991 already wrote.

WHAT THIS SHIPS
---------------
`data/clean/tribal_newsletter_corpus.csv`   one row per publication CHANNEL a
Native entity operates, plus the recorded absences, discriminated by
`record_status`.
`data/clean/tribal_newsletter_coverage.csv` one row per spine entity - the
denominator, which is the half that makes the corpus a finding aid rather than
a list.

Nobody publishes a cross-nation catalogue of tribal periodicals with archive
depth. The nearest published things are single-nation mastheads and
membership lists, and neither carries a denominator, so neither can answer
"which nations publish, and which do not."

WHAT THIS DELIBERATELY DOES NOT SHIP
------------------------------------
The issues. A tribal newspaper carries obituaries, birthdays, funeral notices
and health notices about people who are not public figures. Cedar records that
the publication exists and how deep its archive runs; it does not extract a
natural person's private news from it. 990's invariant 7 fails the build on any
field over 1,200 characters, because that is the shape body text would arrive
in, and `verify --selftest` below proves that check fires.

The deals extracted from the tribal press are NOT part of this collection.
`data/staging/deals_from_newsletters/MERGE_PROPOSAL.md` holds 258 tier-A
candidates and they belong INSIDE `deals_classified.csv`, merged by the agent
who owns that table. As a standalone product they would be a pile of
unverified sentences.

WHAT `conserve` ACCOUNTS FOR
----------------------------
Three funnels, each summing exactly to its own input or raising:
  1. the SPINE, partitioned by probe outcome - where all 1,555 entities went;
  2. the CORPUS, partitioned by `record_status`;
  3. the GAP SWEEP, partitioned by outcome and by skip reason, which is the
     only place a reader can see that 45 entities were skipped because the web
     map had recorded a federal ArcGIS API endpoint as their website.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
csv.field_size_limit(10_000_000)
BUILT = date.today().isoformat()

CLEAN = ROOT / "data" / "clean"
CORPUS = CLEAN / "tribal_newsletter_corpus.csv"
COVER = CLEAN / "tribal_newsletter_coverage.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
SWEEP_STATE = (ROOT / "data" / "staging" / "tribe_harvest"
               / "newsletter_gap_sweep" / "_state.json")
CORPUS_STATE = ROOT / "docs" / "NEWSLETTER_CORPUS_STATE.json"
CONSERVATION = CLEAN / "cedar_harvest_conservation.csv"

CB_FIELDS = ["dataset", "variable", "type", "units", "pct_filled", "n_rows",
             "published", "access_tier", "description", "generated"]
CONS_FIELDS = ["source_table", "rows_in", "disposition", "rows", "pct",
               "examples", "harvest_date"]

CB_BLOCK = {"tribal_newsletter_corpus.csv": "19a_tribal_newsletter_corpus",
            "tribal_newsletter_coverage.csv": "19b_tribal_newsletter_coverage"}


def read_csv(p):
    if not Path(p).exists():
        return []
    with Path(p).open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(p, fields, rows):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(p)


def jload(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# ===========================================================================
# STAGE `codebook`
# ===========================================================================
# A clean table that no `codebook_master.csv` block documents at 60% column
# overlap is INVISIBLE to 512's shippable list and therefore to 518, which
# then reports the collection as NOT_TESTED with "0 tables". The gaming
# collection shipped 912 of 104,412 rows for exactly this reason
# (docs/GAMING_SOURCE_AUDIT_2026-08-26.md).
#
# Two writes, following 1072: the FRAGMENT this dataset owns, and an APPEND to
# the master. An append cannot shrink the master; a rewrite can, which is why
# `41_build_codebooks.py` is the one script on NEVER_RUN.
CB_GENERIC = ("Harvested field, carried as the source published it. See "
              "docs/NEWSLETTER_CORPUS.md for how the channel was discovered.")

CB_DESC = {
    # ---- corpus ----------------------------------------------------------
    "newsletter_id":
        "THE KEY. `NLTR-<cedar_uid or EIN>-<md5(channel_url)[:8]>`. "
        "Deterministic: the same publisher and the same channel URL produce "
        "the same id on every rebuild, because the digest is hashlib.md5 and "
        "not Python's `hash()`, which is randomised per process. "
        "`ferc_filing_id` in this repo is built with `hash()` and 4 of 2,534 "
        "shared documents kept their id across two builds; this one is stable "
        "by construction. Unique on the full file, re-measured by 512 on "
        "every run.",
    "cedar_uid":
        "The publishing entity in Cedar's identity system, joining "
        "data/spine/cedar_entity_spine.csv. BLANK on the 139 rows that reached "
        "the corpus through shard I's tribe-serving-nonprofit slice, which is "
        "keyed by IRS EIN and whose publishers are not spine entities - the id "
        "carries the EIN instead. A blank here means 'not a spine entity', "
        "never 'unresolved'.",
    "record_status":
        "THE DISCRIMINATOR, and the column to filter on before counting "
        "anything. `publication_channel` is the dataset - a real, reachable "
        "channel. `probe_absence` is an entity a machine-readable probe "
        "reached and found nothing on; it is kept here so the negative sits "
        "beside the positives, and `discovery_technique` names which routes "
        "ran, so it is an absence for THOSE routes and not a claim about the "
        "world. `contact_point_only` is an email-signup form with no archive. "
        "`flagged_not_native_publisher` is a shard-I place-name collision "
        "(Peoria Audubon Society, Wichita Shakespeare Company) - flagged, "
        "never deleted, and never counted as a Native publication. Counting "
        "rows instead of filtering this column overstates the channel count "
        "by 35%.",
    "channel_type":
        "What kind of channel it is: `newsletter`, `news_page`, "
        "`press_release`, `publications`, `annual_report`, "
        "`shareholder_communication`, `statutory_filings`, "
        "`wp_media_library`, `newsletter_issue`, `email_signup`, "
        "`none_found`. Normalised from a dozen upstream spellings.",
    "channel_url":
        "The channel's index or archive page - never an issue. Blank on every "
        "`probe_absence` row, and 990's invariant refuses a "
        "`publication_channel` row without one.",
    "channel_host":
        "Host of `channel_url`, lower-cased and www-stripped, or the explicit "
        "sentinel `URL_MALFORMED` where the harvested string is not a URL. "
        "The sentinel is a flag, not a repair: one inherited row carries "
        "`hhttps://`, and this project's rule is flag, never delete. "
        "RESTRICTED-HOST ENFORCEMENT IS BY HOST, NOT NAME - Colville's paper "
        "is tribaltribune.com, Southern Ute's is sudrum.com, Chickasaw's is "
        "chickasawtimes.net, and a name-only filter misses all three.",
    "publication_name":
        "The masthead as the publisher writes it, where the channel has one. "
        "Blank where the channel is a news page rather than a named "
        "periodical - that is a real distinction, not a gap.",
    "archive_earliest_year":
        "Earliest year the channel's own index or media library EXPOSES. A "
        "FLOOR, not a founding date: a paper printing since 1966 whose site "
        "indexes 2002 onward reads as 2002.",
    "archive_latest_year": "Latest year exposed by the same index.",
    "archive_span_years":
        "`archive_latest_year - archive_earliest_year + 1`. Blank where either "
        "endpoint is unknown. Inherits the floor caveat above, so this is a "
        "lower bound on how far back the publication runs.",
    "archive_depth_n_issues":
        "Issues the index or media library exposes. For WordPress media "
        "libraries this is `X-WP-Total`, which gives the depth without "
        "downloading a single issue.",
    "archive_depth_basis": "What was counted to produce the depth.",
    "back_issues_open":
        "Whether back issues are reachable without a login or a paywall.",
    "business_content":
        "Whether the channel carries economic content - contracts, "
        "enterprises, development. Screening signal for the deals route, not "
        "an editorial judgement about the paper.",
    "n_recent_issue_urls":
        "How many recent issue URLs were recorded. Capped at 3 BY DESIGN: "
        "this is a finding aid, not an archive, and the cap is what keeps it "
        "from becoming one.",
    "recent_issue_urls":
        "At most three recent issue URLs, pipe-separated. Links only - no "
        "issue text is stored anywhere in Cedar.",
    "discovery_technique":
        "Which machine-readable route surfaced the channel, or - on a "
        "`probe_absence` row - which routes RAN. Read it before treating an "
        "absence as an absence.",
    "served_tribe_id":
        "Where the publisher serves a nation other than itself (a regional "
        "consortium's newsletter), the nation served. Not the publisher.",
    "source_shard": "Which harvest produced the row.",
    "note":
        "Free text, capped at 1,100 characters so it cannot become a body-text "
        "carrier. `FLAG_` prefixes mark rows kept for an upstream owner.",
    # ---- coverage --------------------------------------------------------
    "canonical_name": "The entity's name in the Cedar spine.",
    "has_live_site":
        "Whether the web map holds any 2xx/3xx URL for the entity. READ IT "
        "WITH `site_url_class`: on its own it says `yes` for entities whose "
        "only known URL is a dead site's Wayback capture or a federal API "
        "response about them.",
    "site_url":
        "The URL a probe would use. WITHHELD (blank) on the 10 "
        "`excluded_terms_stated_restrictive` rows - republishing the URL of a "
        "source that told us not to scrape it still carries that source into "
        "Cedar.",
    "site_url_class":
        "WHY an entity could or could not be probed, and the column that makes "
        "the coverage rates honest. `own_live_site` is a host the entity "
        "operates. `wayback_snapshot_only`, `propublica_irs_profile_only`, "
        "`social_media_only` and `third_party_api_endpoint` are all pages "
        "ABOUT the entity, none of which can be probed for a newsletter; "
        "`no_url_anywhere` has nothing at all. 108 of 210 Native Hawaiian "
        "Organizations fall in the last five, which is why their headline "
        "coverage rate is a fact about the world and not a Cedar backlog.",
    "probe_status":
        "`found`, `attempted_none_found`, `not_probed` or "
        "`excluded_terms_stated_restrictive`. THESE ARE THREE DIFFERENT "
        "CLAIMS and the table keeps them apart: `not_probed` is "
        "NOT_SEARCHED_MACHINE_READABLE, which is not an absence.",
    "n_channels": "Publication channels found for this entity.",
    "best_channel_type": "Channel type of the richest channel found.",
    "best_channel_url": "URL of that channel.",
    "probed_by": "Which harvests reached this entity. Blank means none did.",
}


def _cb_type(vals):
    nz = [v for v in vals if (v or "").strip()]
    if not nz:
        return "text"
    try:
        for v in nz[:500]:
            int(v)
        return "integer"
    except (TypeError, ValueError):
        return "text"


def stage_codebook(_argv) -> int:
    frag_dir = CLEAN / "codebook"
    frag_dir.mkdir(parents=True, exist_ok=True)
    master = CLEAN / "codebook_master.csv"
    existing = read_csv(master)
    have = {(r["dataset"], r["variable"]) for r in existing}
    new_rows = []
    for fname, block in CB_BLOCK.items():
        rows = read_csv(CLEAN / fname)
        if not rows:
            print(f"  ! {fname} has no rows - run 990 first")
            return 1
        frag = []
        for col in list(rows[0].keys()):
            vals = [r.get(col, "") for r in rows]
            filled = sum(1 for x in vals if (x or "").strip())
            frag.append({
                "dataset": block, "variable": col, "type": _cb_type(vals),
                "units": ("code" if col.endswith(("_id", "_uid", "_status",
                                                  "_class", "_type"))
                          else "year" if col.endswith("_year")
                          else "date" if col.endswith("_date")
                          else "count" if col.startswith("n_")
                          or col.endswith("_n_issues") or col.endswith("_years")
                          else "url" if col.endswith(("_url", "_urls"))
                          else "text"),
                "pct_filled": round(100.0 * filled / len(rows), 1),
                "n_rows": len(rows), "published": 1,
                # Every column is either a URL the publisher put on the open
                # web, a fact about that publication, or Cedar's own
                # derivation. No issue text, no natural person, no licensed
                # vendor field - so the whole block is `public`.
                "access_tier": "public",
                "description": CB_DESC.get(col, CB_GENERIC),
                "generated": BUILT,
            })
        write_csv(frag_dir / (block + ".csv"), CB_FIELDS, frag)
        for r in frag:
            if (r["dataset"], r["variable"]) not in have:
                new_rows.append(r)
        print(f"  {block}: {len(frag)} variables documented, {len(rows)} rows")

    if new_rows:
        bak = master.with_suffix(
            f".csv.bak_{BUILT}_pre_1105_newsletter_corpus_ship")
        if master.exists() and not bak.exists():
            bak.write_bytes(master.read_bytes())
        with master.open("a", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=CB_FIELDS, extrasaction="ignore")
            for r in new_rows:
                w.writerow(r)
        print(f"  appended {len(new_rows)} rows to codebook_master.csv "
              f"({len(existing)} -> {len(existing) + len(new_rows)})")
    else:
        print("  codebook_master.csv already carries both blocks")

    # THE REGISTRATION ONLY COUNTS IF THE MATCHER AGREES. A fragment that
    # scores below 0.60 leaves the table `UNDOCUMENTED` and the collection
    # NOT_TESTED, and it would do so silently.
    import cedar_codebook as CB
    groups = CB.dataset_groups()
    ok = True
    for fname, block in CB_BLOCK.items():
        g, s = CB.match_group(CB.header_of(CLEAN / fname), groups)
        flag = "OK" if (g == block and s >= CB.MATCH_THRESHOLD) else "REFUSED"
        if flag != "OK":
            ok = False
        print(f"  match {fname:<34} -> {g} @ {s:.3f}  {flag}")
    return 0 if ok else 1


# ===========================================================================
# STAGE `conserve` - C5, measured not typed
# ===========================================================================
# The question is not "how many rows are there" but "where did every row that
# entered go". Each `add()` asserts its dispositions sum to its input; a
# conservation ledger that does not conserve is worse than none.
def stage_conserve(_argv) -> int:
    rows = read_csv(CORPUS)
    cover = read_csv(COVER)
    sweep = jload(SWEEP_STATE)
    if not rows or not cover:
        print("  run 990 first")
        return 1

    out = []

    def add(table, rows_in, groups, examples=None):
        examples = examples or {}
        total = 0
        for disp, n in groups:
            total += n
            out.append({"source_table": table, "rows_in": rows_in,
                        "disposition": disp, "rows": n,
                        "pct": round(100.0 * n / rows_in, 2) if rows_in else 0.0,
                        "examples": examples.get(disp, ""),
                        "harvest_date": BUILT})
        assert total == rows_in, (
            f"{table}: dispositions sum to {total}, not {rows_in} - a row "
            f"conservation ledger that does not conserve is worse than none")

    # 1. THE SPINE FUNNEL. Every entity Cedar knows, and what happened to it.
    #    This is the denominator claim, and it is the one a reader must be
    #    able to audit: a catalogue without one is a list.
    ps = Counter(c["probe_status"] for c in cover)
    npc = Counter(c["site_url_class"] for c in cover
                  if c["probe_status"] == "not_probed")
    npb = Counter(c["entity_class"] for c in cover
                  if c["probe_status"] == "not_probed"
                  and c["site_url_class"] == "own_live_site")
    groups = [
        ("emitted:publication_channel_found_and_catalogued", ps["found"]),
        ("emitted:absence_recorded_after_every_machine_readable_route_ran",
         ps["attempted_none_found"]),
        ("refused:terms_stated_restrictive_excluded_by_every_route_by_HOST_and_by_entity",
         ps["excluded_terms_stated_restrictive"]),
    ]
    for k, n in sorted(npc.items()):
        if k == "own_live_site":
            continue
        groups.append((f"not_probed:site_url_class_is_{k}_there_is_no_site_to_probe", n))
    for k, n in sorted(npb.items()):
        groups.append((f"not_probed:deliberately_out_of_scope_{k.replace(' ', '_')}", n))
    add("data/spine/cedar_entity_spine.csv (newsletter probe universe)",
        len(cover), groups, {
            "refused:terms_stated_restrictive_excluded_by_every_route_by_HOST_and_by_entity":
                "Confederated Colville, CTUIR/Umatilla, Yakama, Chickasaw, "
                "NANA/Akima, Southern Ute, Forest County Potawatomi, "
                "Stillaguamish. Their site URLs are withheld from the coverage "
                "table too. Asking is the route back in.",
            "not_probed:site_url_class_is_third_party_api_endpoint_there_is_no_site_to_probe":
                "the web map had recorded a BIA Tribal Leaders Directory "
                "ArcGIS FeatureServer query as these entities' WEBSITE. A "
                "response about you is not a site you operate, and probing it "
                "would have asked a federal API for a newsletter.",
        })

    # 2. THE CORPUS, by what the row actually claims.
    rs = Counter(r["record_status"] for r in rows)
    add("data/clean/tribal_newsletter_corpus.csv", len(rows), [
        ("emitted:reachable_publication_channel", rs["publication_channel"]),
        ("emitted:recorded_absence_for_the_routes_named_in_discovery_technique",
         rs["probe_absence"]),
        ("emitted:contact_point_only_signup_form_with_no_archive",
         rs["contact_point_only"]),
        ("flagged:shard_I_place_name_collision_not_a_Native_publication",
         rs["flagged_not_native_publisher"]),
    ], {"flagged:shard_I_place_name_collision_not_a_Native_publication":
        "Peoria Audubon Society, Wichita Shakespeare Company, Fond du Lac "
        "County Audubon Society. Kept and flagged for the shard-I owner, "
        "never counted as a Native publication, never deleted."})

    # 3. THE GAP SWEEP. Its skip reasons are the only place a reader can see
    #    WHY the frontier stops where it does.
    if sweep:
        att = int(sweep.get("attempted") or 0)
        sk = sweep.get("skipped") or {}
        tot = att + sum(sk.values())
        add("data/staging/tribe_harvest/newsletter_gap_sweep/gap_sweep.jsonl",
            tot,
            [("emitted:channel_found_where_no_prior_probe_had_looked",
              int(sweep.get("found") or 0)),
             ("emitted:absence_confirmed_across_every_route_run",
              int(sweep.get("none_found") or 0)),
             ("rejected:host_quarantined_for_serving_one_body_to_many_urls",
              int(sweep.get("quarantined") or 0))]
            + [(f"skipped:{k}", v) for k, v in sorted(sk.items())],
            {"rejected:host_quarantined_for_serving_one_body_to_many_urls":
             "every response body is md5-hashed; one endpoint in this project "
             "returned the same PDF 302 times with 302 green statuses"})

    prior = [r for r in read_csv(CONSERVATION)
             if "tribal_newsletter" not in (r.get("source_table") or "")
             and "newsletter_gap_sweep" not in (r.get("source_table") or "")
             and "newsletter probe universe" not in (r.get("source_table") or "")]
    bak = CONSERVATION.with_suffix(
        f".csv.bak_{BUILT}_pre_1105_newsletter_corpus_ship")
    if CONSERVATION.exists() and not bak.exists():
        bak.write_bytes(CONSERVATION.read_bytes())
    write_csv(CONSERVATION, CONS_FIELDS, prior + out)
    for r in out:
        print(f"  {r['source_table'].split('/')[-1][:40]:<42} {r['rows']:>5}  "
              f"{r['pct']:>6}%  {r['disposition'][:58]}")
    print(f"  ledger {len(prior)} prior rows + {len(out)} newsletter rows")
    return 0


# ===========================================================================
# STAGE `verify`
# ===========================================================================
def verify(rows=None, cover=None, cons=None):
    """Ship-standard invariants ON TOP of 990's twelve. Empty list means pass."""
    rows = read_csv(CORPUS) if rows is None else rows
    cover = read_csv(COVER) if cover is None else cover
    cons = read_csv(CONSERVATION) if cons is None else cons
    f = []

    # S1. THE DENOMINATOR IS THE WHOLE SPINE. A coverage table that silently
    #     drops entities turns a found-rate into a number about nothing.
    if SPINE.exists() and cover:
        spine_n = sum(1 for _ in read_csv(SPINE))
        if len(cover) != spine_n:
            f.append("S1 COVERAGE_IS_NOT_THE_SPINE: %d coverage rows vs %d "
                     "spine entities" % (len(cover), spine_n))

    # S2. THE CONSERVATION LEDGER MUST STILL ACCOUNT FOR THE LIVE FILES. A
    #     ledger written once and never re-checked is a stale receipt.
    want = {"data/clean/tribal_newsletter_corpus.csv": len(rows)}
    by_tab = defaultdict(int)
    seen_in = {}
    for r in cons:
        t = r.get("source_table") or ""
        if "tribal_newsletter" in t or "newsletter probe universe" in t:
            by_tab[t] += int(r.get("rows") or 0)
            seen_in[t] = int(r.get("rows_in") or 0)
    for t, n in want.items():
        if t not in seen_in:
            f.append("S2 CONSERVATION_MISSING for %s - run `conserve`" % t)
        elif seen_in[t] != n or by_tab[t] != n:
            f.append("S2 CONSERVATION_STALE for %s: ledger says rows_in=%d "
                     "summing to %d, file holds %d"
                     % (t, seen_in[t], by_tab[t], n))

    # S3. NO PRIVATE PERSONAL NEWS. The corpus stores index metadata; the
    #     length cap in 990 (invariant 7) is the structural guard against body
    #     text. This is the vocabulary guard, and WHAT IT SCANS IS THE WHOLE
    #     POINT.
    #
    #     THE FIRST VERSION OF THIS CHECK WAS WRONG AND FIRED ON 88 REAL ROWS.
    #     It scanned `note`, and `note` is CEDAR's own description of the
    #     source: "The Council is the newsletter of Tanana Chiefs Conference
    #     ... it carries member-village council news, obituaries and program
    #     notices." That sentence is not an obituary. It is an honest
    #     description of what a paper prints, it is exactly what a reader
    #     needs, and a check that deletes it would have made the corpus less
    #     truthful in the name of privacy. Saying that a publication carries
    #     obituaries is not extracting one.
    #
    #     A leak would land in a field that IDENTIFIES A DOCUMENT, not one
    #     that describes a source: a slug like `/2024/03/obituary-jane-doe/`
    #     in `recent_issue_urls`, or a `publication_name` scraped off a
    #     memorial page. Those three columns are the scan. Measured
    #     2026-09-02: 0 hits, and the selftest below proves the check still
    #     fires when one is planted.
    PRIVATE = ("obituar", "in-memoriam", "in_memoriam", "funeral",
               "memorial-service", "birthday", "passed-away", "survived-by",
               "condolence", "hospice", "wake-service", "death-notice")
    hits = []
    for r in rows:
        blob = ((r.get("publication_name") or "") + " "
                + (r.get("channel_url") or "") + " "
                + (r.get("recent_issue_urls") or "")).lower()
        for term in PRIVATE:
            if term in blob:
                hits.append((r.get("newsletter_id"), term))
                break
    if hits:
        f.append("S3 PRIVATE_PERSONAL_NEWS_IN_A_DOCUMENT_IDENTIFIER: %d rows, "
                 "e.g. %s" % (len(hits), hits[0]))

    # S4. RESTRICTED HOSTS, BY HOST. Re-run here and not only in 990 because
    #     this is the invariant a downstream consumer would break first, and a
    #     refusal that depends on another module importing cleanly is a
    #     refusal that can fail open.
    RESTRICTED = ("colvilletribes.com", "tribaltribune.com",
                  "colvillecasinos.com", "ctuir.org", "wildhorseresort.com",
                  "yakama.com", "yakama.org", "legendscasino.com",
                  "chickasaw.net", "chickasawtimes.net",
                  "chickasawbusinessnetwork.com", "nana.com", "akima.com",
                  "southernute-nsn.gov", "sudrum.com", "skyutecasino.com",
                  "fcpotawatomi.com", "potawatomi.com", "paysbig.com",
                  "cartercasino.com", "stillaguamish.com",
                  "angelofthewinds.com")
    bad = [r.get("newsletter_id") for r in rows
           if any((r.get("channel_host") or "") == d
                  or (r.get("channel_host") or "").endswith("." + d)
                  for d in RESTRICTED)]
    if bad:
        f.append("S4 RESTRICTED_HOST_IN_CORPUS: %d rows, e.g. %s"
                 % (len(bad), bad[0]))

    # S5. MIDDLETOWN RANCHERIA'S /Stagingsite/ STAYS REFUSED. 13 newsletter
    #     PDFs sit under a publicly-reachable staging environment. It was
    #     queued to ASK rather than fetched, and a later sweep must not
    #     quietly pick it up because it happens to return 200.
    stag = [r.get("newsletter_id") for r in rows
            if "/stagingsite/" in (r.get("channel_url") or "").lower()]
    if stag:
        f.append("S5 STAGING_ENVIRONMENT_HARVESTED: %d rows, e.g. %s - "
                 "Middletown Rancheria's staging site is refused, not queued"
                 % (len(stag), stag[0]))

    # S6. A `found` COVERAGE ROW MUST POINT AT A PUBLICATION CHANNEL, not at a
    #     probe_absence row. The false-absence guard, run forwards.
    chan = {r.get("cedar_uid") for r in rows
            if r.get("record_status") == "publication_channel" and r.get("cedar_uid")}
    ghost = [c.get("canonical_name") for c in cover
             if c.get("probe_status") == "found" and c.get("cedar_uid") not in chan]
    if ghost:
        f.append("S6 FOUND_WITHOUT_A_PUBLICATION_CHANNEL: %d, e.g. %s"
                 % (len(ghost), ghost[0]))
    return f


def selftest():
    """Prove each invariant fires on a synthetic violation, then that a clean
    fixture passes. A check that has never failed on purpose is not known to
    work."""
    base = {"newsletter_id": "NLTR-X", "cedar_uid": "CE-T",
            "record_status": "publication_channel", "channel_url":
            "https://example.org/news", "channel_host": "example.org",
            "publication_name": "The Example", "note": ""}
    cov = [{"cedar_uid": "CE-T", "probe_status": "found",
            "canonical_name": "T", "site_url_class": "own_live_site"}]
    spine_n = sum(1 for _ in read_csv(SPINE))
    pad = [{"cedar_uid": "CE-p%d" % i, "probe_status": "not_probed",
            "canonical_name": "p", "site_url_class": "no_url_anywhere"}
           for i in range(spine_n - 1)]
    good_cons = [{"source_table": "data/clean/tribal_newsletter_corpus.csv",
                  "rows_in": "1", "disposition": "emitted:x", "rows": "1"}]
    ok = []

    ok.append(("S1_denominator", any("S1 " in x for x in
                                     verify([dict(base)], cov, good_cons))))
    ok.append(("S2_conservation_missing",
               any("S2 CONSERVATION_MISSING" in x for x in
                   verify([dict(base)], cov + pad, []))))
    stale = [dict(good_cons[0], rows_in="99", rows="99")]
    ok.append(("S2_conservation_stale",
               any("S2 CONSERVATION_STALE" in x for x in
                   verify([dict(base)], cov + pad, stale))))
    r = dict(base)
    r["recent_issue_urls"] = "https://example.org/2024/03/obituary-jane-doe/"
    ok.append(("S3_private_in_slug", any("S3 " in x for x in
                                         verify([r], cov + pad, good_cons))))
    # and the NEGATIVE case, which is the half the first version failed: a
    # note that DESCRIBES what the paper carries must NOT trip the check.
    r = dict(base)
    r["note"] = ("carries member-village council news, obituaries and program "
                 "notices")
    ok.append(("S3_description_is_not_a_leak",
               not any("S3 " in x for x in verify([r], cov + pad, good_cons))))
    r = dict(base); r["channel_host"] = "sudrum.com"
    ok.append(("S4_restricted_host", any("S4 " in x for x in
                                         verify([r], cov + pad, good_cons))))
    r = dict(base); r["channel_url"] = "https://x.org/Stagingsite/n.pdf"
    ok.append(("S5_staging", any("S5 " in x for x in
                                 verify([r], cov + pad, good_cons))))
    r = dict(base); r["record_status"] = "probe_absence"
    ok.append(("S6_ghost_found", any("S6 " in x for x in
                                     verify([r], cov + pad, good_cons))))
    # and the clean fixture must pass, or every FIRES above is meaningless
    ok.append(("clean_fixture_passes",
               not verify([dict(base)], cov + pad, good_cons)))

    for name, fired in ok:
        print("  selftest %-26s %s" % (name, "FIRES" if fired else "DID NOT FIRE"))
    return 0 if all(x for _, x in ok) else 1


def stage_verify(argv) -> int:
    if "--selftest" in argv:
        if selftest():
            print("SELFTEST FAILED - an invariant that cannot fire is not a "
                  "check")
            return 1
    fails = verify()
    for x in fails:
        print("FAIL", x)
    if fails:
        return 1
    rows = read_csv(CORPUS)
    chan = sum(1 for r in rows if r["record_status"] == "publication_channel")
    cover = read_csv(COVER)
    print("verify OK - %d corpus rows (%d publication channels) over a %d-entity "
          "denominator, 6 ship invariants held"
          % (len(rows), chan, len(cover)))
    return 0


def main() -> int:
    stages = {"codebook": stage_codebook, "conserve": stage_conserve,
              "verify": stage_verify}
    argv = sys.argv[1:]
    cmd = argv[0] if argv else ""
    if cmd not in stages:
        print(__doc__)
        return 2
    return stages[cmd](argv)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
    sys.exit(main())
