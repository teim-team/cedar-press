#!/usr/bin/env python3
"""
Cedar Press - SHARD F, step 5b: finalise the roster file. ZERO NETWORK, idempotent.

Three corrections, each of which changes what a count MEANS, so each is applied
explicitly and every dropped row is kept in `_membership_rejected.jsonl` with the
rule that dropped it. Nothing is deleted silently.

RULE 1 - NAVIGATION IS NOT MEMBERSHIP
    NAFOA's roster page is genuine (142 of 205 strings match Cedar's register),
    but the same page's chrome contributed `Become a Member Tribe`,
    `Community Forum` and four other calls-to-action. They are tribe-shaped and
    they are not members.

RULE 2 - FEWER THAN FOUR NAMES IS NOT A ROSTER
    Fourteen organisations yielded one to three names apiece - `Community`,
    `Tribal Enterprises`, `Nanwalek Community Building`. Those are incidental
    matches on an ordinary page, not a published membership list. Counting them
    as rosters would inflate the headline this shard exists to report. They are
    relabelled `insufficient_evidence_not_a_roster` and their rows are kept, so
    the next agent sees what was actually on the page rather than an absence.

    Four is the same floor the page-level roster test uses.

RULE 3 - AN ORGANISATION WITH NO SITE STILL NEEDS A ROW
    Eight roster-class organisations had no verified website, so step 5 never
    reached them and they were silently absent from the file. An organisation
    missing from a roster dataset is indistinguishable from one with no members.
    They get an explicit row naming why.

Output: rewrites data/staging/org_membership/shard_f.jsonl
        data/staging/tribe_harvest/shard_f/_membership_rejected.jsonl
"""
import json, os, re, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shard_f_fetch as F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f")
OUT = os.path.join(ROOT, "data", "staging", "org_membership", "shard_f.jsonl")
REJ = os.path.join(SH, "_membership_rejected.jsonl")

ROSTER_FLOOR = 4

NAV = re.compile(
    r"^(become|join|search|browse|view|see|find|meet|explore|learn|our |the )"
    r"|\b(forum|committee|certificat|leadership|intro|login|portal|directory|"
    r"membership (dues|levels|benefits|form|application)|advisory|"
    r"become a member|member benefits|member login|sign in|donate|"
    r"conference|academy|institute|scholarship|fellowship|internship|"
    r"newsletter|podcast|webinar)\b"
    r"|^(tribes|members|member tribes|tribal (enterprises|nations|governments|"
    r"communities|members)|community|communities|villages)\s*$",
    re.I)


def main():
    rows = [json.loads(l) for l in open(OUT, encoding="utf-8") if l.strip()]
    slice_rows = json.load(open(os.path.join(SH, "_slice.json"), encoding="utf-8"))
    resolved = F.load_resolved()

    kept, rejected = [], []

    # ---- RULE 1
    for r in rows:
        if r.get("membership_status") == "current" and NAV.search(r["member_name_raw"]) \
                and not r.get("candidate_cedar_uid"):
            r["_rejected_by"] = ("RULE 1 navigation-not-membership: the string is page "
                                 "chrome, matches no Cedar entity, and sits on a roster "
                                 "page only because the template put it there")
            rejected.append(r)
        else:
            kept.append(r)

    # ---- RULE 2
    cnt = collections.Counter(r["org_cedar_uid"] for r in kept
                              if r.get("membership_status") == "current")
    for r in kept:
        if r.get("membership_status") == "current" and cnt[r["org_cedar_uid"]] < ROSTER_FLOOR:
            r["membership_status"] = "insufficient_evidence_not_a_roster"
            r["note"] = (f"only {cnt[r['org_cedar_uid']]} member-shaped names were found "
                         f"for this organisation, below the {ROSTER_FLOOR}-name roster "
                         f"floor. This row records WHAT WAS ON THE PAGE; it is not "
                         f"evidence of a published membership list and must not be "
                         f"counted as one.")

    # ---- RULE 3
    ROSTER_CLASSES = {"Intertribal Organization",
                      "Federal-level self-governance consortium"}
    have = {r["org_cedar_uid"] for r in kept}
    probes = {}
    p = os.path.join(SH, "_probe_results.jsonl")
    for line in open(p, encoding="utf-8"):
        line = line.strip()
        if line:
            d = json.loads(line)
            probes.setdefault(d["cedar_uid"], []).append(d)
    added = 0
    for e in slice_rows:
        uid = e["cedar_uid"]
        if e["entity_class"] not in ROSTER_CLASSES or uid in have:
            continue
        att = probes.get(uid, [])
        why = "; ".join(f"{a['url'] or '(none)'} -> {a['http_status']}/{a['verdict']}"
                        for a in att[:5]) or "no candidate URL could be constructed"
        kept.append({
            "org_cedar_uid": uid, "org_handle": e["handle"],
            "org_name": e["canonical_name"], "org_entity_class": e["entity_class"],
            "org_website": "", "as_of_date": "2026-09-01", "retrieved_date": "2026-09-01",
            "member_name_raw": "", "member_type": "",
            "membership_status": "no_website_so_no_roster_reachable",
            "source_url": "", "technique": "", "quote": "",
            "note": ("this organisation is in the roster-bearing classes but shard F "
                     "found no verified website, so no roster could be sought. "
                     "Probe outcomes: " + why),
        })
        added += 1

    with open(OUT, "w", encoding="utf-8") as fh:
        for r in kept:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(REJ, "w", encoding="utf-8") as fh:
        for r in rejected:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    st = collections.Counter(r["membership_status"] for r in kept)
    orgs_roster = len({r["org_cedar_uid"] for r in kept
                       if r["membership_status"] == "current"})
    mem = sum(1 for r in kept if r["membership_status"] == "current")
    matched = sum(1 for r in kept if r["membership_status"] == "current"
                  and r.get("candidate_cedar_uid"))
    print(f"rows: {len(kept)}  (rejected by rule 1: {len(rejected)}; "
          f"no-site rows added by rule 3: {added})")
    for k, v in st.most_common():
        print(f"  {k:42s} {v}")
    print(f"\nORGANISATIONS PUBLISHING A ROSTER: {orgs_roster}")
    print(f"MEMBER ROWS: {mem}   with a Cedar candidate: {matched} "
          f"({matched / mem:.0%})" if mem else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
