import json, os, csv, time, hashlib, requests, re, sys
from pathlib import Path
RAW=str(Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "external" / "ancsa_portal")
os.makedirs(RAW,exist_ok=True)
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
S=requests.Session(); S.headers.update({"User-Agent":UA})
S.get("https://portal.akdbsstar.us/StarWebPortal/page/default/portal.aspx",timeout=60)
sel=json.load(open("regional_ar.json"))
order={y:i for i,y in enumerate(['2016','2017','2018','2019','2020','2021','2022','2023','2024','2025','2026'])}
sel.sort(key=lambda s:(order.get(s['year'],99), s['corp_guess']))
LOG="download_log.json"
log=json.load(open(LOG)) if os.path.exists(LOG) else {}
def safe(s): return re.sub(r'[^A-Za-z0-9._-]+','_',s).strip('_')[:100]
BUDGET=4*1024**3
used=sum(v.get("bytes",0) for v in log.values())
for s in sel:
    did=s["doc_id"]
    if did in log: continue
    if used>BUDGET:
        print("BUDGET REACHED",flush=True); break
    url="https://portal.akdbsstar.us/StarWebPortal/ViewFile.aspx?Id="+did
    try:
        r=S.get(url,timeout=600)
    except Exception as e:
        print("ERR",did,repr(e)[:100],flush=True); log[did]={"status":"error","error":repr(e)[:200]}
        json.dump(log,open(LOG,"w")); time.sleep(10); continue
    if r.status_code!=200 or not r.content:
        log[did]={"status":"http_%d"%r.status_code}; json.dump(log,open(LOG,"w")); time.sleep(4); continue
    ct=r.headers.get("Content-Type","")
    ext=".pdf" if r.content[:4]==b"%PDF" else (".bin")
    fn=safe(s["year"]+"__"+s["corp_guess"]+"__"+s["desc"])+"__"+did[:8]+ext
    open(os.path.join(RAW,fn),"wb").write(r.content)
    log[did]={"status":"ok","local_file":fn,"bytes":len(r.content),
              "sha256":hashlib.sha256(r.content).hexdigest(),"content_type":ct,
              "url":url,"desc":s["desc"],"year":s["year"],"corp_guess":s["corp_guess"],
              "retrieved":time.strftime("%Y-%m-%d")}
    used+=len(r.content)
    json.dump(log,open(LOG,"w"))
    print("%s %8.1fKB %s"%(s['year'],len(r.content)/1024,s['desc'][:60]),flush=True)
    time.sleep(4)
print("DL DONE",flush=True)
