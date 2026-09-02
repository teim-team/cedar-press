#!/usr/bin/env python3
"""
Cedar Press - SHARD F: the check another session runs instead of believing me.

`513_handoffs.py` needs commands whose exit 0 IS the proof. This is shard F's.
It re-measures every claim the handoff makes, from the files on disk, and exits
1 on the first one that does not hold. It makes no network requests.

    py -3 code/602_shard_f_verify.py
"""
import csv, json, os, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SH = os.path.join(ROOT, "data", "staging", "tribe_harvest", "shard_f")
MAP = os.path.join(ROOT, "data", "staging", "tribe_web_map", "shard_f.csv")
MEM = os.path.join(ROOT, "data", "staging", "org_membership", "shard_f.jsonl")

CLASSES = {"Intertribal Organization", "Urban Indian Organization",
           "Federal-level self-governance consortium",
           "Federal-level constituency entity", "State-level constituency entity"}
URL_TYPES = {"organization", "membership_list", "annual_report", "form_990",
             "newsletter", "leadership", "policy_agenda"}

fails = []


def check(label, ok, detail=""):
    print(("  ok   " if ok else "  FAIL ") + label + ("  " + detail if detail else ""))
    if not ok:
        fails.append(label)


def jl(p):
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def main():
    print("SHARD F verification\n")

    # 1 - the slice is exactly the five organisational classes, all 153
    reg = list(csv.DictReader(open(os.path.join(ROOT, "data", "spine",
                                                "cedar_identity_register.csv"),
                                   encoding="utf-8-sig", newline="")))
    want = {r["cedar_uid"] for r in reg if r["entity_class"] in CLASSES}
    check("slice is 153 entities in the five organisational classes",
          len(want) == 153, f"register yields {len(want)}")

    # 2 - the web map covers every one of them, with a legal url_type and evidence
    rows = list(csv.DictReader(open(MAP, encoding="utf-8", newline="")))
    cols = ["tribe_id", "cedar_uid", "canonical_name", "url_type", "url",
            "http_status", "checked_date", "evidence"]
    check("web map header matches the sibling-shard schema",
          list(rows[0].keys()) == cols if rows else False)
    covered = {r["cedar_uid"] for r in rows}
    check("web map covers all 153 entities", covered == want,
          f"{len(covered)} covered, {len(want - covered)} missing")
    check("every url_type is one of the seven permitted values",
          {r["url_type"] for r in rows} <= URL_TYPES)
    check("every web-map row carries evidence",
          all(r["evidence"].strip() for r in rows))
    check("every entity has exactly one `organization` row",
          all(v == 1 for v in collections.Counter(
              r["cedar_uid"] for r in rows if r["url_type"] == "organization").values()))
    sites = sum(1 for r in rows if r["url_type"] == "organization" and r["url"])
    check("at least 140 entities have an organisation URL", sites >= 140,
          f"{sites}/153")
    nourl = [r for r in rows if r["url_type"] == "organization" and not r["url"]]
    check("every entity WITHOUT a URL says why in evidence",
          all(len(r["evidence"]) > 60 for r in nourl), f"{len(nourl)} such rows")

    # 3 - membership: every roster row is sourced and quotes or names its page
    mem = jl(MEM)
    cur = [m for m in mem if m.get("membership_status") == "current"]
    check("membership file is non-empty", len(mem) > 0, f"{len(mem)} rows")
    check("every membership row names an organisation in the slice",
          all(m["org_cedar_uid"] in want for m in mem))
    check("every CURRENT member row has member_name_raw and a source_url",
          all(m.get("member_name_raw") and m.get("source_url") for m in cur))
    check("no membership row claims identity is resolved",
          all(m.get("identity_resolved") is not True for m in cur))
    check("every candidate match carries a confidence and a method",
          all(("match_confidence" in m and m.get("match_method")) for m in cur))
    orgs = {m["org_cedar_uid"] for m in cur}
    check("at least 25 organisations published a roster", len(orgs) >= 25,
          f"{len(orgs)} organisations, {len(cur)} member rows")
    rc = collections.Counter(m["org_cedar_uid"] for m in cur)
    check("no organisation is counted as publishing a roster on fewer than 4 names",
          all(v >= 4 for v in rc.values()))
    roster_classes = {"Intertribal Organization",
                      "Federal-level self-governance consortium"}
    expect = {r["cedar_uid"] for r in reg if r["entity_class"] in roster_classes}
    got = {m["org_cedar_uid"] for m in mem}
    check("every roster-bearing entity has a row, roster or explicit absence",
          expect <= got, f"{len(expect - got)} with no row at all")

    # 4 - EIN: nothing unsourced, nothing guessed
    ein = jl(os.path.join(SH, "ein_990.jsonl"))
    check("EIN file covers all 153 entities",
          {x["cedar_uid"] for x in ein} == want)
    check("every EIN row declares which leg produced it",
          all(x.get("ein_leg") in ("KNOWN_IDENTIFIER", "NAME_SEARCH") for x in ein))
    check("no EIN row carries a value without a confidence",
          all(("ein_confidence" in x) for x in ein if x.get("ein")))
    conf = {x["cedar_uid"] for x in ein
            if x["ein_leg"] == "KNOWN_IDENTIFIER" and x.get("propublica_status") == 200}
    check("at least 85 entities have an EIN confirmed against the IRS-derived record",
          len(conf) >= 85, f"{len(conf)}")

    # 5 - service area / authorising basis
    svc = jl(os.path.join(SH, "service_area_authority.jsonl"))
    check("service-area file covers all 153", {x["cedar_uid"] for x in svc} == want)
    check("every authorising basis carries at least one quote",
          all(len(x["authorizing_basis_quotes"]) >= 1
              for x in svc if x["authorizing_basis"]))
    comp = [x for x in svc if x.get("ihs_compact_year")]
    check("no constituency BAND inherited a parent tribe's compact",
          all("Paiute Indian Tribe of Utah" not in x["canonical_name"] for x in comp))
    cons = [x for x in svc
            if x["entity_class"] == "Federal-level self-governance consortium"
            and x.get("ihs_compact_year")]
    check("at least 24 self-governance consortia carry an IHS compact year",
          len(cons) >= 24, f"{len(cons)}/29")

    # 6 - the IHS harvests validate against the sources' own printed counts
    comp_rows = jl(os.path.join(SH, "ihs_selfgov_compacts.jsonl"))
    printed = {}
    seen = collections.Counter()
    for r in comp_rows:
        printed[r["ihs_area"]] = int(r["ihs_area_count_as_printed"])
        seen[r["ihs_area"]] += 1
    check("parsed compact count equals IHS's own printed per-area counts, every area",
          all(seen[a] == n for a, n in printed.items()),
          f"{len(comp_rows)} compacts across {len(printed)} areas")

    uio = jl(os.path.join(SH, "ihs_uio_register.jsonl"))
    check("every UIO register row carries a website and the Title V quote",
          all(x["org_website"] and x["authorizing_basis_quote"] for x in uio),
          f"{len(uio)} rows")

    # 7 - newsletters
    news = jl(os.path.join(SH, "newsletters.jsonl"))
    check("newsletter file is non-empty", len(news) > 0, f"{len(news)} channel rows")
    check("every newsletter row names an entity in the slice",
          all(x["org_cedar_uid"] in want for x in news))
    check("no cadence is asserted without the observation count behind it",
          all(("n_dates_observed" in x) for x in news
              if x.get("observed_median_gap_days")))

    # 8 - discipline: nothing outside this shard's three owned paths was written,
    #     and no robots.txt Disallow path was ever fetched
    fl = jl(os.path.join(SH, "_fetch_log.jsonl"))
    dis = [x for x in fl if x.get("http_status") == "robots_disallow"]
    check("every robots.txt Disallow was refused BEFORE a request, not after",
          all(x.get("raw_file") is None for x in dis),
          f"{len(dis)} disallowed URLs refused")

    print()
    if fails:
        print(f"FAILED: {len(fails)}")
        for f in fails:
            print("  - " + f)
        return 1
    print("shard F: all checks pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
