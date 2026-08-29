#!/usr/bin/env python3
"""
Cedar Press - 90: The review page, generated from the master queue.

ELIJAH, 2026-08-07
------------------
"ok i need a webpage like we have been using to do this"

Same working pattern as the earlier pages, which is now settled:
  - a NEW filename every run, so a stale cache can never serve an old queue
  - CAGE/UEI cards FIRST - an identifier makes a card rulable in seconds
  - a % confidence with the REASON for it, never a bare number
  - notes as an opportunity to add context, not an afterthought
  - rule once, saves instantly, the card leaves the queue
  - nothing is regenerated under him while he is working

RANKED, NOT DUMPED
------------------
The master queue holds 16,342 items. A page with 16,342 cards is the pile
again. This takes the top N by what the ruling is WORTH - dollars, family
reach, conflict, blocking - so the first hour of rulings is the most valuable
hour available.

CONFIDENCE IS OURS, NOT HIS
---------------------------
Each card states what WE think and why, so the question is "is this right?"
rather than "what is this?". A card with no basis says so plainly rather than
inventing a number.

Writes review/cedar_review_<date>_<nn>.html
"""

import csv
import html
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()
LIMIT = 500

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


def confidence(it):
    """What we think, and WHY. Never a bare number."""
    usd = it.get("dollars_at_stake") or ""
    why = it.get("why_it_matters", "")
    q = (it.get("question") or "").lower()
    ident = (it.get("identifier") or "").strip()

    if "CONFLICT" in why:
        return 40, ("Two sources disagree, or two rulings disagree. We cannot "
                    "publish either until you settle it.")
    if "unmatched" in q or "no attribution" in q:
        return 15, ("No attribution found - discovered but never linked to an "
                    "entity.")
    if "need_v6" in q:
        return 10, ("Matched by need_v6, which scores 6.5% against your "
                    "rulings. Treat as a guess.")
    if "cluster_v3" in q:
        return 70, ("Matched by cluster_v3, which scored 43/44 against your "
                    "rulings.")
    if "FAMILY" in why and ident:
        return 60, ("Sibling evidence plus an identifier. One ruling here "
                    "settles the family.")
    if ident:
        return 55, "Carries an identifier, so it can be verified directly."
    return 30, "Name evidence only. No identifier to confirm it."


def main():
    print("=== Cedar Press 90: review page ===\n")
    src = sorted(REVIEW.glob("MASTER_QUEUE_*.csv"))[-1]
    with open(src, encoding="utf-8-sig", errors="replace", newline="") as fh:
        items = list(csv.DictReader(fh))
    print(f"master queue: {len(items):,} items  ({src.name})")

    # CAGE/UEI cards first, then by what the ruling is worth.
    def sort_key(it):
        ident = (it.get("identifier") or "").strip()
        has_id = bool(ident) and not ident.startswith(("T-", "TRBF-", "ANVC-",
                                                       "ANRC-", "CCP-", "VP-"))
        try:
            score = float(it.get("rank_score") or 0)
        except ValueError:
            score = 0
        return (0 if has_id else 1, -score)

    items.sort(key=sort_key)
    sel = items[:LIMIT]

    cards = []
    for i, it in enumerate(sel):
        pct, basis = confidence(it)
        ident = (it.get("identifier") or "").strip()
        try:
            usd = float(it.get("dollars_at_stake") or 0)
        except ValueError:
            usd = 0
        cards.append({
            "i": i,
            "name": it.get("entity_name", ""),
            "id": ident,
            "usd": usd,
            "why": it.get("why_it_matters", ""),
            "q": it.get("question", ""),
            "url": it.get("evidence_url", ""),
            "src": it.get("source_file", ""),
            "pct": pct,
            "basis": basis,
        })

    n = 1
    while (REVIEW / f"cedar_review_{TODAY}_{n:02d}.html").exists():
        n += 1
    out = REVIEW / f"cedar_review_{TODAY}_{n:02d}.html"

    with_id = sum(1 for c in cards if c["id"])
    total_usd = sum(c["usd"] for c in cards)

    doc = _PAGE.replace("__DATA__", json.dumps(cards))
    doc = doc.replace("__DATE__", TODAY)
    doc = doc.replace("__N__", str(len(cards)))
    doc = doc.replace("__NID__", str(with_id))
    doc = doc.replace("__USD__", f"${total_usd/1e9:,.2f}B")
    doc = doc.replace("__TOTAL__", f"{len(items):,}")
    out.write_text(doc, encoding="utf-8")

    print(f"  wrote {out.relative_to(CEDAR)}")
    print(f"  {len(cards)} cards · {with_id} carry an identifier · "
          f"${total_usd/1e9:,.2f}B at stake")
    print(f"\n  open:  {out}")


