#!/usr/bin/env python3
"""
Cedar Press - 58: Apply agent lobbying rulings to Dataset 4.

PROVENANCE OF THIS BATCH
------------------------
`review/agent_rulings_lobbying_2026-08-05.csv` - 381 rulings on clients the
matcher refused to resolve, every row carrying evidence. The agent that
produced it was terminated mid-run when the account hit its monthly spend
limit, but it had already written its output, so the work is intact and only
the reporting was lost. That is what checkpointing is for.

RULING SHAPES
-------------
  <entity name>                      -> resolve and attribute
  "NOT A NATIVE ENTITY - <reason>"   -> exclude. Palantir and C.H. Robinson are
                                        in the file because the queue
                                        deliberately included every unmatched
                                        client above $1M regardless of whether
                                        the name looked Native - that is what
                                        surfaced NANA Development and
                                        Kamehameha Schools, which have no
                                        Native token in their names.
  "NATIVE ORGANIZATION - <kind>"     -> in scope, no single owning entity
  "<TRIBE_ID> <name>"                -> the agent resolved it itself; trust the
                                        id but verify it exists in the spine

EVIDENCE STANDARD
-----------------
Same asymmetry as scripts 34, 53 and 56. Excluding is safe because it can only
under-attribute. Attributing is not, so an attribution reaches tier A only with
a filing URL or a primary source in the note; otherwise tier B.

Reads  review/agent_rulings_lobbying_*.csv
       data/clean/native_entity_lobbying_disclosures.csv
       data/clean/lobbying_unmatched_clients.csv
Writes data/clean/lobbying_client_attribution.csv
       review/lobbying_still_ambiguous.csv
"""

import csv
import importlib.util
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

CEDAR = Path(__file__).resolve().parent.parent
CLEAN = CEDAR / "data" / "clean"
SPINE = CEDAR / "data" / "spine"
REVIEW = CEDAR / "review"
TODAY = date.today().isoformat()

NOT_NATIVE_RE = re.compile(r"^\s*not a native entity", re.I)
ORG_RE = re.compile(r"^\s*native organi[sz]ation\s*[-:]\s*(?P<kind>.+)$", re.I)
HOLD_RE = re.compile(r"^\s*(ambiguous|unresolved|hold|multi)", re.I)
# The agent sometimes answered with the spine id followed by the name.
IDPREFIX_RE = re.compile(r"^\s*(?P<tid>[A-Z]{4}-[A-Z0-9\-]+)\s+(?P<name>.+)$")
PRIMARY_RE = re.compile(r"https?://", re.I)


# --- REGENERATE GUARD (ADR-017, 2026-09-02) --------------------------------
def _carry_live_columns(path, canonical):
    """Derive this writer's header instead of declaring it.

    A wholesale writer holding a FIXED `fieldnames` list deletes every column
    an in-place enricher added since - no error, no exception, a diff nobody
    reads. Canonical order first so column order stays stable, then whatever
    the live file already carries. A retired column stays retired because it
    is not on disk; a promoted column survives because it is.

    THIS BUILD CANNOT REPOPULATE AN ENRICHER'S COLUMN. Carried columns are
    written BLANK and NAMED on stdout, which is strictly better than deleted:
    the schema survives and the enricher can refill them. Re-run the enricher
    after this build - `cedar_pipeline.enrichers_to_rerun(<table>)` names it.
    """
    import csv as _csv
    import os as _os
    canonical = list(canonical)
    _p = str(path)
    if not _os.path.exists(_p):
        return canonical
    with open(_p, encoding="utf-8-sig", newline="", errors="replace") as _fh:
        _live = next(_csv.reader(_fh), [])
    _extra = [c for c in _live if c and c not in canonical]
    if _extra:
        print("  [regenerate guard] %s: carrying %d enricher column(s) through "
              "this rebuild, BLANK - re-run the enricher: %s"
              % (_os.path.basename(_p), len(_extra), ", ".join(_extra)))
    return canonical + _extra


