#!/usr/bin/env python3
"""
1125_np_website_native_check.py -- ask the ORGANISATION'S OWN WEBSITE whether
it describes itself as Native.

WHY THIS EXISTS
---------------
`docs/CORROBORATION_LAYER_2026-09-02.md` P4 measured that Cedar's nonprofit
Native-status claim has ZERO independent evidence families. The determination
in `np_orgs.disposition = NATIVE_VERIFIED_STRICT` is a NAME MATCH OVER AN IRS
BMF ROW, and the IRS never asserts that an organisation is Native. The
`n_coders_agree` column reads like five sources; four of them read the same BMF
row. An organisation's OWN WEBSITE is the first genuinely independent observer
this dataset can have.

It is also how the open disagreement gets settled: of the 293
`NATIVE_VERIFIED_STRICT` rows with a Form 990 on this disk, 214 give NO Native
signal in their own filed words, and a subset of those cross a state line
(`KANSAS HUMANE SOCIETY OF WICHITA`, `WAMPANOAG COUNTRY CLUB`,
`UNITED HABESHA COMMUNITY OF WICHITA` -- Ethiopian/Eritrean diaspora --
`CHICKASAW CIVIC THEATRE`, where Chickasaw, ALABAMA is a city).

THE ONE QUESTION ASKED OF EVERY PAGE
------------------------------------
Does this organisation describe itself as Native, tribal, or serving a named
nation, IN ITS OWN WORDS? Quotes are literal substrings of retrieved bytes and
the bytes are kept on disk beside them.

SILENCE IS NOT REFUTATION. A page that says nothing Native is
`CHECKED_NO_SIGNAL` and is kept strictly distinct from a page whose own words
name a different community. Neither is a refutation of the IRS-side row; both
are evidence a human can act on, which is more than the dataset had this
morning.

NO DOMAIN IS EVER GUESSED. Every URL comes from the filer's own Form 990
`WebsiteAddressTxt` element in a return already on this disk, from the filer's
own IRS Form 990-N e-Postcard `Website URL` field (the only route for the 990_N
tier, which files no Form 990 at all), or from shard-I's already-retrieved
probe of those same filer-typed fields. A guessed domain that returns 200 is
fabrication with a status code next to it.

THE ENTITY LAYER'S WEB MAP IS REFUSED AS A URL SOURCE, and the refusal is the
point. `np_orgs.cedar_uid` names the entity Cedar KEYED THE NONPROFIT TO -- the
tribe or corporation -- not the nonprofit. 41 of the 293 have no 990 website
field and a `cedar_uid` whose site is in `cedar_web_map.csv`; reading it would
ask the Ahtna corporation's website whether AHTNA INTERTRIBAL RESOURCE
COMMISSION is Native. A tribe's own site is Native by construction, so that
route manufactures a "yes" on every row it touches and corroborates nothing.
It is counted and named in `plan`, never fetched.

NO SECOND MATCHER. The fetch, robots, decode, sentence and evidence machinery
is IMPORTED from `data/staging/np_harvest/web_probe.py` rather than rewritten --
two matchers for one job drift, and a drifted matcher is worse than none
because it is trusted (AGENT_FIELD_GUIDE, and the nonprofits methodology's own
`resolve_entity` note). Only the OUTPUT DIRECTORIES are overridden, so nothing
is written into shard-I's directory.

PULL DISCIPLINE (docs/PULL_DISCIPLINE.md)
  robots.txt per host, honoured, fetched with the same UA as content;
  >=2.5s per host, >=0.8s global; single stream; NO retry loop; at most 2
  content requests per organisation; RUN_DEADLINE on every run; host lock at
  logs/_HOSTLOCK_1125_np_website_check.json.

TERMS (docs/PUBLICATION_POLICY.md, TERMS-OWNER-RULING-2026-09-02)
  Terms language on a tribal or nonprofit website no longer blocks harvest.
  Still binding and honoured here: technical access controls (nothing
  login-gated, no admin/staging path -- see FORBIDDEN below), and a natural
  person's data apart from their public role (no name, home address, personal
  email or phone is extracted or written by this script).

usage
  py -3 code/1125_np_website_native_check.py plan
  py -3 code/1125_np_website_native_check.py fetch [--minutes M] [--limit N]
                                                   [--population f293|nvs]
  py -3 code/1125_np_website_native_check.py build
  py -3 code/1125_np_website_native_check.py verify     # exit 1 on breach
  py -3 code/1125_np_website_native_check.py selftest   # prove verify FIRES
"""
import argparse
import csv
import collections
import datetime
import hashlib
import importlib.util
import json
import os
import re
import sys
from urllib.parse import urlparse

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
STAGE = os.path.join(ROOT, "data", "staging", "np_website_check")
RAW = os.path.join(STAGE, "pages")
ROBOTSD = os.path.join(STAGE, "robots")
PROBE = os.path.join(STAGE, "_probe.jsonl")
LOCK = os.path.join(ROOT, "logs", "_HOSTLOCK_1125_np_website_check.json")
OUT = os.path.join(ROOT, "review", "np_website_native_check_2026-09-02.csv")
LADDER = os.path.join(STAGE, "_ladder.json")
TODAY = "2026-09-02"

NP_ORGS = os.path.join(ROOT, "data", "clean", "np_orgs.csv")
INCL = os.path.join(ROOT, "data", "staging", "np_mission", "inclusion_basis.jsonl")
XMLIDX = os.path.join(ROOT, "data", "staging", "np_harvest", "_xml_index.csv")
SHARDI = os.path.join(ROOT, "data", "staging", "np_harvest", "_web_probe.jsonl")
WEBMAP = os.path.join(ROOT, "data", "staging", "cedar_web_map.csv")
DISAG = os.path.join(ROOT, "data", "clean", "cedar_corroboration_disagreements.csv")
PROPUB = os.path.join(ROOT, "data", "raw", "external", "propublica_990")

