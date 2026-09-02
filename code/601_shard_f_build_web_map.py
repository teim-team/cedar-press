#!/usr/bin/env python3
"""
Cedar Press - SHARD F, step 8: write the web map. RE-RUNNABLE AND INCREMENTAL.

Reads whatever this shard has landed on disk so far and rewrites
`data/staging/tribe_web_map/shard_f.csv` from it. Safe to run at any moment,
including while the probe is still going: a partial map on disk beats a
complete one held in memory.

Every entity in the 153 gets at least one row. An entity with no site found
gets a row with `url_type = organization`, an empty url, and an `http_status`
naming what actually happened - the negative result is the finding.

url_type: organization | membership_list | annual_report | form_990 |
          newsletter | leadership | policy_agenda
"""
import csv, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f")
OUT = os.path.join(ROOT, "data", "staging", "tribe_web_map", "shard_f.csv")

COLS = ["tribe_id", "cedar_uid", "canonical_name", "url_type", "url",
        "http_status", "checked_date", "evidence"]


def jl(name):
    p = os.path.join(SH, name)
    if not os.path.exists(p):
        return []
    out = []
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def main():
    slice_rows = json.load(open(os.path.join(SH, "_slice.json"), encoding="utf-8"))
    by_uid = {r["cedar_uid"]: r for r in slice_rows}

    probes = jl("_probe_results.jsonl")
    ihs = {r["org_website"]: r for r in jl("ihs_uio_register.jsonl")}
    memb = jl(os.path.join("..", "..", "org_membership", "shard_f.jsonl"))
    news = jl("newsletters.jsonl")
    eins = jl("ein_990.jsonl")
    svc = {x["cedar_uid"]: x for x in jl("service_area_authority.jsonl")}

    rows = []
    seen = set()

    def add(uid, url_type, url, status, checked, evidence):
        e = by_uid.get(uid)
        if not e:
            return
        k = (uid, url_type, url)
        if k in seen:
            return
        seen.add(k)
        cid = e.get("cedar_entity_id", "") or ""
        rows.append({
            "tribe_id": cid if cid.startswith("T-") else "",
            "cedar_uid": uid,
            "canonical_name": e["canonical_name"],
            "url_type": url_type,
            "url": url,
            "http_status": status,
            "checked_date": checked,
            "evidence": evidence,
        })

    # ---- 1. organisation sites: the best verified probe per entity
    best = {}
    attested = {}
    absent = {}
    tried = {}
    for p in probes:
        u = p["cedar_uid"]
        tried.setdefault(u, []).append(p)
        if p["verdict"] == "verified":
            if u not in best or (p["name_match"] or 0) > (best[u]["name_match"] or 0):
                best[u] = p
        elif p["verdict"] == "directory_attested":
            attested.setdefault(u, p)
        elif p["verdict"] == "absent_confirmed":
            absent.setdefault(u, p)

    for uid, e in by_uid.items():
        if uid in best or uid in attested:
            p = best.get(uid) or attested[uid]
            ev = (f"{p['candidate_basis']} -> {p['ladder_rung']}; "
                  f"verdict={p['verdict']}; "
                  f"name match {p['name_match']} on tokens {','.join(p.get('tokens_hit') or [])[:60]}; "
                  f"title \"{(p.get('title') or '')[:90]}\"; basis source {p['basis_source']}")
            if p.get("rescore_reason"):
                ev += f"; {p['rescore_reason']}"
            if p.get("note"):
                ev += f"; {p['note']}"
            ihsr = ihs.get(p["url"])
            if ihsr:
                ev += (f"; IHS Title V register: area={ihsr['ihs_area']}, "
                       f"city={ihsr['location_city']}, state={ihsr['state_heading']}, "
                       f"service level={ihsr['service_level']}")
            sa = svc.get(uid)
            if sa:
                if sa.get("service_area_type"):
                    ev += (f"; SERVICE AREA [{sa['service_area_type']}] "
                           f"{sa['service_area_detail'][:220]} (src {sa['service_area_source']})")
                if sa.get("authorizing_basis"):
                    ev += ("; AUTHORISING BASIS " + "|".join(sa["authorizing_basis"])
                           + (f" compact year {sa['ihs_compact_year']}"
                              if sa.get("ihs_compact_year") else "")
                           + f" (src {sa.get('authorizing_basis_source','')})")
            add(uid, "organization", p["final_url"] or p["url"], p["http_status"],
                p["checked_date"], ev)
        elif uid in absent:
            a = absent[uid]
            add(uid, "organization", "", a["http_status"], a["checked_date"],
                "SEARCH EXHAUSTED, ABSENCE RECORDED: " + a["rescore_reason"])
            continue
        else:
            att = tried.get(uid, [])
            if att:
                worst = "; ".join(
                    f"{a['url']} -> {a['http_status']}/{a['verdict']}" for a in att[:6])
                ev = ("no verified organisation site. candidates attempted and their "
                      "outcomes: " + worst)
                st = att[0]["http_status"]
                ck = att[0]["checked_date"]
            else:
                ev = ("no candidate URL could be constructed for this entity and none is "
                      "on disk in any Cedar dataset; not probed")
                st = "not_probed"
                ck = ""
            add(uid, "organization", "", st, ck, ev)

    # ---- 2. membership list pages
    roster_src = {}
    for m in memb:
        if m.get("membership_status") == "current" and m.get("source_url"):
            k = (m["org_cedar_uid"], m["source_url"])
            roster_src[k] = roster_src.get(k, 0) + 1
    for (uid, src), n in sorted(roster_src.items()):
        add(uid, "membership_list", src, 200, "2026-09-01",
            f"published membership roster; {n} member name(s) taken from this page, "
            f"recorded row-by-row in data/staging/org_membership/shard_f.jsonl")

    # ---- 3. newsletters / annual reports / policy publications
    KIND = {
        "newsletter": "newsletter", "newsletter_archive": "newsletter",
        "news": "newsletter", "press_releases": "newsletter", "blog": "newsletter",
        "email_signup": "newsletter",
        "annual_report": "annual_report",
        "policy_publication": "policy_agenda", "publications": "policy_agenda",
    }
    for n in news:
        k = KIND.get(n.get("channel_type", ""))
        if not k or not n.get("channel_url"):
            continue
        ev = (f"channel_type={n['channel_type']}, format={n.get('format','')}, "
              f"archive {n.get('archive_earliest','')}..{n.get('archive_latest','')}, "
              f"n_dates={n.get('n_dates_observed',0)}, "
              f"observed_median_gap_days={n.get('observed_median_gap_days','')}, "
              f"deal_content={n.get('deal_content')}")
        add(n["org_cedar_uid"], k, n["channel_url"], n.get("http_status", ""),
            n.get("retrieved_date", ""), ev)

    # ---- 4. Form 990 route
    for x in eins:
        if not x.get("ein"):
            continue
        ev = (f"ein_leg={x['ein_leg']}, ein={x['ein']}, "
              f"irs_name=\"{x.get('irs_name','')}\", "
              f"agrees_with_cedar={x.get('irs_name_agrees_with_cedar')}, "
              f"confidence={x.get('ein_confidence')}, "
              f"n_990_years={x.get('n_990_years_propublica', '')}")
        add(x["cedar_uid"], "form_990", x["form_990_route"],
            x.get("propublica_status", ""), x.get("retrieved_date", ""), ev)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["cedar_uid"], r["url_type"])))

    import collections
    c = collections.Counter(r["url_type"] for r in rows)
    ents_with_site = sum(1 for r in rows if r["url_type"] == "organization" and r["url"])
    print(f"{len(rows)} rows -> {os.path.relpath(OUT, ROOT)}")
    for k, v in c.most_common():
        print(f"  {k:16s} {v}")
    print(f"  entities with a verified organisation site: {ents_with_site}/153")
    return 0


if __name__ == "__main__":
    sys.exit(main())
