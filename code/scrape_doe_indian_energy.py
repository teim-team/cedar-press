"""Scrape DOE Office of Indian Energy project pages listed in the Tribal Energy Projects Database.

Index source: the database page's map app (natlabrockies.github.io/eere-ie-projects-map) reads a
public Google Sheet; exported to doe_ie_export.csv. Each row links to an energy.gov project page
carrying DOE Grant Number, DOE/Awardee/Total amounts and period of performance.
"""
import re, os, csv, io, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_util import fetch, RAW, text, save_manifest

MONEY = r'\$([\d,]+(?:\.\d{2})?)'


def field(t, label, pat=r'(.+)'):
    m = re.search(re.escape(label) + r'\s*\n\s*' + pat, t)
    return m.group(1).strip() if m else ''


def main():
    src = os.path.join(RAW, 'doe_ie_export.csv')
    rows = list(csv.DictReader(io.StringIO(open(src, 'rb').read().decode('utf-8'))))
    out = []
    for i, r in enumerate(rows):
        url = r['Link'].strip()
        if not url:
            continue
        s, b = fetch(url)
        t = text(b)
        rec = dict(project=r['Project'], tribe=r['Tribe'], state=r['State'],
                   year=r['Year'], assistance_type=r['Assistance Type'],
                   technology=r['Technology'], url=url, http=s)
        rec['awardee'] = field(t, 'Tribe/Awardee:')
        rec['location'] = field(t, 'Location:')
        rec['project_title'] = field(t, 'Project Title:')
        rec['grant_number'] = field(t, 'DOE Grant Number:')
        m = re.search(r'Project Amounts:\s*\n\s*DOE:\s*\n\s*' + MONEY, t)
        rec['doe_amount'] = m.group(1).replace(',', '') if m else ''
        m = re.search(r'Awardee:\s*\n\s*' + MONEY, t)
        rec['awardee_amount'] = m.group(1).replace(',', '') if m else ''
        m = re.search(r'Total:\s*\n\s*' + MONEY, t)
        rec['total_amount'] = m.group(1).replace(',', '') if m else ''
        m = re.search(r'Project Period of Performance:\s*\n\s*Start:\s*\n\s*([\d/]+)', t)
        rec['pop_start'] = m.group(1) if m else ''
        m = re.search(r'End:\s*\n\s*([\d/]+)', t)
        rec['pop_end'] = m.group(1) if m else ''
        out.append(rec)
        if i % 20 == 0:
            print(i, s, rec['tribe'][:35], rec['doe_amount'], rec['pop_start'], flush=True)
    p = os.path.join(RAW, 'doe_indian_energy_project_details.csv')
    with open(p, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print('WROTE', len(out), p)
    print('with doe_amount', len([r for r in out if r['doe_amount']]),
          '>=1M', len([r for r in out if r['doe_amount'] and float(r['doe_amount']) >= 1e6]),
          'with pop_start', len([r for r in out if r['pop_start']]))


if __name__ == '__main__':
    main()