csv.field_size_limit(10 ** 9)


# --------------------------------------------------------------------------
# import shard-I's probe machinery; do NOT write a second matcher
# --------------------------------------------------------------------------
def load_wp():
    p = os.path.join(ROOT, "data", "staging", "np_harvest", "web_probe.py")
    if not os.path.exists(p):
        raise SystemExit("UNMEASURED: %s is absent; this script reuses its "
                         "matcher on purpose and will not rewrite one." % p)
    spec = importlib.util.spec_from_file_location("shard_i_web_probe", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(ROBOTSD, exist_ok=True)
    m.RAW = RAW
    m.ROBOTSD = ROBOTSD
    return m


# a technical-access-control fence, per the owner ruling's carve-out #1
FORBIDDEN = re.compile(r"/(wp-admin|admin|\.env|\.git|staging|Stagingsite|"
                       r"backup|dump|phpmyadmin|login|signin|wp-login)", re.I)


# --------------------------------------------------------------------------
# population -- computed, never typed
# --------------------------------------------------------------------------
def rd(p):
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def rj(p):
    out = []
    if not os.path.exists(p):
        return out
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


def n9(e):
    return (e or "").strip().lstrip("0")


def population():
    """Return (ladder, targets). Every rung is computed from the live files."""
    orgs = rd(NP_ORGS)
    incl = {n9(d.get("ein")): d for d in rj(INCL)}
    nvs = [r for r in orgs if (r.get("disposition") or "").strip()
           == "NATIVE_VERIFIED_STRICT"]
    have990 = [r for r in nvs if n9(r.get("EIN")) in incl]
    silent = [r for r in have990
              if incl[n9(r["EIN"])].get("inclusion_basis") in
              ("placename_only", "no_native_signal")]
    crossing = [r for r in silent
                if "state_conflict" in (r.get("cedar_link_basis") or "")]
    # the corroboration layer's own 29 -- read, not re-derived, because it spans
    # three dispositions and this script's population is one of them
    d29 = [r for r in rd(DISAG)
           if r["verdict"] == "OWN_990_SILENT_AND_THE_LINK_CROSSES_A_STATE_LINE"]
    ladder = {
        "np_orgs_rows": len(orgs),
        "disposition_NATIVE_VERIFIED_STRICT": len(nvs),
        "with_a_form_990_on_this_disk": len(have990),
        "own_990_gives_no_native_signal": len(silent),
        "...and_cedar_link_crosses_a_state_line": len(crossing),
        "corroboration_layer_cross_state_facts_all_dispositions": len(d29),
        "inclusion_basis_breakdown_of_the_990_subset": dict(collections.Counter(
            incl[n9(r["EIN"])].get("inclusion_basis", "") for r in have990)),
        "measured_on": TODAY,
        "measured_by": "code/1125_np_website_native_check.py population()",
    }
    return ladder, {"nvs": nvs, "f293": have990, "silent": silent,
                    "crossing": crossing}, incl


# --------------------------------------------------------------------------
# URL discovery -- zero network, and no domain is ever guessed
# --------------------------------------------------------------------------
WEBTAG = re.compile(r"<WebsiteAddressTxt>(.*?)</WebsiteAddressTxt>", re.S | re.I)


def xml_index():
    """EIN -> [(tax_period, path)] from shard-I's index plus inclusion_basis."""
    idx = collections.defaultdict(list)
    if os.path.exists(XMLIDX):
        for r in rd(XMLIDX):
            p = (r.get("local_path") or "").replace("\\", "/")
            if p:
                idx[n9(r.get("EIN"))].append((r.get("tax_period") or "", p))
    for d in rj(INCL):
        p = (d.get("source_file") or "").replace("\\", "/")
        if p:
            idx[n9(d.get("ein"))].append((str(d.get("tax_period") or ""), p))
    return idx


def website_from_990(ein, idx):
    """The filer's own WebsiteAddressTxt, newest return first."""
    for tp, rel in sorted(set(idx.get(ein, [])), reverse=True):
        p = rel if os.path.isabs(rel) else os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        m = WEBTAG.search(txt)
        if m and m.group(1).strip():
            return m.group(1).strip(), ("Form 990 WebsiteAddressTxt, tax period "
                                        "%s, %s" % (tp, rel))
    return "", ""


def shard_i_index():
    return {n9(d.get("EIN")): d for d in rj(SHARDI)}


SHARDI_ROWS = os.path.join(ROOT, "data", "staging", "np_harvest", "shard_i.jsonl")


def shard_i_seed_index():
    """The filer's own IRS 990-N e-Postcard `Website URL` field, extracted by
    shard-I from the bulk e-Postcard corpus. Same class of evidence as
    WebsiteAddressTxt -- a field the filer typed on its own return -- and the
    only route for the 990_N tier, which files no Form 990 at all."""
    out = {}
    for d in rj(SHARDI_ROWS):
        u = (d.get("website_url") or "").strip()
        if u:
            out.setdefault(n9(d.get("EIN")), (u, d.get("route") or ""))
    return out


def webmap_index():
    out = collections.defaultdict(list)
    if os.path.exists(WEBMAP):
        for r in rd(WEBMAP):
            if (r.get("url") or "").strip():
                out[(r.get("cedar_uid") or "").strip()].append(r)
    return out


def propublica_has_website():
    """MEASURED, not assumed: does the cached ProPublica payload carry a URL?"""
    n = hits = 0
    for fn in sorted(os.listdir(PROPUB))[:200] if os.path.isdir(PROPUB) else []:
        if not fn.endswith(".json"):
            continue
        n += 1
        try:
            d = json.load(open(os.path.join(PROPUB, fn), encoding="utf-8"))
        except Exception:
            continue
        org = d.get("organization") or {}
        if any(k for k in org if "web" in k.lower() or k.lower().endswith("url")):
            hits += 1
    return n, hits


# --------------------------------------------------------------------------
# reading the page's own words
# --------------------------------------------------------------------------
# A community the page names for ITSELF that is not Native. These are the
# shapes the 29 cross-state rows actually take, and each is a literal phrase
# the page has to contain -- not an inference from a name.
OTHER_COMMUNITY = re.compile(
    r"(city of chickasaw|chickasaw,? alabama|chickasaw,? iowa|"
    r"habesha|ethiopian|eritrean|"
    r"laguna woods|laguna beach|laguna niguel|laguna hills|"
    r"charrer[ií]a|charro|"
    r"country club|private membership club|golf club|"
    r"humane society|animal shelter|"
    r"parent teacher|booster club|"
    r"charter school|school district|elementary school|high school)", re.I)

# The page naming a nation explicitly. Kept separate from shard-I's broad
# NATIVE regex so a "nation" in "nationwide" cannot reach it.
NATION_WORD = re.compile(
    r"\b(tribal (?:government|council|nation|member|citizen)s?|"
    r"federally recognized tribe|sovereign nation|"
    r"tribally (?:chartered|owned|controlled|operated)|"
    r"american indian|native american|alaska native|native hawaiian|"
    r"indigenous|indian country|first nations?)\b", re.I)


# A LAND ACKNOWLEDGEMENT IS NOT A SELF-DESCRIPTION, and treating it as one is
# the single loudest false positive this pass found. `LUMMI ISLAND HISTORICAL
# SOCIETY` writes "Our deepest respect and gratitude for our Indigenous
# neighbours, the Lummi Nation"; `COMMUNITIES IN SCHOOLS PUYALLUP` writes "this
# land acknowledgement is one small step toward true allyship". Both sentences
# name a nation, and both say the organisation is NOT it. Scored as Native
# self-description they would have manufactured exactly the corroboration this
# whole pass exists to test for.
ACKNOWLEDGEMENT = re.compile(
    r"(land acknowledg|we acknowledge|acknowledge that (?:we|this|the)|"
    r"traditional (?:and unceded )?(?:home)?lands? of|"
    r"ancestral (?:home)?lands? of|unceded (?:territor|lands)|"
    r"original (?:stewards|caretakers|inhabitants|peoples?)|allyship|"
    r"pay (?:our )?respects? to|whose (?:traditional )?land|"
    r"indigenous neighbou?rs|we honou?r the)", re.I)

# FIRST-PERSON IDENTITY, in two strengths, because "we are proud to serve
# Native American students" and "we are enrolled members of the Shinnecock
# Indian Nation" are not the same sentence and a single pattern cannot tell
# them apart. STRONG wins over SERVING; WEAK loses to it.
STRONG_IDENTITY = re.compile(
    r"(enrolled (?:members?|citizens?) of the|"
    r"tribally[- ](?:chartered|owned|controlled|operated)|"
    r"(?:chartered|established|created|founded) by (?:the )?"
    r"(?:federally[- ]recognized )?[A-Za-z'’ .-]{0,45}"
    r"(?:tribes?|tribal|nations?|pueblos?|bands?|rancheria)|"
    r"an? (?:instrumentality|arm|program|department|division|entity|"
    r"subsidiary) of the [A-Za-z'’ .-]{0,45}"
    r"(?:tribe|nation|pueblo|band|community)|"
    r"is an? (?:federally[- ]recognized|native[- ]owned|native[- ]led|"
    r"native[- ]controlled|indigenous[- ]led|tribal government)|"
    r"(?:recognized|reorganized) as a tribal government|"
    r"our (?:tribe|nation|pueblo|rancheria)\b|"
    r"our tribal (?:members?|citizens?|communit\w+|government|council|"
    r"people|elders|youth|families)|"
    r"indigenous[- ]l(?:e|ea)d organization)", re.I)

WEAK_IDENTITY = re.compile(
    r"(we are [^.;]{0,60}?(?:federally[- ]recognized|tribal|native|"
    r"indigenous|american indian|alaska native|native hawaiian)|"
    r"our people\b|the tribe(?:'|’)s (?:own |)programs)", re.I)

# SERVING is a different fact from BEING, and the nonprofits methodology
# already draws that line: "Native control was never inferred from a
# reservation service area alone -- that is native_serving at most."
SERVING = re.compile(
    r"(serv(?:es|ing|e) .{0,50}(?:native|american indian|alaska native|"
    r"indigenous|tribal)|"
    r"our (?:students|clients|patients|families|participants) are "
    r".{0,40}(?:native|american indian|indigenous)|"
    r"(?:support|assist|help) .{0,40}(?:native american|american indian|"
    r"alaska native|indigenous|tribal) (?:people|communit|famil|youth|student))",
    re.I)


def _classify(wp, corpus):
    """Split the page's own sentences into the four things they can be.

    Precedence, and it is the whole point of the function:
      acknowledgement  -> removed first; naming a nation to say you are NOT it
      STRONG identity  -> beats a service claim in the same sentence
      service claim    -> beats a WEAK identity phrase in the same sentence
      weak identity    -> what is left of "we are ... Native"
    """
    ctrl, nat, _memb = wp.evidence(corpus)
    named = [s for s in (ctrl + nat) if NATION_WORD.search(s)]
    ack = [s for s in named if ACKNOWLEDGEMENT.search(s)]
    rest = [s for s in named if s not in ack]
    ident, serve = [], []
    for s in rest:
        if STRONG_IDENTITY.search(s):
            ident.append(s)
        elif SERVING.search(s):
            serve.append(s)
        elif WEAK_IDENTITY.search(s):
            ident.append(s)
    control = [s for s in ctrl if s in ident]
    return control, ident, serve, ack, rest


def verdict_for(wp, corpus, status_ok, thin):
    """
    Returns (verdict, why, quotes). SILENCE IS NOT REFUTATION, and neither is
    a land acknowledgement, and neither is serving Native people -- the
    vocabulary keeps all four apart.
    """
    if not status_ok:
        return ("NOT_CHECKED_NO_READABLE_PAGE",
                "the host returned no readable page", [])
    if thin:
        return ("NOT_CHECKED_PAGE_TOO_THIN",
                "the page loaded but carries almost no text -- a parked or "
                "script-rendered shell; absence of Native language here is a "
                "property of the page, not of the organisation", [])
    control, ident, serve, ack, rest = _classify(wp, corpus)
    if control and ident:
        return ("WEBSITE_SAYS_NATIVE_AND_STATES_A_CONTROL_RELATIONSHIP",
                "the organisation's own page states, in the first person, a "
                "Native charter, ownership or control relationship",
                (control + ident)[:3])
    if ident:
        return ("WEBSITE_SAYS_NATIVE",
                "the organisation's own page describes ITSELF as Native, "
                "tribal, or a body of a named nation", ident[:3])
    if serve:
        return ("WEBSITE_SAYS_IT_SERVES_NATIVE_PEOPLE",
                "the organisation's own page says it SERVES Native people and "
                "does not claim to BE Native. Serving is not control -- the "
                "nonprofits methodology refuses that inference explicitly.",
                serve[:3])
    if ack and not rest:
        return ("WEBSITE_ACKNOWLEDGES_A_NATION_BUT_DOES_NOT_CLAIM_TO_BE_ONE",
                "the only Native language on the page is a land "
                "acknowledgement or a statement of allyship, which names a "
                "nation in order to say the organisation is NOT it",
                ack[:3])
    if rest:
        return ("WEBSITE_USES_NATIVE_LANGUAGE_UNSPECIFICALLY",
                "the page carries Native language that is neither a "
                "first-person identity claim, a service claim, nor an "
                "acknowledgement. A human read is what this is for.", rest[:3])
    other = OTHER_COMMUNITY.search(corpus)
    if other:
        return ("WEBSITE_NAMES_A_DIFFERENT_COMMUNITY",
                "the organisation's own page names a non-Native community, "
                "place or institution type for itself (matched literal: %r). "
                "THIS IS NOT A REFUTATION of the IRS-side row; it is the "
                "organisation's own description of itself."
                % other.group(0), [])
    return ("CHECKED_NO_SIGNAL",
            "the page was read in full and carries no Native language. "
            "SILENCE IS NOT REFUTATION.", [])


# PUBLICATION_POLICY carve-out #2 survives the owner's terms ruling: a natural
# person's data held apart from their public role may not be PUBLISHED, even
# though the page may be harvested. The raw bytes stay on disk under
# data/staging/; what reaches review/ is redacted. This fired on its first run
# -- LEGACY TRADITIONAL SCHOOL MARICOPA's quote carried a phone number -- which
# is why the check exists rather than the assumption.
CONTACT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"
                     r"|\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}")
