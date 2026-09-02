"""SHARD-E: run the docs/HIDDEN_DATA_TECHNIQUES.md checklist over the HTML this
shard ALREADY fetched. ZERO NEW REQUESTS.

A rendered page is a lossy view of the data behind it. For ANC corporate sites
the payoff is specific:

  * `<script type="application/ld+json">` Organization markup carries
    `parentOrganization` / `subOrganization` -- literally the ownership edge in
    structured form, asserted by the parent.
  * `__NEXT_DATA__` / `__NUXT__` / `window.__INITIAL_STATE__` routinely ship the
    COMPLETE unpaginated subsidiary collection the tiles render a slice of, with
    fields the template never shows.
  * `data-*` attributes, hidden inputs, `<select>` options and HTML comments hold
    the taxonomy and, sometimes, entries dropped from the visible list.

Writes data/staging/tribe_harvest/shard_e/_hidden_data.jsonl -- one record per
page, naming the technique that fired and what it yielded. Edges found this way
still go through 533's spec and its verbatim guard; this script only reports what
is there.

BOUNDARY (docs/HIDDEN_DATA_TECHNIQUES.md): this reads bytes already served to an
anonymous visitor and stored on disk. It requests nothing, and touches no admin,
staging, login-gated or robots-disallowed path.
"""
from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
H = ROOT / "data" / "staging" / "tribe_harvest" / "shard_e"
RAW = H / "raw"
OUT = H / "_hidden_data.jsonl"

STATE_KEYS = ("__NEXT_DATA__", "__NUXT__", "__INITIAL_STATE__", "__APOLLO_STATE__",
              "wpApiSettings", "page-data.json", "algolia")
OWNERSHIP_KEYS = ("parentOrganization", "subOrganization", "brand", "department",
                  "memberOf", "owns", "subsidiar", "parent_id", "parentId")


def jsonld(h):
    out = []
    for m in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            h, re.S | re.I):
        try:
            out.append(json.loads(m.group(1).strip()))
        except Exception:
            out.append({"_unparsed": m.group(1).strip()[:400]})
    return out


def walk_ids(o, acc):
    """schema.org `identifier` PropertyValue pairs. Emmonak Corporation publishes
    its SAM UEI and CAGE code here and nowhere on the visible page -- an
    identifier handed over by the entity itself, which is worth far more to the
    identifier graph than any name."""
    if isinstance(o, dict):
        if o.get("@type") == "PropertyValue" and o.get("propertyID"):
            acc.append((str(o["propertyID"]), str(o.get("value", ""))))
        for v in o.values():
            walk_ids(v, acc)
    elif isinstance(o, list):
        for v in o:
            walk_ids(v, acc)


def walk_orgs(o, acc, key):
    if isinstance(o, dict):
        if key in o:
            v = o[key]
            for x in (v if isinstance(v, list) else [v]):
                if isinstance(x, dict) and x.get("name"):
                    acc.append(str(x["name"]))
                elif isinstance(x, str):
                    acc.append(x)
        for v in o.values():
            walk_orgs(v, acc, key)
    elif isinstance(o, list):
        for v in o:
            walk_orgs(v, acc, key)


def walk_types(o, acc):
    if isinstance(o, dict):
        t = o.get("@type")
        if t:
            acc.append(t if isinstance(t, str) else "/".join(map(str, t)))
        for v in o.values():
            walk_types(v, acc)
    elif isinstance(o, list):
        for v in o:
            walk_types(v, acc)


def main():
    probes = {}
    for line in (H / "_probe_results.jsonl").open(encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("raw_file", "").endswith(".html"):
            probes[r["raw_file"]] = r

    recs, hit_ld, hit_state, hit_own = 0, 0, 0, 0
    with OUT.open("w", encoding="utf-8") as f:
        for rf, r in sorted(probes.items()):
            p = RAW / rf
            if not p.exists():
                continue
            h = p.read_text(encoding="utf-8", errors="replace")
            rec = {"url": r["url"], "canonical_name": r.get("canonical_name"),
                   "cedar_uid": r.get("cedar_uid"), "raw_file": rf,
                   "techniques_fired": []}

            ld = jsonld(h)
            if ld:
                types = []
                walk_types(ld, types)
                own = sorted({k for k in OWNERSHIP_KEYS if k in json.dumps(ld)})
                rec["jsonld_types"] = sorted(set(types))[:20]
                rec["jsonld_ownership_keys"] = own
                rec["jsonld_sample"] = json.dumps(ld, ensure_ascii=False)[:1200]
                rec["techniques_fired"].append("ld+json")
                hit_ld += 1
                if own:
                    hit_own += 1
                ids = []
                walk_ids(ld, ids)
                if ids:
                    rec["published_identifiers"] = [{"type": a, "value": b}
                                                    for a, b in ids][:20]
                    rec["techniques_fired"].append("ld+json published identifiers")
                subs, pars = [], []
                walk_orgs(ld, subs, "subOrganization")
                walk_orgs(ld, pars, "parentOrganization")
                if subs:
                    rec["jsonld_subOrganization"] = sorted(set(subs))[:40]
                if pars:
                    rec["jsonld_parentOrganization"] = sorted(set(pars))[:10]

            st = [k for k in STATE_KEYS if k in h]
            if st:
                rec["embedded_state_keys"] = st
                rec["techniques_fired"].append("embedded application state")
                hit_state += 1
                m = re.search(r'id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', h, re.S)
                if m:
                    rec["next_data_bytes"] = len(m.group(1))
                    blob = m.group(1)
                    rec["next_data_ownership_keys"] = sorted(
                        {k for k in OWNERSHIP_KEYS if k in blob})
                    rec["next_data_head"] = blob[:800]

            # generator / platform, which decides whether wp-json is worth a probe
            g = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)',
                          h, re.I)
            if g:
                rec["generator"] = g.group(1)[:80]
            rec["wordpress"] = bool(re.search(r"/wp-(content|includes|json)/", h))
            if re.search(r'<link[^>]+rel=["\']https://api\.w\.org/["\']', h):
                rec["wp_json_link_advertised"] = True
                rec["techniques_fired"].append("wp-json advertised in <link>")

            sel = re.findall(r"<select[^>]*>(.*?)</select>", h, re.S | re.I)
            opts = []
            for s in sel:
                opts += [re.sub(r"\s+", " ", x).strip()
                         for x in re.findall(r"<option[^>]*>(.*?)</option>", s, re.S | re.I)]
            if len(opts) >= 5:
                rec["select_option_vocabulary"] = opts[:60]
                rec["techniques_fired"].append("select/filter vocabulary")

            comments = re.findall(r"<!--(.*?)-->", h, re.S)
            long_c = [re.sub(r"\s+", " ", c).strip()[:300] for c in comments
                      if len(c.strip()) > 120 and "[if" not in c]
            if long_c:
                rec["html_comments"] = long_c[:6]
                rec["techniques_fired"].append("html comments")

            datas = re.findall(r'\sdata-([a-z0-9_-]{3,30})=', h, re.I)
            if datas:
                from collections import Counter
                rec["data_attributes"] = [k for k, _ in Counter(datas).most_common(20)]

            if rec["techniques_fired"] or rec.get("data_attributes"):
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                recs += 1

    print("pages examined", len(probes), "| records", recs,
          "| ld+json", hit_ld, "| embedded state", hit_state,
          "| ld+json carrying an ownership key", hit_own)
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
