#!/usr/bin/env python3
"""
Cedar Press - 128: build the entity reconciliation review page.

WHY A BUILDER SCRIPT RATHER THAN HAND-WRITTEN HTML
--------------------------------------------------
The 2026-08-06 page shipped broken: `cpy(''+v+'',this)` produced adjacent string
literals, a SyntaxError, and ONE SyntaxError kills the whole script tag - so zero
cards rendered and the page looked empty. Elijah found it, not us.

Enforced here, permanently:
  1. **No inline handlers.** Every action is a `data-` attribute read by one
     delegated listener. Nothing concatenates a value into executable JS.
  2. **Everything user-supplied goes through `esc()`** before innerHTML.
  3. A structural check greps the output for both failure modes.
  4. **Visually inspect the rendered page before sending the link.**

WHAT ELIJAH ASKED FOR (2026-08-12), ALL IMPLEMENTED
---------------------------------------------------
  - our proposed entity AND a confidence %, or an honest "no read"
  - class first, THEN the specific name: "ANC (click) then enter the name of it"
  - one-click copy of UEI / CAGE with visible confirmation
  - export he can COPY-PASTE, not only a file download
  - a card marks itself as looked-at when he works through it
  - per-entry notes
  - a running total of entities and dollars resolved

    py -3 code/129_build_review_queue.py   # first: build the queue + guesses
    py -3 code/128_build_review_page.py    # then: render
"""

import json
import sys
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
OUT = CEDAR / "web_claude" / "entity_reconciliation.html"
QUEUE = CEDAR / "data" / "interim" / "review_queue.json"