REDACT = "[contact detail redacted: PUBLICATION_POLICY natural-person carve-out]"


def redact(s):
    return CONTACT.sub(REDACT, s or "")


def quotes_for(wp, corpus, limit=3):
    control, ident, serve, ack, rest = _classify(wp, corpus)
    out = []
    for s in (control + ident + serve + ack + rest):
        if s not in out:
            out.append(s)
    return out[:limit]


def other_quote(wp, corpus):
    for s in wp.sentences(corpus):
        if OTHER_COMMUNITY.search(s):
            return s
    m = OTHER_COMMUNITY.search(corpus)
    return m.group(0) if m else ""


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def cmd_plan(a):
    ladder, tgt, incl = population()
    idx = xml_index()
    si = shard_i_index()
    ss = shard_i_seed_index()
    wm = webmap_index()
    pool = tgt[a.population]
    wp = load_wp()
    src = collections.Counter()
    parse = collections.Counter()
    for r in pool:
        ein = n9(r["EIN"])
        u, basis = website_from_990(ein, idx)
        if u:
            src["form_990_WebsiteAddressTxt"] += 1
        elif ein in si and (si[ein].get("url_probed") or ""):
            src["shard_I_already_probed"] += 1
            u = si[ein]["url_probed"]
        elif ein in ss:
            src["irs_990n_epostcard_website_field"] += 1
            u = ss[ein][0]
        elif (r.get("cedar_uid") or "").strip() in wm:
            src["REFUSED_only_url_is_the_KEYED_ENTITYS_site_not_the_orgs"] += 1
            continue
        else:
            src["NO_URL_PUBLISHED_ANYWHERE_CEDAR_HOLDS"] += 1
            continue
        parse["parses_as_a_url" if wp.normalise(u) else
              "url_field_is_not_a_url"] += 1
    n, hits = propublica_has_website()
    print(json.dumps(ladder, indent=1))
    print("\npopulation chosen: %s  (%d organisations)" % (a.population, len(pool)))
    print("url source:", json.dumps(dict(src), indent=1))
    print("parseability:", json.dumps(dict(parse), indent=1))
    print("\nProPublica cached payloads inspected: %d; carrying a website field: "
          "%d  -- MEASURED, so ProPublica is recorded as NOT a URL source here "
          "rather than assumed to be one." % (n, hits))
    os.makedirs(STAGE, exist_ok=True)
    json.dump(ladder, open(LADDER, "w"), indent=1)
    print("\nladder written to", os.path.relpath(LADDER, ROOT))


