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

    # A PDF that crashes MuPDF or tesseract takes the whole process down
    # NATIVELY - no Python exception, no traceback, exit code 1 - and the run
    # then restarts on the same document forever. Measured twice on this
    # corpus at documents ~171 and ~164.
    #
    # So mark the document BEFORE opening it. If the marker survives, the
    # previous run died inside that document: record it as a crash, skip it,
    # and carry on. That converts a poison pill into one honest failed row.
    marker = REVIEW / "_ancsa_1031_extracting.txt"
    first = not EXTRACT_LOG.exists()
    if marker.exists() and marker.read_text(encoding="utf-8").strip():
        crashed = marker.read_text(encoding="utf-8").strip()
        cid, _, cfile = crashed.partition("|")
        out(f"  previous run died inside {cfile} - recording it as a native "
            f"crash and skipping it")
        with open(EXTRACT_LOG, "w" if first else "a",
                  encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            if first:
                w.writerow(EX_COLS)
            w.writerow([cid, "", "", cfile, "", 0, 0, 0, 0, 0, "",
                        datetime.now(timezone.utc).isoformat(), SCRIPT,
                        "NATIVE_CRASH_SKIPPED"])
        first = False
        marker.write_text("", encoding="utf-8")
        todo = [t for t in todo if t["portal_document_id"] != cid]

    for i, r in enumerate(todo, 1):
        marker.write_text(f'{r["portal_document_id"]}|{r["local_file"]}',
                          encoding="utf-8")
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
        marker.write_text("", encoding="utf-8")
        if i % 10 == 0:
            out(f"  {i:,}/{len(todo):,}")
    out("")
    out(f"  extract log -> {EXTRACT_LOG.relative_to(CEDAR)}")
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

    # The portal lists the SAME PDF under more than one document id: 358
    # distinct ids resolve to 328 distinct sha256. Mining both copies emits
    # every passage twice, which would inflate a count nobody could then
    # reconcile. De-duplicate on the file's own hash, keeping the first id.
    seen_sha, dedup, dropped = set(), [], 0
    for r in ex:
        sha = (man.get(r["portal_document_id"], {}) or {}).get("sha256", "")
        if sha and sha in seen_sha:
            dropped += 1
            continue
        if sha:
            seen_sha.add(sha)
        dedup.append(r)
    out(f"  {dropped} byte-identical duplicate documents dropped "
        f"(same PDF under a second portal id)")
    ex = dedup
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
                # The quote is CLIPPED at 1,000 characters. Figures found past
                # the clip point are real in the document and absent from the
                # row's own evidence, which is exactly the thing invariant I3
                # refuses. Re-derive both lists from the clipped text so a row
                # can never cite what it does not show.
                clipped = s.strip()[:1000]
                m = MONEY.findall(clipped)
                d = DATE.findall(clipped)
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


# =================================================================== stage ==
# Promote the BUSINESS_COMBINATION_OR_DISPOSITION class into TRANSACTIONS.
#
# Each row below was read in the extracted text of one AS 45.55.139 annual
# report. `verify` re-opens that text file and asserts the quote is still in
# it, and that any populated value appears inside the quote - the same
# invariant code/1032 applies to EDGAR. A staged row cannot carry a figure its
# own source does not state.
#
# Value discipline, from ANCSA_PORTAL_V2_LOG's catalogue of traps: goodwill is
# not a price; a bargain purchase gain is not a price; a contingent earnout
# maximum is not consideration; a noncontrolling interest inside "total
# consideration transferred" was not bought; an equity-method carrying value
# is a balance.

STAGED_TX = REVIEW / "deals_ancsa_1031_staged.csv"

TX_COLS = ["candidate_id", "event_date", "event_year", "deal_title",
           "native_party", "native_party_type", "counterparty",
           "native_party_role", "deal_category", "instrument", "status",
           "status_class", "announced_value_usd", "value_type", "state",
           "industry", "date_basis", "notes", "confidence", "source_channel",
           "portal_document_id", "source_url", "txt_file", "evidence_quote",
           "staged_by", "staged_date", "record_scope",
           "already_in_deals_classified"]


def _deals_index():
    """Existing rows, for a conservative duplicate check on the TARGET name."""
    p2 = CLEAN / "deals_classified.csv"
    if not p2.exists():
        return []
    with open(p2, encoding="utf-8-sig", newline="") as fh:
        return [(r["Deal_ID"], r["Event_Date"], r["Deal_Title"],
                 " ".join([r["Deal_Title"], r["Native_Party"],
                           r["Counterparty_or_Funder"],
                           r["Description"]]).lower())
                for r in csv.DictReader(fh)]


# A token is generic if the LEDGER SAYS SO, not if a list says so.
#
# Two failures, both ENTITY_MATCH_RULES rule 1 reproduced inside a duplicate
# checker: a single `environmental` matched `H&S Environmental, Inc.` to a
# Sealaska row, and `estate` matched an unnamed Chapter 11 estate to a Mohegan
# row. A word denylist then over-corrected and refused `aleyon`, `situk` and
# `mobius`, which are unique proper nouns that happen to be short.
#
# The structural predicate: measure the token's FREQUENCY in the ledger it is
# being checked against. A token appearing in more than GENERIC_AT rows cannot
# distinguish a transaction, however long it is; one appearing in none is
# distinctive, however short.
GENERIC_AT = 5


# A counterparty field can say the filing did not name one. That is prose,
# not a name, and tokenising it produced a "check" on the words `unnamed`,
# `chapter`, `estate`, `extracted` and `passage`.
_NOT_A_NAME = re.compile(
    r"^\s*(not named|not stated|an unnamed|unnamed|unknown|undisclosed)\b",
    re.I)


def _dupe_note(tx, deals, tokfreq):
    """A duplicate needs the TARGET and the ACQUIRER, not either alone."""
    if _NOT_A_NAME.search(tx["cp"] or "") or not (tx["cp"] or "").strip():
        return ("the filing does not name the counterparty - a duplicate "
                "check on the acquirer alone would be meaningless, so none "
                "was made")
    tgt = re.sub(r"[^a-z0-9 ]", " ", tx["cp"].lower())
    raw = [t for t in tgt.split() if len(t) > 3]
    toks = [t for t in raw if tokfreq.get(t, 0) <= GENERIC_AT]
    dropped = [f"{t} ({tokfreq.get(t, 0)} rows)" for t in raw
               if tokfreq.get(t, 0) > GENERIC_AT]
    if not toks:
        why = (f"; dropped as generic: {', '.join(dropped)}" if dropped else "")
        return ("no distinctive target name in the filing - a duplicate check "
                "on the acquirer alone would be meaningless, so none was "
                "made" + why)
    acq = [t for t in re.sub(r"[^a-z0-9 ]", " ", tx["corp"].lower()).split()
           if len(t) > 4 and tokfreq.get(t, 0) <= 200]
    for did, ed, title, blob in deals:
        if all(t in blob for t in toks) and (not acq or
                                             any(a in blob for a in acq)):
            return f"POSSIBLE DUPLICATE of {did} ({ed}): {title[:80]}"
    return (f"no - checked on {', '.join(toks)}"
            + (f"; dropped as generic: {', '.join(dropped)}" if dropped else ""))

# corporation, fiscal year -> the transaction. `quote` must be verbatim from
# the extracted text of that document.
ANCSA_TX = [
 dict(cid="AS4555139-TX-001", corp="Afognak Native Corporation", fy="2016",
      date="2015-08-19",
      basis="'a Stock Purchase Agreement (SPA) that was executed on August 19, 2015'",
      title="Afognak Native Corporation sells Community Power Corporation to Syntech Bioenergy, LLC",
      cls="Alaska Native Village Corporation", cp="Syntech Bioenergy, LLC",
      role="Seller", cat="Divestiture", instr="Stock Purchase Agreement",
      status="Completed", sclass="Completed", value="", vtype="",
      quote="Discontinued Operations In August, 2015, the Corporation completed the sale of the Community Power Corporation to Syntech Bioenergy, LLC under the terms of a Stock Purchase Agreement (SPA) that was executed on August 19, 2015.",
      notes="No sale price is stated. The FY2017 report records a note receivable of $5,810 thousand 'related to the sale of Community Power Corporation' - that is a RECEIVABLE BALANCE, not the consideration, and is not entered as a value. Afognak states amounts in thousands.",
      conf="High"),
 dict(cid="AS4555139-TX-002", corp="Afognak Native Corporation", fy="2016",
      date="2017-01-01",
      basis="'assuming management control on January 1, 2017'",
      title="Afognak Native Corporation acquires 100 percent of the stock of Aleyon Inc.",
      cls="Alaska Native Village Corporation", cp="Aleyon Inc.",
      role="Acquirer", cat="Acquisition", instr="Stock purchase",
      status="Completed", sclass="Completed", value="", vtype="",
      quote="The Corporation acquired 100 percent of the stock of Aleyon Inc., assuming management control on January 1, 2017.",
      notes="No consideration stated in this note. The FY2017 report carries a purchase-price allocation for the same target under the spelling 'Alcyon' (customer contracts $3,854 thousand and other assets) - an allocation is not a price and no value was taken from it. THE SPELLING DIFFERS BETWEEN THE TWO REPORTS, Aleyon and Alcyon, and neither was corrected.",
      conf="Medium"),
 dict(cid="AS4555139-TX-003", corp="K'oyitl'ots'ina, Limited", fy="2016",
      date="2013-07-01",
      basis="'effective July 1, 2013, the Corporation purchased a 100 percent ownership interest'",
      title="K'oyitl'ots'ina, Limited purchases a 100 percent ownership interest in Yukon Fire Protection Services, Inc.",
      cls="Alaska Native Village Corporation", cp="Yukon Fire Protection Services, Inc.",
      role="Acquirer", cat="Acquisition", instr="Purchase of ownership interest",
      status="Completed", sclass="Completed",
      value="3839848", vtype="Total purchase price as stated",
      quote="The purchase price totaled $3,839,848, included $3,423,685 for goodwill, which is the excess of the purchase price over the fair value of identifiable assets and liabilities.",
      notes="VALUE TRAP AVOIDED: $3,423,685 of the $3,839,848 is GOODWILL, not a second payment. The price is $3,839,848 and goodwill is a component of its allocation. The effective date comes from the adjoining sentence in the same note: 'effective July 1, 2013, the Corporation purchased a 100 percent ownership interest in Yukon Fire Protection Services, Inc., a corporation located in Anchorage, Alaska.'",
      conf="High"),
 dict(cid="AS4555139-TX-004", corp="Yak-Tat Kwaan, Inc.", fy="2016",
      date="2015-02-09",
      basis="'a note payable in the amount of $270,000 on February 9, 2015'",
      title="Yak-Tat Kwaan, Inc. purchases Situk Equipment, Inc. through a new subsidiary, Kwaan Leasing, LLC",
      cls="Alaska Native Village Corporation", cp="Situk Equipment, Inc.",
      role="Acquirer", cat="Acquisition", instr="Purchase of a company via a newly formed leasing subsidiary",
      status="Completed", sclass="Completed",
      value="249200", vtype="Stated value of the company purchased",
      quote="Business Combination and Goodwill In 2015, the Company created a subsidiary called Kwaan Leasing, LLC and used this entity to purchase Situk Equipment, Inc. valued at $249,200 in exchange for $50,000 cash and a note payable in the amount of $270,000 on February 9, 2015.",
      notes="ARITHMETIC FLAG, NOT RESOLVED: the filing says Situk was 'valued at $249,200' and paid for with $50,000 cash PLUS a $270,000 note, which totals $320,000 and exceeds the stated valuation. The filing is recorded as written; announced_value_usd carries the stated $249,200 and the discrepancy is disclosed here rather than reconciled.",
      conf="Medium"),
 dict(cid="AS4555139-TX-005", corp="The Kuskokwim Corporation", fy="2016",
      date="2016-04-15",
      basis="MONTH-LEVEL ONLY - 'In April, 2016'. Mid-month placeholder, per the ledger convention.",
      title="The Kuskokwim Corporation's subsidiary PHS acquires the assets of an Arizona company out of Chapter 11 bankruptcy",
      cls="Alaska Native Village Corporation", cp="an unnamed Arizona company (Chapter 11 estate)",
      role="Acquirer", cat="Acquisition", instr="Asset purchase out of Chapter 11",
      status="Completed", sclass="Completed",
      value="1600000", vtype="Consideration as stated",
      quote="Business Combination In April, 2016, PHS acquired the assets of an Arizona Company out of Chapter 11 Bankruptcy in exchange for consideration of $1,600,000.",
      notes="THE TARGET IS NOT NAMED in the filing and was not inferred. Date is month-level; the day is a placeholder and is disclosed as such in date_basis.",
      conf="Medium"),
 dict(cid="AS4555139-TX-006", corp="Ouzinkie Native Corporation", fy="2016",
      date="2015-01-01",
      basis="'Effective January 1, 2015, the Company purchased 100% of the stock'",
      title="Ouzinkie Native Corporation purchases 100% of the stock of Mobius Industries USA, Inc.",
      cls="Alaska Native Village Corporation", cp="Mobius Industries USA, Inc.",
      role="Acquirer", cat="Acquisition", instr="Stock Purchase Agreement",
      status="Completed", sclass="Completed", value="", vtype="",
      quote="Business Combination Effective January 1, 2015, the Company purchased 100% of the stock of Mobius Industries USA, Inc.",
      notes="VALUE TRAP AVOIDED: the note goes on to say '$700,000 of the maximum purchase price is subject to a 3-year performance-based contingent earnout agreement based on the future performance of Mobius.' An earnout tranche is not the price and the price itself is not stated, so announced_value_usd is blank. Ouzinkie discloses the same structure for two other targets - $1,900,000 of a 10-year earnout on ITS and a 4-year earnout on CAS - which are separate transactions in earlier years.",
      conf="High"),
 dict(cid="AS4555139-TX-007", corp="Ouzinkie Native Corporation", fy="2016",
      date="2016-01-01",
      basis="'The Company sold its ownership in ITSS effective January 1, 2016.'",
      title="Ouzinkie Native Corporation sells its ownership in ITSS",
      cls="Alaska Native Village Corporation", cp="not named in the filing",
      role="Seller", cat="Divestiture", instr="Sale of ownership interest",
      status="Completed", sclass="Completed", value="", vtype="",
      quote="The Company sold its ownership in ITSS effective January 1, 2016.",
      notes="Neither the buyer nor the price is stated and neither was inferred. A divestiture is the scarcest class in this dataset and is worth the row even unpriced.",
      conf="Medium"),
 dict(cid="AS4555139-TX-008", corp="Gana-A'Yoo, Limited", fy="2016",
      date="2015-06-15",
      basis="MONTH-LEVEL ONLY - 'In June 2015'. Mid-month placeholder.",
      title="Gana-A'Yoo, Limited sells its entire interest in Block 13 for $633,000",
      cls="Alaska Native Village Corporation", cp="not named in the filing",
      role="Seller", cat="Divestiture", instr="Sale of an equity interest",
      status="Completed", sclass="Completed",
      value="633000", vtype="Sale proceeds as stated",
      quote="In June 2015, the Company sold its entire interest in Block 13 for $633,000 resulting in a loss of $46,946, which is included in earnings from unconsolidated affiliates in the consolidated statements of income.",
      notes="VALUE TRAP AVOIDED: the $46,946 is the LOSS on disposal, not a second figure of consideration. Gana-A'Yoo's fiscal year ends September 30, but the transaction month is stated so the calendar year is not in doubt.",
      conf="High"),
 dict(cid="AS4555139-TX-009", corp="Azachorok Inc.", fy="2016",
      date="2015-07-01",
      basis="YEAR-LEVEL ONLY - 'During 2015'. Azachorok's fiscal year is the calendar year, so the calendar year is determined; the day and month are a placeholder and the date is Medium confidence.",
      title="Azachorok Contract Services, LLC purchases 100% of the ownership shares of AMC Defense Technologies, Inc.",
      cls="Alaska Native Village Corporation", cp="AMC Defense Technologies, Inc.",
      role="Acquirer", cat="Acquisition", instr="Purchase of ownership shares",
      status="Completed", sclass="Completed", value="", vtype="",
      quote="Note 14: Business Combination and Goodwill During 2015, Azachorok Contract Services, LLC, a wholly owned subsidiary of Azachorok, Incorporated, and purchased 100% of the ownership shares of AMC",
      notes="No price is stated in the passage as extracted. The $1,800,000 that the miner captured alongside it belongs to a lease schedule in the preceding paragraph and is NOT consideration. A maintainer should re-read the full Note 14 in the source PDF before assigning any value.",
      conf="Medium"),
 dict(cid="AS4555139-TX-010", corp="Tyonek Native Corporation", fy="2017",
      date="2016-04-28",
      basis="'Effective April 28, 2016 the Company purchased through an asset purchase agreement'",
      title="Tyonek Native Corporation purchases a line of business from SELEX Galileo Inc.",
      cls="Alaska Native Village Corporation", cp="SELEX Galileo Inc.",
      role="Acquirer", cat="Acquisition", instr="Asset purchase agreement",
      status="Completed", sclass="Completed", value="", vtype="",
      quote="Business Combination Effective April 28, 2016 the Company purchased through an asset purchase agreement a line of business from SELEX Galileo Inc.",
      notes="VALUE TRAP AVOIDED: the allocation table gives a 'Fair Value of Invested Capital' of $6,538,379 (property and equipment $5,171,516, other assets $408,379, goodwill $958,484). That is the fair value of what was ACQUIRED, not a stated purchase price, and it includes goodwill. announced_value_usd is blank and the allocation is recorded here.",
      conf="High"),
 dict(cid="AS4555139-TX-011", corp="Natives of Kodiak, Incorporated", fy="2017",
      date="2016-07-01",
      basis="YEAR-LEVEL ONLY - 'During 2016, the Company entered into a stock purchase agreement'. Natives of Kodiak's fiscal year is the calendar year, so the calendar year is determined; the day and month are a placeholder.",
      title="Natives of Kodiak, Incorporated agrees to acquire 100% of H&S Environmental, Inc. for $4,000,000 cash plus long-term debt and an earnout of up to $3,800,000",
      cls="Alaska Native Village Corporation", cp="H&S Environmental, Inc.",
      role="Acquirer", cat="Acquisition", instr="Stock purchase agreement",
      status="Completed", sclass="Completed",
      value="4000000", vtype="Cash portion of the consideration as stated",
      quote="During 2016, the Company entered into a stock purchase agreement to acquire 100% of the issued and outstanding shares of common stock of H&S Environmental, Inc., a Massachusetts corporation, for $4,000,000 cash, long-term debt and an earn out payment of up to $3,800,000 over a five-year period endin",
      notes="VALUE TRAP: the $3,800,000 is an EARNOUT MAXIMUM over five years to 2020-12-31 and pays nothing unless the targets are met - it is not in announced_value_usd. The 'long-term debt' component is unquantified in this sentence. So $4,000,000 is a FLOOR on the consideration, not the whole of it, and value_type says so.",
      conf="High"),
 dict(cid="AS4555139-TX-012", corp="Choggiung Limited", fy="2017",
      date="2016-09-30",
      basis="'During the year ended September 30, 2016, the Corporation acquired various land and rental properties'. Fiscal-year-end date used because the note gives no other.",
      title="Choggiung Limited acquires land and rental properties, recognising a bargain purchase gain of $354,868",
      cls="Alaska Native Village Corporation", cp="not named in the filing",
      role="Acquirer", cat="Acquisition", instr="Business combination (land and rental properties)",
      status="Completed", sclass="Completed", value="", vtype="",
      quote="Accordingly, the Corporation recognized a bargain purchase gain on the acquisition as follows: Excess of fair value over acquisition price $ 591,868 Recognition of deferred tax liability (237,000) Bargain purchase gain $ 354,868",
      notes="VALUE TRAP AVOIDED, TWICE: $591,868 is the EXCESS OF FAIR VALUE OVER THE ACQUISITION PRICE and $354,868 is the resulting BARGAIN PURCHASE GAIN. Neither is a price - the price itself is not stated, and it is necessarily LOWER than the fair value by $591,868. announced_value_usd is blank. Same shape as the Sealaska/Blue Sea Food trap in ANCSA_PORTAL_V2_LOG.",
      conf="Medium"),
 dict(cid="AS4555139-TX-013", corp="Gana-A'Yoo, Limited", fy="2018",
      date="2018-09-30",
      basis="FISCAL-YEAR-END PLACEHOLDER. The note states a price and no date in the extracted passage; Gana-A'Yoo's fiscal year ends September 30, so the calendar year is NOT determined by the fiscal year alone and this row is Medium confidence on its date.",
      title="Gana-A'Yoo, Limited completes an acquisition for $2,700,000 with a contingent increase of up to $300,000",
      cls="Alaska Native Village Corporation", cp="not named in the extracted passage",
      role="Acquirer", cat="Acquisition", instr="Acquisition with a contract-extension earn-up",
      status="Completed", sclass="Completed",
      value="2700000", vtype="Purchase price as stated",
      quote="The purchase price of the acquisition was $2,700,000.",
      notes="VALUE TRAP AVOIDED: the adjoining sentence says 'The purchase price may increase up to $300,000, calculated as $60,000 per year for each year a named contract extends past October 1, 2024, up to a maximum of five years.' That is a contingent increase and is not added. THE TARGET IS NOT NAMED in the extracted passage and the date is a placeholder - both should be settled from the source PDF before this row is merged.",
      conf="Low"),
 dict(cid="AS4555139-TX-014", corp="Alaska Peninsula Corporation", fy="2018",
      date="2018-12-31",
      basis="FISCAL-YEAR-END PLACEHOLDER - the extracted passage carries a price and no date.",
      title="Alaska Peninsula Corporation completes a purchase for $454,000 in cash and a $390,000 note payable",
      cls="Alaska Native Village Corporation", cp="not named in the extracted passage",
      role="Acquirer", cat="Acquisition", instr="Purchase with cash and a seller note",
      status="Completed", sclass="Completed",
      value="844000", vtype="Cash of $454,000 plus a $390,000 note payable, both stated as consideration for the purchase",
      quote="The purchase price recorded in cash was $454,000 and a $390,000 note payable for the purchase.",
      notes="The two components are both stated as consideration FOR THE PURCHASE, so they sum: 454,000 + 390,000 = 844,000. This is the one place in this file where a value is a sum, and it is written out here so a reviewer can refuse it. TARGET NOT NAMED and DATE IS A PLACEHOLDER - both must be settled from the source PDF before merging.",
      conf="Low"),

 dict(cid="AS4555139-TX-015", corp="Choggiung Limited", fy="2019",
      date="2018-08-01",
      basis="FISCAL-YEAR PLACEHOLDER. The FY ending 2019-03-31 report carries the acquisition-date allocation; the note does not give the acquisition date in the extracted passage, and the earnout runs 'from the acquisition date through July 31, 2021'.",
      title="Choggiung Limited acquires Bristol Industries, LLC",
      cls="Alaska Native Village Corporation", cp="Bristol Industries, LLC",
      role="Acquirer", cat="Acquisition", instr="Business combination with contingent consideration",
      status="Completed", sclass="Completed",
      value="2691398", vtype="CASH consideration only - see notes on the contingent half",
      quote="The following table summarizes the consideration paid for Bristol Industries, LLC and the amounts of estimated fair value of the assets acquired and liabilities assumed at the acquisition date: Consideration: Cash $ 2,691,398",
      notes="TWO DEFENSIBLE VALUES AND ONE CHOICE. The FY2020 report states Consideration: Cash $2,691,398, Contingent consideration arrangement $2,691,398, Fair value of total consideration transferred $5,382,796. Under ASC 805 the contingent half IS consideration, so $5,382,796 is a legitimate figure - but it is a fair-value ESTIMATE of a payment conditional on Bristol Industries' EBITDA through 2021-07-31, capped at $897,133 per closing anniversary, and the deals ledger's convention is to carry what was actually paid. announced_value_usd is the $2,691,398 of cash and BOTH figures are recorded here so a reviewer can take the other. DATE IS A PLACEHOLDER.",
      conf="Medium"),
 dict(cid="AS4555139-TX-016", corp="Natives of Kodiak, Incorporated", fy="2019",
      date="2019-04-01",
      basis="'On April 1, 2019, the Company's wholly owned subsidiary KOMAN Government Solutions, LLC (KGS) entered into a stock purchase agreement'",
      title="KOMAN Government Solutions, LLC acquires 100% of Trinity Analysis and Development Corporation",
      cls="Alaska Native Village Corporation", cp="Trinity Analysis and Development Corporation",
      role="Acquirer", cat="Acquisition", instr="Stock purchase agreement",
      status="Completed", sclass="Completed",
      value="1500000", vtype="Cash portion of the consideration; long-term debt is a further, separately stated component",
      quote="On April 1, 2019, the Company\u2019s wholly owned subsidiary KOMAN Government Solutions, LLC (KGS) entered into a stock purchase agreement to acquire 100% of the issued and outstanding shares of common stock of Trinity Analysis and Development Corporation, a Florida corporation, for $1,500,000 cash and long-term debt with a fa",
      notes="VALUE IS A FLOOR: the consideration is '$1,500,000 cash AND long-term debt', and the debt component is not quantified in this sentence. The same note adds 'three potential payments of additional purchase price of $250,000 each based on certain events occurring before the third anniversary of closing' - contingent, so excluded.",
      conf="High"),
 dict(cid="AS4555139-TX-017", corp="Natives of Kodiak, Incorporated", fy="2018",
      date="2018-11-21",
      basis="'On November 21, 2018, the Trust purchased a 13.5% ownership interest'",
      title="The Natives of Kodiak settlement trust purchases a 13.5% interest in Global Windcrest Partners II, LLC",
      cls="Alaska Native Village Corporation", cp="Global Windcrest Partners II, LLC",
      role="Equity investor", cat="Equity investment", instr="Purchase of a minority interest",
      status="Completed", sclass="Completed",
      value="499500", vtype="Total purchase price as stated",
      quote="On November 21, 2018, the Trust purchased a 13.5% ownership interest in Global Windcrest Partners II, LLC, a real estate company established for purposes of developing Global Windcrest II, LLC, for a total purchase price of $499,500.",
      notes="The buyer is the corporation's SETTLEMENT TRUST, not the corporation. Under ANCSA a settlement trust is a distinct legal person holding assets for shareholders, and the distinction should survive into the entity layer rather than be flattened to the corporation.",
      conf="High"),
 dict(cid="AS4555139-TX-018", corp="Bethel Native Corporation", fy="2019",
      date="2019-04-15",
      basis="MONTH-LEVEL ONLY - 'a lease purchase agreement executed in April 2019'. Mid-month placeholder.",
      title="Bethel Native Corporation completes a purchase of just over $20,000,000 through a lease purchase agreement",
      cls="Alaska Native Village Corporation", cp="not named in the extracted passage",
      role="Acquirer", cat="Acquisition", instr="Lease purchase agreement",
      status="Completed", sclass="Completed",
      value="20000000", vtype="'just over $20,000,000' - the filing's own words; the exact figure is not stated",
      quote="The purchase price was just over $20,000,000, secured through a lease purchase agreement executed in April 2019.",
      notes="THE FILING SAYS 'JUST OVER' AND GIVES NO EXACT FIGURE. $20,000,000 is therefore a FLOOR, and value_type says so. The target is not named in this passage and must be read from the source PDF before merging. This is the largest single village-corporation transaction in this wave.",
      conf="Medium"),
 dict(cid="AS4555139-TX-019", corp="Old Harbor Native Corporation", fy="2023",
      date="2023-06-30",
      basis="FISCAL-YEAR PLACEHOLDER - the allocation table gives no acquisition date in the extracted passage.",
      title="Old Harbor Native Corporation acquires EP Roofing, LLC",
      cls="Alaska Native Village Corporation", cp="EP Roofing, LLC",
      role="Acquirer", cat="Acquisition", instr="Business combination with a seller note and contingent consideration",
      status="Completed", sclass="Completed",
      value="4746526", vtype="Cash $3,123,186 plus the $1,623,340 note payable; the contingent $399,271 is excluded",
      quote="Consideration: Cash $ 3,123,186 Note payable 1,623,340 Contingent consideration 399,271 Fair value of consideration $ 5,145,797",
      notes="VALUE CHOICE MADE EXPLICIT: the filing's own 'Fair value of consideration' is $5,145,797 and includes $399,271 of CONTINGENT consideration, which the same note describes as 'up to $100,000 annually for five years, depending on EP Roofing, LLC's profitability.' announced_value_usd carries cash + note = $4,746,526, the amount actually owed regardless of performance. A reviewer who prefers the ASC 805 total should take $5,145,797; both are in this row. DATE IS A PLACEHOLDER.",
      conf="Medium"),
 dict(cid="AS4555139-TX-020", corp="Old Harbor Native Corporation", fy="2025",
      date="2025-06-30",
      basis="FISCAL-YEAR PLACEHOLDER - the allocation table gives no acquisition date in the extracted passage.",
      title="Old Harbor Native Corporation acquires STR Holdings, LLC for $21,791,744 in cash",
      cls="Alaska Native Village Corporation", cp="STR Holdings, LLC",
      role="Acquirer", cat="Acquisition", instr="Business combination",
      status="Completed", sclass="Completed",
      value="21791744", vtype="Cash transferred by Old Harbor, as stated",
      quote="The following table summarizes the consideration paid for STR Holdings, LLC along with the amounts of the assets acquired and liabilities assumed, which were recognized at the acquisition: Consideration Cash (Transferred by OHI) $ 21,791,744",
      notes="The largest transaction in this wave, and the second time Old Harbor appears - it acquired EP Roofing in FY2023 (AS4555139-TX-019). VALUE TRAP AVOIDED: the recognised assets in the same table ($8,923,493 cash, $30,776,942 other current assets, $28,257,741 property and equipment against $31,670,544 of current liabilities) are the ALLOCATION, not the price. DATE IS A PLACEHOLDER and must be settled before merging.",
      conf="Medium"),
 dict(cid="AS4555139-TX-021", corp="Kootznoowoo Incorporated", fy="2025",
      date="2025-06-30",
      basis="FISCAL-YEAR PLACEHOLDER - the consideration table gives no acquisition date in the extracted passage.",
      title="Kootznoowoo Incorporated completes an acquisition for total consideration of $2,980,000",
      cls="Alaska Native Village Corporation", cp="not named in the extracted passage",
      role="Acquirer", cat="Acquisition", instr="Business combination with deferred payments",
      status="Completed", sclass="Completed",
      value="2980000", vtype="Total consideration transferred, as stated: cash at closing plus two deferred payments",
      quote="Cash paid at closing $ 2,086,000 Deferred payment \u2013 first anniversary of closing 745,000 Deferred payment \u2013 second anniversary of closing 149,000 Total consideration transferred $ 2,980,000",
      notes="The deferred payments are FIXED by date, not contingent on performance, so they belong in the total and the filing itself sums them. A further $157,219 of the sellers' transaction costs was 'accounted for as additional consideration transferred' - NOT added here, because it is an accounting treatment of a cost rather than a price agreed between the parties, and adding it would make the row disagree with the filing's own stated total. TARGET NOT NAMED and DATE IS A PLACEHOLDER.",
      conf="Medium"),
 dict(cid="AS4555139-TX-022", corp="Paug-Vik Inc. Ltd.", fy="2025",
      date="2025-06-30",
      basis="FISCAL-YEAR PLACEHOLDER - the allocation gives no acquisition date in the extracted passage.",
      title="Paug-Vik Inc. Ltd. completes an acquisition for a total purchase price of $700,000",
      cls="Alaska Native Village Corporation", cp="not named in the extracted passage",
      role="Acquirer", cat="Acquisition", instr="Purchase of a business including a DOT lease",
      status="Completed", sclass="Completed",
      value="700000", vtype="Total purchase price, as stated and as cross-footed by the allocation",
      quote="The final purchase consideration was allocated to the assets acquired as follows: Building and improvement $ 282,500 Intangible asset \u2013 DOT lease 88,710 Goodwill 328,790 Total purchase price $ 700,000",
      notes="The allocation cross-foots: 282,500 + 88,710 + 328,790 = 700,000, which confirms the total is a price and not a fair-value estimate. TARGET NOT NAMED and DATE IS A PLACEHOLDER.",
      conf="Medium"),
 dict(cid="AS4555139-TX-023", corp="Shee Atika, Incorporated", fy="2021",
      date="2021-06-30",
      basis="FISCAL-YEAR PLACEHOLDER. The FY2024 report calls it 'the Lakota acquisition in 2021'; the FY2021 allocation gives no date in the extracted passage.",
      title="Shee Atika, Incorporated acquires Lakota",
      cls="Alaska Native Village Corporation", cp="Lakota (as named in the FY2024 report)",
      role="Acquirer", cat="Acquisition", instr="Business combination, part-funded by notes payable to individuals",
      status="Completed", sclass="Completed", value="", vtype="",
      quote="The purchase price allocation for the acquisition was as follows: Cash and cash equivalents $ 78,826 Accounts receivable 1,444,296 Property and equipment 93,770 Goodwill 5,166,154 Total Assets Acquired 6,783,046",
      notes="VALUE TRAP AVOIDED: $6,783,046 of Total Assets Acquired and $6,546,454 of Net Assets Acquired are the ALLOCATION, and $5,166,154 of it is GOODWILL. Neither is a stated price and the price is not stated. announced_value_usd is blank. Part of the price was a note payable to individuals, carried at $2,083,430 and secured by commercial property in Sitka - a BALANCE, not the price.",
      conf="Medium"),
 dict(cid="AS4555139-TX-024", corp="Shee Atika, Incorporated", fy="2024",
      date="2024-06-30",
      basis="FISCAL-YEAR PLACEHOLDER - 'An additional $2.5 million was added to the balance in FY24 for the acquisition of Eikon Research'.",
      title="Shee Atika, Incorporated acquires Eikon Research",
      cls="Alaska Native Village Corporation", cp="Eikon Research",
      role="Acquirer", cat="Acquisition", instr="Business combination, part-funded by notes payable to individuals",
      status="Completed", sclass="Completed", value="", vtype="",
      quote="An additional $2.5 million was added to the balance in FY24 for the acquisition of Eikon Research as discussed in Note 14.",
      notes="VALUE TRAP: the $2.5 million is an ADDITION TO THE NOTE-PAYABLE BALANCE for a portion of the purchase price, not the purchase price. announced_value_usd is blank. The FY2024 goodwill roll-forward shows $4,605,775 of goodwill acquired during the year, which is also not a price. DATE IS A PLACEHOLDER.",
      conf="Low"),
]


# The owner's rule inside one ANC: a sale between two subsidiaries of the same
# corporation is a relabelling, not a transaction.
ANCSA_INTRA_FAMILY_REFUSED = [
 ("Shee Atika: SAFE sells its interest in SAE to SAI, 2021, $147,000 cash, gain $175,824",
  "SAFE and SAI are both Shee Atika entities. The asset never leaves the family, so under the owner's rule this is a relabelling. The cash and the recognised gain are internal."),
 ("Shee Atika: SAFE sells its interest in AMTS to SAI, 2021, $117,000 cash, gain $145,055",
  "Same family, same reason."),
 ("Shee Atika: SAFE sells its interest in BAS to SAI, 2021, $49,000 cash, loss $52,433",
  "Same family, same reason. Note the LOSS - an internal transfer can book a loss, which is another reason it is not a market price."),
 ("Natives of Kodiak: the WCPB transaction, purchase price $4,500,000 against a carrying value of ($117,550)",
  "The filing says the difference 'was recorded to equity' AS A RESULT OF THE COMMON CONTROL. A common-control transaction is the accounting name for exactly what the owner's rule describes, and the $4,500,000 is not a market price. Refused."),
 ("Old Harbor: $108,333 contributed to Nuniaq Patrol, LLC 'to fund 1/3 of the vessel's purchase price'",
  "A capital contribution into a jointly owned vehicle is not the price of anything Old Harbor bought - the same trap ANCSA_PORTAL_V2_LOG records for Huna Totem's $2,550,000 into Na-Dena'."),
]

ANCSA_INTRA_OUT = REVIEW / "deals_ancsa_1031_intra_family_refused.csv"


def cmd_stage():
    out("=== 1031 stage - AS 45.55.139 transactions ===")
    out("")
    with open(EXTRACT_LOG, encoding="utf-8-sig", newline="") as fh:
        ex = list(csv.DictReader(fh))
    man = {}
    with open(MANIFEST, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            man[r["portal_document_id"]] = r
    # A corporation can have MORE THAN ONE document for a fiscal year, so
    # (corporation, year) does not identify the source. Locate the document by
    # SEARCHING for the quote instead: that both finds the right file and is
    # itself the evidence the quote exists. The (corporation, year) key is
    # kept only to break a tie.
    def _norm(t):
        return re.sub(r"\s+", " ", t)

    texts = {}
    for r in ex:
        if not r["txt_file"]:
            continue
        tf = CEDAR / r["txt_file"]
        if tf.exists():
            texts[r["portal_document_id"]] = (
                r, _norm(tf.read_text(encoding="utf-8", errors="replace")))

    def find_source(corp, fy, quote):
        q = _norm(quote).strip()
        hits = [r for r, t in texts.values() if q in t]
        if not hits:
            return None
        exact = [r for r in hits
                 if r["corporation_name"] == corp and r["period_covered"] == fy]
        if exact:
            return exact[0]
        same_corp = [r for r in hits if r["corporation_name"] == corp]
        return (same_corp or hits)[0]

    deals = _deals_index()
    tokfreq = {}
    for _, _, _, blob in deals:
        for t in set(re.findall(r"[a-z0-9]{4,}", blob)):
            tokfreq[t] = tokfreq.get(t, 0) + 1
    rows, missing = [], []
    for t in ANCSA_TX:
        src = find_source(t["corp"], t["fy"], t["quote"])
        if not src:
            missing.append(t["cid"])
            continue
        m = man.get(src["portal_document_id"], {})
        rows.append({
            "candidate_id": t["cid"], "event_date": t["date"],
            "event_year": t["date"][:4], "deal_title": t["title"],
            "native_party": t["corp"], "native_party_type": t["cls"],
            "counterparty": t["cp"], "native_party_role": t["role"],
            "deal_category": t["cat"], "instrument": t["instr"],
            "status": t["status"], "status_class": t["sclass"],
            "announced_value_usd": t["value"], "value_type": t["vtype"],
            "state": "AK", "industry": "",
            "date_basis": t["basis"], "notes": t["notes"],
            "confidence": t["conf"],
            "source_channel": "AS_45.55.139_annual_report",
            "portal_document_id": src["portal_document_id"],
            "source_url": m.get("portal_url", ""),
            "txt_file": src["txt_file"],
            "evidence_quote": t["quote"], "staged_by": SCRIPT,
            "staged_date": TODAY,
            "record_scope": "STAGED_CANDIDATE_NOT_MERGED",
            "already_in_deals_classified": _dupe_note(t, deals, tokfreq),
        })
    with open(STAGED_TX, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=TX_COLS)
        w.writeheader()
        w.writerows(rows)
    out(f"  {len(rows)} transactions -> {STAGED_TX.relative_to(CEDAR)}")
    if missing:
        out(f"  {len(missing)} not stageable - no extracted document "
            f"contains the quote: {', '.join(missing)}")
    with open(ANCSA_INTRA_OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["candidate", "why_refused", "refused_by", "refused_date"])
        for c, why in ANCSA_INTRA_FAMILY_REFUSED:
            w.writerow([c, why, SCRIPT, TODAY])
    out(f"  {len(ANCSA_INTRA_FAMILY_REFUSED)} intra-family transfers refused "
        f"-> {ANCSA_INTRA_OUT.relative_to(CEDAR)}")
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

    # I5  every staged transaction's quote must still be in its own text file,
    #     and any populated value must appear inside that quote
    if STAGED_TX.exists():
        with open(STAGED_TX, encoding="utf-8-sig", newline="") as fh:
            tx = list(csv.DictReader(fh))
        badq, badv = [], []
        for r in tx:
            tf = CEDAR / r["txt_file"]
            if not tf.exists():
                badq.append(r["candidate_id"])
                continue
            txt = re.sub(r"\s+", " ",
                         tf.read_text(encoding="utf-8", errors="replace"))
            q = re.sub(r"\s+", " ", r["evidence_quote"]).strip()
            if q not in txt:
                badq.append(r["candidate_id"])
                continue
            v = (r["announced_value_usd"] or "").strip()
            if not v:
                continue
            try:
                target = float(v.replace(",", ""))
            except ValueError:
                badv.append(r["candidate_id"])
                continue
            nums = []
            for m2 in re.finditer(r"([\d][\d,]*(?:\.\d+)?)", q):
                try:
                    nums.append(float(m2.group(1).replace(",", "")))
                except ValueError:
                    pass
            # a value is admissible if it is stated, or is the sum of exactly
            # two stated figures (the Alaska Peninsula cash + note case, which
            # the row itself writes out)
            ok_v = any(abs(n - target) < 0.5 for n in nums)
            if not ok_v:
                for i in range(len(nums)):
                    for j in range(i + 1, len(nums)):
                        if abs(nums[i] + nums[j] - target) < 0.5:
                            ok_v = True
                            break
                    if ok_v:
                        break
            if not ok_v:
                badv.append(r["candidate_id"])
        out(f"  I5 staged quote present in its own text file: "
            f"{len(tx) - len(badq)}/{len(tx)}")
        out(f"  I6 staged value derivable from its own quote: "
            f"{len(tx) - len(badv)}/{len(tx)}")
        if badq:
            fails.append(f"I5 quote not found: {', '.join(badq)}")
        if badv:
            fails.append(f"I6 value not in quote: {', '.join(badv)}")

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
    if cmd == "stage":
        return cmd_stage()
    if cmd == "verify":
        return cmd_verify()
    if cmd == "verify-synthetic":
        return cmd_verify_synthetic()
    out(f"unknown command {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
