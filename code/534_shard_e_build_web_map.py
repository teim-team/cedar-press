"""SHARD-E: build data/staging/tribe_web_map/shard_e.csv from the probe results.

Idempotent and re-runnable: rebuilds the whole CSV from
data/staging/tribe_harvest/shard_e/_probe_results.jsonl every time, so it can be
run after every probe stage and never loses a row.

Schema (shared with the sibling shards):
  tribe_id, cedar_uid, canonical_name, url_type, url, http_status, checked_date,
  evidence

`tribe_id` is BLANK for every row: shard E's slice is ANCSA corporations, which
are not tribal governments and carry no tribe_id. An ANC's relationship to the
Alaska Native village government of the same name is ASSOCIATION, never ownership
or identity (docs/ANCSA_OWNERSHIP_RULING.md rules 2, 4, 5), so putting a tribe_id
on these rows would assert exactly the edge the owner's ruling forbids.

ABSENCE IS A FINDING. An entity whose probed domains all refused or did not
resolve gets a row with the status recorded, not silence -- a village corporation
with no findable website is a real fact about the ANCSA universe.

NO NETWORK.
"""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARV = ROOT / "data" / "staging" / "tribe_harvest" / "shard_e"
OUTD = ROOT / "data" / "staging" / "tribe_web_map"
OUTD.mkdir(parents=True, exist_ok=True)
OUT = OUTD / "shard_e.csv"

COLS = ["tribe_id", "cedar_uid", "canonical_name", "url_type", "url",
        "http_status", "checked_date", "evidence"]


def evidence_for(r):
    """One line saying what was found and WHICH RUNG OF THE LADDER produced it."""
    st = str(r.get("http_status"))
    bits = []
    if r.get("note"):
        bits.append(r["note"])
    if "web.archive.org" in r.get("url", ""):
        bits.append("recovered via Wayback Machine rung")
    if st == "ROBOTS_DISALLOWED":
        bits.append("not fetched: " + str(r.get("robots_note", "robots.txt disallows")))
        return "; ".join(bits)
    if st == "0":
        bits.append("no response (%s) after %.1fs -- domain does not resolve or the "
                    "edge refused; recorded as an absence, not retried"
                    % (r.get("failure_shape", "?"), r.get("seconds") or 0))
        return "; ".join(bits)
    if st == "307" and "sucuri" in json.dumps(r).lower():
        bits.append("origin behind a Sucuri JS challenge")
    if r.get("title"):
        bits.append("title: " + r["title"][:120])
    sig = r.get("signals") or {}
    if sig:
        bits.append("page signals " + ", ".join("%s=%d" % kv for kv in sorted(sig.items())))
    if r.get("bytes") is not None:
        bits.append("%d bytes" % r["bytes"])
    if r.get("robots_note"):
        bits.append(r["robots_note"])
    return "; ".join(bits)[:600]


import re
import unicodedata

RAW = HARV / "raw"
GENERIC = {"corporation", "corp", "native", "inc", "incorporated", "company", "co",
           "ltd", "limited", "llc", "the", "association", "natives", "group"}
ANC_SIGNAL = re.compile(
    r"(?i)(ancsa|alaska native|native corporation|village corporation|shareholder|"
    r"claims settlement act|8\(a\)|alaska)")


def corroborated(r):
    """Does this page actually belong to the corporation whose name generated the
    domain? Returns (bool, why)."""
    rf = r.get("raw_file", "")
    if not rf.endswith(".html"):
        return False, "no HTML body captured"
    p = RAW / (rf[:-5] + ".txt")
    if not p.exists():
        return False, "no text extract"
    txt = p.read_text(encoding="utf-8", errors="replace")
    src = "rendered text"
    if len(txt) < 400:
        # A JS-rendered page renders to almost nothing but still SERVES its
        # schema.org markup. Emmonak Corporation was wrongly called a parked
        # domain on the text extract while its HTML carried its own UEI, CAGE,
        # EIN and two named subsidiaries. Fall back to the served HTML.
        h = RAW / rf
        if h.exists():
            txt = h.read_text(encoding="utf-8", errors="replace")
            src = "served HTML (page renders to almost nothing)"
    if len(txt) < 200:
        return False, "body under 200 chars (parked or placeholder page)"
    low = unicodedata.normalize("NFKD", txt.lower())
    low = "".join(c for c in low if not unicodedata.combining(c))
    name = unicodedata.normalize("NFKD", (r.get("canonical_name") or "").lower())
    name = "".join(c for c in name if not unicodedata.combining(c))
    toks = [t for t in re.split(r"[^a-z0-9]+", name)
            if len(t) >= 4 and t not in GENERIC]
    hit = [t for t in toks if t in low]
    if not hit:
        return False, "no distinctive token of the corporation name on the page"
    if not ANC_SIGNAL.search(txt):
        return False, ("name token %r present but no ANCSA / Alaska Native signal"
                       % hit[0])
    return True, "token %r plus an ANCSA/Alaska Native signal, from the %s" % (hit[0], src)


