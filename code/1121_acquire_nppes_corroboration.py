#!/usr/bin/env python3
"""
1121 - CMS NPPES: a second, genuinely independent source for
       `entity.state`, `entity.city` and the legal name.

    py -3 code/1121_acquire_nppes_corroboration.py probe
    py -3 code/1121_acquire_nppes_corroboration.py pull [--limit N] [--refetch]
    py -3 code/1121_acquire_nppes_corroboration.py build
    py -3 code/1121_acquire_nppes_corroboration.py verify    # exits 1 on breach
    py -3 code/1121_acquire_nppes_corroboration.py selftest  # proves it FIRES

WHY
---
`START_HERE.md` item 0 and `docs/ASSERTION_LAYER.md`: across **8,975
single-valued facts, 0 have a second source, 0 disagree, and 2 have more than
one independent evidence family.** The arbitration machinery works and has
nothing to arbitrate. That is not "the data agrees with itself"; it means
nothing has ever checked it.

CMS enumeration is a THIRD evidence family, independent of both the Federal
Register roster and the IRS BMF. The FR roster is Interior's list of
sovereigns; the BMF is Treasury's list of exempt organisations; NPPES is
HHS's list of enumerated health care providers, populated by a separate
application with a separate authority, and `KNOWN_ISSUES` A3 records that 258
Native Hawaiian entities return no IRS organisation at all.

===========================================================================
THE ONE DESIGN DECISION THAT MAKES THIS A CORROBORATION AND NOT AN ECHO
===========================================================================
**The query passes the NAME and NOTHING ELSE. It never passes `state`.**

NPPES accepts `state=` and `city=` parameters, and using them would have
made the match rate look far better. It would also have made the result
worthless: a search seeded with Cedar's own answer for `state` can only
return records that agree with Cedar's `state`, and the "corroboration" would
be Cedar reading its own value back out of a remote host. That is the
evidence-lineage trap `ASSERTION_LAYER` names - **a copy of a source sitting
in the spine, and the source itself, are the same evidence family** - wearing
a query parameter instead of a table.

So: query by organisation name; retrieve whatever states come back; and
compare afterwards. `state_agrees` can therefore be FALSE, and a FALSE is the
single most valuable row in the output.
===========================================================================

SELECTION DECLARATION  (PULL_DISCIPLINE, "THE RULE")
----------------------------------------------------
  leg USED    : KNOWN_IDENTIFIER - one query per spine entity, seeded from
                `data/spine/cedar_entity_spine.csv`.`canonical_name`.
  leg MISSING : TYPE_FILTER. NPPES has no Native flag; the nearest thing is a
                taxonomy code, and no taxonomy means "tribal". **This pull
                therefore cannot discover an entity Cedar does not already
                know**, which is the defining property of the selection and
                not a defect to be fixed inside it. Corroborating what we
                hold is exactly the job here; discovery is 1120's job.
  population_basis on every row: `KNOWN_IDENTIFIER`

WHAT IT WRITES
--------------
  data/clean/nppes_org_registrations.csv
      one row per NPI-2 organisation record retrieved. Deduplicated on
      `npi` across all queries - one NPI can answer several spine names.
  data/clean/nppes_spine_name_candidates.csv
      one row per (cedar_uid, npi) CANDIDATE, plus **one row per spine entity
      that was queried and matched nothing**, carrying
      `match_method = NOT_MATCHED`. Negatives are rows: "attempted and found
      nothing" must be distinguishable from "never attempted", which is the
      grain rule `entity_dated_public_facts.csv` already follows.

      Every row carries `confidence_tier = C`. **A NAME MATCH IS NOT A
      DETERMINATION.** `docs/START_HERE.md` standing rule 1: a tier is
      inherited from the source row, never assigned by the consumer, and the
      exactness of a key says nothing about the correctness of a link.
      `code/1118_corroboration_layer.py` is the consumer; this script hands
      it evidence and adjudicates nothing.

  The comparison columns it hands to 1118, per candidate row:
      `nppes_state`, `spine_state`, `state_agrees`  in {AGREE, DISAGREE, NO_SPINE_VALUE, NO_NPPES_VALUE}
      `nppes_city`,  `spine_city`,  `city_agrees`   same vocabulary
      `nppes_legal_name`, `spine_canonical_name`, `name_token_jaccard`

PERSONAL DATA
-------------
NPPES publishes an `authorized_official_*` block - a named natural person and
their direct telephone number. Those columns are **not written at all**;
PUBLICATION_POLICY holds a natural person's data apart from their public
role, and here Cedar has no need of the person, only of the organisation.
The org-level `telephone_number` on the practice address IS written, because
it is the organisation's own switchboard.
"""
from __future__ import annotations

