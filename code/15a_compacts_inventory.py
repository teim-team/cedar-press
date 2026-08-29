#!/usr/bin/env python3
"""
15a_compacts_inventory.py -- Cedar Press Compacts dataset, Step A.

Inventories the local copy of the BIA Office of Indian Gaming compact PDF
archive and reports:
  1. filename parse rate (date + tribe token) -- NO date is ever guessed
  2. reconciliation of PDFs on disk vs. the BIA index CSV
  3. an honest assessment of the two prior extractions carried over from
     the votingpatterns project.

Zero fabrication: every emitted field is either read verbatim from a source
file or derived by an explicitly-named deterministic rule.
"""
import csv, os, re, sys, json, collections, io

BASE = r"C:\Users\esm247\Desktop\Cedar Press"
EXT  = os.path.join(BASE, "data", "raw", "external", "compacts")
PDF  = os.path.join(EXT, "pdf")
TXT  = os.path.join(EXT, "text")
IDX  = os.path.join(EXT, "index", "bia_compact_index.csv")
PRIOR= os.path.join(EXT, "prior_extractions")
INT  = os.path.join(BASE, "data", "interim")
os.makedirs(INT, exist_ok=True)

out = io.StringIO()
def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.write(s + "\n")

# ---------------------------------------------------------------- filename parse
# Observed prefix variants: "508_compliant_", "508 Compliant ", "508 Compliant.",
# "508 Compliant" (no sep), "508 Compliant  " (double space), "508 C ".
PREFIX = re.compile(r'^\s*508[ _]?(?:compliant|c)\b[ _.]*', re.I)
# Date forms actually present in the archive. Both are unambiguous because the
# 4-digit year anchors the order. We never accept a bare 2-digit component pair.
D_YMD = re.compile(r'(?<!\d)(19\d{2}|20\d{2})[._-](\d{1,2})[._-](\d{1,2})(?!\d)')
D_MDY = re.compile(r'(?<!\d)(\d{1,2})[._-](\d{1,2})[._-](19\d{2}|20\d{2})(?!\d)')
YEAR_ONLY = re.compile(r'(?<!\d)(19\d{2}|20\d{2})(?!\d)')

# Trailing document-type boilerplate stripped to isolate the tribe token.
DOCTYPE = re.compile(
    r'\b(tribal[ _]state[ _]gaming[ _]compact|gaming[ _]compact|compact'
    r'|secretarial[ _]procedures|gaming[ _]procedures|procedures'
    r'|agreement[ _]to[ _]amend|amendment|amendments|amended'
    r'|deemed[ _]approved|extension|restated|and|&)\b', re.I)

def parse_filename(fn):
    """Return dict with parsed_date (ISO or ''), date_form, tribe_token, flags."""
    stem = os.path.splitext(fn)[0]
    body = PREFIX.sub('', stem)
    had_prefix = body != stem
    d, form, span = '', '', None
    m = D_YMD.search(body)
    if m:
        y, mo, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12 and 1 <= dd <= 31:
            d, form, span = f"{y:04d}-{mo:02d}-{dd:02d}", "YYYY.MM.DD", m.span()
    if not d:
        m = D_MDY.search(body)
        if m:
            mo, dd, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= mo <= 12 and 1 <= dd <= 31:
                d, form, span = f"{y:04d}-{mo:02d}-{dd:02d}", "MM.DD.YYYY", m.span()
    year_only = ''
    if not d:
        m = YEAR_ONLY.search(body)
        if m:
            year_only, span = m.group(1), m.span()   # year recorded, NOT a date
    rest = (body[:span[0]] + ' ' + body[span[1]:]) if span else body
    rest = rest.replace('_', ' ')
    tribe = DOCTYPE.sub(' ', rest)
    tribe = re.sub(r'\b\d+\b', ' ', tribe)              # stray "0", "1995" copies
    tribe = re.sub(r'[^A-Za-z\'\- ]', ' ', tribe)
    tribe = re.sub(r'\s+', ' ', tribe).strip()
    return dict(had_prefix=had_prefix, parsed_date=d, date_form=form,
                year_only=year_only, tribe_token=tribe)

pdfs = sorted(os.listdir(PDF))
txts = set(os.path.splitext(f)[0] for f in os.listdir(TXT))
log("=" * 78)
log("STEP A -- PDF INVENTORY")
log("=" * 78)
log(f"PDFs on disk (local copy)         : {len(pdfs)}")
log(f"Extracted .txt sidecars on disk   : {len(txts)}")

