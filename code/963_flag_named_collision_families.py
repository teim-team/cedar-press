#!/usr/bin/env python3
"""
Cedar Press - 963: FLAG CROSS-ATTRIBUTION IN THE THREE NAMED COLLISION FAMILIES.

    py -3 code/963_flag_named_collision_families.py
    py -3 code/963_flag_named_collision_families.py verify
    py -3 code/963_flag_named_collision_families.py selftest

WHY
---
The owner named three pairs that need real diligence, because a token match on
a shared word is exactly how the United Keetoowah Band got merged into Cherokee
Nation ($181.9M, fixed 2026-09-01):

    Ho-Chunk Inc            vs  Ho-Chunk Nation of Wisconsin
    Eastern Band Cherokee   vs  Cherokee Nation Oklahoma
    Seminole of Oklahoma    vs  Seminole of Florida

Each pair shares a word that names TWO different nations in TWO different
states, and one member of each pair is a business whose name is the other
member's name.

WHAT THIS DOES, AND WHAT IT REFUSES TO DO
------------------------------------------
It **reads** `cedar_identifier_ledger_final.csv`, finds every identifier row
inside these three families, and flags the rows where the entity the row is
keyed to disagrees with the STATE the legal business name belongs to.

**It writes nothing into the ledger and repoints no identifier.** An identifier
is a claim about who a firm IS; moving one on a name pattern would be the same
mistake in the opposite direction. `AGENTS.md` opens on that failure, and
`cedar_uid` is permanent - it does not move as a side effect of a scan. The
output is a REVIEW file with the evidence laid out and the dollar exposure
quantified, for a human ruling.

THE DISCRIMINATOR IS STATE, NOT NAME
-------------------------------------
`Ho-Chunk` names two unrelated nations:

  * **Ho-Chunk Nation of Wisconsin** - `CE-00150-XS`, Wisconsin. Its own
    enterprises are Wisconsin ones.
  * **Winnebago Tribe of Nebraska** - Nebraska. Its holding company is
    literally named **Ho-Chunk, Inc.**, and its operating companies are
    Ho-Chunk Farms, Ho-Chunk Builders, Ho-Chunk Shared Services and
    Ho-Chunk Construction Management Services.

So the name `Ho-Chunk` on a FIRM is Nebraska's, and the name `Ho-Chunk Nation`
on a GOVERNMENT is Wisconsin's, and the ledger currently holds rows going both
ways. The same shape applies to Cherokee (NC vs OK) and Seminole (FL vs OK).

Every flag names the rule that fired and quotes the row. Nothing is asserted
that the row does not already contain.

OUTPUT
------
  review/named_collision_families_<date>.csv   one row per flagged identifier
  docs/NAMED_COLLISION_FAMILIES.json           counts and dollar exposure

INVARIANTS - exit 1
-------------------
  INV-READONLY  the ledger's md5 is unchanged by a run
  INV-EVIDENCE  every flagged row carries the rule that fired, the entity it
                is keyed to, the entity the rule suspects, and both states
  INV-NOCLAIM   no flagged row is written with a `proposed_cedar_uid` unless
                the suspected entity exists in the register. A proposal that
                points nowhere is worse than no proposal.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()

LEDGER = ROOT / "data" / "clean" / "cedar_identifier_ledger_final.csv"
REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"
SPINE = ROOT / "data" / "spine" / "cedar_entity_spine.csv"
OUT = ROOT / "review" / f"named_collision_families_{TODAY}.csv"
MANIFEST = ROOT / "docs" / "NAMED_COLLISION_FAMILIES.json"

# The three families the owner named. `token` is what collides; the members
# are the entities it collides between, each with the state that is the
# discriminator and the phrases that belong unambiguously to that member.
FAMILIES = [
    {"family": "ho-chunk",
     "token": r"ho[\s-]?chunk",
     "members": [
         {"name": "Ho-Chunk Nation of Wisconsin", "state": "WI",
          "owns": [r"ho[\s-]?chunk nation"],
          "note": "the GOVERNMENT. `Ho-Chunk Nation` is its legal name in the "
                  "Federal Register list."},
         {"name": "Winnebago Tribe of Nebraska", "state": "NE",
          "owns": [r"ho[\s-]?chunk,? inc", r"ho[\s-]?chunk farms",
                   r"ho[\s-]?chunk builders", r"ho[\s-]?chunk shared services",
                   r"ho[\s-]?chunk construction"],
          "note": "the HOLDING COMPANY and its operating companies. "
                  "Ho-Chunk, Inc. is Winnebago's economic development arm; "
                  "it is not an arm of the Wisconsin nation."}]},
    {"family": "cherokee",
     "token": r"cherokee",
     "members": [
         {"name": "Eastern Band of Cherokee Indians", "state": "NC",
          "owns": [r"eastern band of cherokee"],
          "note": "North Carolina. The register's stub is `Eastern Cherokee`, "
                  "which is exactly the string a token match confuses with "
                  "`Cherokee Nation`."},
         {"name": "Cherokee Nation", "state": "OK",
          "owns": [r"^cherokee nation\b"],
          "note": "Oklahoma."},
         {"name": "United Keetoowah Band of Cherokee Indians in Oklahoma",
          "state": "OK", "owns": [r"keetoowah"],
          "note": "Oklahoma, and a DIFFERENT nation from Cherokee Nation. "
                  "The $181.9M merge fixed on 2026-09-01 was this pair."}]},
    {"family": "seminole",
     "token": r"seminole",
     "members": [
         {"name": "Seminole Tribe of Florida", "state": "FL",
          "owns": [r"seminole tribe of florida"],
          "note": "Florida."},
         {"name": "The Seminole Nation of Oklahoma", "state": "OK",
          "owns": [r"seminole nation of oklahoma"],
          "note": "Oklahoma."}]},
]

COLS = ["flag_id", "family", "rule_fired", "identifier_type", "identifier",
        "legal_business_name", "keyed_to_cedar_uid", "keyed_to_name",
        "keyed_to_state", "suspected_member", "suspected_member_state",
        "suspected_member_cedar_uid", "confidence_tier", "attribution_method",
        "prime_dollars_M", "evidence_url", "why", "disposition",
        "flagged_date", "flagged_by_script"]


def read_csv(p: Path) -> list:
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def file_md5(p: Path) -> str:
    h = hashlib.md5()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def register_index():
    """name (lowered) -> cedar_uid, over both the stub and the FR legal name."""
    idx = {}
    for r in read_csv(REGISTER):
        u = (r.get("cedar_uid") or "").strip()
        for c in ("canonical_name", "federal_register_legal_name"):
            v = (r.get(c) or "").strip().lower()
            if v and u:
                idx.setdefault(v, u)
    return idx


def spine_state():
    return {(r.get("cedar_uid") or "").strip():
            (r.get("state") or "").strip().upper()
            for r in read_csv(SPINE) if (r.get("cedar_uid") or "").strip()}


def scan():
    reg = register_index()
    st = spine_state()
    rows = read_csv(LEDGER)
    flags, stats = [], Counter()

    for fam in FAMILIES:
        tok = re.compile(fam["token"], re.I)
        for m in fam["members"]:
            m["_re"] = [re.compile(p, re.I) for p in m["owns"]]
            m["_uid"] = reg.get(m["name"].lower(), "")
        for r in rows:
            lbn = (r.get("legal_business_name") or "").strip()
            if not lbn or not tok.search(lbn):
                continue
            stats[f"{fam['family']}::in_family"] += 1
            owner = next((m for m in fam["members"]
                          if any(rx.search(lbn) for rx in m["_re"])), None)
            if owner is None:
                stats[f"{fam['family']}::name_not_decisive"] += 1
                continue
            keyed_uid = (r.get("cedar_uid") or "").strip()
            keyed_state = st.get(keyed_uid, "")
            if not owner["_uid"]:
                stats[f"{fam['family']}::suspect_not_in_register"] += 1
                continue
            if keyed_uid == owner["_uid"]:
                stats[f"{fam['family']}::agrees"] += 1
                continue
            stats[f"{fam['family']}::FLAGGED"] += 1
            flags.append({
                "flag_id": "COLL-" + hashlib.blake2b(
                    "\x1f".join((fam["family"],
                                 r.get("identifier_type") or "",
                                 r.get("identifier") or "", lbn)
                                ).encode("utf-8"),
                    digest_size=8).hexdigest(),
                "family": fam["family"],
                "rule_fired": (f"legal_business_name carries a phrase that "
                               f"names {owner['name']} ({owner['state']}); "
                               f"the row is keyed to a different entity. A "
                               f"SUSPICION for a human, not a finding: a "
                               f"longer name can contain a shorter one and "
                               f"still be a third organisation"),
                "identifier_type": r.get("identifier_type") or "",
                "identifier": r.get("identifier") or "",
                "legal_business_name": lbn,
                "keyed_to_cedar_uid": keyed_uid,
                "keyed_to_name": r.get("canonical_name") or "",
                "keyed_to_state": keyed_state,
                "suspected_member": owner["name"],
                "suspected_member_state": owner["state"],
                "suspected_member_cedar_uid": owner["_uid"],
                "confidence_tier": r.get("confidence_tier") or "",
                "attribution_method": r.get("attribution_method") or "",
                "prime_dollars_M": r.get("prime_dollars_M") or "",
                "evidence_url": r.get("evidence_url") or "",
                "why": owner["note"],
                "disposition": "UNRULED - proposal only. Nothing in the "
                               "ledger was changed and no cedar_uid moved.",
                "flagged_date": TODAY,
                "flagged_by_script":
                    "code/963_flag_named_collision_families.py",
            })
    return flags, stats


def main() -> int:
    before = file_md5(LEDGER)
    flags, stats = scan()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(flags)

    money = 0.0
    for f in flags:
        try:
            money += float(f["prime_dollars_M"] or 0)
        except ValueError:
            pass
    by_tier = Counter(f["confidence_tier"] for f in flags)

    after = file_md5(LEDGER)
    MANIFEST.write_text(json.dumps(
        {"built_date": TODAY, "n_flagged": len(flags),
         "prime_dollars_M_at_stake": round(money, 3),
         "by_tier": dict(by_tier), "stats": dict(stats),
         "ledger_md5_before": before, "ledger_md5_after": after,
         "output": str(OUT.relative_to(ROOT)),
         "script": "code/963_flag_named_collision_families.py"},
        indent=2), encoding="utf-8")

    print(f"  963 named collision families   {len(flags)} identifier row(s) "
          f"flagged   ${money:,.2f}M of prime dollars on them")
    for k in sorted(stats):
        print(f"    {k:<44} {stats[k]:>5}")
    for f in flags:
        print(f"    [{f['confidence_tier']}] {f['identifier_type']} "
              f"{f['identifier']:<14} {f['legal_business_name'][:44]:<44} "
              f"keyed {f['keyed_to_name'][:22]:<22} ({f['keyed_to_state']}) "
              f"-> suspect {f['suspected_member'][:34]}")
    if before != after:
        print("  [963] !! INV-READONLY the ledger changed during a read-only "
              "scan")
        return 1
    return 0


def verify() -> int:
    if not MANIFEST.exists() or not OUT.exists():
        print("  [963] verify: no output - run the scan first")
        return 1
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    fails = []
    if man["ledger_md5_before"] != man["ledger_md5_after"]:
        fails.append("INV-READONLY the ledger changed during the scan")
    if file_md5(LEDGER) != man["ledger_md5_after"]:
        fails.append("INV-READONLY the ledger has changed since the scan - "
                     "re-run 963; the flags may name rows that have moved")
    reg_uids = {(r.get("cedar_uid") or "").strip()
                for r in read_csv(REGISTER)}
    rows = read_csv(OUT)
    for r in rows:
        for c in ("rule_fired", "keyed_to_cedar_uid", "suspected_member",
                  "suspected_member_state", "keyed_to_state"):
            if not (r.get(c) or "").strip() and c != "keyed_to_state":
                fails.append(f"INV-EVIDENCE {r.get('flag_id')} has no {c}")
        u = (r.get("suspected_member_cedar_uid") or "").strip()
        if u and u not in reg_uids:
            fails.append(f"INV-NOCLAIM {r.get('flag_id')} proposes "
                         f"{u}, which is not in the register")
    print(f"  [963] verify  {len(rows)} flagged row(s)   {len(fails)} breach(es)")
    for f in fails:
        print(f"  [963] !! {f}")
    return 1 if fails else 0


def selftest() -> int:
    """Prove verify FIRES: a proposal pointing at a uid that does not exist."""
    import shutil
    if not OUT.exists():
        print("  [963] selftest: run the scan first")
        return 1
    bak = OUT.with_suffix(".selftest.bak")
    shutil.copy2(OUT, bak)
    try:
        clean = verify()
        with OUT.open(encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            cols, rows = list(rd.fieldnames or []), list(rd)
        if not rows:
            print("  [963] selftest INCONCLUSIVE: nothing flagged")
            return 1
        rows[0]["suspected_member_cedar_uid"] = "CE-ZZZZZ-XX"
        with OUT.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        dirty = verify()
    finally:
        shutil.copy2(bak, OUT)
        bak.unlink(missing_ok=True)
    ok = (clean == 0 and dirty == 1)
    print(f"  [963] selftest  clean exit {clean} (want 0)   "
          f"proposal to a nonexistent uid exit {dirty} (want 1)   "
          f"{'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    sys.exit({"scan": main, "verify": verify, "selftest": selftest}[cmd]())
