#!/usr/bin/env python3
"""
Cedar Press - 1166: rebuild the owner adjudication queue so that every card left in
it is a question only the owner can answer.

WHY THIS EXISTS
---------------
The field sheet shipped on 2026-09-02 presented 72 cards worth a nominal
$40,155,242,647. Measured on 2026-09-03 against the actual tables, most of that was
an artifact of how the cards were built, not a question about the data. The owner's
complaint was exact:

    "I'm 100% I have ruled these before and it doesn't clear the queue when I'm
     done"                                                    -- owner, 2026-09-02

He had. Four defects, each measured in docs/OWNER_QUEUE_RECONCILIATION_2026-09-03.md
and each closed by one of the gates below.

  1. PARENT-CLUSTER DOLLARS ON A CHILD'S CARD. The $19.26B card read
     "Broadleaf, Inc". Broadleaf is 324 rows / $137,013,762 -- 0.7% of the
     92,568-row ASRC parent cluster whose total the card was printing. Worse, all
     92,568 of those rows are ALREADY correctly keyed to CE-00078-KR. The single
     largest item in the queue was not a question at all.

  2. ONE UEI'S DOLLARS PRINTED ONCE PER CARD. Four UEIs carried 14 cards between
     them, each showing the full cluster total. Summing the cards double-counted
     $13,080,624,275 -- 32.6% of the stated queue.

  3. NEGATIVE RULINGS RE-ASKED. 14 cards / $469,658,366 matched a ledger row that
     was ALREADY tier X. Tier X is not missing data; AGENTS.md:1962 defines it as a
     negative ruling, and the tribe_id on a tier-X row records WHICH candidate was
     rejected. Reading a refusal as an open conflict is what made the queue
     un-clearable.

  4. DIACRITICS COUNTED AS DISAGREEMENT. `Ukpeagvik Inupiat Corporation` vs
     `UKPEAGVIK INUPIAT CORPORATION` is one entity, and five cards / $8.03B of
     "conflict" were nothing but the diacritics.

  5. NAMES COMPARED WHERE IDENTIFIERS WERE AVAILABLE. Owner ruling 2026-09-03 on
     `Eklutna` vs `EKLUTNA, INC.`: "it's the same thing essentially... I checked
     the cage code and it goes to this website [eklutnainc.com]... I don't want
     you to get cut off in like ASRC Inc versus ASRC company. Like, that's
     stupid." He was right, and his method is the fix -- see gate 4b.

RESOLVE BY IDENTIFIER, NOT BY NAME
----------------------------------
An earlier version of this script argued that corporate suffixes are load-bearing,
because a village government and its ANCSA village corporation are different legal
persons under different statutes (25 U.S.C. 5123 vs 43 U.S.C. 1607) and must never
share a cedar_uid. That premise is TRUE and the conclusion drawn from it was WRONG:
it led to comparing two display strings and calling the difference a conflict.

Cedar already keeps those two entities apart, and it does so where it counts -- on
the identifier. UEI JWA7LVNPBSM5 resolves to ANVC-EKLUTN-00, canonical name
`Eklutna, Inc.`; the Native Village of Eklutna is a different row on a different
UEI (ZWNKTD5RK531, AKNF-EKLTNA-00-CKINLT). The card had simply abbreviated
`Eklutna, Inc.` to `Eklutna` and then compared its own abbreviation to the source
string. Same for `M3NNALGMSSX7` -> `The Port Graham Corporation`.

So gate 4b asks the only question that can actually be wrong: does the identifier
resolve to exactly one entity? If it does, the names on the card are decoration.
If it resolves to more than one, that is a data defect to fix, still not a question
for the owner. `_fold_for_identity` remains suffix-preserving, because it is now
only ever used on cards that have NO identifier to resolve.

WHAT THIS SCRIPT DOES NOT DO
----------------------------
It does not apply a single ruling. Cards are suppressed from the QUEUE when an
answer already exists somewhere; the answer itself is never written back to a
source table from here. Flag, never delete; cedar_uid is permanent.
"""

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/clean/cedar_identifier_ledger_final.csv"
RULINGS = ROOT / "review/cedar_research_rulings_2026-09-03.csv"
SHEET = ROOT / "dist/owner_rulings_field_sheet.html"
OUT_REPORT = ROOT / "review" / f"1166_queue_rebuild_{date.today().isoformat()}.csv"

