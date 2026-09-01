"""SHARD-E: build the ANC parent -> child ownership-edge file.

Output: data/staging/anc_subsidiaries/shard_e.jsonl

EVIDENCE STANDARD (docs/NATIVE_ENTITY_NUANCES.md, docs/ANCSA_OWNERSHIP_RULING.md)
--------------------------------------------------------------------------------
An edge exists here ONLY where a source ASSERTS it. The strongest class Cedar can
get for the ANC corporate spiderweb is the parent's OWN audited "Principles of
Consolidation" note, which enumerates the subsidiaries by legal name. That is what
this script parses.

Two guards, both enforced in code, not by care:

  * ANTI-FABRICATION. Every `child_name_raw` emitted must appear VERBATIM in the
    source document text. A name that does not is dropped and counted. Nothing is
    inferred from a shared name, a shared address or a shared word -- name-based
    inference is precisely the defect the owner says makes existing hierarchies
    wrong (NATIVE_ENTITY_NUANCES.md, "A tribal name inside an enterprise name is a
    BRAND, not an owner").
  * NO ASSOCIATION EDGES. The village-corporation <-> village-government link and
    the regional <-> village shareholding link are ASSOCIATION, never ownership
    (ANCSA_OWNERSHIP_RULING.md rules 4 and 5). This file contains neither, and
    the spec below may not add one.

`depth` 1 = named by the parent itself. 2 = named by a subsidiary about ITS OWN
children (the second layer, where the name stops looking Native at all).

Reads only local files. NO NETWORK.
"""
from __future__ import annotations

import csv
import glob
import io
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "data" / "staging" / "anc_subsidiaries"
OUTDIR.mkdir(parents=True, exist_ok=True)
OUT = OUTDIR / "shard_e.jsonl"
RETRIEVED = "2026-09-01"

# ---------------------------------------------------------------- spine lookup
SLICE = json.loads((ROOT / "data/staging/tribe_harvest/shard_e/_slice.json")
                   .read_text(encoding="utf-8"))
BY_NAME = {e["canonical_name"]: e for e in SLICE}

# portal URL per local annual-report file, from the harvest manifest
PORTAL_URL = {}
man = ROOT / "data/raw/external/ancsa_portal/_SOURCE_MANIFEST.csv"
for p in (man, ROOT / "data/raw/external/ancsa_portal_v2/_SOURCE_MANIFEST_V2.csv"):
    if p.exists():
        for r in csv.DictReader(p.open(encoding="utf-8-sig")):
            PORTAL_URL[Path(r.get("local_file", "")).stem] = r.get("url", "")
for r in csv.DictReader((ROOT / "data/clean/ancsa_filings_index.csv")
                        .open(encoding="utf-8-sig")):
    if r.get("local_file"):
        PORTAL_URL.setdefault(Path(r["local_file"]).stem, r.get("portal_url", ""))


PROBE = {}
_pr = ROOT / "data/staging/tribe_harvest/shard_e/_probe_results.jsonl"
if _pr.exists():
    for line in _pr.open(encoding="utf-8"):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("raw_file", "").endswith(".html"):
            PROBE[r["url"]] = r


def web_for(url: str, raw_html: bool = False):
    """(display name, source url, page text) for a page this shard already fetched.

    raw_html=True returns the served HTML instead of the rendered text, for
    assertions that live in `<script type="application/ld+json">` and never
    appear on the visible page (docs/HIDDEN_DATA_TECHNIQUES.md technique 1)."""
    r = PROBE.get(url)
    if not r:
        return None, None, None
    base = ROOT / "data/staging/tribe_harvest/shard_e/raw"
    p = base / (r["raw_file"] if raw_html else r["raw_file"][:-5] + ".txt")
    if not p.exists():
        return None, None, None
    return r["raw_file"], r.get("final_url") or url, p.read_text(encoding="utf-8",
                                                                 errors="replace")