rows = []
for fn in pdfs:
    p = parse_filename(fn)
    stem = os.path.splitext(fn)[0]
    p.update(pdf_filename=fn, bytes=os.path.getsize(os.path.join(PDF, fn)),
             has_txt=int(stem in txts))
    rows.append(p)

n = len(rows)
n_date = sum(1 for r in rows if r['parsed_date'])
n_ymd  = sum(1 for r in rows if r['date_form'] == 'YYYY.MM.DD')
n_mdy  = sum(1 for r in rows if r['date_form'] == 'MM.DD.YYYY')
n_yr   = sum(1 for r in rows if not r['parsed_date'] and r['year_only'])
n_none = sum(1 for r in rows if not r['parsed_date'] and not r['year_only'])
n_tribe= sum(1 for r in rows if len(r['tribe_token']) >= 4)
n_clean= sum(1 for r in rows if r['parsed_date'] and len(r['tribe_token']) >= 4)

log("")
log("-- filename date parse --")
log(f"  full date parsed                : {n_date:5d}  ({100*n_date/n:5.2f}%)")
log(f"      of which YYYY.MM.DD         : {n_ymd:5d}")
log(f"      of which MM.DD.YYYY         : {n_mdy:5d}")
log(f"  YEAR ONLY (no day -> NOT dated) : {n_yr:5d}  ({100*n_yr/n:5.2f}%)")
log(f"  no date token at all            : {n_none:5d}  ({100*n_none/n:5.2f}%)")
log(f"  DOES NOT PARSE to a date        : {n_yr+n_none:5d}  ({100*(n_yr+n_none)/n:5.2f}%)")
log("-- filename tribe token --")
log(f"  non-empty tribe token (>=4 ch)  : {n_tribe:5d}  ({100*n_tribe/n:5.2f}%)")
log(f"  CLEAN PARSE (date AND tribe)    : {n_clean:5d}  ({100*n_clean/n:5.2f}%)")

log("")
log("-- filenames that do NOT yield a date (verbatim) --")
for r in rows:
    if not r['parsed_date']:
        log(f"    [{'year=' + r['year_only'] if r['year_only'] else 'NO DATE '}] {r['pdf_filename']}")

# ---------------------------------------------------------------- index reconcile
idx = list(csv.DictReader(open(IDX, encoding='utf-8')))
log("")
log("=" * 78)
log("STEP A2 -- RECONCILE PDFs AGAINST THE BIA INDEX (primary source)")
log("=" * 78)
log(f"BIA index rows                    : {len(idx)}")
idx_fn = collections.Counter(r['pdf_filename'] for r in idx)
disk = set(pdfs)
in_idx_not_disk = [f for f in idx_fn if f not in disk]
in_disk_not_idx = sorted(disk - set(idx_fn))
log(f"index filenames not on disk       : {len(in_idx_not_disk)} -> {in_idx_not_disk}")
log(f"PDFs on disk not in index         : {len(in_disk_not_idx)} -> {in_disk_not_idx[:10]}")
dupes = [f for f, c in idx_fn.items() if c > 1]
log(f"duplicate pdf_filename in index   : {dupes}")
log(f"decision values                   : {dict(collections.Counter(r['decision'] for r in idx))}")
log(f"index rows with blank fr_url      : {sum(1 for r in idx if not r['fr_url'].strip())}")
log(f"distinct states                   : {len(set(r['state'] for r in idx))}")

# date agreement: filename-parsed date vs BIA index date_iso
by_fn = {r['pdf_filename']: r for r in rows}
agree = dis = nofn = 0
disagreements = []
for r in idx:
    f = r['pdf_filename']
    if f not in by_fn or not by_fn[f]['parsed_date']:
        nofn += 1; continue
    if by_fn[f]['parsed_date'] == r['date_iso']:
        agree += 1
    else:
        dis += 1
        disagreements.append((f, by_fn[f]['parsed_date'], r['date_iso']))
log("")
log("-- filename date vs BIA index date_iso --")
log(f"  agree                           : {agree}")
log(f"  disagree                        : {dis}")
log(f"  no filename date to compare     : {nofn}")
for d in disagreements[:40]:
    log(f"    DISAGREE {d[0]} | filename={d[1]} index={d[2]}")

# FR url embedded date vs index date  (tests whether index date == FR publication date)
FRDATE = re.compile(r'federalregister\.gov/documents/(\d{4})/(\d{2})/(\d{2})/')
fr_agree = fr_dis = fr_none = 0
fr_dis_ex = []
for r in idx:
    m = FRDATE.search(r['fr_url'] or '')
    if not m:
        fr_none += 1; continue
    frd = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    if frd == r['date_iso']:
        fr_agree += 1
    else:
        fr_dis += 1
        if len(fr_dis_ex) < 15: fr_dis_ex.append((r['pdf_filename'], r['date_iso'], frd))