csv.field_size_limit(10_000_000)

UEI_RE = re.compile(r"^[A-Z0-9]{12}$")


def _fold_for_identity(name: str) -> str:
    """Case, punctuation and diacritics only.

    NFKD then dropping combining marks turns `Ukpeaġvik Iñupiat` into
    `UKPEAGVIK INUPIAT`, which is what gate 4 needs. It deliberately leaves INC,
    CORPORATION, LLC and THE standing -- see the module docstring.
    """
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^A-Z0-9]", "", stripped.upper())


def load_cards(sheet: Path) -> list:
    src = sheet.read_text(encoding="utf-8")
    m = re.search(r"const CARDS = (\[.*?\]);\n", src, re.DOTALL)
    if not m:
        sys.exit(f"FATAL: no CARDS payload found in {sheet}")
    return json.loads(m.group(1))


def card_uei(card: dict) -> str:
    for code in card.get("codes") or []:
        if UEI_RE.fullmatch(code):
            return code
    return ""


def load_ledger_index(path: Path):
    """name -> set of tiers, and uei -> set of tiers.

    Both are needed: gate 3 matches a card by whichever identifier it carries, and
    a card that carries no UEI can still be matched by name.
    """
    by_name = defaultdict(set)
    by_uei = defaultdict(set)
    uei_to_tribes = defaultdict(set)
    uei_to_canon = {}
    if not path.exists():
        print(f"  WARNING: {path} absent - gates 3 and 4b cannot run")
        return by_name, by_uei, uei_to_tribes, uei_to_canon
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            tier = (row.get("confidence_tier") or "").strip()
            if not tier:
                continue
            for field in ("legal_business_name", "canonical_name"):
                key = _fold_for_identity(row.get(field))
                if key:
                    by_name[key].add(tier)
            ident = (row.get("identifier") or "").strip()
            if UEI_RE.fullmatch(ident):
                by_uei[ident].add(tier)
                # Gate 4b reads this. A tier-X row records a REFUSED candidate, so
                # counting it as a resolution would make every refused identifier
                # look resolved. Only positive rows resolve an identifier.
                tribe = (row.get("tribe_id") or "").strip()
                if tribe and tier != "X":
                    uei_to_tribes[ident].add(tribe)
                    uei_to_canon.setdefault(ident, (row.get("canonical_name") or "").strip())
    return by_name, by_uei, uei_to_tribes, uei_to_canon


def load_settled_ueis(path: Path) -> dict:
    """UEIs Cedar has already answered from a published source."""
    settled = {}
    if not path.exists():
        print(f"  WARNING: {path} absent - gate 2 (already-researched) cannot run")
        return settled
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            key = (row.get("uei") or row.get("cluster_key") or "").strip()
            if key:
                settled[key] = (row.get("ruled_entity") or "").strip()
    return settled