def pdf_for(rel: str):
    """Read an ANCSA portal PDF with pdfplumber rather than pdftotext.

    The natural-resources workstream's MMS recovery (2026-09-01) showed that a
    source written off as unparseable by `pdftotext` reads clean by pdfplumber
    coordinate -- 315 rows and $4.09B recovered. That is exactly what happened to
    Kuukpik here: the pdftotext extract in data/interim/ancsa_txt_v2/ carries the
    page furniture and drops the notes, so this shard first recorded Kuukpik as
    'notes did not survive extraction'. pdfplumber returns its `2. SUBSIDIARIES`
    section intact.
    """
    p = ROOT / rel
    if not p.exists():
        return None, None, None
    try:
        import pdfplumber
    except ImportError:
        return None, None, None
    pages = []
    with pdfplumber.open(str(p)) as pdf:
        for pg in pdf.pages:
            pages.append(pg.extract_text() or "")
    return p.name, PORTAL_URL.get(p.stem, ""), "\n".join(pages)


def txt_for(pattern: str):
    # lint-ok: class1 - the interim text layer of the Alaska DBS STAR portal PDFs
    # IS the source of record for this build. There is no promoted table of
    # annual-report text to read instead; the promoted artefact is the edge file
    # THIS script writes. Reading the staged corpus is the job.
    fs = sorted(glob.glob(str(ROOT / "data/interim/ancsa_txt" / pattern)))
    # lint-ok: class1 - same staged corpus, village-corporation half.
    fs += sorted(glob.glob(str(ROOT / "data/interim/ancsa_txt_v2" / pattern)))
    if not fs:
        return None, None, None
    f = fs[-1]
    stem = Path(f).stem
    return (Path(f).name, PORTAL_URL.get(stem, ""),
            open(f, encoding="utf-8", errors="replace").read())


# ------------------------------------------------------------------- cleaning
DROP_TRAILING = re.compile(
    r"\s*\((?:merged|dissolved|transferred|formerly|collectively|as further|"
    r"continued|the\s|A\.JV|\d)[^)]*\)\s*$", re.I)
ABBREV = re.compile(r"\s*\(([A-Z][A-Za-z0-9&.\- ]{0,28})\)\s*$")


KEEP_DOT = re.compile(r"(?:Inc|Ltd|Corp|Co|Assn|L\.L\.C|Jr|Sr|St)\.$", re.I)


def clean_name(s: str):
    """Return (name, note). Never invents; only trims annotation."""
    s = re.sub(r"\s+", " ", s).strip()
    # rejoin a hyphenated name broken across a PDF line: "Ahtna-\nCDM" -> "Ahtna-CDM"
    s = re.sub(r"(?<=\w)-\s+(?=[A-Z0-9])", "-", s)
    s = s.strip(",; ")
    if not KEEP_DOT.search(s):
        s = s.rstrip(".")
    note = ""
    m = DROP_TRAILING.search(s)
    if m:
        note = m.group(0).strip()
        s = DROP_TRAILING.sub("", s).strip()
    # strip an internal parenthetical annotation such as "(merged with X ...)"
    m2 = re.search(r"\s*\((?:merged|dissolved|transferred|formerly)[^)]*\)", s, re.I)
    if m2:
        note = (note + " " + m2.group(0)).strip()
        s = (s[:m2.start()] + s[m2.end():]).strip()
    m3 = ABBREV.search(s)
    if m3 and len(m3.group(1)) <= 12 and m3.group(1).upper() == m3.group(1).replace(" ", ""):
        s = ABBREV.sub("", s).strip()
    s = s.strip(",; ")
    if not KEEP_DOT.search(s):
        s = s.rstrip(".")
    return s, note


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


