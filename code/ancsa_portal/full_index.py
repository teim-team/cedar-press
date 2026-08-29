import lib2, json, os, csv, time, sys
cen=json.load(open("year_census.json"))
years=[y for y,v in cen.items() if v]
corps=json.load(open("corps.json"))
OUT="index_rows.csv"; DONE="index_done.json"
done=json.load(open(DONE)) if os.path.exists(DONE) else {}
FIELDS=["corp","year_searched","doc_id","desc","year","category"]
f=open(OUT,"a",newline="",encoding="utf-8")
w=csv.DictWriter(f,fieldnames=FIELDS)
if os.path.getsize(OUT)==0 if os.path.exists(OUT) else True: pass
if not done: w.writeheader()
p=lib2.Portal()
t0=time.time()
for y in sorted(years):
    for c in corps:
        k=c+"||"+y
        if k in done: continue
        tot=None
        for a in range(4):
            try:
                tot,rows=p.search(corp=c,year=y); break
            except Exception as e:
                print("RETRY",k,repr(e)[:120],flush=True); time.sleep(8)
        if tot is None:
            print("FAIL",k,flush=True); continue
        for r in rows:
            w.writerow({"corp":c,"year_searched":y,"doc_id":r["doc_id"],"desc":r["desc"],
                        "year":r["year"],"category":r["category"]})
        f.flush()
        done[k]={"total":tot,"got":len(rows)}
        json.dump(done,open(DONE,"w"))
        if tot: print(y,c,tot,len(rows),"| elapsed %.0fs"%(time.time()-t0),flush=True)
print("DONE",flush=True)