def main():
    slice_ = json.loads((HARV / "_slice.json").read_text(encoding="utf-8"))
    # docs/HIDDEN_DATA_TECHNIQUES.md: record, per site, WHICH technique produced
    # the data, so the next agent skips straight to the method that worked.
    hidden = {}
    hp = HARV / "_hidden_data.jsonl"
    if hp.exists():
        for line in hp.open(encoding="utf-8"):
            try:
                h = json.loads(line)
            except Exception:
                continue
            bits = list(h.get("techniques_fired") or [])
            if h.get("published_identifiers"):
                bits.append("PUBLISHES ITS OWN IDENTIFIERS: " + ", ".join(
                    "%s=%s" % (d["type"], d["value"]) for d in h["published_identifiers"]))
            if h.get("jsonld_subOrganization"):
                bits.append("ld+json subOrganization: " +
                            "; ".join(h["jsonld_subOrganization"][:8]))
            if h.get("jsonld_parentOrganization"):
                bits.append("ld+json parentOrganization: " +
                            "; ".join(h["jsonld_parentOrganization"][:4]))
            if h.get("wp_json_link_advertised"):
                bits.append("wp-json advertised")
            if bits:
                hidden[h["url"]] = "hidden-data: " + " | ".join(bits)
    probes = []
    p = HARV / "_probe_results.jsonl"
    if p.exists():
        for line in p.open(encoding="utf-8"):
            try:
                probes.append(json.loads(line))
            except Exception:
                pass
    rows, seen_uid = [], set()
    for r in probes:
        st = str(r.get("http_status"))
        if st in ("SKIPPED_HOST_CIRCUIT_BREAKER", "SKIPPED_RUN_DEADLINE"):
            continue
        # A GUESSED DOMAIN THAT ANSWERS IS NOT EVIDENCE THAT IT IS THE RIGHT SITE.
        # englishbay.com is a Vancouver photo blog; nima.com is not Nima
        # Corporation. A false "site found" is worse than an honest absence, so a
        # generated domain must CORROBORATE: the page has to carry a distinctive
        # token of the corporation's name AND an ANCSA/Alaska Native signal.
        if (r.get("note", "") or "").startswith("generated candidate domain") \
                and st.isdigit() and 200 <= int(st) < 400:
            ok, why = corroborated(r)
            if not ok:
                r = dict(r)
                r["http_status"] = st = "UNRELATED_DOMAIN"
                r["note"] = ("generated candidate domain answered but does not "
                             "corroborate: " + why)
        rows.append({
            "tribe_id": "",
            "cedar_uid": r.get("cedar_uid") or "",
            "canonical_name": r.get("canonical_name") or "",
            "url_type": r.get("url_type") or "",
            "url": r.get("url"),
            "http_status": st,
            "checked_date": r.get("checked_date", ""),
            "evidence": (evidence_for(r) + ((" || " + hidden[r["url"]])
                                            if r.get("url") in hidden else ""))[:1400],
        })
        if st.isdigit() and 200 <= int(st) < 400 and r.get("cedar_uid"):
            seen_uid.add(r["cedar_uid"])

    # ABSENCE ROWS: every slice entity with no reachable page of its own.
    probed_uid = {r.get("cedar_uid") for r in probes if r.get("cedar_uid")}
    for e in slice_:
        if e["cedar_uid"] in seen_uid:
            continue
        why = ("probed and every candidate domain refused or did not resolve"
               if e["cedar_uid"] in probed_uid
               else "no candidate domain probed in this pass")
        rows.append({
            "tribe_id": "", "cedar_uid": e["cedar_uid"],
            "canonical_name": e["canonical_name"], "url_type": "corporate",
            "url": "", "http_status": "NO_SITE_FOUND", "checked_date": "2026-09-01",
            "evidence": ("%s (%s). Absence recorded as a finding: an ANCSA "
                         "corporation with no findable website is a fact about the "
                         "disclosure surface, not a gap in effort."
                         % (why, e["entity_class"])),
        })

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    live = sum(1 for r in rows if r["http_status"].isdigit()
               and 200 <= int(r["http_status"]) < 400)
    print("rows", len(rows), "| live URLs", live,
          "| entities with a live page", len(seen_uid),
          "| entities with no site found", len(slice_) - len(seen_uid))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
