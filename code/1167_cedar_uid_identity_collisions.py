#!/usr/bin/env python3
"""
Cedar Press - 1167: find `cedar_uid` values that resolve to more than one Native
entity, and separate a real merge from a harmless alias.

    py -3 code/1167_cedar_uid_identity_collisions.py          # report
    py -3 code/1167_cedar_uid_identity_collisions.py verify   # exit 1 on a MERGE

WHY
---
Owner, 2026-09-02: *"The Cedar UID must always resolve to the same impermeable
Native entity, while the dataset separately identifies the event/object/business
and describes the Native entity's role."*

That invariant has never been guarded. `846_session_audit.py:128` asserts *"every
cedar_uid in the register is unique and none is blank"*, which is a DIFFERENT
claim - uniqueness of a register row, not "resolves to one entity in the ledger".
A uid can be perfectly unique as a register row and still name two tribes
downstream, and twelve of them do.

WHY THIS TEST AND NOT THE OBVIOUS ONE
--------------------------------------
The first version of this check compared `cedar_uid` against `tribe_id`. That was
wrong twice over. `tribe_id` is the CICD NEID, which the owner retired on
2026-09-01 (`843_retire_cicd_scheme.py`) and had to repeat on 2026-09-03 because
77 files in `data/clean` still carried it. Testing Cedar's identity against a
retired scheme measures the retired scheme, not Cedar. Worse, it would have gone
on reporting collisions after the NEID column was finally dropped everywhere, and
then silently reported none - not because they were fixed but because the
evidence column was gone.

So this test never reads `tribe_id`. It asks only: for one `cedar_uid`, how many
distinct `canonical_name` values sit on its POSITIVE rows? That question survives
any identifier migration, because `canonical_name` is what the uid is claiming to
BE.

Tier X rows are excluded. A tier-X row records a REFUSED candidate (AGENTS.md
:1962), so counting its name would invent a collision out of a correct refusal.

ALIAS vs MERGE - THE WHOLE DIFFICULTY
--------------------------------------
Measured 2026-09-03: 209 of 859 uids carry more than one canonical name. Reporting
that as 209 defects would be false and would bury the real ones. The overwhelming
majority are the same entity written short and long:

    Navajo / Navajo Nation          Hopi / Hopi Tribe        Zuni / Pueblo of Zuni

Those are ALIAS and they are fine. What is not fine is two entities sharing a key:

    Bristol Bay Native Corporation / Buena Vista Rancheria
    Cook Inlet Region, Incorporated / Lumbee
    Tikigaq Corporation / Paiute Indian Tribe of Utah

The separator is token containment, not string similarity. Similarity scores
would rank `Crow` against `Crow Creek` as near-identical when they are two
federally recognized tribes, and would rank `Zuni` against `Pueblo of Zuni` as
distant when they are one. Containment gets both right: every distinctive token of
the shorter name appears in the longer one, or it does not.

STOPWORDS ARE LOAD-BEARING AND ARE NOT A CONVENIENCE
-----------------------------------------------------
`Tribe`, `Nation`, `Band`, `of`, `the`, `Indians` carry no identity - `Hopi` and
`Hopi Tribe` differ only by one. But `Corporation`, `Inc` and `Council` are NOT
stopworded here, because in Alaska they are exactly what distinguishes an ANCSA
village corporation from the federally recognized village of the same name -
different legal persons under 43 U.S.C. 1607 and 25 U.S.C. 5123. Stopwording them
would silently merge `Cape Fox Corporation` into `Saxman` and call it an alias.
That is the error this script exists to find, so it must not commit it.
"""

import csv
import re
import shutil
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/clean/cedar_identifier_ledger_final.csv"
OUT = ROOT / "review" / f"1167_cedar_uid_collisions_{date.today().isoformat()}.csv"

csv.field_size_limit(10_000_000)