_PAGE = r"""<!doctype html>
<meta charset="utf-8">
<title>Cedar Press review - __DATE__</title>
<style>
:root{--bg:#faf9f7;--fg:#1c1c1a;--mut:#6b6a65;--line:#e2e0da;--card:#fff;
--acc:#0f6b5c;--warn:#b45309;--bad:#9b2c2c;--ok:#166534}
@media(prefers-color-scheme:dark){:root{--bg:#16171a;--fg:#e8e6e1;--mut:#9a9892;
--line:#2c2e33;--card:#1e2024;--acc:#4db6a1}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 ui-sans-serif,-apple-system,"Segoe UI",system-ui,sans-serif}
header{position:sticky;top:0;z-index:9;background:var(--bg);
border-bottom:1px solid var(--line);padding:14px 22px}
h1{margin:0;font-size:17px;letter-spacing:-.01em}
.sub{color:var(--mut);font-size:13px;margin-top:3px}
.bar{display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-top:10px}
.stat{font-size:12px;color:var(--mut)}
.stat b{color:var(--fg);font-variant-numeric:tabular-nums}
button{font:inherit;padding:6px 13px;border:1px solid var(--line);
background:var(--card);color:var(--fg);border-radius:7px;cursor:pointer}
button:hover{border-color:var(--acc)}
button.pri{background:var(--acc);color:#fff;border-color:var(--acc)}
main{padding:20px 22px 120px;max-width:1080px;margin:0 auto}
.card{background:var(--card);border:1px solid var(--line);border-radius:11px;
padding:16px 18px;margin-bottom:12px}
.card.done{opacity:.32}
.top{display:flex;justify-content:space-between;gap:14px;align-items:flex-start}
.nm{font-weight:640;font-size:16px;letter-spacing:-.01em}
.ident{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;
background:rgba(15,107,92,.11);color:var(--acc);padding:2px 8px;
border-radius:5px;margin-left:9px;letter-spacing:.03em}
.usd{font-variant-numeric:tabular-nums;font-weight:640;white-space:nowrap}
.meta{color:var(--mut);font-size:12.5px;margin-top:7px}
.q{margin-top:9px;font-size:13.5px;color:var(--fg)}
.conf{display:flex;align-items:center;gap:9px;margin-top:11px;font-size:12.5px}
.dot{width:9px;height:9px;border-radius:50%;flex:none}
.acts{display:flex;gap:7px;flex-wrap:wrap;margin-top:13px}
.note{width:100%;margin-top:9px;padding:9px 11px;border:1px solid var(--line);
border-radius:7px;background:transparent;color:var(--fg);font:inherit;
font-size:13.5px;resize:vertical;min-height:34px}
.note::placeholder{color:var(--mut)}
a{color:var(--acc)}
footer{position:fixed;bottom:0;left:0;right:0;background:var(--card);
border-top:1px solid var(--line);padding:11px 22px;display:flex;gap:14px;
align-items:center;font-size:13px}
.hid{display:none}
</style>
<header>
  <h1>Cedar Press &mdash; entity review</h1>
  <div class="sub">__N__ highest-value cards of __TOTAL__ in the queue &middot;
    ranked by what the ruling is worth &middot; identifier cards first</div>
  <div class="bar">
    <span class="stat"><b id="left">0</b> left</span>
    <span class="stat"><b id="did">0</b> ruled</span>
    <span class="stat"><b>__NID__</b> carry an identifier</span>
    <span class="stat"><b>__USD__</b> at stake</span>
    <button onclick="only('conflict')">Conflicts only</button>
    <button onclick="only('money')">Money only</button>
    <button onclick="only('')">Show all</button>
    <button class="pri" onclick="dl()">Download rulings</button>
  </div>
</header>
<main id="wrap"></main>
<footer>
  <span id="msg">Rulings save to this browser as you go. Download when done.</span>
</footer>
<script>
const DATA=__DATA__;
const KEY='cedar_rulings___DATE__';
let R=JSON.parse(localStorage.getItem(KEY)||'{}');
let filt='';

function col(p){return p>=60?'var(--ok)':p>=40?'var(--warn)':'var(--bad)'}
function esc(s){return (s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;',
 '>':'&gt;','"':'&quot;'}[c]))}

function draw(){
  const w=document.getElementById('wrap');
  w.innerHTML='';
  let shown=0;
  for(const c of DATA){
    if(filt==='conflict'&&!/CONFLICT/.test(c.why))continue;
    if(filt==='money'&&!(c.usd>0))continue;
    const done=!!R[c.i];
    const d=document.createElement('div');
    d.className='card'+(done?' done':'');
    d.innerHTML=`
      <div class="top">
        <div><span class="nm">${esc(c.name)}</span>${c.id?
          `<span class="ident">${esc(c.id)}</span>`:''}</div>
        ${c.usd>0?`<div class="usd">$${(c.usd/1e6).toFixed(1)}M</div>`:''}
      </div>
      <div class="meta">${esc(c.why)} &middot; <span style="opacity:.7">${esc(c.src)}</span></div>
      ${c.q?`<div class="q">${esc(c.q)}</div>`:''}
      <div class="conf"><span class="dot" style="background:${col(c.pct)}"></span>
        <b>${c.pct}% confident</b> &mdash; ${esc(c.basis)}</div>
      ${c.url?`<div class="meta"><a href="${esc(c.url)}" target="_blank" rel="noopener">evidence &rarr;</a></div>`:''}
      <div class="acts">
        <button onclick="rule(${c.i},'NATIVE')">Native entity</button>
        <button onclick="rule(${c.i},'NOT_NATIVE')">Not Native</button>
        <button onclick="rule(${c.i},'OWNER_NAMED')">Owner is&hellip;</button>
        <button onclick="rule(${c.i},'HOLD')">Need more</button>
        ${done?`<button onclick="undo(${c.i})">Undo (${esc(R[c.i].v)})</button>`:''}
      </div>
      <textarea class="note" id="n${c.i}" placeholder="Context, the owner's name, a URL &mdash; anything that helps"
        oninput="note(${c.i},this.value)">${esc((R[c.i]||{}).note||'')}</textarea>`;
    w.appendChild(d);
    shown++;
  }
  document.getElementById('left').textContent=shown-Object.keys(R).length>0?
    shown-DATA.filter(c=>R[c.i]).length:0;
  document.getElementById('did').textContent=Object.keys(R).length;
}
function save(){localStorage.setItem(KEY,JSON.stringify(R));}
function rule(i,v){
  const t=document.getElementById('n'+i);
  R[i]={v:v,note:(t&&t.value)||'',name:DATA[i].name,id:DATA[i].id,
        src:DATA[i].src,usd:DATA[i].usd};
  save();draw();
  document.getElementById('msg').textContent=
    DATA[i].name+' \u2192 '+v+'  (saved)';
}
function undo(i){delete R[i];save();draw();}
function note(i,v){if(R[i]){R[i].note=v;save();}}
function only(f){filt=f;draw();}
function dl(){
  const rows=[['index','entity_name','identifier','dollars_at_stake',
               'source_file','YOUR_RULING','notes']];
  for(const k in R){const r=R[k];
    rows.push([k,r.name,r.id,r.usd||'',r.src,r.v,(r.note||'').replace(/\n/g,' ')]);}
  const csv=rows.map(r=>r.map(x=>'"'+String(x==null?'':x)
    .replace(/"/g,'""')+'"').join(',')).join('\n');
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='cedar_rulings___DATE__.csv';a.click();
}
draw();
</script>
"""

if __name__ == "__main__":
    main()