def cmd_fetch(a):
    wp = load_wp()
    ladder, tgt, incl = population()
    os.makedirs(STAGE, exist_ok=True)
    os.makedirs(os.path.join(ROOT, "logs"), exist_ok=True)
    idx = xml_index()
    si = shard_i_index()
    ss = shard_i_seed_index()
    wm = webmap_index()
    pool = tgt[a.population]
    # the silent ones first, and the state-crossing ones before those: they are
    # the rows a human is waiting on
    cross = {n9(r["EIN"]) for r in tgt["crossing"]}
    silent = {n9(r["EIN"]) for r in tgt["silent"]}
    pool.sort(key=lambda r: (0 if n9(r["EIN"]) in cross else
                             1 if n9(r["EIN"]) in silent else 2,
                             r.get("org_name", "")))
    if a.limit:
        pool = pool[:a.limit]

    wp.DEADLINE[0] = __import__("time").time() + a.minutes * 60
    done = {d["EIN"] for d in rj(PROBE)}
    json.dump({"host": "many (one per nonprofit)", "pid": os.getpid(),
               "script": "code/1125_np_website_native_check.py",
               "started": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "policy": "<=2 content requests per org, 2.5s/host, 0.8s global, "
                         "robots honoured, no retry loop, %d-min RUN_DEADLINE"
                         % a.minutes,
               "note": "np_orgs NATIVE_VERIFIED_STRICT websites, seeded ONLY "
                       "from the filer's own Form 990 WebsiteAddressTxt, "
                       "shard-I's completed probe, or the entity web map. "
                       "0 domains guessed.",
               "active": True}, open(LOCK, "w"), indent=1)

    n = ok = refused = nourl = 0
    with open(PROBE, "a", encoding="utf-8", newline="\n") as fh:
        for r in pool:
            ein = n9(r["EIN"])
            if ein in done:
                continue
            if wp.past_deadline():
                print("RUN_DEADLINE reached; stopping cleanly", flush=True)
                break
            n += 1
            d = incl.get(ein, {})
            rec = {
                "EIN": ein,
                "ein_as_filed": r.get("EIN", ""),
                "org_name": r.get("org_name", ""),
                "state": r.get("state", ""),
                "city": r.get("city", ""),
                "disposition": r.get("disposition", ""),
                "np_orgs_tier": r.get("tier", ""),
                "confidence_tier": r.get("confidence_tier", ""),
                "cedar_uid": r.get("cedar_uid", ""),
                "keyed_entity": r.get("cedar_spine_canonical_name", "")
                                or r.get("tribe_canonical_name", ""),
                "cedar_link_basis": r.get("cedar_link_basis", ""),
                "link_crosses_a_state_line": "Y" if ein in cross else "N",
                "own_990_inclusion_basis": d.get("inclusion_basis", ""),
                "own_990_quote": (d.get("quote") or "")[:400],
                "own_990_source_file": d.get("source_file", ""),
                "retrieved_date": TODAY,
                "harvested_by": "code/1125_np_website_native_check.py",
            }
            u, basis = website_from_990(ein, idx)
            rec["url_source"] = "form_990_WebsiteAddressTxt"
            rec["url_source_basis"] = basis
            if not u and ein in si and (si[ein].get("url_probed") or ""):
                u = si[ein]["url_probed"]
                rec["url_source"] = "shard_I_np_harvest_probe"
                rec["url_source_basis"] = ("data/staging/np_harvest/"
                                           "_web_probe.jsonl (already fetched "
                                           "2026-09-01)")
            if not u and ein in ss:
                u = ss[ein][0]
                rec["url_source"] = "irs_990n_epostcard_website_field"
                rec["url_source_basis"] = (
                    "the filer's own IRS Form 990-N e-Postcard Website URL "
                    "field, from the bulk e-Postcard corpus "
                    "(data/staging/np_harvest/shard_i.jsonl, route=%s)"
                    % ss[ein][1])
            if not u and (r.get("cedar_uid") or "").strip() in wm:
                rec["url_source"] = "none"
                rec["url_source_basis"] = (
                    "REFUSED: the only URL Cedar holds for this row is the "
                    "KEYED ENTITY's site (cedar_web_map.csv, cedar_uid %s), "
                    "which is the tribe or corporation the nonprofit was "
                    "matched to and not the nonprofit. A tribe's own site is "
                    "Native by construction, so reading it would manufacture "
                    "a yes and corroborate nothing."
                    % (r.get("cedar_uid") or "").strip())
            rec["url_as_published"] = u
            if not u:
                nourl += 1
                rec.update({"url_probed": "", "http_status": "",
                            "verdict": "NOT_CHECKED_NO_URL_PUBLISHED",
                            "verdict_basis": rec.get("url_source_basis") or
                                             "no Form 990 WebsiteAddressTxt "
                                             "and no prior probe of one. No "
                                             "domain was guessed.",
                            "url_source": "none"})
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
                continue
            pu = wp.normalise(u)
            rec["url_probed"] = pu
            if not pu:
                nourl += 1
                rec.update({"http_status": "",
                            "verdict": "NOT_CHECKED_URL_FIELD_IS_NOT_A_URL",
                            "verdict_basis": "the filer's own website field "
                                             "(%r) does not parse as a URL"
                                             % u[:60]})
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
                continue
            p = urlparse(pu)
            if FORBIDDEN.search(p.path or "/"):
                rec.update({"http_status": "REFUSED_ACCESS_CONTROLLED_PATH",
                            "verdict": "NOT_CHECKED_ACCESS_CONTROLLED_PATH",
                            "verdict_basis": "the owner ruling's carve-out #1: "
                                             "technical access controls are "
                                             "untouched by it"})
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
                continue
            allow, why = wp.robots_allows(p.scheme, p.netloc, p.path or "/")
            if allow is None:
                print("deadline during robots; stopping", flush=True)
                break
            rec["robots"] = why
            if not allow:
                rec.update({"http_status": "ROBOTS_DISALLOW",
                            "verdict": "NOT_CHECKED_ROBOTS_DISALLOW",
                            "verdict_basis": "robots.txt forbids this path; not "
                                             "fetched, per pull discipline. The "
                                             "owner ruling releases TERMS "
                                             "language, not a host's "
                                             "operational preference expressed "
                                             "in robots."})
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
                continue
            wp._sleep_for(p.netloc)
            st, final, body, rc = wp.curl(pu)
            rec.update({"http_status": st, "curl_exit": rc,
                        "final_url": final, "bytes": len(body)})
            status_ok = st.startswith("2") and len(body) > 400
            corpus = ""
            if status_ok:
                ok += 1
                h = hashlib.sha1(pu.encode()).hexdigest()[:16]
                fn = "%s_%s_home.html" % (ein, h)
                open(os.path.join(RAW, fn), "wb").write(body)
                rec["raw_home"] = "data/staging/np_website_check/pages/" + fn
                rec["page_title"] = wp.page_title(body)
                cl = wp.classify_links(wp.links(body, final))
                rec["about_page_url"] = cl.get("about", "")
                text = wp.to_text(body)
                atxt = ""
                au = cl.get("about", "")
                if au and not wp.past_deadline():
                    apu = urlparse(au)
                    if not FORBIDDEN.search(apu.path or "/"):
                        al, aw = wp.robots_allows(apu.scheme, apu.netloc,
                                                  apu.path or "/")
                        if al:
                            wp._sleep_for(apu.netloc)
                            ast, af, ab, arc = wp.curl(au)
                            rec["about_http_status"] = ast
                            if ast.startswith("2") and len(ab) > 400:
                                afn = "%s_%s_about.html" % (ein, h)
                                open(os.path.join(RAW, afn), "wb").write(ab)
                                rec["raw_about"] = ("data/staging/"
                                                    "np_website_check/pages/"
                                                    + afn)
                                atxt = wp.to_text(ab)
                        else:
                            rec["about_http_status"] = "ROBOTS_DISALLOW"
                corpus = (text + "\n" + atxt)[:400_000]
                rec["text_chars"] = len(corpus)
                rec["evidence_source"] = ("about page + home page" if atxt
                                          else "home page")
            else:
                refused += 1
                rec["text_chars"] = 0
            thin = status_ok and len(corpus) < 400
            v, why2 = verdict_for(wp, corpus, status_ok, thin)
            rec["verdict"] = v
            rec["verdict_basis"] = why2
            rec["native_self_description_quotes"] = quotes_for(wp, corpus)
            rec["other_community_quote"] = (other_quote(wp, corpus)
                                            if v == "WEBSITE_NAMES_A_DIFFERENT_COMMUNITY"
                                            else "")
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n"); fh.flush()
            if n % 20 == 0:
                print("%d attempted | %d readable | %d refused | %d no-url | "
                      "%.0f min left"
                      % (n, ok, refused, nourl,
                         (wp.DEADLINE[0] - __import__("time").time()) / 60),
                      flush=True)
    try:
        d = json.load(open(LOCK))
    except Exception:
        d = {}
    d.update({"active": False,
              "released": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "attempted": n, "readable": ok, "refused": refused,
              "no_url": nourl})
    json.dump(d, open(LOCK, "w"), indent=1)
    print("DONE attempted=%d readable=%d refused=%d no_url=%d" % (n, ok, refused,
                                                                  nourl))


