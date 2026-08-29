"""Parse the HUD ONAP award PDFs recovered from Wayback into one award table.

Output: data/raw/external/federal_award_lists/hud_onap_awards_parsed.csv
Every recipient name and amount is transcribed from the PDF text; nothing is inferred.
"""
import re, os, csv, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_util import RAW

MONEY = r'\$([\d,]+(?:\.\d{2})?)'
out = []


def T(f):
    return open(os.path.join(RAW, f), encoding='utf-8').read()


def flat(s):
    return re.sub(r'\s+', ' ', s).strip()


# ---- FY2023 IHBG Competitive: "ST Recipient $Amount Description"  (doc dated July 29, 2024)
def ihbg_fy23():
    t = T('hud_FY23_IHBGCOMP_Awardees.txt')
    n = 0
    for line in t.split('\n'):
        m = re.match(r'\s*([A-Z]{2})\s+(.+?)\s+' + MONEY + r'\s+(.*)$', line)
        if not m:
            continue
        n += 1
        out.append(dict(program='IHBG Competitive', round='FY 2023',
                        state=m.group(1), recipient=flat(m.group(2)),
                        amount=m.group(3).replace(',', ''), desc=flat(m.group(4)),
                        doc_date='2024-07-29',
                        date_basis='Date printed on the HUD ONAP award list document (July 29, 2024)',
                        source_file='hud_FY23_IHBGCOMP_Awardees.pdf',
                        source_url='https://www.hud.gov/sites/dfiles/PIH/documents/FY23_IHBGCOMP_Awardees.pdf'))
    print('IHBG FY2023', n)


# ---- FY2024 IHBG Competitive: run-together text (doc dated December 27, 2024)
def ihbg_fy24():
    t = T('hud_FY24_IHBG-COMP_Awards.txt')
    body = t.split('Project Description', 1)[1]
    body = body.split('$150,000,000')[0]
    # split into records at each 2-letter state code that begins a record
    recs = re.findall(r'([A-Z]{2})\s?([A-Z][^$]{3,120}?)\$([\d,]+)'
                      r'([^$]*?)(?=[A-Z]{2}\s?[A-Z][^$]{3,120}?\$|$)', body)
    n = 0
    for stt, name, amt, desc in recs:
        n += 1
        out.append(dict(program='IHBG Competitive', round='FY 2024', state=stt,
                        recipient=flat(name), amount=amt.replace(',', ''),
                        desc=flat(desc), doc_date='2024-12-27',
                        date_basis='Date printed on the HUD ONAP award list document (December 27, 2024)',
                        source_file='hud_FY24_IHBG-COMP_Awards.pdf',
                        source_url='https://www.hud.gov/sites/dfiles/PIH/documents/FY24_IHBG-COMP_Awards.pdf'))
    print('IHBG FY2024', n)


# ---- FY2020 IHBG Competitive: "ST Recipient $Amount"  (no in-document date)
def ihbg_fy20():
    t = T('hud_HUD_IHBG_Competitive_Awards_2021-04-12.txt')
    n = 0
    for line in t.split('\n'):
        m = re.match(r'\s*([A-Z]{2})\s+(.+?)\s+' + MONEY + r'\s*$', line)
        if not m or 'TOTAL' in line:
            continue
        n += 1
        out.append(dict(program='IHBG Competitive', round='FY 2020', state=m.group(1),
                        recipient=flat(m.group(2)), amount=m.group(3).replace(',', ''),
                        desc='', doc_date='2021-04-12',
                        date_basis='PDF creation date of the HUD award list (2021-04-12); '
                                   'HUD file name is HUD_IHBG_Competitive_Awards_4.12.21.pdf. '
                                   'NOT an award action date.',
                        source_file='hud_HUD_IHBG_Competitive_Awards_2021-04-12.pdf',
                        source_url='https://www.hud.gov/sites/dfiles/PIH/documents/HUD_IHBG_Competitive_Awards_4.12.21.pdf'))
    print('IHBG FY2020', n)


