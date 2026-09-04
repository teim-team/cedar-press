#!/usr/bin/env python3
"""
Cedar Press - 511: SAM-declared ownership CONNECTIONS for the largest entities.

    py -3 code/511_sam_entity_hierarchy.py canary            # ONE call, prove the key
    py -3 code/511_sam_entity_hierarchy.py pull --budget 8   # batched UEI sweep, resumable
    py -3 code/511_sam_entity_hierarchy.py discover --budget 5   # ultimateParentUEISAM sweep
    py -3 code/511_sam_entity_hierarchy.py report            # read-only, what we hold

STATUS 2026-08-30, MEASURED SAME DAY - PARKED, AND WHY
------------------------------------------------------
Nine calls in, reality arrived: the key is the 10-calls/day tier (429 with
nextAccessTime), and at that tier the API HIDES entityHierarchyInformation -
62 registrations returned, zero carried it, including subsidiaries that
certainly declare parents. So at our access level this script can fetch
registration facts but not the one section it was built for. The worklist is
saved and resumes if the key ever gains a role (1,000/day, sections included).

The mission moved to where the same declarations are public and unmetered:
the parent-UEI columns on the FPDS/USAspending extracts already on disk.
13_build_fpds_hierarchy.py gained the 602 MB assistance extract that had
never been harvested - 2,290 -> 2,901 edges, 24,977 -> 29,981 cage triples,
zero calls. Use THIS script only for adjudication-time lookups (a few calls,
registration facts); use 13's tables for the spiderweb.

WHY THE TOP ENTITIES FIRST (owner direction, 2026-08-30)
--------------------------------------------------------
Measured from our own ledger before any call was spent: the top 20 Native
entities hold 71.2% of the $175B of prime contract dollars we track (top 10 =
54.1%), and they hold 831 of the UEIs we already know. The Entity Management
API takes up to 100 UEIs PER CALL, so the entire known top-20 universe is nine
calls. Concentration is why this rolls out fast.

THE TRUST MODEL - THE OWNER'S RULE, AND THE REASON THIS TABLE IS SHAPED
THE WAY IT IS
----------------------------------------------------------------------
    "I would trust the connections, not the hierarchy."

The declared hierarchy is the registrant's own FAR 4.18 filing. What it proves
is that a CONNECTION exists - Arctic Slope Federal Services declared Arctic
Slope Regional Corporation above it, and nobody declares themselves into a
tribal family by accident. What it does NOT prove is the tree: the declared
"highest-level owner" is routinely the highest INCORPORATED owner (Ho-Chunk,
Inc., not the Winnebago Tribe of Nebraska), levels get skipped, and stale
registrations keep dead structures alive. The last hop - holding company ->
tribe - is Cedar's proprietary edge and never comes from here.

So this script writes EDGES, one declaration per row, and refuses to write
structure:

  * it NEVER touches parent_entity_id / ultimate_parent_entity_id in the spine;
  * it NEVER mints a spine entity from a subsidiary name. Arctic Slope Federal
    Services is not a Native entity; it is a registration owned by one. New
    subsidiary UEIs land in a CANDIDATES file for the ledger process, already
    attributed to the owning entity at tier B, method sam_declared_hierarchy;
  * every edge carries the declaration verbatim (who declared, which role,
    when we saw it) so a later ruling can overrule it without losing it.

CALL DISCIPLINE
---------------
The key's tier is unknown until a 429 says otherwise: a personal key with no
role is 10 requests/day, with a role 1,000/day. Every run therefore takes an
explicit --budget, spends it in batches of up to 100 UEIs, and CHECKPOINTS
after every response. A 429 or an exhausted budget stops cleanly with the
worklist saved; the next run resumes where this one stopped. State that is
mid-sweep is never reported as complete - the FERC per-docket budget that
truncated four dockets and marked them done (class4) is the named disease
here, and the `swept` marker below is only written when totalRecords for the
batch has been fully paged.

Writes
------
data/raw/sam_hierarchy/<date>_batch<N>.json   raw responses, never edited
data/clean/sam_entity_connections.csv         one row per declared edge
data/clean/sam_subsidiary_candidates.csv      UEIs we did not know, attributed
review/sam_hierarchy_state.json               resumable worklist + checkpoints
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
SPINE = ROOT / "data" / "spine"
RAW = ROOT / "data" / "raw" / "sam_hierarchy"
STATE_P = ROOT / "review" / "sam_hierarchy_state.json"
CONN_P = CLEAN / "sam_entity_connections.csv"
CAND_P = CLEAN / "sam_subsidiary_candidates.csv"
TODAY = date.today().isoformat()
csv.field_size_limit(10_000_000)

API = "https://api.sam.gov/entity-information/v3/entities"
# BATCH is 10, not the API's 100-value maximum, because the RESPONSE page is
# capped at 10 records ("Size Cannot Exceed 10 Records"). A 100-UEI query
# still costs ten paged calls to read, so ten-UEI batches cost exactly the
# same number of calls and need no paging state that could half-complete.
# Checked against the docs 2026-08-30 BEFORE spending budget - the first
# draft assumed batches of 100 in one call, which would have marked 90 of
# every 100 UEIs as swept without ever fetching them.
BATCH = 10
TOP_N = 20           # the concentration argument above; raise deliberately

CONN_COLS = ["edge_id", "child_uei", "child_cage", "child_legal_name",
             "child_city", "child_state", "child_reg_status",
             "declared_role", "parent_uei", "parent_legal_name",
             "declaring_party", "cedar_entity_id", "cedar_note",
             "trust_note", "source", "pulled_date"]
CAND_COLS = ["uei", "cage", "legal_name", "city", "state", "reg_status",
             "attributed_to_entity_id", "attribution_method",
             "confidence_tier", "evidence", "found_date"]

TRUST_NOTE = ("Owner's rule 2026-08-30: trust the CONNECTION, not the "
              "hierarchy. This row proves a declared link exists; it does not "
              "prove the tree. The declared highest owner is often the highest "
              "INCORPORATED owner, not the tribe - that last hop is the "
              "spine's, never SAM's.")


def sam_key() -> str:
    import os
    key = os.environ.get("SAM_API_KEY", "")
    if not key:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                key, _ = winreg.QueryValueEx(k, "SAM_API_KEY")
        except OSError:
            pass
    if not key:
        sys.exit("no SAM_API_KEY in environment or user registry - "
                 "run code/set_sam_key.ps1 first")
    return key


def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def _derive(canonical, path) -> list:
    """Canonical order first, then any column the live file already carries.

    A FIXED literal header is the regenerate defect (ADR-017): a wholesale
    writer silently deleting an in-place enricher's column. Added 2026-09-02
    after `845` rule 17 flagged `CONN_COLS -> sam_entity_connections.csv` as
    losing `cedar_uid`. Same shape as `code/354_correction_register.py`.
    """
    if not Path(path).exists():
        return list(canonical)
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            live = next(csv.reader(fh), [])
    except OSError:
        return list(canonical)
    return list(canonical) + [c for c in live if c and c not in canonical]


def write_csv(p: Path, rows, cols) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    cols = _derive(cols, p)
    with p.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def edge_id(child_uei, role, parent_uei) -> str:
    """Content-addressed - a re-pull yields the same id (class7: never mint
    from position or process)."""
    h = hashlib.sha1(f"{child_uei}|{role}|{parent_uei}".encode()).hexdigest()
    return "SAMEDGE-" + h[:12].upper()


def load_state() -> dict:
    if STATE_P.exists():
        return json.loads(STATE_P.read_text(encoding="utf-8"))
    return {"built": "", "worklist": [], "swept": [], "parents_swept": [],
            "calls_spent_total": 0, "last_429": ""}


def save_state(st: dict) -> None:
    STATE_P.parent.mkdir(parents=True, exist_ok=True)
    STATE_P.write_text(json.dumps(st, indent=1), encoding="utf-8")


def top_entities():
    """(tribe_id, name, dollars_M, [ueis]) for the TOP_N by prime dollars,
    ranked from OUR ledger - the same measurement that justified this script."""
    led = read_csv(CLEAN / "cedar_identifier_ledger_final.csv")
    sp = {r["tribe_id"]: r for r in read_csv(SPINE / "cedar_entity_spine.csv")}
    dol = defaultdict(float)
    ueis = defaultdict(list)
    for r in led:
        tid = (r.get("tribe_id") or "").strip()
        if not tid or r.get("confidence_tier") == "X":
            continue
        try:
            dol[tid] += float(r.get("prime_dollars_M") or 0)
        except ValueError:
            pass
        if r.get("identifier_type") == "UEI":
            u = (r.get("identifier") or "").strip().upper()
            if u and u not in ueis[tid]:
                ueis[tid].append(u)
    rk = sorted(dol.items(), key=lambda kv: -kv[1])[:TOP_N]
    return [(tid, (sp.get(tid, {}).get("canonical_name") or tid), d,
             sorted(ueis[tid])) for tid, d in rk]


def call_api(key, params, tag):
    """One metered request. Returns (json, None) or (None, why-stopped)."""
    q = dict(params)
    q["api_key"] = key
    url = API + "?" + urllib.parse.urlencode(q)
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return None, "429 rate-limited - the daily budget is spent; resume tomorrow"
        return None, f"HTTP {e.code} {e.reason}"
    except Exception as e:            # noqa: BLE001 - a pull must stop cleanly
        return None, f"{type(e).__name__}: {e}"
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / f"{TODAY}_{tag}.json").write_text(
        json.dumps(data, indent=1), encoding="utf-8")
    return data, None


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("canary", "pull", "discover",
                                                "report"):
        print(__doc__.split("Writes")[0])
        return 2
    cmd = sys.argv[1]
    budget = 0
    if "--budget" in sys.argv:
        budget = int(sys.argv[sys.argv.index("--budget") + 1])

    st = load_state()
    led = read_csv(CLEAN / "cedar_identifier_ledger_final.csv")
    known_ueis = {(r.get("identifier") or "").strip().upper()
                  for r in led if r.get("identifier_type") == "UEI"}
    uid_of = {(r.get("identifier") or "").strip().upper():
              (r.get("tribe_id") or "").strip()
              for r in led if r.get("identifier_type") == "UEI"
              and r.get("confidence_tier") != "X"}
    conns = {r["edge_id"]: r for r in read_csv(CONN_P)}
    cands = {r["uei"]: r for r in read_csv(CAND_P)}

    if cmd == "report":
        print(f"  connections held : {len(conns)}")
        print(f"  candidates held  : {len(cands)}")
        print(f"  batches swept    : {len(st['swept'])}, "
              f"parents swept: {len(st['parents_swept'])}")
        print(f"  calls spent total: {st['calls_spent_total']}"
              + (f"  (last 429: {st['last_429']})" if st["last_429"] else ""))
        if st["worklist"]:
            print(f"  WORKLIST NOT EMPTY: {len(st['worklist'])} batch(es) "
                  f"remain - the sweep is NOT complete")
        return 0

    key = sam_key()

    def ingest(data):
        added_e = added_c = 0
        for e in data.get("entityData", []):
            reg = e.get("entityRegistration") or {}
            core = e.get("coreData") or {}
            pa = core.get("physicalAddress") or {}
            child = (reg.get("ueiSAM") or "").strip().upper()
            if not child:
                continue
            eh = core.get("entityHierarchyInformation") or {}
            for role, node in (("immediate", eh.get("immediateParentEntity")),
                               ("ultimate", eh.get("ultimateParentEntity"))):
                node = node or {}
                puei = (node.get("ueiSAM") or "").strip().upper()
                if not puei or puei == child:
                    continue
                eid = edge_id(child, role, puei)
                if eid in conns:
                    continue
                conns[eid] = dict(
                    edge_id=eid, child_uei=child,
                    child_cage=reg.get("cageCode") or "",
                    child_legal_name=reg.get("legalBusinessName") or "",
                    child_city=pa.get("city") or "",
                    child_state=pa.get("stateOrProvinceCode") or "",
                    child_reg_status=reg.get("registrationStatus") or "",
                    declared_role=role, parent_uei=puei,
                    parent_legal_name=node.get("legalBusinessName") or "",
                    declaring_party=child,
                    cedar_entity_id=uid_of.get(child, ""),
                    cedar_note=("known to the ledger" if child in known_ueis
                                else "NEW"),
                    trust_note=TRUST_NOTE, source="sam_entity_api_v3",
                    pulled_date=TODAY)
                added_e += 1
            if child not in known_ueis and child not in cands:
                # the owner of a NEW registration is whoever its declared
                # parent maps to in OUR ledger - attribution via the declared
                # connection, tier B, never tier A, never a spine row.
                parent_uei = ((eh.get("ultimateParentEntity") or {})
                              .get("ueiSAM") or "").strip().upper()
                owner = uid_of.get(parent_uei, "")
                cands[child] = dict(
                    uei=child, cage=reg.get("cageCode") or "",
                    legal_name=reg.get("legalBusinessName") or "",
                    city=pa.get("city") or "",
                    state=pa.get("stateOrProvinceCode") or "",
                    reg_status=reg.get("registrationStatus") or "",
                    attributed_to_entity_id=owner,
                    attribution_method="sam_declared_hierarchy",
                    confidence_tier="B" if owner else "C",
                    evidence=(f"declared ultimate parent {parent_uei} is "
                              f"{owner or 'not in the ledger'}; a "
                              f"registration declared into a family, not a "
                              f"name match"),
                    found_date=TODAY)
                added_c += 1
        return added_e, added_c

    if cmd == "canary":
        print("511 canary - ONE metered call, Arctic Slope Regional Corporation's lead UEI")
        tops = top_entities()
        asrc = next((t for t in tops if "Arctic Slope" in t[1]), tops[0])
        u = asrc[3][0]
        data, err = call_api(key, {"ueiSAM": u, "includeSections":
                                   "entityRegistration,coreData"}, "canary")
        st["calls_spent_total"] += 1
        if err:
            st["last_429"] = TODAY if "429" in err else st["last_429"]
            save_state(st)
            print(f"  STOPPED: {err}")
            return 1
        ae, ac = ingest(data)
        write_csv(CONN_P, list(conns.values()), CONN_COLS)
        write_csv(CAND_P, list(cands.values()), CAND_COLS)
        save_state(st)
        print(f"  {asrc[1]}: {data.get('totalRecords')} record(s), "
              f"+{ae} edge(s), +{ac} candidate(s) - the key works; "
              f"run `pull --budget N`")
        return 0

    if cmd == "pull":
        if not budget:
            sys.exit("pull requires --budget N (calls to spend THIS run)")
        if not st["worklist"] and not st["swept"]:
            tops = top_entities()
            all_ueis = sorted({u for _, _, _, us in tops for u in us})
            st["worklist"] = [all_ueis[i:i + BATCH]
                              for i in range(0, len(all_ueis), BATCH)]
            print(f"  worklist built: {len(all_ueis)} UEIs from the top "
                  f"{TOP_N} entities -> {len(st['worklist'])} batch(es)")
        spent = 0
        while st["worklist"] and spent < budget:
            batch = st["worklist"][0]
            data, err = call_api(
                key, {"ueiSAM": "[" + "~".join(batch) + "]", "size": "10",
                      "includeSections": "entityRegistration,coreData"},
                f"batch{len(st['swept']):03d}")
            spent += 1
            st["calls_spent_total"] += 1
            if err:
                st["last_429"] = TODAY if "429" in err else st["last_429"]
                save_state(st)
                print(f"  STOPPED after {spent - 1} good call(s): {err}")
                print(f"  worklist saved - {len(st['worklist'])} batch(es) "
                      f"remain. NOT complete.")
                return 1
            total = data.get("totalRecords", 0)
            ae, ac = ingest(data)
            # class4 guard: a batch is swept ONLY if nothing was truncated.
            if total > len(data.get("entityData", [])):
                print(f"  batch of {len(batch)}: totalRecords {total} > "
                      f"returned {len(data.get('entityData', []))} - "
                      f"TRUNCATED, batch stays on the worklist")
                save_state(st)
                continue
            st["swept"].append(len(batch))
            st["worklist"].pop(0)
            write_csv(CONN_P, list(conns.values()), CONN_COLS)
            write_csv(CAND_P, list(cands.values()), CAND_COLS)
            save_state(st)
            print(f"  batch of {len(batch):3d}: {total} registration(s), "
                  f"+{ae} edge(s), +{ac} candidate(s)")
        done = not st["worklist"]
        print(f"\n  {'SWEEP COMPLETE' if done else 'BUDGET SPENT - resume with pull'}"
              f" - {len(conns)} edges, {len(cands)} candidates on disk")
        return 0

    if cmd == "discover":
        if not budget:
            sys.exit("discover requires --budget N")
        # parents worth sweeping: every parent_uei our edges point at that we
        # have not yet asked "who else declares you?"
        parents = sorted({r["parent_uei"] for r in conns.values()}
                         - set(st["parents_swept"]))
        if not parents:
            print("  nothing to discover - run pull first, or all parents swept")
            return 0
        spent = 0
        for puei in parents:
            if spent >= budget:
                break
            # The page is capped at 10 records, so a parent with N declared
            # children costs ceil(N/10) calls. Page until done or the budget
            # runs out; the parent is marked swept ONLY when the last page
            # landed (class4: partial is never complete).
            page, got, total, ae, ac, stopped = 0, 0, None, 0, 0, False
            while spent < budget:
                data, err = call_api(
                    key, {"ultimateParentUEISAM": puei, "size": "10",
                          "page": str(page),
                          "includeSections": "entityRegistration,coreData"},
                    f"discover_{puei}_p{page}")
                spent += 1
                st["calls_spent_total"] += 1
                if err:
                    st["last_429"] = TODAY if "429" in err else st["last_429"]
                    save_state(st)
                    print(f"  STOPPED at {puei} page {page}: {err}")
                    stopped = True
                    break
                total = data.get("totalRecords", 0)
                recs = data.get("entityData", [])
                e1, c1 = ingest(data)
                ae, ac, got = ae + e1, ac + c1, got + len(recs)
                write_csv(CONN_P, list(conns.values()), CONN_COLS)
                write_csv(CAND_P, list(cands.values()), CAND_COLS)
                save_state(st)
                if got >= total or not recs:
                    break
                page += 1
            if stopped:
                return 1
            if total is not None and got >= total:
                st["parents_swept"].append(puei)
                save_state(st)
                print(f"  {puei}: {total} declared child(ren), +{ae} edge(s), "
                      f"+{ac} NEW candidate(s)")
            else:
                print(f"  {puei}: {got}/{total} fetched - budget ran out "
                      f"mid-parent, NOT marked swept")
        print(f"\n  {len(conns)} edges, {len(cands)} candidates on disk; "
              f"{len(set(parents) - set(st['parents_swept']))} parent(s) remain")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