# Words that never distinguish one Native entity from another.
# NOTE what is deliberately ABSENT: corporation, inc, council, authority, village.
# See the module docstring - in Alaska those words ARE the distinction.
STOP = {
    "tribe", "tribes", "nation", "nations", "band", "bands", "of", "the", "and",
    "indian", "indians", "reservation", "community", "pueblo", "rancheria",
    "a", "in", "at", "for",
}


def tokens(name: str) -> set:
    """Distinctive tokens: lowercase words, minus stopwords and pure noise."""
    words = re.findall(r"[A-Za-z0-9']+", (name or "").lower())
    return {w for w in words if w not in STOP and len(w) > 1}


def _near(a: str, b: str) -> bool:
    """True when two tokens differ by a single edit - a typo, not an entity.

    `Warm Springs Tribe` vs `Warms Springs Tribe` has disjoint token sets under
    the containment test and would be reported as two entities sharing a key. It
    is one entity and a stray `s`. Without this, the script's own output would
    contain a defect of the kind it claims to detect.
    """
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    for i in range(len(long_)):
        if long_[:i] + long_[i + 1:] == short:
            return True
    return False


def _typo_equivalent(a: set, b: set) -> bool:
    """Token sets that match once single-character typos are forgiven."""
    only_a, only_b = a - b, b - a
    if not only_a or not only_b or len(only_a) != len(only_b):
        return False
    remaining = list(only_b)
    for token in only_a:
        hit = next((r for r in remaining if _near(token, r)), None)
        if hit is None:
            return False
        remaining.remove(hit)
    return True


def classify(names: list) -> str:
    """ALIAS if every name nests into a common core; MERGE if two are disjoint.

    Pairwise, because a three-name group can hold one alias pair and one true
    merge at once - CE-0018V-EC is exactly that: `Paiute Indian Tribe of Utah`
    and `Paiute of Utah` are an alias pair, and `Tikigaq Corporation` is an
    intruder on both.

    Returns MERGE, ALIAS, or TYPO. TYPO is reported separately because it is a
    real defect - a misspelled canonical name - but NOT an identity collision,
    and conflating the two would overstate the collision count.
    """
    toks = [tokens(n) for n in names]
    verdict = "ALIAS"
    for i in range(len(toks)):
        for j in range(i + 1, len(toks)):
            a, b = toks[i], toks[j]
            if not a or not b:
                continue
            if a <= b or b <= a:
                continue
            if _typo_equivalent(a, b):
                verdict = "TYPO"
                continue
            return "MERGE"
    return verdict


ALIASES = ROOT / "data/clean/entity_aliases.csv"