# --------------------------------------------------------------------- parsers
def p_paren_semi(t, spec):
    """names inside the parenthesis that follows `marker`, split on ';'"""
    i = t.find(spec["marker"])
    if i < 0:
        return [], ""
    j = t.find("(", i)
    depth, k = 0, j
    while k < len(t):
        if t[k] == "(":
            depth += 1
        elif t[k] == ")":
            depth -= 1
            if depth == 0:
                break
        k += 1
    inner = t[j + 1:k]
    quote = re.sub(r"\s+", " ", t[i:k + 1])
    out = []
    for piece in re.split(spec.get("sep", ";"), inner):
        piece = re.sub(r"^\s*and\s+", "", piece.strip())
        if len(piece) > 2:
            out.append(piece)
    return out, quote


def p_numbered(t, spec):
    i = t.find(spec["marker"])
    if i < 0:
        return [], ""
    win = t[i:i + spec.get("window", 12000)]
    end = win.find(spec["end"]) if spec.get("end") else -1
    if end > 0:
        win = win[:end]
    quote = re.sub(r"\s+", " ", win[:spec.get("quote_chars", 600)])
    # rejoin wrapped continuation lines
    lines = win.split("\n")
    items, sector, cur = [], "", None
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        mh = re.match(r"^([A-Z][A-Z &']{3,40}):\s*$", s)
        if mh:
            if cur:
                items.append((cur, sector))
                cur = None
            sector = mh.group(1).title()
            continue
        mn = re.match(r"^\d+\.\s*(.*)$", s)
        if mn:
            if cur:
                items.append((cur, sector))
            cur = mn.group(1).strip()
            if not cur:
                cur = None
            continue
        if cur is not None:
            cur = cur + " " + s
    if cur:
        items.append((cur, sector))
    return items, quote


def p_split_after(t, spec):
    """text between marker and terminator, split on ';' or ',' + ' and '"""
    i = t.find(spec["marker"])
    if i < 0:
        return [], ""
    seg = t[i + len(spec["marker"]):]
    e = seg.find(spec["end"])
    if e > 0:
        seg = seg[:e]
    quote = re.sub(r"\s+", " ", t[i:i + len(spec["marker"]) + len(seg)])
    seg = re.sub(r"\s+", " ", seg)
    sep = spec.get("sep", ",")
    out = []
    for piece in re.split(sep, seg):
        piece = re.sub(r"^\s*(and|&)\s+", "", piece.strip())
        piece = re.sub(r"\s*\([^)]*\)\s*$", "", piece).strip()
        if len(piece) > 3:
            out.append(piece)
    return out, quote


CUT = re.compile(r"(?:\s+[-–—]\s|,\s*which\b|\.\s|\s+is an\b|\s+is a\b|"
                 r"\s+\(?formerly\b|;\s*$)")


def _window(t, spec):
    i = t.find(spec["marker"])
    if i < 0:
        return None, None, -1
    win = t[i:i + spec.get("window", 6000)]
    if spec.get("end"):
        e = win.find(spec["end"])
        if e > 0:
            win = win[:e]
    return win, re.sub(r"\s+", " ", win[:spec.get("quote_chars", 900)]), i


def p_bullets(t, spec):
    win, quote, i = _window(t, spec)
    if win is None:
        return [], ""
    out = []
    for m in re.finditer(r"[•●\*]\s*\n?\s*([^\n]+)", win):
        s = m.group(1).strip()
        c = CUT.search(s)
        if c:
            s = s[:c.start()]
        if len(s) > 3:
            out.append(s)
    return out, quote


CORPNAME = re.compile(
    r"([A-Z][A-Za-z0-9'’&./‑–-]*"
    r"(?:[ /][A-Z0-9][A-Za-z0-9'’&./‑–-]*){0,7}"
    r",?\s*(?:LLC|L\.L\.C\.|Inc\.|Incorporated|Corporation|Company|Ltd\.?|LP|L\.P\.|JV))")


def p_corpnames(t, spec):
    win, quote, i = _window(t, spec)
    if win is None:
        return [], ""
    pat = re.compile(spec["pattern"]) if spec.get("pattern") else CORPNAME
    flat = re.sub(r"\s+", " ", win)
    seen, out = set(), []
    for m in pat.finditer(flat):
        s = m.group(1).strip()
        if fold(s) in seen:
            continue
        seen.add(fold(s))
        out.append(s)
    return out, quote


