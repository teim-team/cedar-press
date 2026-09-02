#!/usr/bin/env python3
"""
Cedar Press - SHARD F, step 4: probe every candidate and VERIFY it.

A 200 is not evidence that a domain belongs to an organisation. Parked pages,
squatters and unrelated businesses all return 200. So every fetched page is
scored against the organisation's own name tokens and the outcome is one of:

    verified      the page's title or body carries the organisation's name
    weak          some tokens hit but not enough to claim it
    wrong_site    200, and the organisation is not named anywhere on the page
    <status>      whatever the host actually said (404, 403, timeout, ...)

Only `verified` rows become a website in the web map. `weak` and `wrong_site`
are kept in the probe log so the negative result is recoverable and so nobody
re-guesses the same domain next quarter.

BROKEN-SOURCE LADDER (docs rung order, recorded per row in `ladder_rung`):
    1 origin          the candidate URL itself
    2 wayback         web.archive.org, for a host that is down or gone
Later rungs (990 corpus, social, news) are handled by the EIN and roster steps,
not here, because they answer different questions than "what is the site".

Outputs:
    data/staging/tribe_harvest/shard_f/_probe_results.jsonl   every attempt
    data/staging/tribe_harvest/shard_f/_resolved_sites.json   the winner per entity
"""
import json, os, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shard_f_fetch as F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f")
CAND = os.path.join(SH, "_candidates.json")
PROBE = os.path.join(SH, "_probe_results.jsonl")
RESOLVED = os.path.join(SH, "_resolved_sites.json")

PARKED = re.compile(
    r"domain (is )?for sale|buy this domain|parked (free )?(by|at)|godaddy\.com/domainsearch"
    r"|this domain (may be|is) for sale|hugedomains|sedoparking|namecheap parked",
    re.I,
)


def score(text, title, tokens, full_name):
    t = (title + " " + text[:12000]).lower()
    if not tokens:
        return 0.0, []
    hits = [k for k in tokens if k in t]
    s = len(hits) / len(tokens)
    if full_name.lower() in t:
        s = 1.0
    return s, hits


def verdict(rec, tokens, full_name):
    if rec["http_status"] != 200:
        return str(rec["http_status"]), 0.0, []
    h = F.read_raw(rec)
    if not h:
        return "empty_body", 0.0, []
    text = F.to_text(h)
    title = F.title_of(h)
    if PARKED.search(text[:4000]):
        return "parked_domain", 0.0, []
    s, hits = score(text, title, tokens, full_name)
    if s >= 0.6:
        v = "verified"
    elif s >= 0.3:
        v = "weak"
    else:
        v = "wrong_site"
    return v, round(s, 2), hits


def main():
    ents = json.load(open(CAND, encoding="utf-8"))
    fh = open(PROBE, "a", encoding="utf-8")
    resolved = {}
    n_ver = n_none = 0

    for i, e in enumerate(ents, 1):
        tokens = e["name_tokens"]
        best = None
        for c in e["candidates"]:
            rec = F.fetch(c["url"])
            v, s, hits = verdict(rec, tokens, e["canonical_name"])
            row = {
                "cedar_uid": e["cedar_uid"],
                "handle": e["handle"],
                "canonical_name": e["canonical_name"],
                "entity_class": e["entity_class"],
                "url": c["url"],
                "candidate_basis": c["candidate_basis"],
                "basis_source": c["basis_source"],
                "ladder_rung": "1_origin",
                "http_status": rec["http_status"],
                "final_url": rec.get("final_url"),
                "robots_note": rec.get("robots_note"),
                "failure_shape": rec.get("failure_shape"),
                "raw_file": rec.get("raw_file"),
                "verdict": v,
                "name_match": s,
                "tokens_hit": hits,
                "title": F.title_of(F.read_raw(rec))[:180] if rec.get("raw_file") else "",
                "checked_date": rec["checked_date"],
            }
            for k in ("ihs_area", "ihs_state", "ihs_city", "ihs_service_level"):
                if k in c:
                    row[k] = c[k]
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            if v == "verified" and (best is None or s > best["name_match"]):
                best = row
            if v == "verified" and s >= 0.99:
                break

        # ---- rung 2: Wayback, only for entities where nothing origin-side worked
        if best is None and e["candidates"]:
            for c in e["candidates"][:2]:
                wb = "https://web.archive.org/web/2024/" + c["url"]
                rec = F.fetch(wb)
                v, s, hits = verdict(rec, tokens, e["canonical_name"])
                row = {
                    "cedar_uid": e["cedar_uid"], "handle": e["handle"],
                    "canonical_name": e["canonical_name"],
                    "entity_class": e["entity_class"],
                    "url": wb, "candidate_basis": c["candidate_basis"] + "+wayback",
                    "basis_source": c["url"], "ladder_rung": "2_wayback",
                    "http_status": rec["http_status"], "final_url": rec.get("final_url"),
                    "robots_note": rec.get("robots_note"),
                    "failure_shape": rec.get("failure_shape"),
                    "raw_file": rec.get("raw_file"), "verdict": v,
                    "name_match": s, "tokens_hit": hits,
                    "title": F.title_of(F.read_raw(rec))[:180] if rec.get("raw_file") else "",
                    "checked_date": rec["checked_date"],
                }
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                fh.flush()
                if v == "verified":
                    best = row
                    break

        if best:
            resolved[e["cedar_uid"]] = best
            n_ver += 1
        else:
            n_none += 1
        print(f"[{i:3d}/{len(ents)}] {'OK ' if best else '-- '} "
              f"{e['canonical_name'][:52]:52s} "
              f"{(best['final_url'] if best else '')}")

    fh.close()
    json.dump(resolved, open(RESOLVED, "w", encoding="utf-8"), indent=1)
    print(f"\nverified site: {n_ver}   no verified site: {n_none}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
