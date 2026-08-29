#!/usr/bin/env python3
"""
16b_extract_funding_rulings.py
Extract every per-recipient ruling from the LINEAGE A hand-checked do-files
(Cedar Press/Federal Spending/code/fed_funding_do_file*.do) into
data/spine/federal_funding_rulings_from_dofile.csv.

Zero fabrication: identifier strings, reasons and line numbers are copied
verbatim from the do-file. reason = the comment the analyst wrote adjacent to
the ruling (trailing // comment, else the ** comment on the following line,
else the ** comment on the preceding line). Blank when the analyst wrote none.
"""
import csv, os, re, datetime, collections
from pathlib import Path

CEDAR = str(Path(__file__).resolve().parent.parent)
CODE  = os.path.join(CEDAR, "Federal Spending", "code")
OUT   = os.path.join(CEDAR, "data", "spine", "federal_funding_rulings_from_dofile.csv")
LOG   = os.path.join(CEDAR, "logs", "16_federal_funding_recon_2026-08-05.log")

_logf = open(LOG, "a", encoding="utf-8")
def log(m):
    line = f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}][RULINGS] {m}"
    print(line, flush=True); _logf.write(line + "\n"); _logf.flush()

URL = re.compile(r"https?://\S+")
COMMENT = re.compile(r"^\s*(\*+|//)\s?(.*)$")

def is_comment(s):
    m = COMMENT.match(s)
    return m.group(2).strip() if m else None