def load_m33():
    spec = importlib.util.spec_from_file_location(
        "m33", CEDAR / "code" / "33_apply_party_rulings.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def read_csv(p):
    if not Path(p).exists():
        return []
    with open(p, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    print("=== Cedar Press 58: apply lobbying rulings ===\n")
    m = load_m33()
    spine = read_csv(SPINE / "cedar_entity_spine.csv")
    by_tid = {r["tribe_id"]: r for r in spine}

    rulings = {}
    for p in sorted(REVIEW.glob("agent_rulings_lobbying_*.csv")):
        n = 0
        for r in read_csv(p):
            rid = (r.get("review_id") or "").strip()
            if not rid.upper().startswith("LOBBY:"):
                continue
            if not (r.get("YOUR_RULING") or "").strip():
                continue
            rulings[rid.split(":", 1)[1].strip().upper()] = r
            n += 1
        print(f"  {p.name}: {n} rulings")
    print(f"\ndistinct clients ruled: {len(rulings):,}")

    # Dollars per client, so the gain can be stated rather than asserted.
    spend = defaultdict(float)
    filings = Counter()
    for r in read_csv(CLEAN / "native_entity_lobbying_disclosures.csv"):
        c = (r.get("client_name") or "").strip().upper()
        filings[c] += 1
        try:
            spend[c] += float(r.get("spend_usd") or 0)
        except ValueError:
            pass
    for r in read_csv(CLEAN / "lobbying_unmatched_clients.csv"):
        c = (r.get("client_name") or "").strip().upper()
        if c not in spend:
            filings[c] += int(float(r.get("n_filings") or 0))
            try:
                spend[c] += float(r.get("total_spend_usd")
                                  or r.get("spend_usd") or 0)
            except ValueError:
                pass

    out, held = [], []
    stats, dollars = Counter(), Counter()

    for client, r in sorted(rulings.items()):
        ans = (r.get("YOUR_RULING") or "").strip()
        note = (r.get("YOUR_NOTE") or "").strip()
        usd = spend.get(client, 0.0)

        if not note:
            stats["REFUSED - no evidence"] += 1
            continue

        if HOLD_RE.match(ans):
            held.append({"client_name": client, "ruling": ans, "note": note[:300],
                         "spend_usd": round(usd, 2)})
            stats["still ambiguous"] += 1
            continue

        if NOT_NATIVE_RE.match(ans):
            out.append({"client_name": client, "tribe_id": "", "canonical_name": "",
                        "client_role": "EXCLUDED", "confidence_tier": "X",
                        "n_filings": filings.get(client, 0),
                        "spend_usd": round(usd, 2),
                        "ruling": ans, "evidence": note[:600],
                        "ruled_by": "agent_research", "ruled_date": TODAY})
            stats["excluded (not Native)"] += 1
            dollars["excluded"] += usd
            continue

        mo = ORG_RE.match(ans)
        if mo:
            out.append({"client_name": client, "tribe_id": "",
                        "canonical_name": client.title(),
                        "client_role": "NATIVE_ORGANIZATION",
                        "confidence_tier": "A" if PRIMARY_RE.search(note) else "B",
                        "n_filings": filings.get(client, 0),
                        "spend_usd": round(usd, 2),
                        "ruling": ans, "evidence": note[:600],
                        "ruled_by": "agent_research", "ruled_date": TODAY})
            stats["native organisation"] += 1
            dollars["native org"] += usd
            continue

        # The agent may have answered with a spine id. Trust it only if the id
        # actually exists - an id that does not resolve is a typo, not a fact.
        name = ans
        mi = IDPREFIX_RE.match(ans)
        if mi and mi.group("tid") in by_tid:
            tid = mi.group("tid")
            canon = by_tid[tid]["canonical_name"]
            how = "agent_supplied_tribe_id"
        else:
            if mi:
                name = mi.group("name")
            tid, canon, how = m.resolve_entity(name, spine)

        if not tid:
            held.append({"client_name": client, "ruling": ans, "note": how,
                         "spend_usd": round(usd, 2)})
            stats[f"unresolved to spine ({how.split(':')[0]})"] += 1
            continue

        tier = "A" if PRIMARY_RE.search(note) else "B"
        out.append({"client_name": client, "tribe_id": tid, "canonical_name": canon,
                    "client_role": "ENTITY", "confidence_tier": tier,
                    "n_filings": filings.get(client, 0),
                    "spend_usd": round(usd, 2),
                    "ruling": ans, "evidence": note[:600],
                    "ruled_by": f"agent_research+{how}", "ruled_date": TODAY})
        stats[f"attributed tier {tier}"] += 1
        dollars[f"tier {tier}"] += usd

    print("\noutcomes")
    for k, v in stats.most_common():
        print(f"  {v:5d}  {k}")
    print("\ndollars by outcome")
    for k, v in dollars.most_common():
        print(f"  ${v/1e6:9,.1f}M  {k}")

    p1 = CLEAN / "lobbying_client_attribution.csv"
    with open(p1, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_carry_live_columns(p1, list(out[0].keys())),
                           restval="", extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    print(f"\n  wrote {p1.relative_to(CEDAR)}  ({len(out):,} clients)")

    if held:
        p2 = REVIEW / "lobbying_still_ambiguous.csv"
        with open(p2, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(held[0].keys()))
            w.writeheader()
            w.writerows(sorted(held, key=lambda r: -r["spend_usd"]))
        print(f"  wrote {p2.relative_to(CEDAR)}  ({len(held):,} still ambiguous)")


if __name__ == "__main__":
    main()