import copy
import csv
import importlib.util
import json
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

_spec = importlib.util.spec_from_file_location("cedar_arcgis", HERE / "cedar_arcgis.py")
ag = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ag)                                       # type: ignore

SCRIPT = "1121_acquire_nppes_corroboration"
HOST = "npiregistry.cms.hhs.gov"
API = f"https://{HOST}/api/"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
RAW = ROOT / "data" / "raw" / "external" / "nppes"
CLEAN = ROOT / "data" / "clean"
LOG = ROOT / "logs" / f"{SCRIPT}.jsonl"
STATE = RAW / "_state.json"
MANIFEST = RAW / "_manifest.json"

PAGE = 200               # the API's own hard maximum
MAX_PAGES = 5            # 1,000 records per spine name is already generous
PAUSE_S = 1.2
NAME_PREFIX_CHARS = 60   # NPPES matches a trailing-wildcard prefix

# Words that carry no discriminating power in a Native organisation name.
# Kept SHORT on purpose: an over-eager stoplist is how "Boys & Girls Clubs of
# Wichita Falls" becomes the Wichita Tribe.
STOP = {"the", "of", "and", "inc", "incorporated", "llc", "corp",
        "corporation", "co", "a", "an", "at", "for", "dba"}

_norm_rx = re.compile(r"[^A-Z0-9 ]+")


def norm(s: str) -> str:
    return _norm_rx.sub(" ", (s or "").upper()).strip()


def tokens(s: str) -> set[str]:
    return {t for t in norm(s).split() if t and t.lower() not in STOP}


def jaccard(a: str, b: str) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def query_url(name: str, skip: int) -> str:
    # NAME ONLY. No state, no city. See the design block above.
    return API + "?" + urllib.parse.urlencode({
        "version": "2.1", "enumeration_type": "NPI-2",
        "organization_name": name, "limit": PAGE, "skip": skip})


def search_name(entity_name: str) -> str:
    n = norm(entity_name)
    if len(n) > NAME_PREFIX_CHARS:
        n = n[:NAME_PREFIX_CHARS].rsplit(" ", 1)[0]
    return n + "*"


def _p(msg: str) -> None:
    """Print that cannot kill a two-hour pull.

    Measured 2026-09-02: the first `pull` ran 875 of 1,555 entities and then
    died on `UnicodeEncodeError` printing a spine name containing `u+016B`,
    because this console is cp1252. **A progress line took down the run.**
    Nothing was lost - `_state.json` is written every 25 entities and the
    resume picked up at 875 - but a logging call must never be able to end a
    network job. Every user-facing string goes through here.
    """
    enc = sys.stdout.encoding or "utf-8"
    sys.stdout.write(msg.encode(enc, "replace").decode(enc, "replace"))
    sys.stdout.write(chr(10))
    sys.stdout.flush()


def read_spine() -> list[dict]:
    with SPINE.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _load(p: Path, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _save(p: Path, d) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".part")
    tmp.write_text(json.dumps(d, indent=2 if p is MANIFEST else None),
                   encoding="utf-8")
    tmp.replace(p)


# ---------------------------------------------------------------------------

def cmd_probe() -> int:
    sess = ag.Session(SCRIPT, LOG, pause_s=PAUSE_S)
    p = ag.robots_posture(API)
    print(f"robots  status={p['robots_status']} served={p['robots_served']} "
          f"verdict={p['verdict']}  (naive-our-UA: {p['naive_our_ua_verdict']})")
    print("  note: this host serves its Angular SPA HTML at /robots.txt. "
          "A soft-404 page is NOT a robots file -> NOT SERVED -> ALLOWED.")
    if p["verdict"] != "ALLOWED":
        return 1
    spine = read_spine()
    print(f"spine: {len(spine):,} entities; "
          f"{sum(1 for r in spine if r['state'].strip()):,} carry a state, "
          f"{sum(1 for r in spine if r['city'].strip()):,} carry a city")
    for probe in ("CHEROKEE NATION", "CONFEDERATED TRIBES OF THE COLVILLE RESERVATION",
                  "SEATTLE INDIAN HEALTH BOARD"):
        d = sess.get(query_url(search_name(probe), 0))["json"]
        got = d.get("results", [])
        _p(f"  {probe[:46]:<46} -> {d.get('result_count', 0):>4} "
           f"e.g. {got[0]['basic']['organization_name'][:40] if got else '-'}")
    print("\nEstimated cost of a full pull: "
          f"~{len(spine):,} requests at {PAUSE_S}s "
          f"= ~{len(spine) * PAUSE_S / 60:.0f} minutes, plus paging.")
    return 0


