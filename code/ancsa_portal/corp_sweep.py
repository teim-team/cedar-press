import lib, json, os, time, sys
ys=json.load(open("year_sweep.json"))
years=sorted([y for y,v in ys.items() if v["n"]>0])
corps=json.load(open("corps.json"))
OUT="corp_sweep.json"
out=json.load(open(OUT)) if os.path.exists(OUT) else {}
print("years with docs:",years,flush=True)
for y in years:
    for c in corps:
        k=c+"||"+y
        if k in out: continue
        for attempt in range(3):
            try:
                pos,rows,err=lib.search(lib.S,corp=c,year=y)
                break
            except Exception as e:
                print("ERR",k,e,flush=True); time.sleep(20); rows=None
        if rows is None: continue
        out[k]={"corp":c,"year":y,"pos":pos,"rows":rows}
        if rows: print(y,"|",c,"->",len(rows),flush=True)
        json.dump(out,open(OUT,"w"),indent=1)
print("DONE",flush=True)
