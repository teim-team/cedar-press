#!/usr/bin/env python3
"""
Cedar Press - SHARD F, step 5: MEMBERSHIP ROSTERS.

THE POINT
---------
An NCAI lobbying filing, a USET grant, a Tanana Chiefs 638 contract are records
that belong to no single tribe. Cedar's two options are `unresolved` and
`multi_entity`, and they are not the same thing: `multi_entity` with a
published, sourced membership list is a fact; `unresolved` is an absence.
This step goes and gets the lists.

METHOD - docs/HIDDEN_DATA_TECHNIQUES.md, run in order of yield
--------------------------------------------------------------
    wp_rest_cpt      /wp-json/wp/v2/types -> a member/tribe custom post type,
                     then that endpoint at per_page=100. One request, whole list.
    select_options   a <select> of member tribes IS the roster.
    arcgis           a FeatureServer behind an embedded member map:
                     ?where=1=1&outFields=*&f=json -> the whole attribute table.
    app_state        __NEXT_DATA__ / __INITIAL_STATE__ - the unpaginated
                     collection the template renders a slice of.
    json_ld          application/ld+json, for clean organisation names.
    rendered_html    the roster page as rendered - the fallback, not the first try.

The technique that produced each row is recorded in `technique`, per the doc.

BOUNDARY (the doc's, in force): only what the server sends an anonymous visitor.
No admin or staging paths, nothing behind a login, no robots.txt Disallow path -
`shard_f_fetch` refuses those before a request is made.

WHAT IS AND IS NOT DONE HERE
----------------------------
* `member_name_raw` is the string EXACTLY as the organisation published it.
* A candidate match against Cedar's register carries a confidence and a method.
  **Identity is NOT resolved here and nothing is written to the spine.**
* An unmatched published name is KEPT. A member Cedar has never heard of is
  precisely what this dataset exists to surface.
* An organisation with no roster gets a row saying so, naming the pages read.
* A claimed count with no names ("over 180 member Tribes") is recorded as a
  claim with its quote and ZERO member rows.

Output: data/staging/org_membership/shard_f.jsonl
        data/staging/tribe_harvest/shard_f/_membership_pages.jsonl
"""
import csv, difflib, html, json, os, re, sys, time, unicodedata
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shard_f_fetch as F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f")
OUT = os.path.join(ROOT, "data", "staging", "org_membership", "shard_f.jsonl")
PAGES = os.path.join(SH, "_membership_pages.jsonl")
TODAY = time.strftime("%Y-%m-%d")

ROSTER_FLOOR = 4        # register matches needed before a page counts as a roster
ROSTER_RATIO = 0.40     # ...and they must be this share of the member-shaped strings

LINK_PAT = [
    (re.compile(r"\bmember\s+tribes?\b", re.I), 10),
    (re.compile(r"\btribal\s+members?\b", re.I), 10),
    (re.compile(r"\bmember\s+(tribal\s+)?nations?\b", re.I), 10),
    (re.compile(r"\bmember\s+(organi[sz]ations?|programs?|villages?|communities)\b", re.I), 9),
    (re.compile(r"\bour\s+(members?|tribes?|communities|villages)\b", re.I), 9),
    (re.compile(r"^\s*members(hip)?\s*$", re.I), 8),
    (re.compile(r"\btribes\s+(we\s+)?serve\b", re.I), 8),
    (re.compile(r"\btribal\s+health\s+programs?\b", re.I), 8),
    (re.compile(r"\bservice\s+area\b", re.I), 7),
    (re.compile(r"\b(communities|villages)\b", re.I), 6),
    (re.compile(r"\bwho\s+we\s+(are|serve)\b", re.I), 5),
    (re.compile(r"\bmember\b", re.I), 4),
]
GUESS_PATHS = ["member-tribes/", "members/", "membership/", "our-members/",
               "tribes/", "communities/"]

TRIBEY = re.compile(
    r"\b(tribe|tribes|tribal|nation|nations|band|bands|pueblo|rancheria|"
    r"reservation|colony|village|community|communities|traditional council|"
    r"native council|indian|ute|sioux|chippewa|paiute|shoshone|apache|"
    r"athabascan|aleut)\b", re.I)

BOILER = re.compile(
    r"^(home|about|about us|contact|contact us|news|events|careers|jobs|search|"
    r"donate|login|log in|menu|privacy|terms|sitemap|resources|programs|services|"
    r"read more|learn more|click here|next|previous|skip to content|"
    r"facebook|twitter|instagram|linkedin|youtube|subscribe|newsletter|"
    r"select|choose|all|none|please select)\s*$", re.I)

