import requests, re, sys, time
BASE="https://portal.akdbsstar.us/StarWebPortal/"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
s=requests.Session()
s.headers.update({"User-Agent":UA,"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language":"en-US,en;q=0.9"})
r=s.get(BASE, timeout=60)
print("ROOT", r.status_code, len(r.text), r.url)
open("probe_root.html","w",encoding="utf-8").write(r.text)
time.sleep(2)
r2=s.get(BASE+"UIPViews/FillXPForm.aspx", timeout=60)
print("FORM", r2.status_code, len(r2.text), r2.url)
open("probe_form.html","w",encoding="utf-8").write(r2.text)
print("COOKIES", s.cookies.get_dict())
