# -*- coding: utf-8 -*-
# ORDERING, WRITTEN DOWN BY A PERSON (class 6). `ancsa_filings_index.csv` has two
# writers and they are NOT interchangeable:
#     1. build_manifest_index.py (this file) opens it "w" from the v1 portal
#        harvest - every row lands with downloaded=no/yes as of 2026-08-05
#     2. ancsa_v2/update_index.py reads it back, takes its own .bak_*_v2 backup,
#        and flips `downloaded`, `retrieved_date`, `local_file`, `bytes` and
#        `sha256` IN PLACE from the v2 manifest
# So update_index.py runs LAST, and re-running this file alone reverts every v2
# download it recorded. Both are one-shot 2026-08-05 harvest scripts and neither
# is in a build plan; the pairing was invisible until the D1 sweep replaced the
# opaque absolute-path literal with a composed path the io scanner can read.
# lint-ok: class6 - ordering declared above; ancsa_v2/update_index.py is the
# enricher and runs last. Re-run 1 then 2, never 1 alone.
"""Builds:
   data/raw/external/ancsa_portal/_SOURCE_MANIFEST.csv
   data/clean/ancsa_filings_index.csv
"""
import csv, json, os, re, unicodedata
from pathlib import Path

RAW = str(Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "external" / "ancsa_portal")
ROSTER = str(Path(__file__).resolve().parent.parent.parent / "data" / "clean" / "anc_ceiling_roster.csv")
IDX_OUT = str(Path(__file__).resolve().parent.parent.parent / "data" / "clean" / "ancsa_filings_index.csv")
MAN_OUT = os.path.join(RAW, "_SOURCE_MANIFEST.csv")
TODAY = "2026-08-05"
VIEW = "https://portal.akdbsstar.us/StarWebPortal/ViewFile.aspx?Id="

# ---------- corporation -> anc_id ----------
def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("\u2019", "'").lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    stop = {"inc", "incorporated", "corporation", "corp", "company", "co", "limited",
            "ltd", "llc", "the", "native", "natives", "of"}
    return " ".join(t for t in s.split() if t and t not in stop)

roster = list(csv.DictReader(open(ROSTER, encoding="utf-8-sig")))
rmap = {}
for r in roster:
    rmap.setdefault(norm(r["corporation_name"]), r)

corps = json.load(open("corps.json"))
# Hand-verified overrides: the roster carries a parenthetical alias that the token
# normaliser cannot strip. Each was checked name-by-name against the roster row.
OVERRIDE = {
    "NANA Regional Corporation, Inc.": "NANA (NANA Regional Corporation, Inc.)",
    "K'oyitl'ots'ina, Limited": "K’oyitl’ots’ina, Ltd. (K Corp)",
    "Tanadgusix Corporation": "Tanadgusix Corporation (TDX)",
}
rbyname = {r["corporation_name"]: r for r in roster}
CORP2ID, CORP2CLASS, CORP2ROSTER = {}, {}, {}
for c in corps:
    hit = rbyname.get(OVERRIDE[c]) if c in OVERRIDE else rmap.get(norm(c))
    if hit:
        CORP2ID[c] = hit["anc_id"]
        CORP2CLASS[c] = hit["anc_class"]
        CORP2ROSTER[c] = hit["corporation_name"]
    else:
        CORP2ID[c] = ""
        CORP2CLASS[c] = ""
        CORP2ROSTER[c] = ""

# ---------- downloaded docs ----------
dl = {k: v for k, v in json.load(open("download_log.json")).items() if v.get("status") == "ok"}

# ---------- index rows ----------
rows = list(csv.DictReader(open("index_rows.csv", encoding="utf-8")))
byid = {}
for r in rows:
    did = r["doc_id"]
    if not did:
        continue
    e = byid.setdefault(did, {"corps": set(), "desc": r["desc"], "year": r["year"],
                              "category": r["category"]})
    e["corps"].add(r["corp"])