log("")
log("-- BIA index date_iso vs date embedded in the Federal Register URL --")
log(f"  agree                           : {fr_agree}")
log(f"  disagree                        : {fr_dis}")
log(f"  no FR url                       : {fr_none}")
for e in fr_dis_ex:
    log(f"    DISAGREE {e[0]} | index={e[1]} FR={e[2]}")

with open(os.path.join(INT, "compacts_pdf_inventory.csv"), "w", newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['pdf_filename','bytes','has_txt','had_prefix',
                                       'parsed_date','date_form','year_only','tribe_token'])
    w.writeheader()
    for r in rows: w.writerow(r)

# ---------------------------------------------------------------- prior extractions
log("")
log("=" * 78)
log("STEP B -- PRIOR EXTRACTION ASSESSMENT")
log("=" * 78)

v2 = list(csv.DictReader(open(os.path.join(PRIOR, 'bia_compact_content_v2.csv'), encoding='utf-8')))
log(f"bia_compact_content_v2.csv rows   : {len(v2)}  cols: {len(v2[0])}")
BOOLISH = set()
fill = []
for c in v2[0].keys():
    vals = [r[c].strip() for r in v2]
    nz = sum(1 for v in vals if v not in ('', '0', 'False', 'false', 'none', 'unknown', '[]', '{}'))
    fill.append((c, nz, 100*nz/len(v2)))
log("  substantive (non-empty, non-zero/none/[]) fill by field:")
for c, nz, p in sorted(fill, key=lambda x: -x[2]):
    log(f"    {c:42s} {nz:5d}  {p:6.2f}%")

log("")
v3 = list(csv.DictReader(open(os.path.join(PRIOR, 'bia_compact_term_v3.csv'), encoding='utf-8')))
hit = [r for r in v3 if r['term_years_v3'].strip()]
log(f"bia_compact_term_v3.csv rows      : {len(v3)}")
log(f"  term_years_v3 populated         : {len(hit)}  ({100*len(hit)/len(v3):.2f}%)")
log(f"  confidence distribution         : {dict(collections.Counter(r['term_match_confidence'] for r in hit))}")
log(f"  family distribution             : {dict(collections.Counter(r['term_pattern_id'] for r in hit))}")

# cross-check v2.term_years against v3
v2t = {r['pdf_filename']: r.get('term_years','').strip() for r in v2}
both = same = diff = 0
diffs = []
for r in hit:
    a = v2t.get(r['pdf_filename'], '')
    if a:
        both += 1
        if a == r['term_years_v3']: same += 1
        else:
            diff += 1
            if len(diffs) < 20: diffs.append((r['pdf_filename'], a, r['term_years_v3']))
log("")
log("-- v2.term_years vs v3.term_years_v3 (independent regex passes, same corpus) --")
log(f"  both populated                  : {both}")
log(f"  identical                       : {same}")
log(f"  CONFLICT                        : {diff}")
for d in diffs: log(f"    CONFLICT {d[0][:70]} | v2={d[1]} v3={d[2]}")

# OCR quality flag
nre = sum(1 for r in v2 if r.get('needs_reocr','').strip() in ('1','True','true'))
log("")
log(f"  v2 rows flagged needs_reocr     : {nre}")
try:
    ar = [float(r['alpha_ratio']) for r in v2 if r.get('alpha_ratio','').strip()]
    nc = [int(float(r['n_chars'])) for r in v2 if r.get('n_chars','').strip()]
    ar.sort(); nc.sort()
    log(f"  alpha_ratio p05/p50/p95         : {ar[len(ar)//20]:.3f} / {ar[len(ar)//2]:.3f} / {ar[19*len(ar)//20]:.3f}")
    log(f"  n_chars    p05/p50/p95          : {nc[len(nc)//20]} / {nc[len(nc)//2]} / {nc[19*len(nc)//20]}")
    log(f"  texts under 2,000 chars         : {sum(1 for x in nc if x < 2000)}")
except Exception as e:
    log("  (alpha_ratio/n_chars unavailable)", e)

with open(os.path.join(BASE, "logs", "15_compacts_2026-08-05.log"), "w", encoding='utf-8') as fh:
    fh.write(out.getvalue())
print("\n[written] data/interim/compacts_pdf_inventory.csv")