def cmd_pull(refetch: bool = False, limit: int | None = None) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    posture = ag.require_allowed(API)
    lock = ag.claim_host(HOST, SCRIPT)
    sess = ag.Session(SCRIPT, LOG, pause_s=PAUSE_S, deadline_s=4 * 3600)

    st = _load(STATE, {"done": {}, "records": {}}) if not refetch else \
        {"done": {}, "records": {}}
    spine = read_spine()
    if limit:
        spine = spine[:limit]
    todo = [r for r in spine if r["cedar_uid"] not in st["done"]]
    print(f"{len(spine):,} spine entities, {len(spine) - len(todo):,} already "
          f"queried, {len(todo):,} to go")

    refused = []
    try:
        for i, e in enumerate(todo, 1):
            uid, nm = e["cedar_uid"], e["canonical_name"]
            q = search_name(nm)
            hits, skip, truncated, shas = [], 0, False, []
            for page in range(MAX_PAGES):
                r = sess.get(query_url(q, skip))
                d = r["json"]
                if d.get("Errors"):
                    st["done"][uid] = {"query": q, "n": 0, "truncated": False,
                                       "error": str(d["Errors"])[:300],
                                       "page_sha256": []}
                    hits = []
                    break
                got = d.get("results", [])
                shas.append(r["sha256"])
                hits.extend(got)
                if len(got) < PAGE:
                    break
                skip += len(got)
                if page == MAX_PAGES - 1:
                    truncated = True
            else:
                truncated = True
            if uid not in st["done"]:
                # The NPIs THIS query returned. Recorded per query, never
                # re-derived by scanning the global pool later: a global scan
                # would attach an NPI that a DIFFERENT entity's query found,
                # which is the containment defect with a new front door.
                st["done"][uid] = {"query": q, "n": len(hits),
                                   "truncated": truncated,
                                   "npis": [h["number"] for h in hits],
                                   "page_sha256": shas,
                                   "distinct_page_sha256": len(set(shas))}
            for h in hits:
                st["records"][h["number"]] = h
            if i % 25 == 0 or i == len(todo):
                _save(STATE, st)
                _p(f"  {i:>5}/{len(todo)}  {nm[:44]:<44} {len(hits):>4} hits "
                   f"| {len(st['records']):,} distinct NPIs so far")
    except ag.EdgeBlocked as ex:
        refused.append(str(ex))
        _save(STATE, st)
        print(f"EDGE BLOCK - stopping the run.\n  {ex}")
        return 2
    finally:
        _save(STATE, st)
        ag.release_host(lock, downloaded_this_run=len(st["done"]),
                        refused_by_host=refused, requests_made=sess.n_requests,
                        bytes_read=sess.bytes_read)

    queried = len(st["done"])
    matched = sum(1 for v in st["done"].values() if v["n"] > 0)
    _save(MANIFEST, {
        "script": SCRIPT, "host": HOST, "api": API,
        "robots": posture,
        "query_shape": "organization_name=<name>* ; enumeration_type=NPI-2 ; "
                       "NO state and NO city parameter, deliberately",
        "spine_entities_queried": queried,
        "spine_entities_with_at_least_one_hit": matched,
        "spine_entities_with_zero_hits": queried - matched,
        "distinct_npis_retrieved": len(st["records"]),
        "truncated_queries": sum(1 for v in st["done"].values()
                                 if v.get("truncated")),
        "errored_queries": sum(1 for v in st["done"].values() if v.get("error")),
        "requests_made": sess.n_requests, "bytes_read": sess.bytes_read,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    })
    print(f"\n{queried:,} entities queried, {matched:,} with a hit, "
          f"{len(st['records']):,} distinct NPIs, {sess.n_requests:,} requests.")
    return 0