HEADLINE = re.compile(
    r"\b20[012]\d\b"
    r"|\b(january|february|march|april|may|june|july|august|september|october|"
    r"november|december)\b"
    r"|[:?!]"
    r"|\b(webinar|conference|summit|register|registration|apply|deadline|"
    r"save the date|call for|announcing|reminder|read more|click|survey|"
    r"comments? on|briefing|listening session|training|workshop|toolkit|"
    r"press release|newsletter|opportunit(y|ies)|posted|blog|podcast|"
    r"job|vacancy|rfp|bid)\b", re.I)

COUNT_CLAIM = re.compile(
    r"((?:over|more than|nearly|approximately|about|all)?\s*\d{1,3})\s+"
    r"(member\s+)?(federally recognized\s+)?(tribes|tribal nations|nations|villages|"
    r"member tribes|tribal governments|tribal health programs|communities|"
    r"urban indian organizations|uios)\b", re.I)

CPT_HINT = re.compile(
    r"member|tribe|tribal|village|nation|clinic|program|consortium|partner|"
    r"community|organization", re.I)

NAMEKEY = re.compile(
    r"^(name|title|tribe|tribe_name|tribal_name|member|member_name|org|org_name|"
    r"organization|organisation|label|community|village|facility|clinic|"
    r"program|programname|fullname|display_name)$", re.I)


# ------------------------------------------------------------------ registry
def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"\b(inc|incorporated|the|of|a)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def load_register():
    p = os.path.join(ROOT, "data", "spine", "cedar_identity_register.csv")
    with open(p, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    idx = {}
    for r in rows:
        n = norm(r["canonical_name"])
        if n:
            idx.setdefault(n, []).append(r)
    return rows, idx


def match_member(raw, idx, keys):
    n = norm(raw)
    if not n:
        return None
    if n in idx:
        r = idx[n][0]
        return (r["cedar_uid"], r["canonical_name"], r["entity_class"], 0.95,
                "exact_normalised_name" + ("_AMBIGUOUS" if len(idx[n]) > 1 else ""))
    cands = [k for k in keys if len(k) >= 8 and (k in n or n in k)]
    if len(cands) == 1:
        r = idx[cands[0]][0]
        return (r["cedar_uid"], r["canonical_name"], r["entity_class"], 0.70, "containment")
    if len(cands) > 1:
        best = max(cands, key=len)
        r = idx[best][0]
        return (r["cedar_uid"], r["canonical_name"], r["entity_class"], 0.45,
                f"containment_AMBIGUOUS_{len(cands)}_candidates")
    close = difflib.get_close_matches(n, keys, n=1, cutoff=0.88)
    if close:
        r = idx[close[0]][0]
        return (r["cedar_uid"], r["canonical_name"], r["entity_class"], 0.60, "fuzzy_0.88")
    return None


# ------------------------------------------------------------------ page work
_LI = re.compile(r"<li\b[^>]*>(.*?)</li>", re.S | re.I)
_TD = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", re.S | re.I)
_H = re.compile(r"<h[2-5]\b[^>]*>(.*?)</h[2-5]>", re.S | re.I)
_STRIP = re.compile(r"<[^>]+>")


def cell_text(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(_STRIP.sub(" ", s))).strip()


def looks_like_member(s):
    if not s or len(s) < 6 or len(s) > 120:
        return False
    if BOILER.match(s) or HEADLINE.search(s):
        return False
    if s.count(" ") > 12:
        return False
    if re.search(r"@|https?://|copyright|all rights reserved", s, re.I):
        return False
    return bool(TRIBEY.search(s))


def candidate_strings(h):
    out = []
    for pat in (_LI, _TD, _H):
        for m in pat.finditer(h):
            t = cell_text(m.group(1))
            if t:
                out.append(t)
    for u, t in F.links_of(h, "http://x/"):
        if t:
            out.append(t)
    return out


# --------------------------------------------------------- hidden-data probes
def tech_select_options(h):
    """A <select> of member tribes IS the roster."""
    out = []
    for m in re.finditer(r"<select\b[^>]*>(.*?)</select>", h, re.S | re.I):
        opts = [cell_text(o) for o in
                re.findall(r"<option\b[^>]*>(.*?)</option>", m.group(1), re.S | re.I)]
        good = [o for o in opts if looks_like_member(o)]
        if len(good) >= 8 and len(good) >= 0.5 * max(1, len(opts)):
            out.extend(good)
    return out


def json_walk(obj, out, depth=0):
    """Pull every plausible name field out of an arbitrary JSON structure."""
    if depth > 8:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and NAMEKEY.match(str(k)) and looks_like_member(v):
                out.append(v)
            else:
                json_walk(v, out, depth + 1)
    elif isinstance(obj, list):
        for v in obj[:3000]:
            json_walk(v, out, depth + 1)


def tech_app_state(h):
    out = []
    for pat in (r'<script[^>]+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;?\s*</script>",
                r"window\.__NUXT__\s*=\s*(\{.*?\})\s*;?\s*</script>"):
        for m in re.finditer(pat, h, re.S | re.I):
            try:
                json_walk(json.loads(m.group(1)), out)
            except Exception:
                pass
    return out


def tech_json_ld(h):
    out = []
    for m in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            h, re.S | re.I):
        try:
            json_walk(json.loads(m.group(1)), out)
        except Exception:
            pass
    return out


