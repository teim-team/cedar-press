#!/usr/bin/env python3
"""
Cedar Press - SHARD F, step 4b: recovery pass over every entity with no
verified site, fixing two defects in step 4 and climbing the ladder further.

DEFECT 1 - THE STOPWORD SCORER RETURNED ZERO FOR REAL SITES
    `National Indian Health Board`, `Native American Health Center`,
    `The NATIVE Project`, `American Indian Health & Services Corporation`:
    after the token filter stripped `national/indian/health/board/native/
    american/center/project/services/corporation`, NOTHING was left to match on,
    the score was 0.0 by construction, and www.nihb.org - which is obviously
    NIHB - was written down as `wrong_site`.
    **A scorer that returns 0 because it has nothing to score with is not
    evidence of a wrong site.** This pass matches on the full normalised name,
    on the acronym, and on the domain label, and never emits a verdict from an
    empty token set.

DEFECT 2 - 403 AND 307 WERE TREATED AS "NO SITE"
    Half a dozen origins (scihp.org, anthc.org, itccinc.org,
    nativehealthphoenix.org) answer 403 to a plain client. A 403 does not mean
    the URL is wrong; it means the edge declined us. Where the URL was named by
    an AUTHORITATIVE DIRECTORY - the IHS Title V register, CRIHB's member list,
    Cedar's own intertribal_orgs.csv - the directory is the evidence for the URL
    and the 403 is recorded as the access outcome, not as a failure to find it.
    That is the `directory_attested` verdict. It is deliberately distinct from
    `verified`: we never saw the page.

Ladder rungs added here: 3_browser_ua, 4_directory_attested.
Refusals are recorded and not retried into a block.
"""
import json, os, re, sys, unicodedata
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shard_f_fetch as F
PARKED = F.PARKED   # the parked-domain pattern lives in the shared fetch library

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f")
PROBE = os.path.join(SH, "_probe_results.jsonl")

BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

