# -*- coding: utf-8 -*-
import csv, os, shutil
ROOT=r"C:\Users\esm247\Desktop\Cedar Press"
IDX=os.path.join(ROOT,"data","clean","ancsa_filings_index.csv")
MAN=os.path.join(ROOT,"data","raw","external","ancsa_portal_v2","_SOURCE_MANIFEST_V2.csv")
bak=IDX+".bak_2026-08-05_v2"
if not os.path.exists(bak): shutil.copy2(IDX,bak); print("backup ->",bak)
man={r["portal_document_id"]:r for r in csv.DictReader(open(MAN,newline="",encoding="utf-8-sig"))}
rows=list(csv.DictReader(open(IDX,newline="",encoding="utf-8-sig")))
fn=list(rows[0].keys())
n=0
for r in rows:
    m=man.get(r["portal_document_id"])
    if not m: continue
    if r["downloaded"]!="yes": n+=1
    r["downloaded"]="yes"; r["retrieved_date"]="2026-08-05"
    r["local_file"]=m["local_file"]; r["bytes"]=m["bytes"]; r["sha256"]=m["sha256"]
with open(IDX,"w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=fn); w.writeheader(); w.writerows(rows)
tot=sum(1 for r in rows if r["downloaded"]=="yes")
print("flipped to downloaded=yes:",n,"| total downloaded now:",tot,"of",len(rows))
import collections
c=collections.Counter((r["anc_class"],r["corporation_name"]) for r in rows if r["downloaded"]=="yes" and r["anc_class"]=="ANC_VILLAGE")
for k,v in sorted(c.items()): print("  ",k[1],v)
