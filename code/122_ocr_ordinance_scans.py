#!/usr/bin/env python3
"""
Cedar Press - 121: recover the 264 image-only ordinance scans by OCR.

WHY rapidocr AND NOT tesseract
------------------------------
`pytesseract` IS installed. The tesseract BINARY is not - not on PATH, not in
Program Files. pytesseract is a wrapper around an executable it does not ship,
so it would fail at the first call with TesseractNotFoundError. Installing the
binary needs an admin MSI.

`rapidocr-onnxruntime` is already installed, is pure-python + ONNX weights, and
is the SAME route that closed an identical ceiling on the declination letters.
No new dependency, no admin install. That is why this file uses it.

WHAT IT DOES
------------
For every ordinance row with `text_layer_status = IMAGE_ONLY_SCAN_NO_TEXT_LAYER`,
render each page at 300 dpi with PyMuPDF and OCR it. Writes:

    data/raw/external/nigc_ordinances/ocr/<ordinance_id>.txt   verbatim OCR
    data/clean/gaming_ordinance_ocr.csv                        one row per doc

IT DOES NOT TOUCH gaming_ordinances.csv. A separate merge step reads the sidecar
and re-extracts provisions, so a bad OCR run can never damage the built file.

REFUSALS CARRIED FORWARD FROM THE BUILD
---------------------------------------
- Rows with `md5_duplicate_of` set are SKIPPED. Kialegee Tribal Town's amendment
  link serves Kalispel's PDF - byte-identical, different URL. OCR-ing it would
  launder another tribe's text into Kialegee's row. The build refused that row;
  so does this.
- OCR text is stored as OCR_RECOVERED, never as TEXT_LAYER_PRESENT. A recovered
  scan is a different evidence grade from a born-digital text layer and must
  stay distinguishable downstream.
- Mean per-line confidence is recorded per document. A page that OCRs at 0.45
  is not the same fact as one at 0.95.

Resumable: an ordinance whose .txt already exists is skipped.

    py -3 code/121_ocr_ordinance_scans.py            # run
    py -3 code/121_ocr_ordinance_scans.py --limit 5  # smoke test
"""

import csv
import sys
import time
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
SRC = CLEAN / "gaming_ordinances.csv"
OCRDIR = CEDAR / "data" / "raw" / "external" / "nigc_ordinances" / "ocr"
OUT = CLEAN / "gaming_ordinance_ocr.csv"
OUTDIR = CEDAR / "data" / "interim" / "ocr_shards"
TODAY = date.today().isoformat()

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

DPI = 220   # 220 is legible for typed ordinance text and ~2x faster than 300
NEEDS = "IMAGE_ONLY_SCAN_NO_TEXT_LAYER"


def main():
    limit = shard = None
    nshard = 1
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    if "--shard" in sys.argv:
        shard, nshard = (int(x) for x in
                         sys.argv[sys.argv.index("--shard") + 1].split("/"))

    import fitz
    from rapidocr_onnxruntime import RapidOCR

    OCRDIR.mkdir(parents=True, exist_ok=True)
    with open(SRC, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rows = list(csv.DictReader(fh))

    todo = [r for r in rows if (r.get("text_layer_status") or "") == NEEDS]
    dup = [r for r in todo if (r.get("md5_duplicate_of") or "").strip()]
    todo = [r for r in todo if not (r.get("md5_duplicate_of") or "").strip()]
    print(f"=== 121: OCR ordinance scans ===")
    print(f"  image-only rows      : {len(todo) + len(dup)}")
    print(f"  refused (md5 dup)    : {len(dup)}  {[r['ordinance_id'] for r in dup]}")
    print(f"  to OCR               : {len(todo)}")
    if shard is not None:
        todo = [r for i, r in enumerate(todo) if i % nshard == shard]
        print(f"  --shard {shard}/{nshard} -> {len(todo)} docs")
    if limit:
        todo = todo[:limit]
        print(f"  --limit {limit}")

    engine = RapidOCR()
    done, failed, t0 = [], [], time.time()

    for i, r in enumerate(todo, 1):
        oid = r["ordinance_id"]
        pdf = CEDAR / (r.get("pdf_path") or "")
        dest = OCRDIR / f"{oid}.txt"
        if dest.exists() and dest.stat().st_size > 0:
            continue
        if not pdf.exists():
            failed.append((oid, "pdf missing"))
            continue
        try:
            doc = fitz.open(pdf)
            pages, confs = [], []
            for pno in range(doc.page_count):
                pix = doc[pno].get_pixmap(dpi=DPI)
                res, _ = engine(pix.tobytes("png"))
                if not res:
                    pages.append("")
                    continue
                pages.append("\n".join(line[1] for line in res))
                confs += [float(line[2]) for line in res if len(line) > 2]
            doc.close()
            text = "\n\f\n".join(pages)
            dest.write_text(text, encoding="utf-8")
            mc = round(sum(confs) / len(confs), 4) if confs else 0.0
            done.append({
                "ordinance_id": oid,
                "tribe_id": r.get("tribe_id", ""),
                "tribe_name": r.get("tribe_name", ""),
                "ocr_txt_path": str(dest.relative_to(CEDAR)).replace("\\", "/"),
                "ocr_chars": len(text),
                "ocr_pages": len(pages),
                "ocr_pages_blank": sum(1 for p in pages if not p.strip()),
                "ocr_mean_confidence": mc,
                "ocr_engine": "rapidocr-onnxruntime",
                "ocr_dpi": DPI,
                "text_layer_status_after": "OCR_RECOVERED",
                "source_url": r.get("source_url", ""),
                "pdf_md5": r.get("pdf_md5", ""),
                "ocr_date": TODAY,
            })
        except Exception as e:
            failed.append((oid, f"{type(e).__name__}: {e}"))
        if i % 10 == 0:
            el = time.time() - t0
            print(f"  {i}/{len(todo)}  {el/60:.1f}m  "
                  f"eta {(el/i)*(len(todo)-i)/60:.0f}m", flush=True)

    if shard is not None:
        OUTDIR.mkdir(parents=True, exist_ok=True)
        globals()["OUT"] = OUTDIR / f"ocr_shard_{shard}.csv"
    # append-only: never drop a prior OCR result
    prior = []
    if OUT.exists():
        with open(OUT, encoding="utf-8-sig", errors="replace", newline="") as fh:
            prior = list(csv.DictReader(fh))
    have = {d["ordinance_id"] for d in done}
    merged = [p for p in prior if p.get("ordinance_id") not in have] + done
    if merged:
        with open(OUT, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(done[0] if done else prior[0]))
            w.writeheader()
            w.writerows(merged)

    print(f"\n  OCR'd this run : {len(done)}")
    print(f"  total in file  : {len(merged)}")
    print(f"  failed         : {len(failed)}")
    for oid, why in failed[:15]:
        print(f"    {oid}  {why}")
    if done:
        lo = [d for d in done if d["ocr_mean_confidence"] < 0.70]
        blank = [d for d in done if d["ocr_pages_blank"] == d["ocr_pages"]]
        print(f"  low confidence (<0.70) : {len(lo)}")
        print(f"  ALL pages blank        : {len(blank)}  <- true image failures")
    print(f"  wrote {OUT.relative_to(CEDAR)}")
    print(f"  elapsed {(time.time()-t0)/60:.1f}m")


if __name__ == "__main__":
    main()