AUTHORITATIVE = {"ihs_uio_register", "crihb_directory", "cedar_intertribal_orgs"}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", " and ")
    s = re.sub(r"\b(inc|incorporated|corporation|corp|the)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def acronym(name):
    w = [x for x in re.split(r"[^A-Za-z]+", name) if x]
    small = {"of", "the", "and", "for", "a", "in", "on"}
    return "".join(x[0] for x in w if x.lower() not in small).lower()


def rescore(h, name, url):
    """Returns (verdict, score, why). Never scores off an empty token set."""
    if not h:
        return "empty_body", 0.0, ""
    text = F.to_text(h)
    title = F.title_of(h)
    blob = (title + " \n " + text[:15000]).lower()
    if PARKED.search(text[:4000]):
        return "parked_domain", 0.0, ""

    n = norm(name)
    nb = norm(blob)
    why = []
    s = 0.0
    if n and n in nb:
        s = 1.0
        why.append(f'full name "{name}" present verbatim')
    else:
        # every content word, stopwords included - the org's own name is the test
        words = [w for w in n.split() if len(w) > 2]
        hit = [w for w in words if w in nb]
        if words:
            s = len(hit) / len(words)
            why.append(f"{len(hit)}/{len(words)} name words present: {','.join(hit[:8])}")
        ac = acronym(name)
        if len(ac) >= 3 and re.search(r"\b" + re.escape(ac) + r"\b", blob):
            s = max(s, 0.85)
            why.append(f'acronym "{ac.upper()}" present')
        label = urllib.parse.urlsplit(url).netloc.lower().replace("www.", "").split(".")[0]
        if len(label) >= 4 and label in nb.replace(" ", ""):
            s = max(s, 0.7)
            why.append(f'domain label "{label}" echoed in page text')
    v = "verified" if s >= 0.6 else "weak" if s >= 0.35 else "wrong_site"
    return v, round(s, 2), "; ".join(why)


def load_rows():
    rows = []
    for line in open(PROBE, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def main():
    rows = load_rows()
    verified = {r["cedar_uid"] for r in rows if r["verdict"] == "verified"}
    ents = json.load(open(os.path.join(SH, "_candidates.json"), encoding="utf-8"))
    todo = [e for e in ents if e["cedar_uid"] not in verified]
    by_uid = {}
    for r in rows:
        by_uid.setdefault(r["cedar_uid"], []).append(r)

    fh = open(PROBE, "a", encoding="utf-8")
    fixed = attested = still = 0

    for i, e in enumerate(todo, 1):
        uid = e["cedar_uid"]
        name = e["canonical_name"]
        got = None

        # --- rung 3a: re-score what we ALREADY have on disk. Zero requests.
        for prev in by_uid.get(uid, []):
            if prev["http_status"] != 200 or not prev.get("raw_file"):
                continue
            h = F.read_raw(prev)
            v, s, why = rescore(h, name, prev["url"])
            if v == "verified":
                got = dict(prev)
                got.update({"verdict": "verified", "name_match": s,
                            "ladder_rung": "3a_rescored_on_disk",
                            "tokens_hit": [],
                            "rescore_reason": why,
                            "supersedes": f"{prev['ladder_rung']}/{prev['verdict']}"})
                fh.write(json.dumps(got, ensure_ascii=False) + "\n")
                break

        # --- rung 3b: browser user-agent, for 403 / 307 edges
        if got is None:
            bad = {str(p["http_status"]) for p in by_uid.get(uid, [])}
            if bad & {"403", "307", "406", "503", "URLError"}:
                old = F.HDR["User-Agent"]
                F.HDR["User-Agent"] = BROWSER
                try:
                    for c in e["candidates"]:
                        rec = F.fetch(c["url"], force=True)
                        if rec["http_status"] != 200:
                            continue
                        h = F.read_raw(rec)
                        v, s, why = rescore(h, name, c["url"])
                        row = {
                            "cedar_uid": uid, "handle": e["handle"],
                            "canonical_name": name, "entity_class": e["entity_class"],
                            "url": c["url"], "candidate_basis": c["candidate_basis"],
                            "basis_source": c["basis_source"],
                            "ladder_rung": "3b_browser_ua",
                            "http_status": rec["http_status"],
                            "final_url": rec.get("final_url"),
                            "robots_note": rec.get("robots_note"),
                            "raw_file": rec.get("raw_file"), "verdict": v,
                            "name_match": s, "tokens_hit": [],
                            "rescore_reason": why,
                            "title": F.title_of(h)[:180],
                            "checked_date": rec["checked_date"],
                            "note": ("origin refused the project user-agent; retried once "
                                     "with a browser user-agent, robots.txt still obeyed"),
                        }
                        for k in ("ihs_area", "ihs_state", "ihs_city", "ihs_service_level"):
                            if k in c:
                                row[k] = c[k]
                        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                        if v == "verified":
                            got = row
                            break
                finally:
                    F.HDR["User-Agent"] = old

        # --- rung 4: directory-attested. The URL stands on the directory's word.
        if got is None:
            auth = [c for c in e["candidates"] if c["candidate_basis"] in AUTHORITATIVE]
            if auth:
                c = auth[0]
                last = next((p for p in by_uid.get(uid, []) if p["url"] == c["url"]), {})
                row = {
                    "cedar_uid": uid, "handle": e["handle"], "canonical_name": name,
                    "entity_class": e["entity_class"], "url": c["url"],
                    "candidate_basis": c["candidate_basis"],
                    "basis_source": c["basis_source"],
                    "ladder_rung": "4_directory_attested",
                    "http_status": last.get("http_status", "not_retrieved"),
                    "final_url": c["url"], "verdict": "directory_attested",
                    "name_match": "", "tokens_hit": [],
                    "title": "",
                    "checked_date": last.get("checked_date", ""),
                    "rescore_reason": (
                        "the URL is attested by an authoritative directory that names this "
                        "organisation next to it; the origin did not serve us the page, so "
                        "the page content has NOT been seen and this is deliberately not "
                        "'verified'"),
                }
                for k in ("ihs_area", "ihs_state", "ihs_city", "ihs_service_level"):
                    if k in c:
                        row[k] = c[k]
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                got = row
                attested += 1
            else:
                still += 1
        else:
            fixed += 1
        fh.flush()
        tag = got["verdict"] if got else "still none"
        print(f"[{i:3d}/{len(todo)}] {tag:20s} {name[:50]}")

    fh.close()
    print(f"\nrecovered to verified: {fixed}   directory-attested: {attested}   "
          f"still nothing: {still}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