CSS = """
:root{
  --paper:#faf9f6; --card:#fff; --ink:#14171a; --muted:#5d6560; --line:#e3e2dc;
  --accent:#2d6a4f; --soft:#e7f0eb; --warn:#8a5a11;
  --tribe:#2d6a4f; --anc:#1d4e79; --nho:#5b3d84; --indiv:#8a5a11;
  --not:#9b2c2c; --hold:#4a5259;
}
@media (prefers-color-scheme:dark){:root{
  --paper:#111412; --card:#191d1b; --ink:#e9ebe8; --muted:#9aa39d; --line:#2b312e;
  --accent:#6ab08c; --soft:#1d2a24; --warn:#d1a04a;
  --tribe:#6ab08c; --anc:#6ea8dc; --nho:#a98cd4; --indiv:#d1a04a;
  --not:#e07070; --hold:#8b969d;}}
:root[data-theme="dark"]{
  --paper:#111412; --card:#191d1b; --ink:#e9ebe8; --muted:#9aa39d; --line:#2b312e;
  --accent:#6ab08c; --soft:#1d2a24; --warn:#d1a04a;
  --tribe:#6ab08c; --anc:#6ea8dc; --nho:#a98cd4; --indiv:#d1a04a;
  --not:#e07070; --hold:#8b969d;}
:root[data-theme="light"]{
  --paper:#faf9f6; --card:#fff; --ink:#14171a; --muted:#5d6560; --line:#e3e2dc;
  --accent:#2d6a4f; --soft:#e7f0eb; --warn:#8a5a11;
  --tribe:#2d6a4f; --anc:#1d4e79; --nho:#5b3d84; --indiv:#8a5a11;
  --not:#9b2c2c; --hold:#4a5259;}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);margin:0;padding:0 16px 92px;
  font:15px/1.5 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:840px;margin:0 auto}
header{position:sticky;top:0;z-index:20;background:var(--paper);
  border-bottom:1px solid var(--line);padding:13px 0 9px;margin-bottom:16px}
h1{font-size:17px;margin:0 0 3px;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:12.5px;margin:0;font-variant-numeric:tabular-nums}
.bar{height:5px;background:var(--line);border-radius:3px;margin:9px 0 8px;overflow:hidden}
.bar span{display:block;height:100%;background:var(--accent);width:0;transition:width .25s}
.tools{display:flex;gap:6px;flex-wrap:wrap}
button{font:inherit;font-size:12.5px;cursor:pointer;border-radius:7px;
  border:1px solid var(--line);background:var(--card);color:var(--ink);padding:5px 10px}
button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.chip.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.card{background:var(--card);border:1px solid var(--line);
  border-left:3px solid var(--line);border-radius:9px;padding:13px 15px;margin-bottom:11px;
  transition:border-left-color .2s,opacity .2s}
.card.seen{border-left-color:var(--warn)}
.card.done{border-left-color:var(--accent);opacity:.5}
.card h2{font-size:15.5px;margin:0 0 2px;letter-spacing:-.01em;text-wrap:balance}
.top{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.src{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.seenmark{font-size:10.5px;color:var(--warn);text-transform:uppercase;letter-spacing:.05em}
.metric{font-variant-numeric:tabular-nums;font-weight:600;font-size:13px;margin:5px 0}
.ids{display:flex;gap:6px;flex-wrap:wrap;margin:7px 0}
.id{font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--soft);
  border:1px solid var(--line);border-radius:5px;padding:3px 8px;cursor:pointer}
.id:hover{border-color:var(--accent)}
.id.none{opacity:.4;cursor:default}
.id.copied{background:var(--accent);color:#fff;border-color:var(--accent)}
.ctx{font-size:13px;color:var(--muted);margin:4px 0}
.read{font-size:13.5px;margin:9px 0;padding:9px 11px;background:var(--soft);
  border:1px solid var(--line);border-radius:7px}
.read .pct{font-weight:700;font-variant-numeric:tabular-nums}
.read .why{display:block;font-size:12px;color:var(--muted);margin-top:3px}
.noread{font-size:12.5px;color:var(--muted);font-style:italic;margin:9px 0}
.acts{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;padding-top:9px;
  border-top:1px solid var(--line)}
.acts button{font-weight:600}
[data-k="TRIBE"]{color:var(--tribe)} [data-k="ANC"]{color:var(--anc)}
[data-k="NHO"]{color:var(--nho)} [data-k="INDIVIDUAL_NATIVE"]{color:var(--indiv)}
[data-k="NOT_NATIVE"]{color:var(--not)} [data-k="HOLD"]{color:var(--hold)}
.acts button.sel{background:var(--accent);color:#fff;border-color:var(--accent)}
.acts .clear{margin-left:auto;color:var(--muted);font-weight:400}
.namebox{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}
.namebox input{flex:1 1 260px;padding:7px 10px;font:inherit;font-size:13.5px;
  border:1px solid var(--accent);border-radius:6px;background:var(--paper);color:var(--ink)}
.namebox button{background:var(--accent);color:#fff;border-color:var(--accent);font-weight:600}
.note{width:100%;margin-top:8px;padding:6px 9px;font:inherit;font-size:13px;
  border:1px solid var(--line);border-radius:6px;background:var(--paper);color:var(--ink)}
.ruled{margin-top:8px;font-size:13px;color:var(--accent);font-weight:600}
footer{position:fixed;bottom:0;left:0;right:0;background:var(--card);z-index:20;
  border-top:1px solid var(--line);padding:8px 16px;display:flex;gap:9px;
  justify-content:center;align-items:center;flex-wrap:wrap;font-size:12.5px;
  font-variant-numeric:tabular-nums}
#exp{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:30;
  display:none;align-items:center;justify-content:center;padding:20px}
#exp.on{display:flex}
.panel{background:var(--card);border-radius:11px;padding:16px;max-width:760px;width:100%}
.panel textarea{width:100%;height:280px;font:12px/1.45 ui-monospace,Menlo,monospace;
  border:1px solid var(--line);border-radius:7px;padding:9px;background:var(--paper);
  color:var(--ink);resize:vertical}
.panel .row{display:flex;gap:8px;justify-content:flex-end;margin-top:10px}
@media(max-width:560px){.acts button{flex:1 1 44%}}
"""

BODY = """
<div class="wrap">
<header>
  <h1>Entity reconciliation queue</h1>
  <p class="sub" id="sub"></p>
  <div class="bar"><span id="bar"></span></div>
  <div class="tools">
    <button class="chip on" data-f="all">All</button>
    <button class="chip" data-f="open">Unruled</button>
    <button class="chip" data-f="hasguess">Has a read</button>
    <button class="chip" data-f="noread">No read</button>
    <button class="chip" data-f="Contract discovery">Contract discovery</button>
    <button class="chip" data-f="Your unresolved ruling">Your rulings</button>
    <button class="chip" data-f="Unlinked deal party">Deal parties</button>
    <button class="chip" data-f="990 Schedule I recipient">990 grantees</button>
    <button class="chip" data-f="Resource fund recipient">Resource funds</button>
    <button class="chip" data-f="Appeal party (IBIA/IBLA)">Appeal parties</button>
    <button class="chip" data-f="Single Audit auditee">Single Audits</button>
    <button class="chip" data-f="NRC meeting participant">NRC</button>
    <button class="chip" data-f="BGOV-only prime awardee">BGOV-only</button>
    <button class="chip" data-f="Assistance legacy id">Assistance ids</button>
  </div>
</header>
<div id="list"></div>
</div>
<footer>
  <span id="tot"></span>
  <button id="export">Export &amp; copy</button>
  <button id="reset">Clear all</button>
</footer>
<div id="exp"><div class="panel">
  <strong>Your rulings</strong>
  <p class="ctx" id="expnote"></p>
  <textarea id="expText" readonly></textarea>
  <div class="row">
    <button id="copyBtn">Copy to clipboard</button>
    <button id="dlBtn">Download CSV</button>
    <button id="closeBtn">Close</button>
  </div>
</div></div>
"""