COLS = ["EIN", "org_name", "state", "city", "disposition", "np_orgs_tier",
        "confidence_tier", "cedar_uid", "keyed_entity",
        "link_crosses_a_state_line", "own_990_inclusion_basis",
        "url_as_published", "url_probed", "url_source", "url_source_basis",
        "http_status", "final_url", "page_title", "text_chars",
        "evidence_source", "verdict", "verdict_basis",
        "native_self_description_quote_1", "native_self_description_quote_2",
        "other_community_quote", "own_990_quote", "own_990_source_file",
        "raw_home", "raw_about", "retrieved_date", "harvested_by"]


def cmd_build(a):
    """Re-derive every verdict FROM THE SAVED BYTES, then write the review CSV.

    The verdict is recomputed here rather than trusted from the fetch, because
    the bytes are on disk and the classifier is the thing most likely to need
    sharpening. It already did: the first fetch scored a land acknowledgement
    as a Native self-description. Re-classifying from the saved page costs no
    network and means a corrected reading never requires re-asking a host.
    """
    wp = load_wp()
    rows = rj(PROBE)
    if not rows:
        raise SystemExit("UNMEASURED: %s is empty. Run `fetch` first. An "
                         "absence of evidence must never print as evidence of "
                         "absence." % os.path.relpath(PROBE, ROOT))
    seen, out, reclassified = set(), [], 0
    for r in rows:
        if r["EIN"] in seen:
            continue
        seen.add(r["EIN"])
        o = dict(r)
        corpus, have = "", False
        for key in ("raw_home", "raw_about"):
            rel = o.get(key) or ""
            p = os.path.join(ROOT, rel) if rel else ""
            if p and os.path.exists(p):
                have = True
                corpus += wp.to_text(open(p, "rb").read()) + "\n"
        if have:
            corpus = corpus[:400_000]
            v, why, quotes = verdict_for(wp, corpus, True, len(corpus) < 400)
            if v != o.get("verdict"):
                reclassified += 1
            o["verdict"], o["verdict_basis"] = v, why
            o["other_community_quote"] = (
                other_quote(wp, corpus)
                if v == "WEBSITE_NAMES_A_DIFFERENT_COMMUNITY" else "")
        else:
            quotes = o.get("native_self_description_quotes") or []
        o["native_self_description_quote_1"] = redact(quotes[0] if quotes
                                                      else "")
        o["native_self_description_quote_2"] = redact(quotes[1]
                                                      if len(quotes) > 1
                                                      else "")
        o["other_community_quote"] = redact(o.get("other_community_quote"))
        o["own_990_quote"] = redact(o.get("own_990_quote"))
        out.append({c: o.get(c, "") for c in COLS})
    print("re-classified %d of %d rows from the saved bytes" %
          (reclassified, len(out)))
    out.sort(key=lambda r: (r["verdict"], r["org_name"]))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    tmp = OUT + ".part"
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)
    os.replace(tmp, OUT)
    c = collections.Counter(r["verdict"] for r in out)
    print("wrote %s -- %d organisations" % (os.path.relpath(OUT, ROOT), len(out)))
    for k, v in c.most_common():
        print("  %-56s %5d" % (k, v))
    return 0