# ---- FY2018-19 IHBG Competitive: "StateName Recipient [AreaOffice] $Amount", wrapped lines
def ihbg_fy1819():
    t = T('hud_FY2018_2019_IHBG_Comp_Awards_Corrected.txt')
    t = t.split('Amount', 1)[1]
    blob = re.sub(r'\n', ' ', t)
    n = 0
    prev = 0
    STNAMES = sorted(['Alaska', 'New York', 'Michigan', 'Mississippi', 'Minnesota', 'Wisconsin',
                      'Montana', 'Wyoming', 'Nebraska', 'Colorado', 'Washington', 'Oregon',
                      'Oklahoma', 'Louisiana', 'Texas', 'California', 'Arizona', 'New Mexico',
                      'Nevada', 'Idaho', 'North Dakota', 'South Dakota', 'Maine', 'Kansas',
                      'North Carolina', 'Utah'], key=len, reverse=True)
    for m in re.finditer(MONEY, blob):
        seg = blob[prev:m.start()]
        prev = m.end()
        seg = re.sub(r'\*[A-Z]+\s*$', '', seg.strip())      # area-office marker (*AONAP ...)
        seg = re.sub(r'[+*]', ' ', seg)
        name = flat(seg)
        state = ''
        for s in STNAMES:
            if name.startswith(s + ' '):
                state, name = s, flat(name[len(s):])
                break
        if not name or 'TOTAL' in name.upper():
            continue
        n += 1
        out.append(dict(program='IHBG Competitive', round='FY 2018-2019', state=state,
                        recipient=name, amount=m.group(1).replace(',', ''), desc='',
                        doc_date='2019-12-16',
                        date_basis='PDF creation date of the corrected HUD award list '
                                   '(2019-12-16). NOT an award action date.',
                        source_file='hud_FY2018_2019_IHBG_Comp_Awards_Corrected.pdf',
                        source_url='https://www.hud.gov/sites/dfiles/PIH/documents/FY_2018-2019_IHBG_Comp_Awards_Corrected.pdf'))
    print('IHBG FY2018-19', n)


# ---- ICDBG FY2023 / FY2024: the project summary states recipient + year + amount together
def icdbg(fname, url, fy, docdate, basis):
    t = re.sub(r'\s+', ' ', T(fname))
    n = 0
    seen = set()
    for m in re.finditer(r'([A-Z][A-Za-z\.\'\-\(\)&,: 0-9]{6,110}?) will use (?:the |its )?'
                         r'(?:FY\s*)?(20\d\d) ICDBG award (?:of )?\(?\$([\d,]+)\)?', t):
        key = (flat(m.group(1)), m.group(3))
        if key in seen:
            continue
        seen.add(key)
        n += 1
        out.append(dict(program='ICDBG', round='FY %s' % fy, state='',
                        recipient=flat(m.group(1)), amount=m.group(3).replace(',', ''),
                        desc='', doc_date=docdate, date_basis=basis,
                        source_file=fname.replace('.txt', '.pdf'), source_url=url))
    print('ICDBG FY%s' % fy, n)


# ---- Alaska ICDBG award lists 2016-2018: "FFY Name Project Type $Amount"
def icdbg_alaska(fname, url, ffy, docdate, basis):
    t = T(fname)
    n = 0
    for m in re.finditer(r'(20\d\d)\s+(.+?)\s+' + MONEY, t):
        n += 1
        out.append(dict(program='ICDBG (Alaska ONAP)', round='FFY %s' % m.group(1), state='AK',
                        recipient=flat(m.group(2)), amount=m.group(3).replace(',', ''),
                        desc='', doc_date=docdate, date_basis=basis,
                        source_file=fname.replace('.txt', '.pdf'), source_url=url))
    print('ICDBG Alaska %s' % ffy, n)


if __name__ == '__main__':
    ihbg_fy23()
    ihbg_fy24()
    ihbg_fy20()
    ihbg_fy1819()
    icdbg('hud_FY23_ICDBG_Awards_and_Project_Summaries.txt',
          'https://www.hud.gov/sites/dfiles/PIH/documents/FY_23_ICDBG_Awards_and_Project_Summaries.pdf',
          '2023', '2024-05-22',
          'PDF creation date of the HUD ICDBG award list (2024-05-22). NOT an award action date.')
    icdbg('hud_FY2024_ICDBG_Awards_and_Project_Summaries.txt',
          'https://www.hud.gov/sites/dfiles/PIH/documents/FY2024ICDBGAwardsandProjectSummaries.pdf',
          '2024', '2025-04-09',
          'PDF creation date of the HUD ICDBG award list (2025-04-09). NOT an award action date.')
    for y, f, u, dd in [
        ('2016', 'hud_2016_Alaska_ICDBG_Awards.txt',
         'https://www.hud.gov/sites/dfiles/PIH/documents/2016_Alaska_ICDBG_Awards.pdf', '2018-07-26'),
        ('2017', 'hud_2017_Alaska_ICDBG_Awards.txt',
         'https://www.hud.gov/sites/dfiles/PIH/documents/2017_Alaska_ICDBG_Awards.pdf', '2018-07-26'),
        ('2018', 'hud_2018_Alaska_ICDBG_Awards.txt',
         'https://www.hud.gov/sites/dfiles/PIH/documents/2018%20Alaska%20ICDBG%20Awards.pdf', '2019-07-31')]:
        icdbg_alaska(f, u, y, dd,
                     'Federal fiscal year printed in the award list. No award date in source.')
    p = os.path.join(RAW, 'hud_onap_awards_parsed.csv')
    with open(p, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['program', 'round', 'state', 'recipient', 'amount',
                                           'desc', 'doc_date', 'date_basis', 'source_file',
                                           'source_url'])
        w.writeheader()
        w.writerows(out)
    print('TOTAL', len(out), '->', p)
    print('>= $1M', len([r for r in out if float(r['amount']) >= 1e6]))