JS = r"""
const KEY = "cedar_recon_v2_2026_08_12";
let S = {};
try { S = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch (e) { S = {}; }
let filter = "all";
const NEEDNAME = { TRIBE: "tribe", ANC: "ANC", NHO: "NHO",
                   INDIVIDUAL_NATIVE: "person or firm" };
const KINDS = [["TRIBE","Tribe"],["ANC","ANC"],["NHO","NHO"],
  ["INDIVIDUAL_NATIVE","Individual Native"],["NOT_NATIVE","Not Native"],["HOLD","Hold"]];

function esc(s){ return String(s == null ? "" : s)
  .replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function save(){ localStorage.setItem(KEY, JSON.stringify(S)); }
function st(id){ return S[id] || (S[id] = {}); }
function money(n){ return n >= 1e6 ? "$" + (n/1e6).toFixed(1) + "M"
                 : n > 0 ? "$" + Math.round(n).toLocaleString() : "$0"; }

function visible(){
  return ITEMS.filter(function(it){
    var r = S[it.id];
    if (filter === "all") return true;
    if (filter === "open") return !(r && r.kind);
    if (filter === "hasguess") return it.conf > 0;
    if (filter === "noread") return !it.conf;
    return it.src === filter;
  });
}

function render(){
  var html = visible().map(function(it){
    var r = S[it.id] || {};
    var cls = "card" + (r.kind ? " done" : (r.seen ? " seen" : ""));
    var ids = [["UEI",it.uei],["CAGE",it.cage],["DUNS",it.duns]].map(function(p){
      return p[1] ? '<span class="id" data-copy="' + esc(p[1]) + '">' + p[0] + " " +
                    esc(p[1]) + "</span>"
                  : '<span class="id none">' + p[0] + " \u2014</span>"; }).join("");
    var read = it.conf
      ? '<div class="read">Our read: <strong>' + esc(it.guess || "\u2014") + "</strong>" +
        (it.gclass ? " \u00b7 " + esc(it.gclass) : "") +
        ' \u00b7 <span class="pct">' + it.conf + "%</span>" +
        '<span class="why">' + esc(it.why) + "</span></div>"
      : '<div class="noread">No read \u2014 we have no candidate for this one.</div>';
    var btns = KINDS.map(function(k){
      return '<button data-k="' + k[0] + '" data-id="' + esc(it.id) + '"' +
             (r.kind === k[0] ? ' class="sel"' : "") + ">" + k[1] + "</button>"; }).join("");
    var box = "";
    if (r.pending && NEEDNAME[r.pending]) {
      box = '<div class="namebox"><input data-name="' + esc(it.id) +
            '" placeholder="Which ' + NEEDNAME[r.pending] + '?" value="' +
            esc(r.entity || it.guess || "") + '">' +
            '<button data-save="' + esc(it.id) + '">Save</button></div>';
    }
    var done = r.kind
      ? '<div class="ruled">' + esc(r.kind) + (r.entity ? " \u2014 " + esc(r.entity) : "") +
        "</div>" : "";
    return '<div class="' + cls + '" data-card="' + esc(it.id) + '">' +
      '<div class="top"><span class="src">' + esc(it.src) + "</span>" +
      (r.seen && !r.kind ? '<span class="seenmark">looked at</span>' : "") + "</div>" +
      "<h2>" + esc(it.name || "(unnamed)") + "</h2>" +
      '<div class="metric">' + esc(it.metric) + "</div>" +
      '<div class="ids">' + ids + "</div>" +
      '<div class="ctx">' + esc(it.ctx) + "</div>" +
      '<div class="ctx">' + esc(it.ctx2) + "</div>" + read +
      '<div class="acts">' + btns +
      (r.kind ? '<button class="clear" data-clear="' + esc(it.id) + '">\u00d7 clear</button>' : "") +
      "</div>" + box + done +
      '<input class="note" data-note="' + esc(it.id) + '" placeholder="note (optional)" value="' +
      esc(r.note || "") + '"></div>';
  }).join("");
  document.getElementById("list").innerHTML = html || '<p class="ctx">Nothing in this view.</p>';

  var ruled = 0, seen = 0, dollars = 0;
  ITEMS.forEach(function(it){ var r = S[it.id];
    if (!r) return;
    if (r.kind) { ruled++; dollars += it.dollars || 0; }
    else if (r.seen) seen++; });
  document.getElementById("sub").textContent =
    ITEMS.length + " observations \u00b7 " + ruled + " ruled \u00b7 " +
    seen + " looked at \u00b7 " + (ITEMS.length - ruled) + " open";
  document.getElementById("bar").style.width = (100 * ruled / ITEMS.length) + "%";
  document.getElementById("tot").textContent =
    ruled + " / " + ITEMS.length + " ruled \u00b7 " + money(dollars) + " resolved";
  observe();
}

var io = null;
function observe(){
  if (!("IntersectionObserver" in window)) return;
  if (io) io.disconnect();
  io = new IntersectionObserver(function(entries){
    var touched = false;
    entries.forEach(function(en){
      if (!en.isIntersecting) return;
      var id = en.target.dataset.card;
      if (S[id] && S[id].seen) return;
      st(id).seen = true; touched = true;
      en.target.classList.add("seen");
      io.unobserve(en.target);
    });
    if (touched) { save(); updateTotals(); }
  }, { threshold: 0.6 });
  document.querySelectorAll("[data-card]").forEach(function(c){ io.observe(c); });
}
function updateTotals(){
  var ruled = 0, seen = 0, dollars = 0;
  ITEMS.forEach(function(it){ var r = S[it.id];
    if (!r) return;
    if (r.kind) { ruled++; dollars += it.dollars || 0; } else if (r.seen) seen++; });
  document.getElementById("sub").textContent =
    ITEMS.length + " observations \u00b7 " + ruled + " ruled \u00b7 " +
    seen + " looked at \u00b7 " + (ITEMS.length - ruled) + " open";
  document.getElementById("tot").textContent =
    ruled + " / " + ITEMS.length + " ruled \u00b7 " + money(dollars) + " resolved";
}

document.addEventListener("click", function(ev){
  var cp = ev.target.closest("[data-copy]");
  if (cp) {
    var v = cp.dataset.copy;
    if (navigator.clipboard) navigator.clipboard.writeText(v);
    else { var t = document.createElement("textarea"); t.value = v;
           document.body.appendChild(t); t.select();
           document.execCommand("copy"); t.remove(); }
    cp.classList.add("copied");
    var old = cp.textContent; cp.textContent = "copied \u2713";
    setTimeout(function(){ cp.classList.remove("copied"); cp.textContent = old; }, 900);
    return;
  }
  var chip = ev.target.closest("[data-f]");
  if (chip) { filter = chip.dataset.f;
    document.querySelectorAll("[data-f]").forEach(function(c){
      c.classList.toggle("on", c === chip); });
    render(); return; }
  var cl = ev.target.closest("[data-clear]");
  if (cl) { var s = st(cl.dataset.clear);
    delete s.kind; delete s.entity; delete s.pending; save(); render(); return; }
  var sv = ev.target.closest("[data-save]");
  if (sv) {
    var id = sv.dataset.save, card = sv.closest("[data-card]");
    var inp = card ? card.querySelector("[data-name]") : null;
    var s2 = st(id);
    s2.kind = s2.pending; s2.entity = inp ? inp.value.trim() : "";
    delete s2.pending; save(); render(); return;
  }
  var b = ev.target.closest("[data-k]");
  if (b) {
    var id2 = b.dataset.id, k = b.dataset.k, s3 = st(id2);
    if (NEEDNAME[k]) { s3.pending = k; delete s3.kind; }
    else { s3.kind = k; s3.entity = ""; delete s3.pending; }
    save(); render(); return;
  }
});
document.addEventListener("change", function(ev){
  var n = ev.target.closest("[data-note]");
  if (n) { st(n.dataset.note).note = n.value; save(); }
});
document.addEventListener("keydown", function(ev){
  if (ev.key !== "Enter") return;
  var inp = ev.target.closest("[data-name]");
  if (!inp) return;
  var card = inp.closest("[data-card]");
  var btn = card ? card.querySelector("[data-save]") : null;
  if (btn) btn.click();
});

function buildCSV(){
  function q(s){ return '"' + String(s == null ? "" : s).replace(/"/g,'""') + '"'; }
  var lines = ["review_id,entity_name,uei,cage,duns,YOUR_RULING,ruled_entity,notes,our_read,our_read_class,our_confidence,agreed_with_our_read,dollars,source"];
  function nm(s){ return String(s||"").toLowerCase().replace(/[^a-z0-9]+/g," ").trim(); }
  ITEMS.forEach(function(it){
    var r = S[it.id];
    if (!r || !r.kind) return;
    // CALIBRATION: did the ruling confirm our read? A confirmation is a labelled
    // example exactly as much as a correction, and it is what lets a confidence
    // band earn the right to auto-apply later.
    var agreed = "NA";
    if (it.conf > 0 && it.guess) {
      if (r.kind === "NOT_NATIVE" || r.kind === "HOLD") agreed = "NO";
      else if (nm(r.entity) && nm(r.entity) === nm(it.guess)) agreed = "YES";
      else if (nm(r.entity)) agreed = "NO";
      else if (it.gclass && r.kind === it.gclass) agreed = "CLASS_ONLY";
    }
    lines.push([it.id, it.name, it.uei, it.cage, it.duns, r.kind, r.entity || "",
                r.note || "", it.guess || "", it.gclass || "", it.conf, agreed,
                it.dollars, it.src].map(q).join(","));
  });
  return lines.join("\n");
}
document.getElementById("export").addEventListener("click", function(){
  var csv = buildCSV();
  var n = csv.split("\n").length - 1;
  var d = 0;
  ITEMS.forEach(function(it){ if (S[it.id] && S[it.id].kind) d += it.dollars || 0; });
  document.getElementById("expnote").textContent =
    n + " ruling(s) \u00b7 " + money(d) + " resolved \u00b7 select all and copy, or download";
  var ta = document.getElementById("expText");
  ta.value = csv;
  document.getElementById("exp").classList.add("on");
  ta.focus(); ta.select();
});
document.getElementById("copyBtn").addEventListener("click", function(){
  var ta = document.getElementById("expText");
  ta.select();
  if (navigator.clipboard) navigator.clipboard.writeText(ta.value);
  else document.execCommand("copy");
  this.textContent = "Copied \u2713";
  var self = this;
  setTimeout(function(){ self.textContent = "Copy to clipboard"; }, 1200);
});
document.getElementById("dlBtn").addEventListener("click", function(){
  var blob = new Blob([buildCSV()], { type: "text/csv" });
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "cedar_rulings_2026-08-12.csv";
  a.click();
});
document.getElementById("closeBtn").addEventListener("click", function(){
  document.getElementById("exp").classList.remove("on");
});
document.getElementById("reset").addEventListener("click", function(){
  if (confirm("Clear all rulings and looked-at marks?")) {
    S = {}; localStorage.removeItem(KEY); render();
  }
});
render();
"""