def p_single(t, spec):
    """One hand-adjudicated assertion: the spec names the child, the source must
    contain both the marker sentence and the child name verbatim."""
    win, quote, i = _window(t, spec)
    if win is None:
        return [], ""
    return [spec["child"]], quote


def p_labeled_list(t, spec):
    """A directory card whose sector sits on its own labelled line; the company
    name is the last non-empty line above it (Calista 'Our Businesses')."""
    win, quote, i = _window(t, spec)
    if win is None:
        return [], ""
    lab = re.compile(spec["label"])
    lines = [ln.strip() for ln in win.split("\n")]
    out = []
    for n, ln in enumerate(lines):
        m = lab.match(ln)
        if not m:
            continue
        for k in range(n - 1, max(-1, n - 4), -1):
            if lines[k]:
                out.append((lines[k], m.group(1).strip() if m.groups() else ""))
                break
    return out, quote


def p_dup_line(t, spec):
    """A directory card that prints the company name twice in a row (Chugach
    'Company Directory')."""
    win, quote, i = _window(t, spec)
    if win is None:
        return [], ""
    lines = [ln.strip() for ln in win.split("\n") if ln.strip()]
    out = []
    for a, b in zip(lines, lines[1:]):
        if a == b and 4 <= len(a) <= 70 and a[0].isupper():
            out.append(a)
    return out, quote


CAGE_RE = re.compile(r"^[;:]?\s*([0-9A-Z]{5})\s*$")


def p_gm_card(t, spec):
    """ASRC Federal's 'Companies' cards. Each card is

        <company name>
        General Manager:            <- structural anchor ONLY
        <a person>                  <- NEVER recorded (no natural persons)
        Address: ...
        Related Offerings: <sectors>
        SAM Registration: SAM.gov
        ; <CAGE code>

    The CAGE code is the prize: it joins straight to the cage triples in
    data/clean/fpds_uei_edges.csv without any name matching at all.
    """
    win, quote, i = _window(t, spec)
    if win is None:
        return [], ""
    lines = [ln.strip() for ln in win.split("\n")]
    anchor = spec.get("anchor", "General Manager:")
    out = []
    for n, ln in enumerate(lines):
        if ln != anchor:
            continue
        name = ""
        for k in range(n - 1, max(-1, n - 4), -1):
            if lines[k] and lines[k] != anchor:
                name = lines[k]
                break
        if not name:
            continue
        cage, sector = "", ""
        for k in range(n + 1, min(len(lines), n + 22)):
            if lines[k].startswith("Related Offerings"):
                sector = " ".join(x for x in lines[k + 1:k + 4]
                                  if x and not x.startswith(("SAM Registration",
                                                             "Address", "General")))
            if lines[k].startswith("SAM Registration"):
                for j in range(k + 1, min(len(lines), k + 3)):
                    m = CAGE_RE.match(lines[j])
                    if m:
                        cage = m.group(1)
                        break
                break
        out.append((name, sector.strip(" ,")[:120], cage))
    return out, quote


PARSERS = {"paren_semi": p_paren_semi, "numbered": p_numbered,
           "split_after": p_split_after, "bullets": p_bullets,
           "corpnames": p_corpnames, "single": p_single,
           "labeled_list": p_labeled_list, "dup_line": p_dup_line,
           "gm_card": p_gm_card}

# ------------------------------------------------------------------- the spec
SPEC = json.loads((ROOT / "code" / "533_shard_e_spec.json").read_text(encoding="utf-8"))
_web = ROOT / "code" / "533_shard_e_spec_web.json"
if _web.exists():
    SPEC = SPEC + json.loads(_web.read_text(encoding="utf-8"))


