"""Fetch helper for the federal award-list retrieval run (2026-08-05).

curl + declared browser User-Agent (the sec.gov trick from the 2000-2019 backfill).
Saves raw bytes to data/raw/external/federal_award_lists/ and returns decoded text.
"""
import subprocess, re, html, os, sys, io, csv, datetime

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

RAW = r"C:\Users\esm247\Desktop\Cedar Press\data\raw\external\federal_award_lists"
os.makedirs(RAW, exist_ok=True)

MANIFEST = []


def fetch(url, fname=None, extra_headers=None, timeout=90):
    """Return (status, bytes). Saves to RAW/fname when fname given."""
    cmd = ["curl", "-s", "-L", "-A", UA,
           "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8",
           "-H", "Accept-Language: en-US,en;q=0.9",
           "--max-time", str(timeout),
           "-w", "\n__HTTPSTATUS__%{http_code}", url]
    for h in (extra_headers or []):
        cmd[4:4] = ["-H", h]
    p = subprocess.run(cmd, capture_output=True)
    out = p.stdout
    m = re.search(rb"\n__HTTPSTATUS__(\d+)$", out)
    status = int(m.group(1)) if m else 0
    body = out[:m.start()] if m else out
    if fname:
        with open(os.path.join(RAW, fname), "wb") as f:
            f.write(body)
        MANIFEST.append(dict(file=fname, url=url, http_status=status,
                             bytes=len(body),
                             fetched_date=datetime.date.today().isoformat()))
    return status, body


def text(body):
    t = body.decode("utf-8", "replace")
    m = re.search(r"<main.*?</main>", t, re.S | re.I)
    b = m.group(0) if m else t
    b = re.sub(r"<(script|style)\b.*?</\1>", "", b, flags=re.S | re.I)
    b = re.sub(r"<br\s*/?>", "\n", b, flags=re.I)
    b = re.sub(r"</(p|div|li|tr|h\d)>", "\n", b, flags=re.I)
    s = html.unescape(re.sub(r"<[^>]+>", "\n", b))
    return "\n".join(l.strip() for l in s.split("\n") if l.strip())


def save_manifest(path=None):
    path = path or os.path.join(RAW, "_SOURCE_MANIFEST.csv")
    exist = []
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig", newline="") as f:
            exist = list(csv.DictReader(f))
    seen = {r["file"] for r in exist}
    rows = exist + [r for r in MANIFEST if r["file"] not in seen]
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "url", "http_status", "bytes", "fetched_date"])
        w.writeheader()
        w.writerows(rows)
    return len(rows)
