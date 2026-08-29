#!/usr/bin/env python3
r"""
Cedar Press - 244: refresh the two individual-Native review queues, and SPLIT
them, because they are two different questions in one file.

WHAT WAS IN ONE FILE AND SHOULD NOT HAVE BEEN
----------------------------------------------
`review/individual_native_ownership_ambiguous_2026-08-26.csv` holds **164 rows**
and `docs/INDIVIDUAL_NATIVE_OWNERSHIP_VERIFICATION_BUILD_LOG.md` §9 breaks them
down:

    MISSING ENTITY ATTRIBUTION                                      67
    site unreachable - retry, not a finding                         37
    native-sounding name (trap token), no supporting claim          24
    claims Native ownership without saying individual or tribal     22
    the only 'third party' found is a SAM mirror or a press release 14
    a source names a NON-Native owner against a federal native flag  1

**The 67 are not this class's question at all.** They are firms whose OWN SITE
declares a tribe, an ANC or an NHO as owner while Cedar attributes them to
nobody - *"missing tier-A ENTITY attributions, at the dollar figure already in
the row"*. The build log calls this the by-product that may be worth more than
the product, and it is the OPPOSITE finding from the one the pass set out to
make. Mixing it into a queue about individual ownership means a reader answering
one question keeps meeting the other, and the two need different evidence and
different reviewers.

So this script writes:

    review/individual_native_ownership_ambiguous_<date>.csv   the 97
    review/missing_entity_attribution_<date>.csv              the 67

**Neither queue is ANSWERED here.** Refreshing a question is not answering it.
`YOUR_RULING` and `YOUR_NOTE` are carried forward BLANK unless the previous file
already held a value, in which case the value is preserved verbatim - an
overwritten ruling is a lost ruling.

WHAT THE REFRESH ADDS
---------------------
Every row now carries `now_in_spine` / `now_surrogate_entity_id`, because 45
firms landed in the spine in this session (`code/241`) and a queue that still
asks about a settled firm wastes the reviewer's only scarce resource. Where a
row's firm is now a ruled entity, the row says so and stays in the file rather
than being deleted, so the reviewer can see what moved.

The MISSING ENTITY ATTRIBUTION queue deliberately **proposes no entity**.
Resolving one from a name is the containment defect, and half these names are
`cedar_domain.NAME_TRAPS` terms. It carries the firm's own declaring sentence,
its URL and its obligation figure, and asks a human.

    py -3 code/244_refresh_individual_native_review_queues.py

Reads   review/individual_native_ownership_ambiguous_2026-08-26.csv
        data/clean/individual_native_ownership_verification.csv
        data/clean/individual_native_firm_register.csv
        data/spine/cedar_entity_spine.csv
Writes  review/individual_native_ownership_ambiguous_<date>.csv
        review/missing_entity_attribution_<date>.csv
        logs/244_refresh_individual_native_review_queues.log
"""

import csv
import importlib.util
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

CEDAR = Path(r"C:\Users\esm247\Desktop\Cedar Press")
CLEAN = CEDAR / "data" / "clean"
REVIEW = CEDAR / "review"
SPINE = CEDAR / "data" / "spine" / "cedar_entity_spine.csv"
LOGS = CEDAR / "logs"
TODAY = date.today().isoformat()
BACKUP_TAG = "pre_244_refresh_individual_native_review_queues"

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))
LOG_LINES = []


def log(m=""):
    print(m)
    LOG_LINES.append(m)


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, CEDAR / "code" / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = load_module("cedar_domain", "cedar_domain.py")

MISSING_ENTITY = "MISSING ENTITY ATTRIBUTION"