# verbatim date token embedded in the Division's document description
DATE_TOK = re.compile(r"\b\d{1,2}[-./]\d{1,2}[-./]\d{2,4}\b"
                      r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s*\d{4}\b")

IDX_COLS = ["corporation_name", "anc_id", "document_type", "filing_date", "period_covered",
            "portal_url", "downloaded", "retrieved_date", "anc_class", "roster_name",
            "document_description", "description_date_token", "portal_document_id",
            "corporation_attribution", "local_file", "bytes", "sha256"]

out = []
for did, e in byid.items():
    cl = sorted(e["corps"])
    corp = "; ".join(cl)
    attribution = "portal per-corporation search" if len(cl) == 1 else \
                  ("MULTI-CORP RESULT (%d)" % len(cl) if len(cl) > 1 else "unattributed")
    d = dl.get(did, {})
    m = DATE_TOK.search(e["desc"])
    out.append({
        "corporation_name": corp,
        "anc_id": "; ".join(CORP2ID.get(c, "") for c in cl),
        "document_type": e["category"],
        "filing_date": "",   # the portal exposes NO filing date field - deliberately blank
        "period_covered": e["year"],
        "portal_url": VIEW + did,
        "downloaded": "yes" if did in dl else "no",
        "retrieved_date": TODAY,
        "anc_class": "; ".join(CORP2CLASS.get(c, "") for c in cl),
        "roster_name": "; ".join(CORP2ROSTER.get(c, "") for c in cl),
        "document_description": e["desc"],
        "description_date_token": m.group(0) if m else "",
        "portal_document_id": did,
        "corporation_attribution": attribution,
        "local_file": d.get("local_file", ""),
        "bytes": d.get("bytes", ""),
        "sha256": d.get("sha256", ""),
    })

out.sort(key=lambda r: (r["period_covered"], r["corporation_name"], r["document_description"]))
with open(IDX_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=IDX_COLS)
    w.writeheader()
    for r in out:
        w.writerow(r)
print("index rows:", len(out), "->", IDX_OUT)

# ---------- manifest ----------
MAN_COLS = ["corporation", "anc_id", "document_type", "filing_date", "period_covered", "url",
            "local_file", "bytes", "sha256", "retrieved_date", "content_type", "document_description",
            "description_date_token", "portal_document_id", "text_extractable"]
hits = json.load(open("scan_hits.json")) if os.path.exists("scan_hits.json") else {}
man = []
for did, v in dl.items():
    e = byid.get(did)
    cl = sorted(e["corps"]) if e else []
    corp = "; ".join(cl) if cl else v.get("corp_guess", "")
    m = DATE_TOK.search(v.get("desc", ""))
    h = hits.get(v["local_file"], {})
    man.append({
        "corporation": corp,
        "anc_id": "; ".join(CORP2ID.get(c, "") for c in cl),
        "document_type": e["category"] if e else "ANCSA Annual Report",
        "filing_date": "",
        "period_covered": v.get("year", ""),
        "url": v["url"], "local_file": v["local_file"], "bytes": v["bytes"], "sha256": v["sha256"],
        "retrieved_date": v.get("retrieved", TODAY), "content_type": v.get("content_type", ""),
        "document_description": v.get("desc", ""),
        "description_date_token": m.group(0) if m else "",
        "portal_document_id": did,
        "text_extractable": ("no_image_only" if h.get("chars", 0) < 5000 else "yes") if h else "",
    })
man.sort(key=lambda r: (r["period_covered"], r["corporation"], r["local_file"]))
with open(MAN_OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=MAN_COLS)
    w.writeheader()
    for r in man:
        w.writerow(r)
print("manifest rows:", len(man), "->", MAN_OUT)

# ---------- coverage stats ----------
done = json.load(open("index_done.json"))
corps_with_docs = sorted({r["corp"] for r in rows})
stats = {
    "index_cells_run": len(done),
    "documents_indexed": len(out),
    "documents_downloaded": len(man),
    "portal_corporations": len(corps),
    "portal_corps_with_documents": len(corps_with_docs),
    "roster_total": len(roster),
    "roster_matched": sum(1 for c in corps if CORP2ID[c]),
}
json.dump(stats, open("coverage_stats.json", "w"), indent=1)
print(stats)