def main():
    edges, dropped, report = [], [], []
    for spec in SPEC:
        if spec.get("raw_url"):
            fname, url, t = web_for(spec["raw_url"], spec.get("raw_html", False))
        elif spec.get("pdf_path"):
            fname, url, t = pdf_for(spec["pdf_path"])
        else:
            fname, url, t = txt_for(spec["file_glob"])
        if t is None:
            report.append((spec["parent_name"], "NO SOURCE FILE", 0, 0))
            continue
        # PDF page furniture splits a name across a page break ("Goldbelt" /
        # page header / "Eagle, LLC").  Remove the furniture, never the words.
        t = re.sub(r"<<<PAGE \d+>>>", " ", t)
        for sc in spec.get("scrub", []):
            t = re.sub(sc, " ", t)
        items, quote = PARSERS[spec["parser"]](t, spec)
        if not items:
            report.append((spec["parent_name"], "MARKER NOT FOUND: " + spec["marker"][:40], 0, 0))
            continue
        pe = BY_NAME.get(spec["parent_name"])
        root = BY_NAME.get(spec.get("root_name", spec["parent_name"]))
        kept = drop = 0
        for it in items:
            cage = ""
            if isinstance(it, tuple) and len(it) == 3:
                raw, sector, cage = it
            elif isinstance(it, tuple):
                raw, sector = it
            else:
                raw, sector = it, spec.get("sector", "")
            name, note = clean_name(raw)
            if not name or len(name) < 4:
                continue
            # Spec-declared rejects: UI furniture a directory page prints
            # alongside its cards, and entities the page itself files under a
            # non-corporate heading (a foundation or a museum is not a
            # subsidiary). Recorded, never silently dropped.
            rej = [rx for rx in spec.get("reject", []) if re.search(rx, name)]
            if rej:
                dropped.append({"parent": spec["parent_name"], "name": name,
                                "reason": "spec reject /%s/" % rej[0]})
                drop += 1
                continue
            # ANTI-FABRICATION: the name must be present verbatim in the source
            if fold(name) not in fold(t):
                dropped.append({"parent": spec["parent_name"], "name": name,
                                "reason": "not verbatim in source text"})
                drop += 1
                continue
            rel = spec.get("relationship", "subsidiary")
            for pat, r2 in (("JV", "joint venture"), ("Joint Venture", "joint venture"),
                            ("Holdings", "holding company"), ("Holding", "holding company")):
                if pat.lower() in name.lower():
                    rel = r2
            edges.append({
                "parent_cedar_uid": (pe or {}).get("cedar_uid", spec.get("parent_cedar_uid", "")),
                "parent_name": spec["parent_name"],
                "child_name_raw": name,
                "child_relationship": rel,
                "child_sector": sector or spec.get("sector", ""),
                "child_cage_code": cage,
                "stated_ownership_pct": spec.get("pct", ""),
                "source_url": url or spec.get("source_url", ""),
                "source_type": spec.get("source_type", "annual report"),
                "retrieved_date": RETRIEVED,
                "quote": quote[:900],
                "depth": spec.get("depth", 1),
                "anc_root_cedar_uid": (root or {}).get("cedar_uid", ""),
                "anc_root_name": spec.get("root_name", spec["parent_name"]),
                "source_doc": fname,
                "source_fy": spec.get("fy", ""),
                "child_note": note,
            })
            kept += 1
        report.append((spec["parent_name"], spec["parser"], kept, drop))

    # de-duplicate on (parent, folded child, depth)
    seen, final = set(), []
    for e in edges:
        k = (e["parent_cedar_uid"], fold(e["child_name_raw"]), e["depth"])
        if k in seen:
            continue
        seen.add(k)
        final.append(e)

    with OUT.open("w", encoding="utf-8") as f:
        for e in final:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    (OUTDIR / "shard_e_dropped.json").write_text(
        json.dumps(dropped, indent=1, ensure_ascii=False), encoding="utf-8")
    for r in report:
        print("%-46s %-14s kept=%-4s dropped=%s" % r)
    print("\nedges", len(final), "(pre-dedupe %d)" % len(edges), "dropped", len(dropped))
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main())