# ---------------------------------------------------------------------------

def _addr(rec: dict, purpose: str) -> dict:
    for a in rec.get("addresses", []):
        if a.get("address_purpose") == purpose:
            return a
    return {}


def _agree(nppes: str, spine: str) -> str:
    n, s = (nppes or "").strip().upper(), (spine or "").strip().upper()
    if not s:
        return "NO_SPINE_VALUE"
    if not n:
        return "NO_NPPES_VALUE"
    return "AGREE" if n == s else "DISAGREE"


def cmd_build() -> int:
    CLEAN.mkdir(parents=True, exist_ok=True)
    st = _load(STATE, None)
    man = _load(MANIFEST, None)
    if not st or not st.get("done"):
        print("nothing pulled - run `pull` first")
        return 1
    recs = st["records"]
    now = man["retrieved_at"] if man else datetime.now(timezone.utc).isoformat()

    # --- 1. the registration table ----------------------------------------
    hdr = ["npi", "legal_name", "other_names", "status", "organizational_subpart",
           "enumeration_date", "certification_date", "last_updated",
           "mailing_address_1", "mailing_city", "mailing_state", "mailing_postal_code",
           "location_address_1", "location_city", "location_state",
           "location_postal_code", "location_telephone",
           "primary_taxonomy_code", "primary_taxonomy_desc", "all_taxonomy_desc",
           "source_url", "retrieved_at", "source_id", "population_basis",
           "inclusion_basis", "inclusion_basis_detail",
           "inclusion_basis_terms_matched", "retrieved_by_n_spine_queries"]
    # ADR-013 C12 `term_match` requires the MATCHED TERMS, not just the fact
    # of matching. An NPI can be returned by several spine names; all of them
    # are recorded, because which query found it is the only reason it is here.
    found_by: dict[str, list[str]] = {}
    for uid, info in st["done"].items():
        for npi in info.get("npis", []):
            found_by.setdefault(npi, []).append(info["query"])

    p1 = CLEAN / "nppes_org_registrations.csv"
    tmp = p1.with_suffix(".csv.part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(hdr)
        for npi, r in sorted(recs.items()):
            b = r.get("basic", {})
            m, loc = _addr(r, "MAILING"), _addr(r, "LOCATION")
            tx = r.get("taxonomies", [])
            prim = next((t for t in tx if t.get("primary")), tx[0] if tx else {})
            w.writerow([
                npi, b.get("organization_name", ""),
                " | ".join(o.get("organization_name", "") for o in r.get("other_names", [])),
                b.get("status", ""), b.get("organizational_subpart", ""),
                b.get("enumeration_date", ""), b.get("certification_date", ""),
                b.get("last_updated", ""),
                m.get("address_1", ""), m.get("city", ""), m.get("state", ""),
                m.get("postal_code", ""),
                loc.get("address_1", ""), loc.get("city", ""), loc.get("state", ""),
                loc.get("postal_code", ""), loc.get("telephone_number", ""),
                prim.get("code") or "", prim.get("desc") or "",
                # NPPES serves `desc: null` on some taxonomy entries -
                # measured, not hypothetical. `t.get("desc","")` returns None
                # for a key that EXISTS with a null value, which is the exact
                # difference between "absent" and "present and empty".
                " | ".join((t.get("desc") or "") for t in tx),
                f"{API}?number={npi}", now, "cms_nppes", "KNOWN_IDENTIFIER",
                "term_match",
                "returned by an NPPES organization_name query seeded from a "
                "Cedar spine entity's canonical name. The NPPES record itself "
                "carries NO Native flag - CMS does not publish one - so this "
                "row's presence is evidence about a NAME, not about identity",
                "; ".join(sorted(set(found_by.get(npi, [])))[:20]),
                len(set(found_by.get(npi, [])))])
    tmp.replace(p1)
    with p1.open("r", encoding="utf-8", newline="") as fh:
        n1 = sum(1 for _ in csv.reader(fh)) - 1
    print(f"BUILD {p1.name:<42} {n1:>8,} rows x {len(hdr)} cols")

    # --- 2. the candidate / comparison table, NEGATIVES INCLUDED ----------
    spine = {r["cedar_uid"]: r for r in read_spine()}
    hdr2 = ["cedar_uid", "spine_canonical_name", "spine_entity_class",
            "spine_state", "spine_city", "nppes_query", "match_method",
            "npi", "nppes_legal_name", "name_token_jaccard",
            "nppes_state", "state_agrees", "nppes_city", "city_agrees",
            "nppes_enumeration_date", "nppes_last_updated",
            "nppes_primary_taxonomy_desc", "hits_for_this_query",
            "query_truncated", "confidence_tier", "attribution_method",
            "source_id", "source_url", "retrieved_at", "population_basis",
            "inclusion_basis", "inclusion_basis_terms_matched"]
    p2 = CLEAN / "nppes_spine_name_candidates.csv"
    tmp = p2.with_suffix(".csv.part")
    n_cand = n_neg = 0
    agree_s = disagree_s = 0
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(hdr2)
        for uid, info in sorted(st["done"].items()):
            e = spine.get(uid)
            if not e:
                continue
            base = [uid, e["canonical_name"], e["entity_class"],
                    e["state"], e["city"], info["query"]]
            # ONLY the NPIs this entity's own query returned. `npis` is
            # recorded per query at pull time; if it is absent the state file
            # predates that field and the honest answer is UNMEASURED, never
            # a global scan of the pool.
            if "npis" not in info:
                raise RuntimeError(
                    f"{uid}: the pull state carries no per-query `npis` list. "
                    "Re-run `pull --refetch`. Deriving candidates by scanning "
                    "every retrieved NPI would attach another entity's hits.")
            npis = info["npis"]
            if info["n"] == 0 or not npis:
                w.writerow(base + ["NOT_MATCHED", "", "", "", "", "NO_NPPES_VALUE",
                                   "", "NO_NPPES_VALUE", "", "", "",
                                   info["n"], info.get("truncated", False),
                                   "C", "nppes_name_query_no_hit", "cms_nppes",
                                   API, now, "KNOWN_IDENTIFIER",
                                   "term_match", info["query"]])
                n_neg += 1
                continue
            for npi in npis:
                r = recs.get(npi)
                if not r:
                    continue
                b = r.get("basic", {})
                loc = _addr(r, "LOCATION") or _addr(r, "MAILING")
                tx = r.get("taxonomies", [])
                prim = next((t for t in tx if t.get("primary")), tx[0] if tx else {})
                nm = b.get("organization_name", "")
                sa = _agree(loc.get("state", ""), e["state"])
                ca = _agree(loc.get("city", ""), e["city"])
                agree_s += sa == "AGREE"
                disagree_s += sa == "DISAGREE"
                w.writerow(base + [
                    "NAME_TOKEN_MATCH", npi, nm,
                    f"{jaccard(e['canonical_name'], nm):.4f}",
                    loc.get("state", ""), sa, loc.get("city", ""), ca,
                    b.get("enumeration_date", ""), b.get("last_updated", ""),
                    prim.get("desc") or "", info["n"], info.get("truncated", False),
                    "C", "nppes_name_query_candidate", "cms_nppes",
                    f"{API}?number={npi}", now, "KNOWN_IDENTIFIER",
                    "term_match", info["query"]])
                n_cand += 1
    tmp.replace(p2)
    print(f"BUILD {p2.name:<42} {n_cand + n_neg:>8,} rows x {len(hdr2)} cols")
    print(f"      {n_cand:,} candidate pairs, {n_neg:,} NOT_MATCHED negatives")
    print(f"      state: {agree_s:,} AGREE, {disagree_s:,} DISAGREE "
          "(a DISAGREE is a FINDING, not an error)")

    (ROOT / "docs" / "nppes_acquisition_1121.json").write_text(json.dumps({
        "script": SCRIPT, "built_at": datetime.now(timezone.utc).isoformat(),
        "nppes_org_registrations_rows": n1,
        "candidate_pairs": n_cand, "not_matched_rows": n_neg,
        "state_agree": agree_s, "state_disagree": disagree_s,
        "handoff": "code/1118_corroboration_layer.py - this script adjudicates "
                   "nothing and writes no assertions.",
    }, indent=2), encoding="utf-8")
    return 0


def cmd_verify() -> int:
    st = _load(STATE, None)
    man = _load(MANIFEST, None)
    fails, checks = [], 0

    def ck(name, cond, detail=""):
        nonlocal checks
        checks += 1
        print(("OK  " if cond else "FAIL") + "  " + name + (f"  {detail}" if detail else ""))
        if not cond:
            fails.append(name)

    if not st or not st.get("done"):
        print("UNMEASURED - nothing pulled.")
        return 1

    spine = read_spine()
    ck("every spine entity was queried (a negative is a row too)",
       len(st["done"]) == len(spine), f"{len(st['done']):,} of {len(spine):,}")
    ck("manifest present and agrees with state",
       bool(man) and man["distinct_npis_retrieved"] == len(st["records"]),
       f"{man['distinct_npis_retrieved'] if man else '-'} vs {len(st['records']):,}")

    p1, p2 = (CLEAN / "nppes_org_registrations.csv",
              CLEAN / "nppes_spine_name_candidates.csv")
    for p in (p1, p2):
        ck(f"{p.name}: built", p.exists())
    if not (p1.exists() and p2.exists()):
        print(f"\n{checks} checks, {len(fails)} failed.")
        return 1

    with p1.open("r", encoding="utf-8", newline="") as fh:
        rows1 = list(csv.DictReader(fh))
    ck("registrations: one row per distinct NPI",
       len(rows1) == len(st["records"]) == len({r["npi"] for r in rows1}),
       f"{len(rows1):,} rows / {len({r['npi'] for r in rows1}):,} distinct")
    ck("registrations: NO authorized_official column shipped",
       not any("authorized_official" in c for c in (rows1[0].keys() if rows1 else [])))

    with p2.open("r", encoding="utf-8", newline="") as fh:
        rows2 = list(csv.DictReader(fh))
    uids = {r["cedar_uid"] for r in rows2}
    ck("candidates: every queried entity appears (matched OR NOT_MATCHED)",
       len(uids) == len(st["done"]), f"{len(uids):,} of {len(st['done']):,}")
    ck("candidates: every row is tier C - a name match is not a determination",
       all(r["confidence_tier"] == "C" for r in rows2),
       str(sum(1 for r in rows2 if r["confidence_tier"] != "C")) + " not C")
    ck("candidates: NOT_MATCHED rows exist (absence is recorded, not silent)",
       any(r["match_method"] == "NOT_MATCHED" for r in rows2),
       str(sum(1 for r in rows2 if r["match_method"] == "NOT_MATCHED")))
    ck("candidates: state_agrees uses only the four declared values",
       {r["state_agrees"] for r in rows2} <= {"AGREE", "DISAGREE",
                                              "NO_SPINE_VALUE", "NO_NPPES_VALUE"},
       str(sorted({r["state_agrees"] for r in rows2})))
    # THE POINT OF THE WHOLE SCRIPT: it must be able to disagree. A
    # corroboration source that can only ever agree is measuring itself.
    ck("candidates: the source is CAPABLE of disagreeing (>0 DISAGREE rows)",
       sum(1 for r in rows2 if r["state_agrees"] == "DISAGREE") > 0,
       str(sum(1 for r in rows2 if r["state_agrees"] == "DISAGREE")))
    ck("candidates: no .part left behind",
       not (CLEAN / "nppes_spine_name_candidates.csv.part").exists())

    print(f"\n{checks} checks, {len(fails)} failed.")
    if fails:
        print("BREACH: " + "; ".join(fails))
        return 1
    return 0


def cmd_selftest() -> int:
    st = _load(STATE, None)
    if not st or not st.get("done"):
        print("UNMEASURED - selftest needs a pulled state file.")
        return 1
    backup = copy.deepcopy(st)
    try:
        drop = next(iter(st["done"]))
        st["done"].pop(drop)
        _save(STATE, st)
        print("--- verify against an INJECTED missing query ---")
        if cmd_verify() != 1:
            print("SELFTEST FAIL: verify did not exit 1 on an injected violation")
            return 1
    finally:
        _save(STATE, backup)
    print("--- restored; re-verifying ---")
    rc = cmd_verify()
    print("\nSELFTEST " + ("PASS" if rc == 0 else "FAIL"))
    return 0 if rc == 0 else 1


def main() -> int:
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "probe":
        return cmd_probe()
    if c == "pull":
        lim = None
        if "--limit" in sys.argv:
            lim = int(sys.argv[sys.argv.index("--limit") + 1])
        return cmd_pull("--refetch" in sys.argv, lim)
    if c == "build":
        return cmd_build()
    if c == "verify":
        return cmd_verify()
    if c == "selftest":
        return cmd_selftest()
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