def harvest(path):
    src = os.path.basename(path)
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    out = []
    # running URL context: the analyst put reference URLs in section headers
    section_url = ""
    for i, raw in enumerate(lines):
        ln = i + 1
        u = URL.search(raw)
        if u and is_comment(raw) is not None:
            section_url = u.group(0).rstrip(".,")
        s = raw.strip()
        if not s or is_comment(raw) is not None:
            continue

        # ---- reason: trailing // comment on the same line
        reason = ""; uncertain = False
        tr = re.search(r"//\s*(.+)$", s)
        if tr: reason = tr.group(1).strip()
        # ---- else comment on the next non-blank line (the file's dominant style)
        if not reason:
            for j in (i + 1, i + 2):
                if j < len(lines):
                    c = is_comment(lines[j])
                    if c:
                        # skip pure section banners
                        if not set(lines[j].strip()) <= {"*"}:
                            reason = c.strip(); break
                    if lines[j].strip():
                        break
        # ---- else comment on the previous line. This one CAN belong to the
        #      preceding ruling, so it is emitted with an explicit caveat
        #      rather than asserted as this ruling's reason.
        if not reason and i > 0:
            c = is_comment(lines[i - 1])
            if c and not set(lines[i - 1].strip()) <= {"*"}:
                reason = c.strip(); uncertain = True
        reason = reason.replace('"', "'")
        if uncertain and reason:
            reason = "[preceding comment, attribution uncertain] " + reason
        # evidence_url is asserted ONLY when the URL is in this ruling's own
        # comment. Section-level URLs are not propagated (would be fabrication).
        ev = URL.search(reason)
        evidence = ev.group(0).rstrip(".,") if ev else ""

        def add(idt, ident, ent, ruling, extra=""):
            out.append({"identifier_type": idt, "identifier": ident,
                        "entity_name": ent, "ruling": ruling,
                        "reason": (extra + " " + reason).strip(),
                        "evidence_url": evidence, "source_file": src,
                        "source_line": ln})

        # ================= EXCLUDE: flag=1 on an exact recipient name
        m = re.match(r'^replace\s+flag\s*=\s*1\s+if\s+((?:Tribe\s*==\s*".*?"\s*\|?\s*)+)$', s)
        if m:
            for nm in re.findall(r'Tribe\s*==\s*"(.*?)"', m.group(1)):
                add("recipient_name_exact", nm, nm, "EXCLUDE",
                    "flag=1 then 'drop if flag==1' (line 1275).")
            continue
        m = re.match(r'^replace\s+flag\s*=\s*1\s+if\s+(.*)$', s)
        if m:
            add("stata_condition", m.group(1), "", "EXCLUDE",
                "flag=1 then 'drop if flag==1'.")
            continue

        # ================= EXCLUDE: drop on exact recipient name(s)
        if re.match(r"^drop\s+if\s+Tribe\s*==", s):
            names = re.findall(r'Tribe\s*==\s*"(.*?)"', s)
            for nm in names:
                add("recipient_name_exact", nm, nm, "EXCLUDE",
                    "explicit 'drop if Tribe==' in the exclusion block.")
            continue

        # ================= EXCLUDE: pattern drops
        m = re.match(r'^drop\s+if\s+strpos\(\s*Tribe\s*,\s*"(.*?)"\s*\)\s*==\s*1(.*)$', s)
        if m:
            add("recipient_name_prefix", m.group(1), "", "EXCLUDE",
                "prefix-pattern drop." + (" cond:" + m.group(2).strip() if m.group(2).strip() else ""))
            continue
        m = re.match(r'^drop\s+if\s+regexm\(\s*Tribe\s*,\s*"(.*?)"\s*\)\s*==\s*1(.*)$', s)
        if m:
            add("recipient_name_regex", m.group(1), "", "EXCLUDE",
                "substring-pattern drop." + (" cond:" + m.group(2).strip() if m.group(2).strip() else ""))
            continue
        m = re.match(r'^gen\s+dummy\s*=\s*1\s+if\s+regexm\(\s*Tribe\s*,\s*"(.*?)"\s*\)\s*==\s*1(.*)$', s)
        if m:
            add("recipient_name_regex", m.group(1), "", "EXCLUDE",
                "flagged via dummy then dropped (drop if dummy==1).")
            continue
        m = re.match(r'^drop\s+if\s+recipient_state_code\s*==\s*"(.*?)"\s*$', s)
        if m:
            add("recipient_state_code", m.group(1), "", "EXCLUDE",
                "whole-state exclusion applied before any tribe matching.")
            continue

        # ================= INCLUDE: tribe_id assignments
        m = re.match(r'^replace\s+tribe_id\s*=\s*(\d+)\s+if\s+(.*)$', s)
        if m:
            tid, cond = m.group(1), m.group(2)
            cond = re.sub(r"//.*$", "", cond).strip()
            mm = re.match(r'^strpos\(\s*Tribe\s*,\s*"(.*?)"\s*\)\s*==\s*1(.*)$', cond)
            if mm:
                add("recipient_name_prefix", mm.group(1), "", "INCLUDE",
                    f"assigned tribe_id={tid}." +
                    (" cond:" + mm.group(2).strip() if mm.group(2).strip() else ""))
                continue
            mm = re.match(r'^Tribe\s*==\s*"(.*?)"(.*)$', cond)
            if mm:
                add("recipient_name_exact", mm.group(1), mm.group(1), "INCLUDE",
                    f"assigned tribe_id={tid}." +
                    (" cond:" + mm.group(2).strip() if mm.group(2).strip() else ""))
                continue
            mm = re.match(r'^regexm\(\s*Tribe\s*,\s*"(.*?)"\s*\)\s*==\s*1(.*)$', cond)
            if mm:
                add("recipient_name_regex", mm.group(1), "", "INCLUDE",
                    f"assigned tribe_id={tid}." +
                    (" cond:" + mm.group(2).strip() if mm.group(2).strip() else ""))
                continue
            add("stata_condition", cond, "", "INCLUDE", f"assigned tribe_id={tid}.")
            continue
    return out

if __name__ == "__main__":
    log("#" * 60)
    rows = []
    for f in ["fed_funding_do_file_corrtd.do", "fed_funding_do_file.do"]:
        p = os.path.join(CODE, f)
        r = harvest(p)
        log(f"{f}: {len(r)} rulings extracted from {sum(1 for _ in open(p, encoding='utf-8', errors='replace'))} lines")
        rows += r
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    cols = ["identifier_type", "identifier", "entity_name", "ruling", "reason",
            "evidence_url", "source_file", "source_line"]
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    log(f"wrote {OUT}: {len(rows):,} rows")
    c = collections.Counter((r["ruling"], r["identifier_type"]) for r in rows)
    for k, v in sorted(c.items()): log(f"   {k[0]:8} {k[1]:24} {v:>6,}")
    log(f"   rulings carrying an analyst comment: "
        f"{sum(1 for r in rows if len(r['reason'].split('.', 1)[-1].strip()) > 0):,}")
    log(f"   rulings carrying an evidence URL   : {sum(1 for r in rows if r['evidence_url']):,}")