def rebuild(cards, by_name, by_uei, settled, uei_to_tribes, uei_to_canon):
    """Apply the four gates. Returns (kept, dropped) with a reason on every drop."""
    dropped = []
    survivors = {}

    for card in cards:
        uei = card_uei(card)
        subject = (card.get("subject") or "").strip()
        cedar = card.get("cedar_owner") or ""
        source = card.get("src_owner") or ""

        # GATE 4 first: a card whose two sides are the same entity was never a
        # conflict, and must not be allowed to occupy a UEI slot in gate 2.
        if cedar and source and _fold_for_identity(cedar) == _fold_for_identity(source):
            dropped.append((card, "diacritics_or_case_only__same_entity", cedar))
            continue

        # GATE 4b -- RESOLVE BY IDENTIFIER, NOT BY NAME.
        #
        # Owner ruling 2026-09-03, on `Eklutna` vs `EKLUTNA, INC.`:
        #
        #     "it's sort of like Eklutna versus Eklutna Inc. Like, it's the same
        #      thing essentially... I checked the cage code and it goes to this
        #      website [eklutnainc.com]... I don't want you to get cut off in like
        #      ASRC Inc versus ASRC company. Like, that's stupid."
        #
        # He is right, and his METHOD is better than the name test above: he
        # resolved the identifier and read off who it belongs to. Cedar already
        # does this. UEI JWA7LVNPBSM5 carries tribe_id ANVC-EKLUTN-00, canonical
        # name `Eklutna, Inc.` -- the corporation -- and the Native Village of
        # Eklutna is a SEPARATE row on a SEPARATE UEI (ZWNKTD5RK531,
        # AKNF-EKLTNA-00-CKINLT). There was never a disagreement; the card
        # abbreviated `Eklutna, Inc.` to `Eklutna` and then compared its own
        # abbreviation against the source string.
        #
        # So the correct test is not "do the two names match" but "does the
        # identifier already resolve to one entity". When the UEI resolves to
        # exactly one tribe_id in the ledger, the name shown on the card is
        # decoration and cannot be evidence of a conflict.
        #
        # This does NOT abandon the village-vs-corporation distinction -- it
        # enforces it at the level where it is actually recorded. Two different
        # UEIs resolving to two different tribe_ids stay two different entities,
        # which is exactly how Cedar already holds Eklutna and Port Graham.
        if uei:
            resolved = uei_to_tribes.get(uei, set())
            if len(resolved) == 1:
                tribe = next(iter(resolved))
                dropped.append((card, "identifier_already_resolves__name_display_only",
                                f"{uei} -> {tribe} ({uei_to_canon.get(uei, '')})"))
                continue
            if len(resolved) > 1:
                dropped.append((card, "identifier_resolves_to_MULTIPLE_entities__data_defect_not_owner_question",
                                f"{uei} -> {sorted(resolved)}"))
                continue

        # GATE 2 runs BEFORE gate 3 on purpose. Both can fire on the same card, and
        # the UEI-bound research answer is the more specific of the two. When gate 3
        # ran first, the eight cards sharing UEI KZMRSJJJN1L6 split across two
        # different suppression buckets purely on how each card's SUBJECT happened
        # to name-match the ledger -- reintroducing, in the report, the same
        # double-count this script exists to remove.
        if uei and uei in settled:
            dropped.append((card, "already_researched__see_cedar_research_rulings", settled[uei]))
            continue

        # GATE 3: already answered.
        #
        # A tier-X row records that ONE candidate was rejected -- it does not mean
        # the identifier is unattributable. An entity can carry a tier-X row
        # refusing candidate A and a tier-A row attributing it to candidate B; St
        # George Tanaq Corporation carries tiers {A, B, X} for exactly that reason.
        # So "any tier X exists" is the WRONG test, and using it inflated this gate
        # from 14 cards / $469,658,366 to 17 cards / $5,286,152,131 on the first
        # run. Split the two cases and label each honestly:
        #   - every row is a refusal          -> the question is closed, negatively
        #   - a positive row (A/B) exists too -> the question is closed, positively
        tiers = set(by_uei.get(uei, set())) | set(by_name.get(_fold_for_identity(subject), set()))
        if tiers and tiers <= {"X"}:
            dropped.append((card, "already_ruled_tier_X__negative_ruling_on_record", ""))
            continue
        if "X" in tiers:
            positives = ",".join(sorted(tiers - {"X"}))
            dropped.append((card, "already_attributed__positive_ruling_on_record",
                            f"tiers={positives} alongside a tier-X refusal"))
            continue

        # GATE 5: nothing to bind a ruling to, and nothing riding on it.
        #
        # A ruling binds to an IDENTIFIER, never to a name -- that is the whole
        # reason review/cedar_research_rulings_2026-09-03.csv is keyed on UEI. A
        # card with no identifier AND no dollars therefore cannot produce a durable
        # ruling even if the owner answers it perfectly: there is nowhere to write
        # the answer and nothing that would change if we did. Twenty-eight of the
        # thirty-one cards surviving the first four gates were in this state.
        # They are not dismissed -- they are routed to identifier backfill, which
        # is the work that has to happen before the question is answerable.
        if not uei and not card.get("usd"):
            dropped.append((card, "no_identifier_and_no_exposure__needs_uei_backfill_first", ""))
            continue

        # GATE 1: one card per UEI, and never the parent cluster's total.
        # A card with no UEI cannot be de-duplicated and is kept as-is; that is
        # safe, because keeping a question is recoverable and dropping one is not.
        if not uei:
            survivors[f"__nouei__{subject}"] = card
            continue
        prior = survivors.get(uei)
        if prior is None:
            survivors[uei] = card
        else:
            dropped.append((card, f"duplicate_of_uei_{uei}__same_dollars_already_shown", prior.get("subject", "")))

    return list(survivors.values()), dropped


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true",
                    help="write the rebuilt payload back into the field sheet")
    args = ap.parse_args()

    cards = load_cards(SHEET)
    by_name, by_uei, uei_to_tribes, uei_to_canon = load_ledger_index(LEDGER)
    settled = load_settled_ueis(RULINGS)

    kept, dropped = rebuild(cards, by_name, by_uei, settled,
                            uei_to_tribes, uei_to_canon)

    naive = sum(c.get("usd", 0) for c in cards)
    remaining = sum(c.get("usd", 0) for c in kept)

    print(f"  cards in                     : {len(cards):>5}   ${naive:>18,.0f}")
    print(f"  cards out (owner must rule)  : {len(kept):>5}   ${remaining:>18,.0f}")
    print(f"  suppressed                   : {len(dropped):>5}")
    print()
    reasons = defaultdict(lambda: [0, 0.0])
    for card, reason, _ in dropped:
        slot = reasons[reason]
        slot[0] += 1
        slot[1] += card.get("usd", 0)
    for reason, (n, usd) in sorted(reasons.items(), key=lambda kv: -kv[1][1]):
        print(f"    {n:>3} cards  ${usd:>18,.0f}  {reason}")

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with OUT_REPORT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["disposition", "subject", "uei", "usd", "reason", "detail"])
        for card in kept:
            w.writerow(["KEPT", card.get("subject", ""), card_uei(card),
                        card.get("usd", 0), "requires_owner_ruling", ""])
        for card, reason, detail in dropped:
            w.writerow(["SUPPRESSED", card.get("subject", ""), card_uei(card),
                        card.get("usd", 0), reason, detail])
    print(f"\n  wrote {OUT_REPORT.relative_to(ROOT)}")

    if not args.write:
        print("  (dry run - pass --write to update the field sheet)")
        return

    src = SHEET.read_text(encoding="utf-8")

    # The sheet saved the owner's answers under `state[c.i]` -- the card's INDEX in
    # the payload. Any rebuild reorders that array, so a saved answer would silently
    # reattach itself to whatever card now sits at that index. Give every card a
    # key derived from its identity instead, and move the sheet onto it. Losing the
    # old local state is the correct trade: an orphaned answer is recoverable from
    # the export, a misattributed one is not detectable at all.
    for i, card in enumerate(kept):
        card["i"] = i
        card["k"] = card_uei(card) or ("n:" + _fold_for_identity(card.get("subject", "")))

    n_sites = src.count("state[c.i]")
    if n_sites:
        src = src.replace("state[c.i]", "state[c.k]")
        print(f"  re-keyed {n_sites} state lookups from array index to stable card key")

    # CHECK BEFORE WRITING. Codex, PR #46: this ran the uniqueness check AFTER
    # `SHEET.write_text`, so a colliding payload was already on disk by the time
    # the guard fired. The owner sheet would carry two cards sharing a state
    # key, and one card's saved answer could overwrite or reattach to the other
    # - the precise failure the re-keying was introduced to prevent.
    #
    # It is reachable: two no-UEI subjects differing only in punctuation, case
    # or diacritics fold to the same `k`, because `_fold_for_identity` is built
    # to erase exactly those differences. A guard that fires after the write is
    # a report, not a guard.
    keys = [c["k"] for c in kept]
    if len(set(keys)) != len(keys):
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        sys.exit(f"FATAL: card keys are not unique - answers would collide. "
                 f"Nothing written. Colliding key(s): {dupes}")

    payload = "const CARDS = " + json.dumps(kept, separators=(",", ":")) + ";\n"
    src = re.sub(r"const CARDS = \[.*?\];\n", lambda _m: payload, src, count=1, flags=re.DOTALL)
    SHEET.write_text(src, encoding="utf-8")
    print(f"  rewrote {SHEET.relative_to(ROOT)} with {len(kept)} cards")


if __name__ == "__main__":
    main()
