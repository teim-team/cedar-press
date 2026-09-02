#!/usr/bin/env python3
"""
32a_fetch_gaming_nepa_pilot.py -- Cedar Press Gaming dataset, Phase 2 Step A.

Retrieves the two PILOT NEPA document sets named in GAMING_DATASET_PLAN.md
phasing step 2 into data/raw/external/gaming_nepa/:

  1. Osage Nation Lake Ozark Casino Resort Project   (clean single-document test)
  2. Menominee Kenosha Casino Project                (stress test: EA + 16 appendices)

URLs come from data/clean/gaming_land_decisions.csv (Phase 1); nothing is
guessed. Fetch posture: bia.gov robots.txt archived in Phase 1 permits /as-ia/*;
these are /sites/default/files/media_document/* PDFs served from the same host.

Nothing is parsed here. This step only retrieves bytes and records provenance
(URL, bytes, SHA-256, page count, retrieved date).
"""
import os, io, csv, sys, time, hashlib, datetime
import urllib.request
from pathlib import Path

BASE = str(Path(__file__).resolve().parent.parent)
EXT  = os.path.join(BASE, "data", "raw", "external", "gaming_nepa")
LOG  = os.path.join(BASE, "logs", "32_gaming_nepa_pilot.log")
os.makedirs(EXT, exist_ok=True)
os.makedirs(os.path.join(EXT, "osage_lake_ozark"), exist_ok=True)
os.makedirs(os.path.join(EXT, "menominee_kenosha"), exist_ok=True)

FETCHED = datetime.date.today().isoformat()
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) CedarPress-research/1.0 "
      "(elijahsamsonmoreno@gmail.com)")

buf = io.StringIO()
def log(*a):
    s = " ".join(str(x) for x in a)
    print(s); buf.write(s + "\n")

# ---------------------------------------------------------------- targets ----
# Read straight out of the Phase 1 decision index so the URL provenance chain
# is unbroken. Two decision_ids, both status Pending.
import pandas as pd
dec = pd.read_csv(os.path.join(BASE, "data", "clean", "gaming_land_decisions.csv"),
                  dtype=str).fillna("")

PILOTS = {
    "GLD-MO-the-osage-nation-20250731": ("osage_lake_ozark", "OSAGE-LAKEOZARK"),
    "GLD-WI-menominee-indian-tribe-of-wisconsin-20260309": ("menominee_kenosha", "MENOM-KENOSHA"),
}

targets = []
for did, (subdir, project_id) in PILOTS.items():
    row = dec[dec.decision_id == did]
    if row.empty:
        log(f"FATAL: decision_id {did} not in gaming_land_decisions.csv")
        sys.exit(1)
    row = row.iloc[0]
    urls   = str(row["document_urls"]).split("|")
    labels = str(row["document_labels"]).split("|")
    types  = str(row["document_types"]).split("|")
    if not (len(urls) == len(labels) == len(types)):
        log(f"WARN {did}: url/label/type counts differ "
            f"({len(urls)}/{len(labels)}/{len(types)}) -- labels aligned by index, "
            f"surplus left blank")
    for i, u in enumerate(urls):
        u = u.strip()
        if not u:
            continue
        targets.append(dict(
            project_id=project_id, decision_id=did, subdir=subdir,
            url=u,
            local_file=os.path.basename(u.split("?")[0]),
            document_label=labels[i] if i < len(labels) else "",
            document_type=types[i] if i < len(types) else "",
        ))
    # also archive the BIA project page itself (document-listing page)
    ppu = str(row["project_page_url"]).strip()
    if ppu:
        targets.append(dict(
            project_id=project_id, decision_id=did, subdir=subdir, url=ppu,
            local_file=f"_bia_project_page_{project_id.lower()}.html",
            document_label="BIA project page (document listing)",
            document_type="bia_project_page",
        ))

log(f"{len(targets)} documents queued across {len(PILOTS)} pilot projects")

# ------------------------------------------------------------------ fetch ----
def fetch(url, dest):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/pdf,text/html,*/*",
    })
    with urllib.request.urlopen(req, timeout=300) as r:
        body = r.read()
        code = r.status
        ctype = r.headers.get("Content-Type", "")
    open(dest, "wb").write(body)
    return body, code, ctype

def page_count(path):
    """Page count via pypdf; returns (n_pages, note)."""
    try:
        from pypdf import PdfReader
        return len(PdfReader(path).pages), ""
    except Exception as e:
        return "", f"page_count_failed: {str(e)[:120]}"

rows = []
for t in targets:
    dest = os.path.join(EXT, t["subdir"], t["local_file"])
    t0 = time.time()
    try:
        body, code, ctype = fetch(t["url"], dest)
    except Exception as e:
        log(f"FAIL {t['local_file']}: {e}")
        # curl fallback with declared UA (the sec.gov pattern)
        rc = os.system(f'curl -sS -L -A "{UA}" -o "{dest}" "{t["url"]}"')
        if rc != 0 or not os.path.exists(dest) or os.path.getsize(dest) == 0:
            rows.append(dict(t, http_status="ERROR", bytes=0, sha256="",
                             content_type="", pages="", fetched_date=FETCHED,
                             note=f"urllib+curl both failed: {str(e)[:150]}"))
            continue
        body = open(dest, "rb").read(); code = "200 (curl fallback)"; ctype = ""
        log(f"  recovered via curl: {t['local_file']}")

    sha = hashlib.sha256(body).hexdigest()
    npg, note = ("", "")
    if t["local_file"].lower().endswith(".pdf"):
        npg, note = page_count(dest)
    log(f"OK   {t['local_file']:<62} HTTP {code}  {len(body):>10,} B  "
        f"{npg or '-':>4} pp  {time.time()-t0:5.1f}s")
    rows.append(dict(t, http_status=code, bytes=len(body), sha256=sha,
                     content_type=ctype, pages=npg, fetched_date=FETCHED,
                     note=note))
    time.sleep(1.0)   # courtesy pacing

# --------------------------------------------------------------- manifest ----
cols = ["project_id", "decision_id", "subdir", "local_file", "source_url",
        "document_label", "document_type", "http_status", "bytes", "sha256",
        "content_type", "pages", "fetched_date", "note"]
man = os.path.join(EXT, "_SOURCE_MANIFEST.csv")
with open(man, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in rows:
        r = dict(r); r["source_url"] = r.pop("url")
        w.writerow({c: r.get(c, "") for c in cols})

ok = sum(1 for r in rows if r["http_status"] != "ERROR")
tot_b = sum(r["bytes"] for r in rows)
tot_p = sum(int(r["pages"]) for r in rows if str(r["pages"]).isdigit())
log(f"\nmanifest: {man}")
log(f"{ok}/{len(rows)} retrieved, {tot_b:,} bytes, {tot_p:,} PDF pages total")

with open(LOG, "a", encoding="utf-8") as f:
    f.write(f"\n===== 32a_fetch_gaming_nepa_pilot.py  {datetime.datetime.now()} =====\n")
    f.write(buf.getvalue())
