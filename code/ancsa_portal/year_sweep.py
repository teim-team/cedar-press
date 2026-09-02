import lib, json, os, sys, time
OUT="year_sweep.json"
out=json.load(open(OUT)) if os.path.exists(OUT) else {}
for y in range(1990,2027):
    k=str(y)
    if k in out: continue
    try:
        pos,rows,err=lib.search(lib.S,year=k)
    except Exception as e:
        print(k,"ERROR",e,flush=True); time.sleep(15); continue
    out[k]={"pos":pos,"n":len(rows),"err":err,"rows":rows}
    print(k,"|",pos,"| rows",len(rows),"| err",err,flush=True)
    json.dump(out,open(OUT,"w"),indent=1)
print("DONE")