def tech_arcgis(h, log):
    """Any FeatureServer/MapServer layer the page embeds -> its attribute table."""
    urls = set()
    for m in re.finditer(r'https?://[^\s"\'<>]+/(?:Feature|Map)Server(?:/\d+)?', h, re.I):
        u = m.group(0)
        if not re.search(r"/\d+$", u):
            u += "/0"
        urls.add(u)
    out = []
    for u in list(urls)[:3]:
        q = (u + "/query?where=1%3D1&outFields=*&returnGeometry=false"
                 "&resultRecordCount=2000&f=json")
        rec = F.fetch(q)
        log.append({"url": q, "http_status": rec["http_status"], "technique": "arcgis"})
        if rec["http_status"] != 200:
            continue
        try:
            d = json.loads(F.read_raw(rec))
        except Exception:
            continue
        for feat in (d.get("features") or [])[:2000]:
            for k, v in (feat.get("attributes") or {}).items():
                if isinstance(v, str) and NAMEKEY.match(str(k)) and looks_like_member(v):
                    out.append(v)
    return out


def tech_wp_rest(base, log):
    """WordPress custom post types are where member directories actually live."""
    out = []
    tu = urllib.parse.urljoin(base, "/wp-json/wp/v2/types")
    t = F.fetch(tu)
    log.append({"url": tu, "http_status": t["http_status"], "technique": "wp_rest_cpt"})
    if t["http_status"] != 200:
        return out
    try:
        types = json.loads(F.read_raw(t))
    except Exception:
        return out
    if not isinstance(types, dict):
        return out
    for slug, meta in types.items():
        if slug in ("post", "page", "attachment", "nav_menu_item", "wp_block",
                    "wp_template", "wp_template_part", "wp_navigation"):
            continue
        rb = (meta or {}).get("rest_base") or slug
        label = str((meta or {}).get("name", "")) + " " + str(slug)
        if not CPT_HINT.search(label):
            continue
        u = urllib.parse.urljoin(base, f"/wp-json/wp/v2/{rb}?per_page=100")
        rec = F.fetch(u)
        log.append({"url": u, "http_status": rec["http_status"],
                    "technique": f"wp_rest_cpt:{rb}"})
        if rec["http_status"] != 200:
            continue
        try:
            items = json.loads(F.read_raw(rec))
        except Exception:
            continue
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            ttl = it.get("title")
            ttl = ttl.get("rendered") if isinstance(ttl, dict) else ttl
            ttl = cell_text(str(ttl or ""))
            if looks_like_member(ttl):
                out.append(ttl)
    return out


def pick_pages(home_html, home_url):
    host = urllib.parse.urlsplit(home_url).netloc.lower().replace("www.", "")
    scored = {}
    for u, t in F.links_of(home_html, home_url):
        hu = urllib.parse.urlsplit(u).netloc.lower().replace("www.", "")
        if hu != host:
            continue
        if re.search(r"\.(pdf|jpg|png|gif|zip|docx?|xlsx?)$", u, re.I):
            continue
        best = 0
        path = urllib.parse.urlsplit(u).path.replace("-", " ")
        for pat, w in LINK_PAT:
            if pat.search(t) or pat.search(path):
                best = max(best, w)
        if best:
            scored[u] = max(scored.get(u, 0), best)
    return [u for u, _ in sorted(scored.items(), key=lambda kv: -kv[1])[:4]]