def _norm_alias(name: str) -> str:
    """Case, punctuation and the article `the`, and nothing else.

    `Confederated Tribes of Warm Springs Reservation` in the ledger against
    `Confederated Tribes of the Warm Springs Reservation` in the alias table is
    one word apart and is the same tribe. Corporate suffixes are still NOT
    stripped - see the module docstring; `Cape Fox Corporation` must never fold
    into `Saxman`.
    """
    s = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower())
    s = re.sub(r"\bthe\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def alias_index():
    """normalised alias name -> {cedar_uid}, from Cedar's own alias table.

    THE ALIAS TABLE ALREADY KNEW. External review, 2026-09-03:

        "Official aliases, historical names, and renamings should be
         adjudicated through an alias and name-history table, not continually
         rediscovered through text comparisons."

    Correct, and sharper than it sounds: `data/clean/entity_aliases.csv` holds
    6,298 rows and BOTH remaining MERGE collisions were already recorded in it.
    `Fort Sill Apache Tribe of Oklahoma` is a `shortened` alias of
    CE-0014G-RS. `Sycuan Band of the Kumeyaay Nation` is a `legal` alias of
    CE-001B4-KX. The containment heuristic was re-deriving, badly, a fact the
    repo had already adjudicated - and getting one of them wrong.

    So the alias table is consulted FIRST and the heuristic only runs on names
    it has never seen.
    """
    idx = defaultdict(set)
    if not ALIASES.exists():
        return idx
    with ALIASES.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            uid = (row.get("cedar_uid") or "").strip()
            nm = _norm_alias(row.get("alias_name"))
            if uid and nm:
                idx[nm].add(uid)
    return idx


def register_truth():
    """cedar_uid -> canonical_name, and canonical_name -> {uid}, from the spine.

    The register is the arbiter and can be, because it holds EXACTLY ONE row per
    uid - verified, all 210 colliding uids present, one row each. So when a
    LEDGER row carries uid U under a name the register does not give U, the
    ledger row is what is wrong.
    """
    reg, by_name = {}, defaultdict(set)
    path = ROOT / "data/spine/cedar_identity_register.csv"
    if not path.exists():
        sys.exit(f"FATAL: {path} is absent - nothing can arbitrate")
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            uid = (row.get("cedar_uid") or "").strip()
            name = (row.get("canonical_name") or "").strip()
            if uid and name:
                reg[uid] = name
                by_name[name].add(uid)
    return reg, by_name


def repoint(apply_it: bool):
    """Send each mis-keyed ledger row to the uid the register gives its name.

    THREE OUTCOMES, and separating them is the whole job:

      REPOINT     the name has its own register row, exactly one. The ledger
                  row is pointing at the wrong uid and the right one is known.
                  16 rows, measured 2026-09-03.
      MINT_NEEDED the name has NO register row and is a constituent band that
                  the owner ruled on 2026-09-03 operates as its own entity:
                  "The bands operate on their own and have their own stuff, but
                  the Minnesota Chippewa tribe has its own stuff." Those bands
                  were never minted, which is why the ledger parked them on the
                  parent's uid. Minting is not repointing and is NOT done here.
      ALIAS       the name has no register row because it is the same entity
                  written long - `Pueblo of Zuni` against `Zuni`. Not a defect.
                  `classify()` already separates these and they are skipped.
    """
    reg, by_name = register_truth()
    rows = list(csv.DictReader(
        LEDGER.open(encoding="utf-8-sig", errors="replace", newline="")))
    by_uid = defaultdict(set)
    for r in rows:
        u = (r.get("cedar_uid") or "").strip()
        n = (r.get("canonical_name") or "").strip()
        if u and n and (r.get("confidence_tier") or "").strip() != "X":
            by_uid[u].add(n)
    ali = alias_index()
    by_uid = {u: {n for n in ns if u not in ali.get(_norm_alias(n), set())}
              for u, ns in by_uid.items()}
    merges = {u for u, ns in by_uid.items()
              if len(ns) > 1 and classify(sorted(ns)) == "MERGE"}

    plan, mint = [], []
    for r in rows:
        uid = (r.get("cedar_uid") or "").strip()
        name = (r.get("canonical_name") or "").strip()
        if uid not in merges or not name or name == reg.get(uid):
            continue
        # A NAME INSIDE A MERGE UID CAN STILL BE AN ALIAS OF THAT UID.
        #
        # `classify()` asks about the uid as a whole: does it carry two names
        # that are not containment-related? CE-0018V-EC does - `Tikigaq
        # Corporation` against `Paiute of Utah` - so the uid is a MERGE. But it
        # ALSO carries `Paiute Indian Tribe of Utah`, which is simply the long
        # form of the register's own name for it, and the first version of this
        # function reported that as MINT_NEEDED: a proposal to mint a new
        # entity for a tribe Cedar already holds. Same for `Sycuan Band of
        # Mission Indians` and `Eastern Shoshone Tribe of the Wind River
        # Reservation`.
        #
        # So each name is re-tested against the register's name for its OWN
        # uid. Containment-related means alias, and an alias is left alone.
        if classify([name, reg.get(uid, "")]) != "MERGE":
            continue
        target = sorted(by_name.get(name, []))
        if not target:
            # The register spells it differently. Ask the alias table before
            # concluding a new entity must be minted - this is what wrongly
            # reported `Confederated Tribes of Warm Springs Reservation` as
            # MINT_NEEDED when CE-001CA-W3 already holds it as a `legal` alias,
            # one word apart ("of the Warm Springs" vs "of Warm Springs").
            target = sorted(ali.get(_norm_alias(name), set()))
        if len(target) == 1 and target[0] != uid:
            plan.append((r, uid, target[0], name))
        elif not target:
            mint.append((r, uid, name))

    # SECOND PASS, NOT GATED ON THE UID BEING A MERGE.
    #
    # The pass above only inspects uids that `classify()` calls MERGE, which
    # misses a row that is mis-keyed on its own. Measured 2026-09-03, after the
    # first pass had run: ONE such row remained in 20,740 -
    #
    #     CE-0017X-NE  "Oneida Nation (Wisconsin)"   -> should be CE-0017Y-V7
    #
    # The register is unambiguous about both: CE-0017X-NE is handle
    # TRBF-ONDANY-00, "Oneida", NY; CE-0017Y-V7 is TRBF-ONDAWI-00, "Oneida
    # Nation (Wisconsin)", WI. Twenty-two rows carry the Wisconsin handle
    # correctly and that one carried it against the New York uid.
    #
    # It was not a rounding error. It made TRBF-ONDAWI-00 claim two uids, which
    # made the NEID->uid map ambiguous for that handle, which left **290
    # retired identifiers in the delivered files** that could not be translated.
    # One row, four datasets downstream.
    #
    # The rule is narrow on purpose: the name must resolve to EXACTLY ONE
    # register uid. A name the register does not hold, or holds twice, is left
    # alone - this pass corrects a key, it never invents one. Measured blast
    # radius across the whole ledger: 1 row.
    # FOREIGN NAMES ARE REPOINTED TOO. They were detected in main() and not
    # acted on here, so `repoint` reported "nothing to write" while a known
    # misattribution stood - a report and a remedy that disagreed with each
    # other. Same rule as everywhere else: the name must resolve to exactly one
    # OTHER uid, via the register or the alias table.
    for r in rows:
        uid = (r.get("cedar_uid") or "").strip()
        name = (r.get("canonical_name") or "").strip()
        if not uid or not name:
            continue
        if uid in ali.get(_norm_alias(name), set()):
            continue
        owners = ((by_name.get(name) or set())
                  | ali.get(_norm_alias(name), set())) - {uid}
        if len(owners) == 1:
            plan.append((r, uid, next(iter(owners)), name))

    already = {id(r) for r, *_ in plan}
    for r in rows:
        if id(r) in already:
            continue
        uid = (r.get("cedar_uid") or "").strip()
        name = (r.get("canonical_name") or "").strip()
        if not uid or not name:
            continue
        target = by_name.get(name, set())
        if len(target) == 1:
            t = next(iter(target))
            if t != uid:
                plan.append((r, uid, t, name))

    print(f"  colliding uids classified MERGE : {len(merges)}")
    print(f"  ledger rows to REPOINT          : {len(plan)}")
    print(f"  names with no register row      : {len(mint)}  (mint, do not repoint)")
    print()
    for _r, old, new, name in plan:
        print(f"    {old} -> {new}   {name}")
    for _r, old, name in mint:
        print(f"    MINT_NEEDED  {name}  (parked on {old})")

    if not apply_it:
        print("\n  dry run - pass `repoint apply` to write")
        return
    if not plan:
        print("\n  nothing to write")
        return
    bak = LEDGER.with_suffix(
        LEDGER.suffix + f".bak_{date.today().isoformat()}_pre_1167_repoint")
    shutil.copy(LEDGER, bak)
    for r, _old, new, _name in plan:
        r["cedar_uid"] = new
    tmp = LEDGER.with_suffix(LEDGER.suffix + ".part")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    tmp.replace(LEDGER)
    print(f"\n  backed up -> {bak.name}")
    print(f"  wrote {LEDGER.name} ({len(rows):,} rows, {len(plan)} repointed)")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "repoint":
        return repoint(apply_it=len(sys.argv) > 2 and sys.argv[2] == "apply")
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    if not LEDGER.exists():
        sys.exit(f"FATAL: {LEDGER} is absent")

    by_uid = defaultdict(set)
    with LEDGER.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            uid = (row.get("cedar_uid") or "").strip()
            name = (row.get("canonical_name") or "").strip()
            tier = (row.get("confidence_tier") or "").strip()
            if uid and name and tier != "X":
                by_uid[uid].add(name)

    ali = alias_index()
    reg, by_name = register_truth()

    # A NAME THAT BELONGS TO A DIFFERENT UID IS A DEFECT ON ITS OWN.
    #
    # Consulting the alias table first was right and it immediately created a
    # blind spot. CE-0014G-RS carried three names; the alias table recognises
    # two of them as its own, leaving ONE - `Confederated Tribes of Warm Springs
    # Reservation`, which belongs to CE-001CA-W3, a different tribe in a
    # different state. A collision test needs two names to compare, so filtering
    # to one made a real misattribution report as zero. Fourth silent zero of
    # the session and the same shape as the others: the check stopped being able
    # to see the thing it was for.
    #
    # So `foreign` is tested independently of how many names a uid has left.
    foreign = {}
    for u, ns in by_uid.items():
        for n in ns:
            if u in ali.get(_norm_alias(n), set()):
                continue                       # recorded as this uid's own name
            owners = (by_name.get(n) or set()) | ali.get(_norm_alias(n), set())
            owners = {o for o in owners if o != u}
            if len(owners) == 1:
                foreign.setdefault(u, []).append((n, next(iter(owners))))

    # Drop any name the alias table already records for THIS uid. What remains
    # is genuinely unadjudicated, and only that goes to the heuristic.
    by_uid = {u: {n for n in ns if u not in ali.get(_norm_alias(n), set())}
              for u, ns in by_uid.items()}
    multi = {u: sorted(n) for u, n in by_uid.items() if len(n) > 1}
    buckets = {"MERGE": {}, "ALIAS": {}, "TYPO": {}}
    for uid, names in multi.items():
        buckets[classify(names)][uid] = names
    merges, aliases, typos = buckets["MERGE"], buckets["ALIAS"], buckets["TYPO"]

    if foreign:
        print(f"  FOREIGN NAMES - a uid carrying a name that belongs to another "
              f"uid: {sum(len(v) for v in foreign.values())} on {len(foreign)} uid(s)")
        for u, items in sorted(foreign.items()):
            for n, owner in items:
                print(f"      {u}  holds  {n[:52]:<52} -> belongs to {owner}")
        print()
    print(f"  cedar_uid values examined            : {len(by_uid):>6,}")
    print(f"  carrying more than one canonical name: {len(multi):>6,}")
    print(f"    ALIAS (short/long form, benign)    : {len(aliases):>6,}")
    print(f"    TYPO  (one entity, misspelt name)  : {len(typos):>6,}   <-- fix the name")
    print(f"    MERGE (two entities, ONE KEY)      : {len(merges):>6,}   <-- defects")
    print()
    for uid, names in sorted(typos.items()):
        print(f"  TYPO {uid}: {' | '.join(names)}")
    if typos:
        print()
    for uid, names in sorted(merges.items()):
        print(f"  {uid}")
        for n in names:
            print(f"        {n}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["verdict", "cedar_uid", "n_names", "canonical_names"])
        for uid, names in sorted(merges.items()):
            w.writerow(["MERGE", uid, len(names), " | ".join(names)])
        for uid, names in sorted(typos.items()):
            w.writerow(["TYPO", uid, len(names), " | ".join(names)])
        for uid, names in sorted(aliases.items()):
            w.writerow(["ALIAS", uid, len(names), " | ".join(names)])
    print(f"\n  wrote {OUT.relative_to(ROOT)}")

    if verify and (merges or foreign):
        sys.exit(f"FAIL: {len(merges)} cedar_uid value(s) resolve to more than "
                 f"one Native entity; {sum(len(v) for v in foreign.values())} "
                 f"row-name(s) belong to a different uid")


if __name__ == "__main__":
    main()
