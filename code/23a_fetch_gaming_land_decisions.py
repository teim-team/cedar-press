#!/usr/bin/env python3
"""
23a_fetch_gaming_land_decisions.py -- Cedar Press Gaming dataset, Phase 1 Step A.

Archives the BIA Office of Indian Gaming "Gaming Land Decisions" index and its
companion "Pending" list into data/raw/external/gaming/ so that every later
stage builds from a LOCAL copy (Cedar Press self-containment rule).

Fetch posture: bia.gov robots.txt (retrieved with this run) allows /as-ia/*.
The Drupal view exposes items_per_page=All, so the whole index comes back in a
single server-rendered request -- no pagination walk, no JS.

Nothing is parsed here. This step only retrieves bytes and records provenance.
"""
import os, csv, io, sys, time, hashlib, datetime
import urllib.request

BASE = r"C:\Users\esm247\Desktop\Cedar Press"
EXT  = os.path.join(BASE, "data", "raw", "external", "gaming")
RAW  = os.path.join(EXT, "bia_gaming_land_decisions")
os.makedirs(RAW, exist_ok=True)

FETCHED = datetime.date(2026, 8, 5).isoformat()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CedarPress-research/1.0 (elijahsamsonmoreno@gmail.com)"

buf = io.StringIO()
def log(*a):
    s = " ".join(str(x) for x in a); print(s); buf.write(s + "\n")

TARGETS = [
    # (local filename, url, description)
    ("robots.txt", "https://www.bia.gov/robots.txt",
     "bia.gov robots.txt at time of fetch (fetch-permission evidence)"),
    ("gaming_land_decisions_all.html",
     "https://www.bia.gov/as-ia/oig/gaming-land-decisions"
     "?field_decision_type_value=All&field_legal_theory_decisions_value=All"
     "&field_bogs_federally_recognized_target_id_selective=All"
     "&field_us_state_s__value_selective=All&items_per_page=All",
     "BIA Gaming Land Decisions index, all facets = All, items_per_page=All"),
    ("gaming_land_decisions_pending_all.html",
     "https://www.bia.gov/as-ia/oig/gaming-land-decisions/pending"
     "?items_per_page=All",
     "BIA Gaming Land Decisions -- Pending list, items_per_page=All"),
    ("gaming_land_decisions_default.html",
     "https://www.bia.gov/as-ia/oig/gaming-land-decisions",
     "BIA Gaming Land Decisions index, default view (25/page) -- facet vocabulary source"),
    ("gaming_land_decisions_pending_default.html",
     "https://www.bia.gov/as-ia/oig/gaming-land-decisions/pending",
     "BIA Gaming Land Decisions Pending, default view -- facet vocabulary source"),
]

rows = []
for fname, url, desc in TARGETS:
    dest = os.path.join(RAW, fname)
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "text/html,*/*"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read()
            code = r.status
    except Exception as e:
        log(f"FAIL {fname}: {e}")
        rows.append(dict(local_file=fname, source_url=url, description=desc,
                         http_status="ERROR", bytes=0, sha256="",
                         fetched_date=FETCHED, note=str(e)[:200]))
        continue
    open(dest, "wb").write(body)
    h = hashlib.sha256(body).hexdigest()
    log(f"OK   {fname}  HTTP {code}  {len(body):,} bytes  {time.time()-t0:.1f}s")
    rows.append(dict(local_file=fname, source_url=url, description=desc,
                     http_status=code, bytes=len(body), sha256=h,
                     fetched_date=FETCHED, note=""))
    time.sleep(1.0)          # courtesy rate limit

# ---------------------------------------------------------------------------
# Phase 2: the 5 "Pending" rows carry no document list in the index -- their
# Title cell is a link to an individual BIA project page. Those pages are index
# pages (document listings), not NEPA documents, so fetching them is inside
# Phase 1 scope: it supplies document_urls for exactly the rows the index leaves
# empty. NEPA documents themselves are NOT downloaded or parsed here.
# ---------------------------------------------------------------------------
import re, html as _html
idx_path = os.path.join(RAW, "gaming_land_decisions_all.html")
proj = []
if os.path.exists(idx_path):
    _h = open(idx_path, encoding="utf-8").read()
    _b = _h[_h.find("<tbody"):_h.find("</tbody>")]
    proj = sorted(set(re.findall(r'<h3><a href="(/as-ia/oig/gaming-decisions/[^"]+)"', _b)))
log(f"\nindividual project pages linked from the index: {len(proj)}")

def slugname(u):
    return "project_" + u.rstrip("/").rsplit("/", 1)[-1][:80] + ".html"

for path in proj:
    url = "https://www.bia.gov" + path
    fname = slugname(path)
    dest = os.path.join(RAW, fname)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = r.read(); code = r.status
    except Exception as e:
        log(f"FAIL {fname}: {e}")
        rows.append(dict(local_file=fname, source_url=url,
                         description="BIA individual gaming-decision project page (Pending row)",
                         http_status="ERROR", bytes=0, sha256="",
                         fetched_date=FETCHED, note=str(e)[:200]))
        continue
    open(dest, "wb").write(body)
    log(f"OK   {fname}  HTTP {code}  {len(body):,} bytes")
    rows.append(dict(local_file=fname, source_url=url,
                     description="BIA individual gaming-decision project page (Pending row)",
                     http_status=code, bytes=len(body),
                     sha256=hashlib.sha256(body).hexdigest(),
                     fetched_date=FETCHED, note=""))
    time.sleep(1.0)

MAN = os.path.join(EXT, "_SOURCE_MANIFEST.csv")
FIELDS = ["local_file", "source_url", "description", "http_status", "bytes",
          "sha256", "fetched_date", "note"]
existing = []
if os.path.exists(MAN):
    existing = [r for r in csv.DictReader(open(MAN, encoding="utf-8"))
                if r.get("local_file") not in {x["local_file"] for x in rows}]
with open(MAN, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
    w.writeheader()
    for r in existing + rows:
        w.writerow(r)
log(f"\nmanifest rows written: {len(existing) + len(rows)} -> {MAN}")

with open(os.path.join(BASE, "logs", "23_gaming_2026-08-05.log"), "a",
          encoding="utf-8") as fh:
    fh.write("\n\n" + "=" * 78 + "\n23a_fetch_gaming_land_decisions.py\n"
             + "=" * 78 + "\n" + buf.getvalue())