def load(p):
    p = Path(p)
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def write_atomic(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        bak = Path(f"{path}.bak_{TODAY}_{BACKUP_TAG}")
        if not bak.exists():
            shutil.copy2(path, bak)
            log(f"  backed up -> {bak.name}")
    part = Path(str(path) + ".part")
    with open(part, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({f: r.get(f, "") for f in fields})
    part.replace(path)
    log(f"  wrote {path.relative_to(CEDAR)}  ({len(rows):,} rows)")


def main():
    log("=== Cedar Press 244: refresh and SPLIT the individual-Native queues "
        "===\n")

    # Take the most recent existing queue, whatever its date stamp.
    # IDEMPOTENCE: this script SPLITS one file into three, so on a second run
    # the "prior queue" it globs is its own output and the split has already
    # happened. Re-uniting every file it writes before splitting again is what
    # makes a re-run a no-op instead of a silent amputation - measured: a naive
    # re-run reported "missing-entity queue: 0" while 67 rows sat in the file
    # beside it, and the row-count guard PASSED because it was comparing
    # against the already-shortened input. A guard that reads the shortened
    # input certifies the shortening.
    prior, seen_rows = [], set()
    for pattern in ("individual_native_ownership_ambiguous_*.csv",
                    "missing_entity_attribution_*.csv",
                    "individual_native_queue_withdrawn_already_ruled_*.csv"):
        for path in sorted(REVIEW.glob(pattern)):
            if ".bak_" in path.name or ".part" in path.name:
                continue
            for row in load(path):
                key = ((row.get("awardee_uei") or "").upper(),
                       (row.get("why_queued") or "").strip())
                if key in seen_rows:
                    continue
                seen_rows.add(key)
                prior.append(row)
    log(f"  prior queues re-united : {len(prior)} distinct rows")

    verification = load(CLEAN / "individual_native_ownership_verification.csv")
    register = load(CLEAN / "individual_native_firm_register.csv")
    spine = load(SPINE)
    log(f"  verification: {len(verification)} rows")
    log(f"  register    : {len(register)} firms now in the spine")
    log(f"  spine       : {len(spine)} entities, "
        f"{sum(1 for r in spine if r.get('entity_class') == D.INDIVIDUAL_NATIVE_CLASS)}"
        f" in class {D.INDIVIDUAL_NATIVE_CLASS!r}")

    # Keyed on IDENTITY. `verification_id` is POSITIONAL: a concurrent rewrite
    # of prime_contracts.csv on 2026-08-26 shifted every id below an insertion
    # point and put one firm's ownership sentence on another firm's row, with
    # its URL and fetch date, and nothing errored. Never join on a rank.
    reg_by_uei = {r["identifier"].upper(): r for r in register
                  if r["identifier_type"] == "UEI"}
    ver_by_uei = {(r["awardee_uei"] or "").upper(): r for r in verification
                  if (r["awardee_uei"] or "").strip()}

    # Preserve any ruling the owner has already written into the prior file.
    prior_answers = {}
    for r in prior:
        u = (r.get("awardee_uei") or "").upper()
        if u and ((r.get("YOUR_RULING") or "").strip()
                  or (r.get("YOUR_NOTE") or "").strip()):
            prior_answers[u] = (r.get("YOUR_RULING", ""), r.get("YOUR_NOTE", ""))
    log(f"  rulings already written into the prior queue, carried forward "
        f"VERBATIM: {len(prior_answers)}")

    # ---- SUBTRACT WHAT THE OWNER HAS ALREADY RULED ----------------------
    # A queue that asks a human about something he already decided burns his
    # only scarce resource and invites him to contradict himself. The
    # 2026-08-12 Schedule I queue asked about 30 EINs already ruled tier X,
    # including UNITED WAY OF THE GREATER CHIPPEWA VALLEY - the case the whole
    # tier-inheritance rule was built on.
    #
    # The subtraction is SCOPED, not blanket: a tier-X row excludes a
    # (identifier, entity) PAIR, so it settles "is this firm owned by THAT
    # entity" and does NOT settle "who owns this firm". A blanket withdrawal on
    # the identifier would suppress a question the ruling never answered.
    ledger = load(CLEAN / "cedar_identifier_ledger_final.csv")
    ruled_x = {}
    for r in ledger:
        if (r.get("confidence_tier") or "").strip() != "X":
            continue
        ruled_x.setdefault(((r.get("identifier_type") or "").strip().upper(),
                            (r.get("identifier") or "").strip().upper()),
                           []).append(r)
    log(f"  ledger tier-X keys indexed for subtraction: {len(ruled_x)}")

    ambiguous, missing_entity, withdrawn = [], [], []
    stats = Counter()

    for r in prior:
        u = (r.get("awardee_uei") or "").upper()
        why = (r.get("why_queued") or "").strip()
        reg = reg_by_uei.get(u)
        ver = ver_by_uei.get(u)
        ruling, note = prior_answers.get(u, ("", ""))

        base = dict(r)
        base["YOUR_RULING"] = ruling
        base["YOUR_NOTE"] = note
        base["now_in_spine"] = "1" if reg else "0"
        base["now_surrogate_entity_id"] = (reg or {}).get(
            "surrogate_entity_id", "")
        base["now_entity_class"] = D.INDIVIDUAL_NATIVE_CLASS if reg else ""
        base["queue_refreshed_date"] = TODAY
        xrows = ruled_x.get(("UEI", u), [])
        base["standing_tier_X_ruling"] = "|".join(
            sorted({(x.get("tier_rationale") or "")[:180] for x in xrows}))
        base["standing_tier_X_entity"] = "|".join(
            sorted({(x.get("tribe_id") or "").strip()
                    for x in xrows if (x.get("tribe_id") or "").strip()}))
        base["withdrawn_reason"] = ""
        if xrows:
            stats["carries a standing tier-X ruling - shown to the reviewer"] += 1
        base["queue_refreshed_by"] = \
            "code/244_refresh_individual_native_review_queues.py"

        if why.upper().startswith(MISSING_ENTITY):
            # A DIFFERENT QUESTION. The firm's own site names a tribe, an ANC
            # or an NHO as owner and Cedar attributes it to nobody. That is a
            # missing tier-A ENTITY attribution at the dollar figure already in
            # the row - the opposite of an individual-ownership finding.
            base["question"] = (
                "This firm's own site declares a TRIBE, ANC or NHO as its "
                "owner, and Cedar attributes it to nobody. Which spine entity "
                "is the owner? No entity is proposed here on purpose: "
                "resolving one from the name is the containment defect, and "
                "several of these names are cedar_domain.NAME_TRAPS terms. "
                "Answer with the entity, or NO - not that owner.")
            base["declaring_sentence"] = (ver or {}).get(
                "self_description_sentence", r.get("self_description_sentence", ""))
            base["declaring_url"] = (ver or {}).get(
                "self_description_url", r.get("self_description_url", ""))
            base["ownership_class_from_evidence"] = (ver or {}).get(
                "ownership_class", "")
            base["tribal_affiliation_name"] = (ver or {}).get(
                "tribal_affiliation_name", "")
            # A tier-X row that NAMES an entity has already answered "is it
            # that one?" for that pair. Withdrawn and REPORTED in its own file,
            # never silently dropped.
            if base["standing_tier_X_entity"]:
                base["withdrawn_reason"] = (
                    f"Already ruled tier X on this identifier against "
                    f"{base['standing_tier_X_entity']}. That refuses the PAIR, "
                    f"not the firm, so 'who DOES own it' stays open - but it "
                    f"must not be re-asked against the entity already refused.")
                withdrawn.append(base)
                stats["withdrawn: already ruled X against the named entity"] += 1
                continue
            missing_entity.append(base)
            stats["MISSING ENTITY ATTRIBUTION -> its own queue"] += 1
            continue

        base["question"] = why or (
            "Ambiguous individual-Native ownership evidence. See tier_basis.")
        base["evidence_independence"] = (ver or {}).get(
            "evidence_independence", "")
        base["third_party_independence"] = (ver or {}).get(
            "third_party_independence", "")
        base["name_trap_warning"] = (ver or {}).get("name_trap_warning", "")
        base["privacy_class"] = (ver or {}).get("privacy_class", "")
        base["publishable_entity_name"] = (ver or {}).get(
            "publishable_entity_name", "")
        base["absence_vocabulary_note"] = (
            "Absence is NO_CLAIM_FOUND, NO_SITE_FOUND, SITE_UNREACHABLE or "
            "NOT_CHECKED. There is no NOT_NATIVE value in this schema and "
            "there never will be one. 'Nobody said' is not 'the answer is no', "
            "and the 106 NO_SITE_FOUND rows come from sessions that exhausted "
            "a ~200-call search budget - a CEILING on absence, not a "
            "measurement of it.")
        ambiguous.append(base)
        stats[f"ambiguous: {why[:52]}"] += 1
        if reg:
            stats["  ...of which the firm is NOW a ruled spine entity"] += 1

    log("\n[1] Split")
    for k, v in stats.most_common():
        log(f"  {k:62s} {v:>4}")

    log(f"\n  ambiguous queue      : {len(ambiguous)}")
    log(f"  missing-entity queue : {len(missing_entity)}")
    log(f"  total                : {len(ambiguous) + len(missing_entity)} "
        f"(prior file held {len(prior)})")
    log(f"  withdrawn (already ruled)  : {len(withdrawn)}")
    if len(ambiguous) + len(missing_entity) + len(withdrawn) != len(prior):
        raise SystemExit("ABORT: the split lost or invented rows. A refresh "
                         "that changes the row count silently is a refresh "
                         "that dropped somebody's question.")

    n_settled = sum(1 for r in ambiguous + missing_entity
                    if r["now_in_spine"] == "1")
    log(f"  rows whose firm is now a ruled entity in the spine : {n_settled}")
    log("  those rows are KEPT, flagged, and not deleted - the reviewer should "
        "see")
    log("  what moved rather than find a shorter file with no explanation.")

    log("\n[2] Guard: nothing here is answered")
    answered = sum(1 for r in ambiguous + missing_entity + withdrawn
                   if (r.get("YOUR_RULING") or "").strip())
    log(f"  rows carrying a YOUR_RULING : {answered}  "
        f"(all carried forward from the prior file, none written here)")
    if answered != len(prior_answers):
        raise SystemExit("ABORT: the number of answered rows changed. This "
                         "script refreshes questions; it must never answer "
                         "one.")
    for r in ambiguous + missing_entity + withdrawn:
        for k, v in r.items():
            if not D.absence_value_ok(v):
                raise SystemExit(f"ABORT: forbidden absence value {v!r} in {k}.")
    log("  forbidden absence values (NOT_NATIVE et al.) : 0")

    log("\n[3] Writing")
    amb_fields = list(ambiguous[0].keys()) if ambiguous else []
    me_fields = list(missing_entity[0].keys()) if missing_entity else []
    if ambiguous:
        write_atomic(REVIEW / f"individual_native_ownership_ambiguous_{TODAY}.csv",
                     ambiguous, amb_fields)
    if missing_entity:
        write_atomic(REVIEW / f"missing_entity_attribution_{TODAY}.csv",
                     missing_entity, me_fields)
    if withdrawn:
        write_atomic(
            REVIEW / f"individual_native_queue_withdrawn_already_ruled_{TODAY}.csv",
            withdrawn, list(withdrawn[0].keys()))

    log("\n[4] Verify by RE-READING")
    a = load(REVIEW / f"individual_native_ownership_ambiguous_{TODAY}.csv")
    b = load(REVIEW / f"missing_entity_attribution_{TODAY}.csv")
    log(f"  ambiguous on disk      : {len(a):,}")
    log(f"  missing-entity on disk : {len(b):,}")

    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / "244_refresh_individual_native_review_queues.log").write_text(
        "\n".join(LOG_LINES), encoding="utf-8")


if __name__ == "__main__":
    main()