def member_type(cls, raw):
    if cls:
        if "Village" in cls:
            return "village"
        if cls in ("Federally recognized tribe", "State-recognized tribe"):
            return "tribe"
        return "organization"
    r = raw.lower()
    if re.search(r"\bvillage\b|\bnative council\b|\btraditional council\b", r):
        return "village"
    if re.search(r"\btribe\b|\bnation\b|\bband\b|\bpueblo\b|\brancheria\b"
                 r"|\breservation\b|\bcolony\b|\bcommunity\b", r):
        return "tribe"
    return "organization"


# ------------------------------------------------------------------------ run
def main():
    resolved = F.load_resolved()
    reg, idx = load_register()
    keys = list(idx.keys())

    # UIOs and constituency entities are not federations: a UIO serves a city, a
    # band is a member OF something. Neither is expected to publish a roster, so
    # neither is probed for one here.
    ROSTER_CLASSES = {"Intertribal Organization",
                      "Federal-level self-governance consortium"}

    only = set(sys.argv[1:]) or None
    targets = [u for u, r in resolved.items()
               if r["entity_class"] in ROSTER_CLASSES and (only is None or u in only)]

    fout = open(OUT, "a", encoding="utf-8")
    fpage = open(PAGES, "a", encoding="utf-8")
    n_roster = n_rows = 0

    for i, uid in enumerate(targets, 1):
        r = resolved[uid]
        home = r.get("final_url") or r["url"]
        if not home:
            continue
        hrec = F.fetch(home)
        hh = F.read_raw(hrec)
        base = hrec.get("final_url") or home
        log = []
        found = {}
        claims = []

        def take(names, technique, src):
            """The SAME roster test the rendered pages get.

            A hidden-data harvest is not automatically a roster either. NCAI's
            __NEXT_DATA__ yielded 'Tribal Directory', 'Indian Country 101' and five
            other programme titles - all tribe-shaped strings, none of them members.
            So a technique's harvest keeps its unmatched names only when the harvest
            as a whole is mostly register-matching; otherwise only the matches survive.
            """
            cand = []
            for s in names:
                s = re.sub(r"\s+", " ", s).strip(" -–—|*")
                if not looks_like_member(s):
                    continue
                k = norm(s)
                if not k or k in found:
                    continue
                mm = match_member(s, idx, keys)
                if mm and mm[0] == uid:
                    continue
                cand.append((k, s, mm))
            if not cand:
                return
            nm = sum(1 for _, _, mm in cand if mm)
            ratio = nm / len(cand)
            is_roster = nm >= ROSTER_FLOOR and ratio >= ROSTER_RATIO
            basis = (f"{technique}: {nm}/{len(cand)} harvested names match Cedar's "
                     f"register ({ratio:.0%})" +
                     (" - over the roster test, unmatched names kept as published"
                      if is_roster else
                      " - below the roster test, only register-matched names kept"))
            for k, s, mm in cand:
                if not is_roster and not mm:
                    continue
                found[k] = {
                    "member_name_raw": s, "technique": technique, "source_url": src,
                    "candidate_cedar_uid": mm[0] if mm else "",
                    "candidate_canonical_name": mm[1] if mm else "",
                    "candidate_entity_class": mm[2] if mm else "",
                    "match_confidence": mm[3] if mm else 0.0,
                    "match_method": mm[4] if mm else "no_candidate_in_cedar_register",
                    "quote": "", "page_is_roster_basis": basis,
                }

        if hh:
            take(tech_wp_rest(base, log), "wp_rest_cpt",
                 urllib.parse.urljoin(base, "/wp-json/wp/v2/"))
            take(tech_select_options(hh), "select_options", base)
            take(tech_arcgis(hh, log), "arcgis_featureserver", base)
            take(tech_app_state(hh), "app_state", base)
            take(tech_json_ld(hh), "json_ld", base)

        pages = pick_pages(hh, base) if hh else []
        for g in GUESS_PATHS:
            gu = urllib.parse.urljoin(base, "/" + g)
            if gu not in pages:
                pages.append(gu)
        for pu in pages[:8]:
            prec = F.fetch(pu)
            log.append({"url": pu, "http_status": prec["http_status"],
                        "technique": "rendered_html"})
            if prec["http_status"] != 200:
                continue
            ph = F.read_raw(prec)
            if not ph:
                continue
            src = prec.get("final_url") or pu
            ptext = F.to_text(ph)
            for m in COUNT_CLAIM.finditer(ptext):
                claims.append({
                    "claim": m.group(0).strip(),
                    "quote": re.sub(r"\s+", " ",
                                    ptext[max(0, m.start() - 90):m.end() + 90]).strip(),
                    "source_url": src})
            take(tech_select_options(ph), "select_options", src)

            hits = []
            seen = set()
            for s in candidate_strings(ph):
                if not looks_like_member(s):
                    continue
                k = norm(s)
                if not k or k in seen:
                    continue
                seen.add(k)
                mm = match_member(s, idx, keys)
                if mm and mm[0] == uid:
                    continue
                pos = ptext.find(s[:60])
                q = (re.sub(r"\s+", " ", ptext[max(0, pos - 60):pos + len(s) + 60]).strip()
                     if pos >= 0 else s)
                hits.append((s, mm, q))
            nm = sum(1 for _, mm, _ in hits if mm)
            ratio = nm / len(hits) if hits else 0.0
            is_roster = nm >= ROSTER_FLOOR and ratio >= ROSTER_RATIO
            basis = (f"{nm}/{len(hits)} member-shaped strings on this page match Cedar's "
                     f"register ({ratio:.0%})" +
                     (f" - over the {ROSTER_RATIO:.0%} roster test, so unmatched names on "
                      f"the page are kept as published" if is_roster else
                      " - below the roster test, so only register-matched names were kept"))
            for s, mm, q in hits:
                if not is_roster and not mm:
                    continue
                k = norm(s)
                if k in found and found[k].get("quote"):
                    continue
                found[k] = {
                    "member_name_raw": s, "technique": "rendered_html", "source_url": src,
                    "candidate_cedar_uid": mm[0] if mm else "",
                    "candidate_canonical_name": mm[1] if mm else "",
                    "candidate_entity_class": mm[2] if mm else "",
                    "match_confidence": mm[3] if mm else 0.0,
                    "match_method": mm[4] if mm else "no_candidate_in_cedar_register",
                    "quote": q[:400], "page_is_roster_basis": basis,
                }

        members = list(found.values())
        base_row = {
            "org_cedar_uid": uid, "org_handle": r["handle"],
            "org_name": r["canonical_name"], "org_entity_class": r["entity_class"],
            "org_website": base, "as_of_date": TODAY, "retrieved_date": TODAY,
        }
        if members:
            n_roster += 1
            for m in members:
                row = dict(base_row)
                row.update({
                    "member_name_raw": m["member_name_raw"],
                    "member_type": member_type(m["candidate_entity_class"],
                                               m["member_name_raw"]),
                    "membership_status": "current",
                    "source_url": m["source_url"],
                    "technique": m["technique"],
                    "quote": m["quote"],
                    "page_is_roster_basis": m.get("page_is_roster_basis", ""),
                    "candidate_cedar_uid": m["candidate_cedar_uid"],
                    "candidate_canonical_name": m["candidate_canonical_name"],
                    "candidate_entity_class": m["candidate_entity_class"],
                    "match_confidence": m["match_confidence"],
                    "match_method": m["match_method"],
                    "identity_resolved": False,
                    "note": ("candidate match only - identity NOT resolved by shard F"
                             if m["candidate_cedar_uid"] else
                             "published as a member but NO candidate in Cedar's register; "
                             "member_name_raw is the fact, resolution is open"),
                })
                fout.write(json.dumps(row, ensure_ascii=False) + "\n")
                n_rows += 1
        else:
            row = dict(base_row)
            row.update({
                "member_name_raw": "", "member_type": "",
                "membership_status": "no_published_roster_found",
                "source_url": base,
                "technique": "; ".join(sorted({l["technique"].split(":")[0] for l in log})),
                "quote": "; ".join(c["quote"] for c in claims)[:400],
                "claimed_member_count": "; ".join(c["claim"] for c in claims)[:200],
                "pages_checked": [l["url"] for l in log],
                "pages_status": [l["http_status"] for l in log],
                "note": ("no member roster located. the techniques named in `technique` "
                         "were run against this site and the pages listed were retrieved "
                         "and read."),
            })
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
        fpage.write(json.dumps({"org_cedar_uid": uid, "org_name": r["canonical_name"],
                                "probes": log, "count_claims": claims},
                               ensure_ascii=False) + "\n")
        fout.flush(); fpage.flush()
        tech = ",".join(sorted({m["technique"] for m in members})) or "-"
        print(f"[{i:3d}/{len(targets)}] {len(members):3d} via {tech[:34]:34s} "
              f"{r['canonical_name'][:42]}")

    fout.close(); fpage.close()
    print(f"\norganisations publishing a roster: {n_roster}/{len(targets)}")
    print(f"member rows: {n_rows}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