def main():
    items = json.load(open(QUEUE, encoding="utf-8"))
    html = "\n".join([
        "<title>Cedar Press \u2014 Entity Reconciliation</title>",
        "<style>" + CSS + "</style>",
        BODY,
        "<script>const ITEMS = " + json.dumps(items, ensure_ascii=False) + ";</script>",
        "<script>" + JS + "</script>",
    ])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"  wrote {OUT.relative_to(CEDAR)}  {len(html):,} bytes, {len(items)} items")

    bad = []
    if "onclick=" in html:
        bad.append("inline onclick")
    if "''+" in html or "+''" in html:
        bad.append("adjacent string literals")
    if html.count("<script>") != html.count("</script>"):
        bad.append("unbalanced script tags")
    for t in ("div", "span", "button", "input"):
        o, c = html.count("<" + t), html.count("</" + t + ">")
        if t != "input" and abs(o - c) > 2:
            bad.append(f"{t} {o}/{c}")
    print("  structural check:", "; ".join(bad) if bad else "clean")
    with_guess = sum(1 for i in items if i["conf"])
    print(f"  cards with a read: {with_guess} / {len(items)}")
    print(f"  dollars in queue : ${sum(i['dollars'] for i in items)/1e6:,.1f}M")


if __name__ == "__main__":
    main()