# --------------------------------------------------------------------------
# verify -- exits 1 on breach, AND fails when the work did not land
# --------------------------------------------------------------------------
def _checks(rows, ladder):
    """Returns list of (name, ok, detail). Pure, so selftest can drive it."""
    out = []
    c = collections.Counter(r["verdict"] for r in rows)
    checked = sum(v for k, v in c.items() if not k.startswith("NOT_CHECKED"))

    # V1 -- THE WORK LANDED. A conservation check beside a no-op is how a
    # commit honestly says nothing happened (AGENT_FIELD_GUIDE rule 5).
    floor = 100
    out.append(("V1_work_landed_at_least_%d_pages_actually_read" % floor,
                checked >= floor,
                "%d organisations reached a verdict from a page that was read"
                % checked))

    # V2 -- silence is kept distinct from refutation
    bad = [r for r in rows if r["verdict"] == "CHECKED_NO_SIGNAL"
           and "SILENCE IS NOT REFUTATION" not in (r.get("verdict_basis") or "")]
    out.append(("V2_silence_is_never_written_as_a_refutation", not bad,
                "%d CHECKED_NO_SIGNAL rows lack the standing caveat" % len(bad)))

    # V3 -- every positive carries a verbatim quote
    pos = [r for r in rows if r["verdict"].startswith("WEBSITE_SAYS_NATIVE")]
    noq = [r for r in pos if not (r.get("native_self_description_quote_1") or "").strip()]
    out.append(("V3_every_native_verdict_carries_a_verbatim_quote", not noq,
                "%d of %d Native verdicts carry no quote" % (len(noq), len(pos))))

    # V4 -- no domain was guessed
    bad4 = [r for r in rows if (r.get("url_probed") or "").strip()
            and (r.get("url_source") or "") not in
            ("form_990_WebsiteAddressTxt", "shard_I_np_harvest_probe",
             "irs_990n_epostcard_website_field")]
    out.append(("V4_no_domain_was_guessed", not bad4,
                "%d probed URLs have no declared publisher-side source"
                % len(bad4)))

    # V5 -- quotes are literal substrings of bytes still on disk
    bad5 = []
    for r in pos[:400]:
        q = (r.get("native_self_description_quote_1") or "").strip()
        hp = r.get("raw_home") or ""
        ap = r.get("raw_about") or ""
        if not q:
            continue
        found = False
        for rel in (hp, ap):
            if not rel:
                continue
            p = os.path.join(ROOT, rel)
            if not os.path.exists(p):
                continue
            try:
                wp = _WP[0]
                t = re.sub(r"\s+", " ", wp.to_text(open(p, "rb").read()))
            except Exception:
                continue
            # A redacted quote is checked in fragments: every piece EITHER
            # side of the redaction must still be literally present, so the
            # redaction can hide a phone number and cannot hide a fabrication.
            frags = [re.sub(r"\s+", " ", x).strip()
                     for x in q.split(REDACT)]
            frags = [x for x in frags if len(x) > 20]
            if frags and all(x in t for x in frags):
                found = True
                break
        if not found:
            bad5.append(r["org_name"])
    out.append(("V5_quotes_are_literal_substrings_of_bytes_on_disk", not bad5,
                "%d quotes could not be re-found in the saved bytes: %s"
                % (len(bad5), bad5[:5])))

    # V6 -- the denominator is stated and matches the live file
    live, _t, _i = population()
    same = all(live[k] == ladder.get(k) for k in
               ("disposition_NATIVE_VERIFIED_STRICT",
                "with_a_form_990_on_this_disk",
                "own_990_gives_no_native_signal"))
    out.append(("V6_ladder_matches_the_live_np_orgs_file", same,
                "recorded %s vs live %s"
                % ({k: ladder.get(k) for k in
                    ("disposition_NATIVE_VERIFIED_STRICT",
                     "with_a_form_990_on_this_disk",
                     "own_990_gives_no_native_signal")},
                   {k: live[k] for k in
                    ("disposition_NATIVE_VERIFIED_STRICT",
                     "with_a_form_990_on_this_disk",
                     "own_990_gives_no_native_signal")})))

    # V7 -- no natural person's data was written
    pii = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b|"
                     r"\b\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}\b")
    bad7 = [r["org_name"] for r in rows
            if pii.search(" ".join(str(r.get(c, "")) for c in
                                   ("native_self_description_quote_1",
                                    "native_self_description_quote_2",
                                    "other_community_quote")))]
    out.append(("V7_no_personal_email_or_phone_in_any_published_quote", not bad7,
                "%d quotes carry a personal contact detail: %s"
                % (len(bad7), bad7[:5])))
    return out


