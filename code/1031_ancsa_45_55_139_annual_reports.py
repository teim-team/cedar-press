#!/usr/bin/env python3
"""1031 - Alaska Statute 45.55.139 annual reports: the 358 EDGAR cannot see.

ANCs are not SEC registrants. They file audited annual reports with the Alaska
Department of Commerce, Community and Economic Development, Division of Banking
and Securities under **AS 45.55.139**, and those reports carry a numbered
business-combination note with an effective date, a cash consideration and a
purchase-price allocation - the disclosure quality EDGAR would give you for a
public filer and gives you for no ANC at all.

`data/clean/ancsa_filings_index.csv` indexes **609** such annual reports across
59 corporations for 2016-2026. Waves 1 and 2 (docs/ANCSA_PORTAL_BUILD_LOG.md,
docs/ANCSA_PORTAL_V2_LOG.md) retrieved 251 - every regional plus seven village
corporations. **358 remain, all of them village corporations**, 41 companies.

Stages
------
  plan      zero network. What is indexed, what is held, what is owed.
  fetch     retrieves the outstanding annual reports. One host lock, 3s gap
            (this is a small state portal, not EDGAR), manifest flushed after
            EVERY request, and `downloaded` flipped in a SEPARATE staged file -
            never in ancsa_filings_index.csv, which another workstream owns.
  extract   text layer via PyMuPDF; page-level OCR fallback at 300 dpi for
            image-only pages (the v2 finding: the manifest's whole-document
            text_extractable boolean is wrong in both directions, so decide
            per PAGE).
  mine      zero network. Finds business-combination / disposition notes and
            stages candidates with the corporation, the date, the figure and
            the sentence that carries it.
  verify    invariants. Exits 1 when one breaks.

Writes nothing to data/clean.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = "code/1031_ancsa_45_55_139_annual_reports.py"
CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
RAWDIR = CEDAR / "data" / "raw"
REVIEW = CEDAR / "review"
LOGS = CEDAR / "logs"
INTERIM = CEDAR / "data" / "interim"

INDEX = CLEAN / "ancsa_filings_index.csv"
CACHE = RAWDIR / "external" / "ancsa_portal_v3"
TEXTDIR = INTERIM / "ancsa_txt_v3"
MANIFEST = REVIEW / "ancsa_1031_fetch_manifest.csv"
EXTRACT_LOG = REVIEW / "ancsa_1031_extract_manifest.csv"
CANDIDATES = REVIEW / "ancsa_1031_deal_candidates.csv"

TODAY = datetime.now().strftime("%Y-%m-%d")
csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

PORTAL = "https://portal.akdbsstar.us/StarWebPortal/ViewFile.aspx?Id="
WARM = "https://portal.akdbsstar.us/StarWebPortal/page/default/portal.aspx"
UA = "Cedar Press research (elijahsamsonmoreno@gmail.com)"
GAP = 3.0
RUN_DEADLINE_S = 3 * 60 * 60


def out(s=""):
    sys.stdout.write(str(s).encode("ascii", "replace").decode() + "\n")
    sys.stdout.flush()


class HostLock:
    def __init__(self, host, policy, note=""):
        self.host = host
        self.path = LOGS / f"_HOSTLOCK_{host}.json"
        self.state = {
            "host": host, "pid": os.getpid(), "script": SCRIPT,
            "claimed_by": "pull",
            "claimed_at": datetime.now(timezone.utc).isoformat(),
            "active": True, "queue": [], "policy": policy, "note": note,
            "downloaded_this_run": 0, "already_on_disk_skipped": 0,
            "refused_by_host": [], "accepted_then_failed_server_side": [],
            "requests_made": 0,
        }

    def __enter__(self):
        LOGS.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                prev = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                prev = {}
            if prev.get("active") and not prev.get("released"):
                raise SystemExit(
                    f"HOSTLOCK HELD on {self.host} by pid {prev.get('pid')} "
                    f"({prev.get('script')}) - deferring, nothing fetched.")
        self._write()
        return self

    def _write(self):
        self.path.write_text(json.dumps(self.state, indent=1), encoding="utf-8")

    def __exit__(self, *exc):
        self.state["active"] = False
        self.state["released"] = datetime.now(timezone.utc).isoformat()
        self.state["released_by"] = SCRIPT
        self._write()
        return False

    def bump(self, **kw):
        for k, v in kw.items():
            if isinstance(v, int) and isinstance(self.state.get(k), int):
                self.state[k] += v
            else:
                self.state[k] = v
        self._write()


def read_index():
    with open(INDEX, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def owed():
    rows = read_index()
    return [r for r in rows
            if r["document_type"] == "ANCSA Annual Report"
            and r["downloaded"] != "yes"]


# ==================================================================== plan ==

def cmd_plan():
    import collections
    out("=== 1031 plan - AS 45.55.139 annual reports ===\n")
    rows = read_index()
    ar = [r for r in rows if r["document_type"] == "ANCSA Annual Report"]
    held = [r for r in ar if r["downloaded"] == "yes"]
    o = owed()
    out(f"  index rows                {len(rows):,}")
    out(f"  ANCSA Annual Report       {len(ar):,}")
    out(f"    already retrieved       {len(held):,}  (waves 1 and 2)")
    out(f"    OWED                    {len(o):,}")
    out(f"  corporations owing        "
        f"{len({r['corporation_name'] for r in o}):,}")
    out(f"  classes owing             "
        f"{dict(collections.Counter(r['anc_class'] for r in o))}")
    out("\n  owed by year")
    for y, c in sorted(collections.Counter(r["period_covered"]
                                           for r in o).items()):
        out(f"    {y}  {c:4d}")
    fetched = 0
    if MANIFEST.exists():
        with open(MANIFEST, encoding="utf-8-sig", newline="") as fh:
            fetched = sum(1 for _ in csv.DictReader(fh))
    out(f"\n  1031 has already fetched  {fetched:,}")
    return 0


# =================================================================== fetch ==

MAN_COLS = ["portal_document_id", "corporation_name", "anc_id", "anc_class",
            "period_covered", "document_description", "portal_url",
            "local_file", "bytes", "sha256", "content_type", "http_status",
            "fetched_at", "fetched_by", "note"]


def safe(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")[:100]


def cmd_fetch(limit=None):
    try:
        import requests
    except ImportError:
        raise SystemExit("requests not available")
    out("=== 1031 fetch - outstanding AS 45.55.139 annual reports ===\n")
    CACHE.mkdir(parents=True, exist_ok=True)

    done = set()
    if MANIFEST.exists():
        with open(MANIFEST, encoding="utf-8-sig", newline="") as fh:
            done = {r["portal_document_id"] for r in csv.DictReader(fh)}
    todo = [r for r in owed() if r["portal_document_id"] not in done]
    out(f"  owed {len(owed()):,}   already fetched by 1031 {len(done):,}   "
        f"to fetch {len(todo):,}")
    if limit:
        todo = todo[:int(limit)]
        out(f"  limited to {len(todo):,} this run")
    if not todo:
        return 0

    first = not MANIFEST.exists()
    S = requests.Session()
    S.headers.update({"User-Agent": UA})
    started = time.time()
    ok = fail = 0
    consecutive = 0
    with HostLock("portal.akdbsstar.us",
                  "sequential, single stream, >=3s gap, stop after 5 "
                  "consecutive refusals, 3h deadline",
                  "1031 AS 45.55.139 annual reports") as lock:
        try:
            S.get(WARM, timeout=60)
            lock.bump(requests_made=1)
        except Exception as e:
            out(f"  warm-up failed: {type(e).__name__}: {e}")
        for i, r in enumerate(todo, 1):
            if time.time() - started > RUN_DEADLINE_S:
                out("  RUN_DEADLINE reached; stopping cleanly")
                break
            did = r["portal_document_id"]
            url = PORTAL + did
            rec = {c: r.get(c, "") for c in MAN_COLS if c in r}
            rec.update(portal_url=url, fetched_by=SCRIPT,
                       fetched_at=datetime.now(timezone.utc).isoformat())
            try:
                time.sleep(GAP)
                resp = S.get(url, timeout=300)
                lock.bump(requests_made=1)
                body = resp.content
                if resp.status_code != 200 or not body:
                    raise RuntimeError(f"HTTP {resp.status_code} "
                                       f"len={len(body)}")
                ct = resp.headers.get("Content-Type", "")
                ext = ".pdf" if (body[:4] == b"%PDF" or "pdf" in ct) else ".bin"
                fn = (safe(f"{r['corporation_name']}_{r['period_covered']}")
                      + "__" + did[:8] + ext)
                p = CACHE / fn
                p.write_bytes(body)
                rec.update(local_file=str(p.relative_to(CEDAR)),
                           bytes=len(body),
                           sha256=hashlib.sha256(body).hexdigest(),
                           content_type=ct, http_status=resp.status_code,
                           note="downloaded_this_run")
                ok += 1
                consecutive = 0
                lock.bump(downloaded_this_run=1)
            except Exception as e:
                rec.update(local_file="", bytes=0, sha256="", content_type="",
                           http_status="ERR",
                           note=f"{type(e).__name__}: {e}")
                fail += 1
                consecutive += 1
                lock.state["refused_by_host"].append(f"{did}: {type(e).__name__}")
            with open(MANIFEST, "w" if first else "a",
                      encoding="utf-8", newline="") as fh:
                w = csv.writer(fh)
                if first:
                    w.writerow(MAN_COLS)
                w.writerow([rec.get(c, "") for c in MAN_COLS])
                fh.flush()
                os.fsync(fh.fileno())
            first = False
            if consecutive >= 5:
                out("  5 consecutive refusals - host refusing, stopping")
                break
            if i % 25 == 0:
                out(f"  {i:,}/{len(todo):,}  ok={ok:,} fail={fail:,}")
    out(f"\n  downloaded {ok:,}  failed {fail:,}")
    out(f"  manifest -> {MANIFEST.relative_to(CEDAR)}")
    return 0


# ================================================================= extract ==

EX_COLS = ["portal_document_id", "corporation_name", "period_covered",
           "local_file", "txt_file", "pages", "pages_text_layer",
           "pages_ocred", "chars_text_layer", "chars_ocr", "method",
           "extracted_at", "extracted_by", "note"]

MIN_CHARS_PER_PAGE = 120     # below this a page is treated as image-only


def cmd_extract(limit=None, ocr=True):
    import fitz
    out("=== 1031 extract - text layer, per-PAGE OCR fallback ===\n")
    TEXTDIR.mkdir(parents=True, exist_ok=True)
    if not MANIFEST.exists():
        raise SystemExit("run `fetch` first")
    with open(MANIFEST, encoding="utf-8-sig", newline="") as fh:
        man = [r for r in csv.DictReader(fh) if r["local_file"]]

    done = set()
    if EXTRACT_LOG.exists():
        with open(EXTRACT_LOG, encoding="utf-8-sig", newline="") as fh:
            done = {r["portal_document_id"] for r in csv.DictReader(fh)}
    todo = [r for r in man if r["portal_document_id"] not in done]
    out(f"  {len(man):,} fetched   {len(done):,} already extracted   "
        f"{len(todo):,} to do")
    if limit:
        todo = todo[:int(limit)]

    tess = None
    if ocr:
        try:
            import pytesseract
            from PIL import Image           # noqa: F401
            exe = Path(os.environ.get("LOCALAPPDATA", "")) / \
                "Programs" / "Tesseract-OCR" / "tesseract.exe"
            if exe.exists():
                pytesseract.pytesseract.tesseract_cmd = str(exe)
            tess = pytesseract
        except Exception as e:
            out(f"  OCR unavailable: {type(e).__name__}")

    first = not EXTRACT_LOG.exists()
    for i, r in enumerate(todo, 1):
        p = CEDAR / r["local_file"]
        rec = {"portal_document_id": r["portal_document_id"],
               "corporation_name": r["corporation_name"],
               "period_covered": r["period_covered"],
               "local_file": r["local_file"],
               "extracted_by": SCRIPT,
               "extracted_at": datetime.now(timezone.utc).isoformat()}
        try:
            doc = fitz.open(str(p))
            texts, n_txt, n_ocr, c_txt, c_ocr = [], 0, 0, 0, 0
            for pno in range(doc.page_count):
                pg = doc.load_page(pno)
                t = pg.get_text("text") or ""
                if len(t.strip()) >= MIN_CHARS_PER_PAGE:
                    n_txt += 1
                    c_txt += len(t)
                    texts.append(t)
                elif tess is not None:
                    from PIL import Image
                    import io
                    pm = pg.get_pixmap(dpi=300, colorspace=fitz.csGRAY)
                    im = Image.open(io.BytesIO(pm.tobytes("png")))
                    o = tess.image_to_string(im) or ""
                    n_ocr += 1
                    c_ocr += len(o)
                    texts.append(o)
                else:
                    texts.append(t)
            npages = doc.page_count
            doc.close()
            tf = TEXTDIR / (p.stem + ".txt")
            tf.write_text("\n\f\n".join(texts), encoding="utf-8")
            rec.update(txt_file=str(tf.relative_to(CEDAR)), pages=npages,
                       pages_text_layer=n_txt, pages_ocred=n_ocr,
                       chars_text_layer=c_txt, chars_ocr=c_ocr,
                       method="pymupdf+tesseract300" if n_ocr else "pymupdf",
                       note="ok")
        except Exception as e:
            rec.update(txt_file="", pages=0, pages_text_layer=0,
                       pages_ocred=0, chars_text_layer=0, chars_ocr=0,
                       method="", note=f"{type(e).__name__}: {e}")
        with open(EXTRACT_LOG, "w" if first else "a",
                  encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            if first:
                w.writerow(EX_COLS)
            w.writerow([rec.get(c, "") for c in EX_COLS])
            fh.flush()
        first = False
        if i % 10 == 0:
            out(f"  {i:,}/{len(todo):,}")
    out(f"\n  extract log -> {EXTRACT_LOG.relative_to(CEDAR)}")
    return 0


# ==================================================================== mine ==

ACQ_CUES = re.compile(
    r"\b(acquisition|acquisitions|acquired|acquire|business combination|"
    r"purchase price|consideration transferred|consideration paid|"
    r"asset purchase|stock purchase|merger|divestiture|disposition|"
    r"disposed of|sold its|sale of (?:its|the) (?:membership|interest|"
    r"subsidiary|stock|assets)|joint venture|equity method investment|"
    r"noncontrolling interest acquired|purchased (?:the|a) "
    r"(?:remaining|additional))\b", re.I)

MONEY = re.compile(
    r"\$\s?[\d,]+(?:\.\d+)?(?:\s?(?:thousand|million|billion))?", re.I)

DATE = re.compile(
    r"\b(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},?\s+(?:19|20)\d{2}\b"
    r"|\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December),?\s+(?:19|20)\d{2}\b"
    r"|\b(?:19|20)\d{2}-\d{2}-\d{2}\b", re.I)

THOUSANDS_CUE = re.compile(
    r"(in thousands|amounts? (?:are )?(?:stated|expressed) in thousands|"
    r"\(in thousands\)|dollars in thousands)", re.I)

CAND_COLS = ["candidate_id", "source_channel", "corporation_name",
             "anc_class", "period_covered", "cue", "cue_class",
             "event_date_text", "money_text",
             "thousands_convention_in_document", "quote",
             "portal_document_id", "source_url", "local_file", "txt_file",
             "page_hint", "staged_by", "staged_date", "record_scope",
             "disposition"]

# A cue alone does not say what KIND of sentence this is, and the difference
# decides whether a figure could ever be a deal value. Measured on the first
# 30 documents: `joint venture` overwhelmingly introduces an EQUITY-METHOD
# CARRYING BALANCE ("investment in this Joint Venture was $2,971 and $12,195
# (in thousands)"), which is a balance-sheet amount and never a price. The
# same trap ANCSA_PORTAL_V2_LOG catalogues as goodwill-read-as-price.
STRONG_CUE = re.compile(
    r"\b(business combination|purchase price|consideration transferred|"
    r"consideration paid|acquired (?:100|[0-9]{1,3}) ?percent|"
    r"purchased (?:100|[0-9]{1,3})%|purchased 100 percent|"
    r"acquired all of the|stock purchase agreement|asset purchase agreement|"
    r"completed the sale of|sold its (?:entire )?(?:interest|ownership)|"
    r"bargain purchase gain|acquisition of (?:the )?(?:stock|assets))\b",
    re.I)
BALANCE_CUE = re.compile(
    r"\b(carrying value|investment (?:in|amount)|equity method|"
    r"total assets|total liabilities|minimum lease|principal payments|"
    r"notes receivable|long-term debt|accumulated|balance sheet|"
    r"backlog|revenue|earnings from)\b", re.I)


def classify_cue(sentence):
    if STRONG_CUE.search(sentence):
        return "BUSINESS_COMBINATION_OR_DISPOSITION"
    if BALANCE_CUE.search(sentence):
        return "BALANCE_OR_RESULT_NOT_A_PRICE"
    return "UNCLASSIFIED"


def sentences(text):
    text = re.sub(r"\s+", " ", text)
    return re.split(r"(?<=[.;])\s+(?=[A-Z(])", text)


def cmd_mine(limit=None):
    out("=== 1031 mine - business-combination notes ===\n")
    if not EXTRACT_LOG.exists():
        raise SystemExit("run `extract` first")
    with open(EXTRACT_LOG, encoding="utf-8-sig", newline="") as fh:
        ex = [r for r in csv.DictReader(fh) if r["txt_file"]]
    man = {}
    with open(MANIFEST, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            man[r["portal_document_id"]] = r
    if limit:
        ex = ex[:int(limit)]

    rows = []
    n = 0
    for r in ex:
        tf = CEDAR / r["txt_file"]
        if not tf.exists():
            continue
        text = tf.read_text(encoding="utf-8", errors="replace")
        thou = "yes" if THOUSANDS_CUE.search(text) else "no"
        pages = text.split("\n\f\n")
        for pno, page in enumerate(pages, 1):
            for s in sentences(page):
                if len(s) < 40 or len(s) > 1200:
                    continue
                if not ACQ_CUES.search(s):
                    continue
                m = MONEY.findall(s)
                d = DATE.findall(s)
                if not m and not d:
                    continue
                n += 1
                mrow = man.get(r["portal_document_id"], {})
                rows.append({
                    "candidate_id": f"AS4555139-{n:05d}",
                    "source_channel": "AS_45.55.139_annual_report",
                    "corporation_name": r["corporation_name"],
                    "anc_class": mrow.get("anc_class", ""),
                    "period_covered": r["period_covered"],
                    "cue": (ACQ_CUES.search(s).group(0) or "").lower(),
                    "cue_class": classify_cue(s),
                    "event_date_text": "; ".join(d[:3]),
                    "money_text": "; ".join(m[:5]),
                    "thousands_convention_in_document": thou,
                    "quote": s.strip()[:1000],
                    "portal_document_id": r["portal_document_id"],
                    "source_url": mrow.get("portal_url", ""),
                    "local_file": r["local_file"],
                    "txt_file": r["txt_file"],
                    "page_hint": pno,
                    "staged_by": SCRIPT, "staged_date": TODAY,
                    "record_scope": "CANDIDATE_NOT_A_DEAL",
                    "disposition": "",
                })
    with open(CANDIDATES, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAND_COLS)
        w.writeheader()
        w.writerows(rows)
    out(f"  {len(rows):,} candidate passages from {len(ex):,} documents")
    out(f"  -> {CANDIDATES.relative_to(CEDAR)}")
    import collections
    out("")
    out("  by cue class")
    for k, v in collections.Counter(r["cue_class"]
                                    for r in rows).most_common():
        out(f"    {v:5d}  {k}")
    out("")
    out("  by corporation")
    for k, v in collections.Counter(r["corporation_name"]
                                    for r in rows).most_common(60):
        strong = sum(1 for r in rows if r["corporation_name"] == k
                     and r["cue_class"] == "BUSINESS_COMBINATION_OR_DISPOSITION")
        out(f"    {v:5d} ({strong:3d} strong)  {k}")
    return 0


# ================================================================== verify ==

def cmd_verify():
    out("=== 1031 verify ===\n")
    fails = []

    # I1  every fetched byte on disk matches its recorded sha256
    if MANIFEST.exists():
        with open(MANIFEST, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        bad = []
        for r in rows:
            lf = (r.get("local_file") or "").strip()
            if not lf:
                continue
            p = CEDAR / lf
            if not p.exists():
                bad.append(lf)
                continue
            if hashlib.sha256(p.read_bytes()).hexdigest() != r["sha256"]:
                bad.append(lf)
        out(f"  I1 sha256 matches disk: {len(rows) - len(bad)}/{len(rows)}")
        if bad:
            fails.append(f"I1 {len(bad)} files disagree with their sha256")
    else:
        out("  I1 no manifest yet")

    # I2  every candidate carries a portal URL and a quote
    if CANDIDATES.exists():
        with open(CANDIDATES, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        bad = [r for r in rows if not (r.get("source_url") or "").strip()
               or not (r.get("quote") or "").strip()]
        out(f"  I2 candidates carry URL + quote: "
            f"{len(rows) - len(bad)}/{len(rows)}")
        if bad:
            fails.append(f"I2 {len(bad)} candidates without a source link "
                         f"or quote")
    else:
        out("  I2 no candidate file yet")

    # I3  a money_text must actually appear in its own quote
    if CANDIDATES.exists():
        with open(CANDIDATES, encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.DictReader(fh))
        bad = []
        for r in rows:
            mt = (r.get("money_text") or "").strip()
            if not mt:
                continue
            for piece in mt.split("; "):
                if piece and piece not in (r.get("quote") or ""):
                    bad.append(r["candidate_id"])
                    break
        out(f"  I3 money_text is present in its quote: "
            f"{len(rows) - len(bad)}/{len(rows)}")
        if bad:
            fails.append(f"I3 {len(bad)} candidates quote a figure their "
                         f"own quote does not contain")

    # I4  ancsa_filings_index.csv must be UNTOUCHED by this script
    #     (another workstream owns it; 1031 stages its own manifest)
    idx_rows = read_index()
    held = sum(1 for r in idx_rows if r["downloaded"] == "yes")
    out(f"  I4 ancsa_filings_index.csv downloaded=yes still {held} "
        f"(1031 must not flip it)")
    if held != 251:
        fails.append(f"I4 ancsa_filings_index.csv downloaded=yes is {held}, "
                     f"expected the 251 waves 1-2 left; 1031 must not write "
                     f"this file")

    if fails:
        out("\nFAIL")
        for f in fails:
            out(f"  {f}")
        return 1
    out("\nOK")
    return 0


def cmd_verify_synthetic():
    import tempfile
    global CANDIDATES
    keep = CANDIDATES
    d = Path(tempfile.mkdtemp())
    CANDIDATES = d / "syn.csv"
    with open(CANDIDATES, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CAND_COLS)
        w.writeheader()
        w.writerow({"candidate_id": "SYN-1", "source_url": "",
                    "quote": "the company acquired a business",
                    "money_text": "$99,999,999"})
    out("=== synthetic violation: no URL, and a figure absent from the quote ===")
    rc = cmd_verify()
    CANDIDATES = keep
    out(f"\nsynthetic run exit code = {rc}  (must be 1)")
    return 0 if rc == 1 else 1


def main(argv):
    if len(argv) < 2:
        out(__doc__)
        return 2
    cmd = argv[1]
    kw = {}
    for a in argv[2:]:
        if a.startswith("--"):
            k, _, v = a[2:].partition("=")
            kw[k.replace("-", "_")] = v or True
    if cmd == "plan":
        return cmd_plan()
    if cmd == "fetch":
        return cmd_fetch(limit=kw.get("limit"))
    if cmd == "extract":
        return cmd_extract(limit=kw.get("limit"),
                           ocr=kw.get("no_ocr") is not True)
    if cmd == "mine":
        return cmd_mine(limit=kw.get("limit"))
    if cmd == "verify":
        return cmd_verify()
    if cmd == "verify-synthetic":
        return cmd_verify_synthetic()
    out(f"unknown command {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
