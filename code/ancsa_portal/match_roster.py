import csv, json, re, sys, unicodedata
ROSTER=r"C:\Users\esm247\Desktop\Cedar Press\data\clean\anc_ceiling_roster.csv"
def norm(s):
    s=unicodedata.normalize("NFKD",s)
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    s=s.lower()
    s=s.replace("\u2019","'").replace("\u02bb","'").replace("\u0121","g").replace("\u0117","e")
    s=re.sub(r"[^a-z0-9]+"," ",s)
    stop={"inc","incorporated","corporation","corp","company","co","limited","ltd","llc","the","native","natives","of"}
    toks=[t for t in s.split() if t and t not in stop]
    return " ".join(toks)
roster=list(csv.DictReader(open(ROSTER,encoding='utf-8-sig')))
rmap={}
for r in roster:
    rmap.setdefault(norm(r['corporation_name']),[]).append(r)
corps=json.load(open('corps.json'))
out={}
for c in corps:
    k=norm(c)
    hit=rmap.get(k)
    if hit:
        out[c]={"anc_id":hit[0]['anc_id'],"roster_name":hit[0]['corporation_name'],"anc_class":hit[0]['anc_class'],"how":"exact_normalized"}
    else:
        # token-subset fallback
        cands=[(rk,rv) for rk,rv in rmap.items() if rk and (rk in k or k in rk)]
        if len(cands)==1:
            rv=cands[0][1][0]
            out[c]={"anc_id":rv['anc_id'],"roster_name":rv['corporation_name'],"anc_class":rv['anc_class'],"how":"substring"}
        else:
            out[c]={"anc_id":"","roster_name":"","anc_class":"","how":"unmatched","cands":[x[1][0]['corporation_name'] for x in cands]}
json.dump(out,open('corp_roster_map.json','w'),indent=1)
m=[c for c in corps if out[c]['anc_id']]
print("matched",len(m),"of",len(corps))
for c in corps:
    if not out[c]['anc_id']: print("  UNMATCHED:",c, out[c].get('cands'))