_WP = [None]


def cmd_verify(a):
    _WP[0] = load_wp()
    if not os.path.exists(OUT):
        print("UNMEASURED: %s does not exist. verify cannot report clean about "
              "work that has not run." % os.path.relpath(OUT, ROOT))
        return 1
    rows = rd(OUT)
    if not rows:
        print("UNMEASURED: %s is empty." % os.path.relpath(OUT, ROOT))
        return 1
    ladder = json.load(open(LADDER)) if os.path.exists(LADDER) else {}
    res = _checks(rows, ladder)
    rc = 0
    for name, ok, detail in res:
        print("%-4s %-58s %s" % ("PASS" if ok else "FAIL", name, detail))
        if not ok:
            rc = 1
    print("\nrows=%d  verdicts=%s" % (len(rows), dict(collections.Counter(
        r["verdict"] for r in rows))))
    print("EXIT", rc)
    return rc


def cmd_selftest(a):
    """Prove each check FIRES. A check that has never failed on purpose is not
    known to work."""
    _WP[0] = load_wp()
    rows = rd(OUT) if os.path.exists(OUT) else []
    if not rows:
        print("UNMEASURED: no built file to mutate; run fetch+build first.")
        return 1
    ladder = json.load(open(LADDER)) if os.path.exists(LADDER) else {}
    base = _checks(rows, ladder)
    if any(not ok for _n, ok, _d in base):
        print("selftest requires a GREEN baseline; verify is red.")
        return 1
    fired = []

    def fires(tag, mut_rows, mut_ladder):
        r = _checks(mut_rows, mut_ladder)
        got = [n for n, ok, _ in r if not ok]
        print("  inject %-34s -> FAIL: %s" % (tag, got or "NOTHING (BAD)"))
        fired.append(bool(got))

    import copy
    m = copy.deepcopy(rows)[:5]
    fires("only 5 rows survive", m, ladder)             # V1
    m = copy.deepcopy(rows)
    for r in m:
        if r["verdict"] == "CHECKED_NO_SIGNAL":
            r["verdict_basis"] = "no signal"
            break
    fires("a silence row loses its caveat", m, ladder)  # V2
    m = copy.deepcopy(rows)
    for r in m:
        if r["verdict"].startswith("WEBSITE_SAYS_NATIVE"):
            r["native_self_description_quote_1"] = ""
            break
    else:
        m.append(dict(rows[0], verdict="WEBSITE_SAYS_NATIVE",
                      native_self_description_quote_1=""))
    fires("a Native verdict loses its quote", m, ladder)  # V3
    m = copy.deepcopy(rows)
    for r in m:
        if (r.get("url_probed") or "").strip():
            r["url_source"] = "guessed_from_the_organisation_name"
            break
    fires("a URL claims a guessed source", m, ladder)   # V4
    m = copy.deepcopy(rows)
    for r in m:
        if r["verdict"].startswith("WEBSITE_SAYS_NATIVE"):
            r["native_self_description_quote_1"] = ("this sentence is not in "
                                                    "the saved bytes anywhere")
            break
    else:
        m.append(dict(rows[0], verdict="WEBSITE_SAYS_NATIVE",
                      native_self_description_quote_1="not in the bytes",
                      raw_home="", raw_about=""))
    fires("a quote is not in the bytes", m, ladder)     # V5
    fires("the ladder disagrees with np_orgs", rows,
          dict(ladder, own_990_gives_no_native_signal=-1))  # V6
    m = copy.deepcopy(rows)
    m[0]["other_community_quote"] = "reach us at someone@example.org"
    fires("a personal email reaches a quote", m, ladder)  # V7
    ok = all(fired)
    print("\nselftest: %d/%d injections fired -> %s"
          % (sum(fired), len(fired), "PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("--population", default="f293",
                                               choices=["f293", "nvs", "silent",
                                                        "crossing"])
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("fetch")
    p.add_argument("--minutes", type=int, default=60)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--population", default="f293",
                   choices=["f293", "nvs", "silent", "crossing"])
    p.set_defaults(fn=cmd_fetch)
    for name, fn in (("build", cmd_build), ("verify", cmd_verify),
                     ("selftest", cmd_selftest)):
        p = sub.add_parser(name); p.set_defaults(fn=fn)
    a = ap.parse_args()
    rc = a.fn(a)
    sys.exit(rc or 0)


if __name__ == "__main__":
    main()
