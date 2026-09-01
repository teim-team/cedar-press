"""SHARD-E: mine the LOCAL ANCSA annual-report corpus for parent->child ownership
assertions.  ZERO NETWORK.

Corpus (already on disk, harvested 2026-08-05 by the Alaska DBS STAR portal passes):
  data/interim/ancsa_txt/      166 files
  data/interim/ancsa_txt_v2/    80 files (village corporations)
  data/interim/ancsa_ocr*/      OCR JSON for image-only pages

Emits candidate PASSAGES only.  Every edge written to
data/staging/anc_subsidiaries/shard_e.jsonl is adjudicated by hand from these
passages -- this script never writes an edge.
"""
import glob, io, json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "staging" / "tribe_harvest" / "shard_e"
OUT.mkdir(parents=True, exist_ok=True)

PATTERNS = [
    ("consolidation", r"[Pp]rinciples of [Cc]onsolidation"),
    ("wholly_owned", r"wholly[- ]owned (?:first-tier )?subsidiar"),
    ("is_a_subsidiary", r"\bis a (?:wholly[- ]owned )?subsidiary of\b"),
    ("family_of_cos", r"[Ff]amily of [Cc]ompanies"),
    ("our_companies", r"\b[Oo]ur [Cc]ompanies\b"),
    ("subsidiaries_of", r"\bsubsidiaries of\b"),
    ("operating_cos", r"[Oo]perating [Cc]ompan(?:y|ies)"),
    ("acquired", r"\bacquired (?:the )?(?:remaining |all |100%|a )?"),
    ("pct_owned", r"\d{1,3}(?:\.\d+)?%\s+(?:equity |ownership |membership |voting )?(?:interest|owned|stake)"),
    ("holding", r"[Hh]olding [Cc]ompany"),
    ("joint_venture", r"\bjoint venture\b"),
    ("llc_list", r"\bLLC\b|\bInc\.|\bCorporation\b"),
]

def corp_of(fn):
    b = os.path.basename(fn)
    parts = b.split("__")
    return (parts[0], parts[1].replace("_", " ").strip()) if len(parts) >= 2 else ("?", b)

def main():
    # lint-ok: class1 - the interim text layer of the Alaska DBS STAR portal PDFs
    # IS the source of record; there is no promoted table of annual-report text
    # and none is possible. This script only INDEXES passages for hand review.
    files = sorted(glob.glob(str(ROOT / "data/interim/ancsa_txt/*.txt")))
    # lint-ok: class1 - same staged corpus, village-corporation half.
    files += sorted(glob.glob(str(ROOT / "data/interim/ancsa_txt_v2/*.txt")))
    idx = []
    hits_f = (OUT / "_report_passages.jsonl").open("w", encoding="utf-8")
    n = 0
    for f in files:
        yr, corp = corp_of(f)
        t = open(f, encoding="utf-8", errors="replace").read()
        idx.append({"file": os.path.relpath(f, ROOT), "year": yr, "corp": corp, "chars": len(t)})
        for tag, pat in PATTERNS:
            if tag == "llc_list":
                continue
            for m in re.finditer(pat, t):
                a, b = max(0, m.start() - 400), min(len(t), m.end() + 1600)
                win = re.sub(r"[ \t]+", " ", t[a:b])
                hits_f.write(json.dumps({"file": os.path.basename(f), "year": yr,
                                         "corp": corp, "tag": tag, "pos": m.start(),
                                         "text": win}, ensure_ascii=False) + "\n")
                n += 1
    hits_f.close()
    json.dump(idx, (OUT / "_report_index.json").open("w", encoding="utf-8"), indent=1)
    byc = {}
    for r in idx:
        byc.setdefault(r["corp"], []).append(r["year"])
    print("files", len(files), "passages", n, "corps", len(byc))
    for k in sorted(byc):
        print(f"  {k}: {min(byc[k])}-{max(byc[k])} ({len(byc[k])})")

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()
