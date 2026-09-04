#!/usr/bin/env python3
"""
Cedar Press - 527: DOC STALENESS. Which documents disagree with live data?

    py -3 code/527_doc_staleness.py            # report
    py -3 code/527_doc_staleness.py verify     # exit 1 if a LIVE doc is stale

WHY
---
Owner, 2026-09-01: *"Do the plans or anything need to be updated, is anything
stale."*

Answering that by hand found six wrong numbers in a plan written hours
earlier, and eleven more across the corpus. It will keep happening: this
project measures constantly, and a measured number in prose is stale the
moment the next measurement lands. `README.md` has said so since August -
*"a superseded figure in a committed document is still committed"* - and the
DOC_CONTRADICTIONS register exists because of it.

So the sweep becomes a command instead of a good intention.

THE DISTINCTION THAT MAKES THIS USABLE
--------------------------------------
Most stale numbers are **correct history** and must not be touched:

  LIVE      a document a reader consults for CURRENT state - the scoreboard,
            the plan, the runbooks, AGENTS.md, README.md. A wrong number here
            misleads. FIX IT.
  RECORD    a build log, a review packet, a dated measurement, an ADR. The
            number was true when written and the document's value IS that it
            says what was believed then. LEAVE IT.

A sweep that cannot tell these apart produces 200 findings nobody acts on,
which is how the last contradictions register stopped being read. This one
reports them separately and only gates on LIVE.

An exemption: a line that already marks itself as historical - "was", "->",
"superseded", "previously", "corrected", "before" - is a correction, not a
staleness. Those are the project's own convention for recording rather than
silently applying, and flagging them would punish exactly the right behaviour.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
csv.field_size_limit(10_000_000)
TODAY = date.today().isoformat()
OUT = ROOT / "docs" / "DOC_STALENESS.md"

# Documents a reader consults for CURRENT state. Everything else is RECORD.
LIVE_DOCS = {
    "README.md", "AGENTS.md", "START_HERE.md",
    "docs/DATASET_READINESS.md", "docs/TWELVE_DATASET_PLAN.md",
    "docs/EXPORT_SAFETY.md", "docs/INVENTORY.md", "docs/KNOWN_ISSUES.md",
    "docs/ASSERTION_LAYER.md", "docs/IDENTIFIER_STANDARD.md",
    "docs/NATIVE_ENTITY_NUANCES.md", "docs/EVENT_IDS.md",
    "docs/datasets/_PUNCHLIST.md", "docs/datasets/_STANDARD.md",
    "review/OWNER_DECISION_QUEUE.md",
}

HISTORICAL_MARKERS = ("was ", "were ", "->", "→", "superseded",
                      "previously", "corrected", "stale", "before ",
                      "no longer", "used to", "at the time", "retracted")

HEADING_RX = re.compile(r"^#{1,6}\s")


def section_spans(lines: list[str]) -> list[tuple[int, int]]:
    """For each line, the [start, end) of the markdown section it sits in.

    THE CORRECTION IS RARELY ON THE SAME LINE AS THE OLD NUMBER.
    The line-level test below already exempts a line that carries the current
    value beside the old one. It did not exempt this, in `KNOWN_ISSUES.md`:

        ## A7 · S3 · Four documents still quoted a grain figure the ratchet
        ...
        **What it was.** `207 of 210 shippable tables have no grain
        declaration` was carried, as current, by ...

        **Measured:** `contract_grain_unstated_shippable = 25`, ...

    The correction is two lines down, under its own bold label, and the whole
    section exists to record it. Flagging that is telling a register of fixed
    issues to stop describing what it fixed.

    The general shape is not "add `what it was` to HISTORICAL_MARKERS" - that
    is another entry in a denylist that only recognises what somebody already
    listed, which is the lesson `docs/ENTITY_MATCH_RULES.md` records. The
    general shape is: **a correction is a unit of prose, not a line.** So the
    correction test runs over the enclosing SECTION.

    Bounded by the nearest heading of ANY level in both directions, so a
    `###` scopes tightly and one long `##` cannot swallow a document. A
    section with no heading above it is bounded by the file.
    """
    starts = [i for i, ln in enumerate(lines) if HEADING_RX.match(ln)]
    spans = []
    for i in range(len(lines)):
        lo = 0
        for s in starts:
            if s <= i:
                lo = s
            else:
                break
        hi = len(lines)
        for s in starts:
            if s > i:
                hi = s
                break
        spans.append((lo, hi))
    return spans


def rows_of(rel: str) -> int:
    p = ROOT / rel
    if not p.exists():
        return -1
    try:
        with p.open(encoding="utf-8-sig", errors="replace") as fh:
            return sum(1 for _ in fh) - 1
    except OSError:
        return -1


def live_facts() -> dict:
    """The measurements prose most often quotes. Each maps to the patterns
    that would be a STALE way of stating it."""
    f = {}
    f["entities"] = rows_of("data/spine/cedar_identity_register.csv")
    f["edges"] = rows_of("data/clean/fpds_uei_edges.csv")
    f["assertions"] = rows_of("data/clean/cedar_assertions.csv")
    f["facts"] = rows_of("data/clean/cedar_resolved_facts.csv")
    f["aliases"] = rows_of("data/clean/entity_aliases.csv")
    try:
        d = json.loads((ROOT / "docs" / "schema" /
                        "dataset_contracts.json").read_text(encoding="utf-8"))
        f["collections"] = d.get("n_collections", -1)
        f["contract_violations"] = d.get("n_violations", -1)
        f["grain_unstated"] = d.get("n_shippable_grain_unstated", -1)
    except (OSError, ValueError):
        pass
    try:
        with (ROOT / "data" / "clean" /
              "cedar_dataset_readiness.csv").open(encoding="utf-8-sig") as fh:
            r = list(csv.DictReader(fh))
        f["ready"] = sum(1 for x in r if x["status"] == "READY")
    except (OSError, KeyError):
        pass
    return f


def sweep():
    live = live_facts()
    # (regex of a value that WOULD be stale, label, current value)
    checks = []
    if live.get("entities", -1) > 0:
        for old in ("1,536", "1536"):
            if old.replace(",", "") != str(live["entities"]):
                checks.append((re.compile(r"\b" + re.escape(old) + r"\b"),
                               "entity count", f"{live['entities']:,}"))
    if live.get("edges", -1) > 0:
        # A BARE NUMBER IS NOT A SUBJECT. This check used to match `2,901`
        # anywhere and flagged `registration_name:CAGE` 2,901 in
        # ASSERTION_LAYER.md - a CAGE attribution count that has nothing to do
        # with ownership edges and merely collided with a superseded edge
        # total. Two counts in one project WILL collide; the fix is to make
        # the check say what it is about, the way the grain check already
        # does, rather than to trust an unqualified integer.
        near = r"(?=[^\n]{0,80}(edge|parent|spiderweb|fpds_uei))"
        for old in ("2,901", "2290", "2,290"):
            if old.replace(",", "") == str(live["edges"]):
                continue
            checks.append((re.compile(r"\b" + re.escape(old) + r"\b" + near,
                                      re.I),
                           "ownership edges", f"{live['edges']:,}"))
    for old in ("29,718", "32,872", "23,310", "34,525"):
        if live.get("assertions", -1) > 0 and \
                old.replace(",", "") != str(live["assertions"]):
            checks.append((re.compile(r"\b" + re.escape(old) + r"\b"),
                           "assertion count", f"{live['assertions']:,}"))
    checks.append((re.compile(r"\b80,778\b"), "prime_contracts duplicates",
                   "0 - they were distinct FPDS transactions"))
    # THIS CHECK USED TO HARDCODE `25`, IN THE SCRIPT WHOSE JOB IS FINDING
    # HARDCODED NUMBERS. It went stale the same way everything else does: the
    # live contract JSON read 32 on 2026-09-01 while this line still offered
    # 25 as the correction. Read it from the same file the gate reads.
    grain = live.get("grain_unstated")
    if isinstance(grain, int) and grain >= 0:
        checks.append((re.compile(r"\b207\b(?=[^\n]{0,50}(grain|unstated))"),
                       "grain unstated", str(grain)))
    checks.append((re.compile(r"\bnot a git repositor"), "repo status",
                   "it IS a git repository since 2026-08-29"))

    live_hits, record_hits = [], []
    for p in sorted(list(ROOT.rglob("*.md"))):
        rel = p.relative_to(ROOT).as_posix()
        if any(s in rel for s in ("graveyard/", "docs/releases/", ".git/")):
            continue
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        is_live = rel in LIVE_DOCS
        spans = section_spans(lines)
        for i, line in enumerate(lines, 1):
            low = line.lower()
            if any(m in low for m in HISTORICAL_MARKERS):
                continue
            for rx, label, now in checks:
                if not rx.search(line):
                    continue
                # A LINE THAT CARRIES THE CURRENT VALUE TOO IS A CORRECTION.
                #
                # HISTORICAL_MARKERS is a denylist of phrasings, and a denylist
                # only recognises what somebody already listed. It has "was",
                # "->", "superseded"; it does not have "the queue said", or
                # "apparent", or a markdown table cell putting old and new side
                # by side. So it flagged three lines that are exactly right:
                #
                #   KNOWN_ISSUES.md   "prime_contracts has ZERO literal
                #                      duplicate rows (the queue said 80,778)"
                #   TWELVE_DATASET_PLAN.md
                #                     "master list **1,536** entities | **1,555**
                #                      - 19 IHS consortia promoted"
                #
                # Both state the correction. Nagging about them trains a reader
                # to ignore this report, which is how the last contradictions
                # register died.
                #
                # The structural test beats another phrase: if the CURRENT value
                # is on the line, the line already knows. This is the same
                # lesson as ENTITY_MATCH_RULES.md and the robots false-block -
                # write the predicate, not a longer list of words.
                bare = now.split(" ")[0].strip().rstrip(",.")
                if bare and bare in line:
                    break
                if bare and bare.replace(",", "") in line.replace(",", ""):
                    break
                # ...AND SO IS A SECTION THAT CARRIES IT. See section_spans.
                lo, hi = spans[i - 1]
                sec = "\n".join(lines[lo:hi])
                if bare and (bare in sec or
                             bare.replace(",", "") in sec.replace(",", "")):
                    break
                (live_hits if is_live else record_hits).append(
                    (rel, i, label, now, line.strip()[:90]))
                break
    return live, live_hits, record_hits


def main() -> int:
    verify = len(sys.argv) > 1 and sys.argv[1] == "verify"
    live, lh, rh = sweep()

    if not verify:
        L = ["# Document staleness — where prose disagrees with live data", "",
             f"*Generated {TODAY} by `code/527_doc_staleness.py`. Two lists, "
             f"deliberately: a **LIVE** document is one a reader consults for "
             f"current state, and a wrong number there misleads. A **RECORD** "
             f"— a build log, a review packet, a dated measurement — was true "
             f"when written, and its value is that it says what was believed "
             f"then. Fix the first. Leave the second.*", "",
             "## Live measurements", "", "| fact | value |", "|---|---:|"]
        for k, v in sorted(live.items()):
            L.append(f"| {k} | {v:,} |" if isinstance(v, int) and v >= 0
                     else f"| {k} | {v} |")
        L += ["", f"## LIVE documents that are stale — {len(lh)}", ""]
        if lh:
            L += ["| document | line | stale | current |", "|---|---:|---|---|"]
            for rel, i, label, now, txt in lh:
                L.append(f"| `{rel}` | {i} | {label} | {now} |")
        else:
            L.append("None. Every live document agrees with the data.")
        L += ["", f"## RECORD documents carrying superseded numbers — "
                  f"{len(rh)} (informational, do not 'fix')", ""]
        for rel, i, label, now, txt in rh[:40]:
            L.append(f"- `{rel}` L{i} — {label}")
        OUT.write_text("\n".join(L), encoding="utf-8")

    print(f"  doc staleness   LIVE stale {len(lh)}   "
          f"RECORD superseded {len(rh)} (informational)")
    for rel, i, label, now, txt in lh[:12]:
        print(f"    STALE  {rel}:{i}  {label} -> should be {now}")
        print(f"           {txt}")
    return 1 if lh else 0


if __name__ == "__main__":
    sys.exit(main())
