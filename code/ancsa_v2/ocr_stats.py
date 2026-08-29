# -*- coding: utf-8 -*-
"""Summarise OCR yield for both runs."""
import json, os, csv
from pathlib import Path
ROOT = str(Path(__file__).resolve().parent.parent.parent)


def stats(ocr_dir, raw_dir, manifest, key_extractable=None):
    pages = os.path.join(ocr_dir, "pages")
    scan = {x["file"]: x for x in json.load(open(os.path.join(ocr_dir, "text_scan.json")))}
    done, att_pages, rec_pages, chars = 0, 0, 0, 0
    empties = []
    for f in sorted(os.listdir(pages)):
        src = f[:-len(".ocr.json")]
        d = json.load(open(os.path.join(pages, f), encoding="utf-8"))
        done += 1
        att_pages += len(d)
        c = sum(len(v.strip()) for v in d.values())
        chars += c
        rec_pages += sum(1 for v in d.values() if len(v.strip()) >= 100)
        if c < 200:
            empties.append((src, c))
    return dict(files_done=done, files_queued=len(scan), pages_attempted=att_pages,
                pages_recovered=rec_pages, chars=chars, low_yield=empties)


a = stats(os.path.join(ROOT, "data", "interim", "ancsa_ocr"),
          os.path.join(ROOT, "data", "raw", "external", "ancsa_portal"), None)
b = stats(os.path.join(ROOT, "data", "interim", "ancsa_ocr_v2"),
          os.path.join(ROOT, "data", "raw", "external", "ancsa_portal_v2"), None)
print("REGIONAL (portal v1 corpus):", {k: v for k, v in a.items() if k != "low_yield"})
print("  low-yield files:", len(a["low_yield"]))
print("VILLAGE (portal v2 corpus):", {k: v for k, v in b.items() if k != "low_yield"})
print("  low-yield files:", len(b["low_yield"]))

# the 33 manifest-flagged image-only items specifically
man = list(csv.DictReader(open(os.path.join(ROOT, "data", "raw", "external", "ancsa_portal",
                                            "_SOURCE_MANIFEST.csv"), newline="", encoding="utf-8-sig")))
flag = [r["local_file"] for r in man if r["text_extractable"] != "yes"]
pdfs = [f for f in flag if f.lower().endswith(".pdf")]
pngs = [f for f in flag if f.lower().endswith(".png")]
pages = os.path.join(ROOT, "data", "interim", "ancsa_ocr", "pages")
ok = []
for f in pdfs:
    p = os.path.join(pages, f + ".ocr.json")
    if os.path.exists(p):
        d = json.load(open(p, encoding="utf-8"))
        ok.append((f, sum(len(v.strip()) for v in d.values())))
print()
print("MANIFEST-FLAGGED image-only PDFs:", len(pdfs), "(+", len(pngs), "PNGs)")
print("  attempted:", len(ok))
print("  yielded >=1000 chars:", sum(1 for f, c in ok if c >= 1000))
print("  yielded 100-999 chars:", sum(1 for f, c in ok if 100 <= c < 1000))
print("  yielded <100 chars:", sum(1 for f, c in ok if c < 100))
for f, c in sorted(ok, key=lambda x: -x[1]):
    print("   %8d  %s" % (c, f[:88]))
