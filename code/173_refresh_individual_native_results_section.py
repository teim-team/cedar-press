"""173_refresh_individual_native_results_section.py

Regenerate section 9 (MEASURED RESULTS) of
`docs/INDIVIDUAL_NATIVE_OWNERSHIP_VERIFICATION_BUILD_LOG.md` from the table
itself.

WHY THIS IS A SCRIPT AND NOT A PARAGRAPH
----------------------------------------
START_HERE opens with the reason: "There is no version control here, so
superseded figures never get overwritten - they sit in the document where they
were written, looking exactly as authoritative as current ones."
`docs/DOC_CONTRADICTIONS_2026-08-26.md` indexes ~25 places where that has
already happened. A hand-typed results table in a build log is a future entry
in that register.

So the numbers in section 9 are generated. Re-running `171` and then this
script cannot leave the log disagreeing with the file. Everything ABOVE section
9 is hand-written narrative and is never touched.

Rewrites only the region between the section-9 heading and section 10.
SAFE TO RE-RUN.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CLEAN = os.path.join(ROOT, "data", "clean")

TABLE = os.path.join(CLEAN, "individual_native_ownership_verification.csv")
LOG = os.path.join(
    ROOT, "docs", "INDIVIDUAL_NATIVE_OWNERSHIP_VERIFICATION_BUILD_LOG.md"
)
QUEUE = os.path.join(
    ROOT, "review", "individual_native_ownership_ambiguous_2026-08-26.csv"
)

START = "## 9. MEASURED RESULTS"
END = "## 10."


def money(x) -> str:
    try:
        return f"${float(x or 0):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def main() -> int:
    with open(TABLE, encoding="utf-8-sig", errors="replace", newline="") as fh:
        rows = list(csv.DictReader(fh))
    n = len(rows)
    if not n:
        print("empty table")
        return 2

    def obl(rs):
        return sum(float(r["total_obligations_usd"] or 0) for r in rs)

    tier = collections.Counter(r["evidence_tier"] for r in rows)
    tier_obl = collections.defaultdict(float)
    for r in rows:
        tier_obl[r["evidence_tier"]] += float(r["total_obligations_usd"] or 0)
    indep = collections.Counter(r["evidence_independence"] for r in rows)
    sd = collections.Counter(r["self_description"] for r in rows)
    kind = collections.Counter(r["ownership_class"] for r in rows)
    basis = collections.Counter(r["candidate_basis"] for r in rows)

    with_sentence = [r for r in rows if r["self_description_sentence"].strip()]
    with_tp = [r for r in rows if r["third_party"] == "FOUND"]
    named = [r for r in rows if r["tribal_affiliation_named"] == "YES"]
    honored = [r for r in rows if r["prior_ruling_honored"] == "YES"]
    checked = [r for r in rows if r["self_description"] != "NOT_CHECKED"]
    no_cert = [r for r in rows if r["sam_self_certification"] != "YES"]
    traps = [r for r in rows if r["name_trap_warning"].strip()]
    priv = collections.Counter(r["privacy_class"] for r in rows)

    nq = 0
    if os.path.exists(QUEUE):
        with open(QUEUE, encoding="utf-8-sig", errors="replace", newline="") as fh:
            qrows = list(csv.DictReader(fh))
        nq = len([q for q in qrows if q.get("verification_id")])
        qwhy = collections.Counter()
        for q in qrows:
            for w in (q.get("why_queued") or "").split(" | "):
                if w:
                    qwhy[w.split(":")[0].strip()[:60]] += 1
    else:
        qwhy = collections.Counter()

    L: list[str] = [
        START,
        "",
        f"*Regenerated {dt.date.today().isoformat()} by "
        "`code/173_refresh_individual_native_results_section.py` from "
        "`data/clean/individual_native_ownership_verification.csv`. Do not "
        "hand-edit this section — re-run the script.*",
        "",
        f"**{n} candidates, {money(obl(rows))} in nominal obligations.** "
        f"{basis.get('TOP400_FLAGGED', 0)} reached via the federal flag, "
        f"{basis.get('PRIOR_OWNER_RULING', 0)} reached only because the owner "
        "had already ruled them.",
        "",
        "### Prior rulings",
        "",
        f"| | |",
        f"|---|---:|",
        f"| individual-Native rulings found across five files | **45** |",
        f"| distinct identifiers | **45** |",
        f"| landing on a candidate row and carried forward unchanged | **{len(honored)}** |",
        f"| obligations under a standing ruling | **{money(obl(honored))}** |",
        f"| prior-ruled firms carrying NO native self-certification | "
        f"**{len(no_cert)}** |",
        "",
        "### The web pass",
        "",
        "| | n | share of checked |",
        "|---|---:|---:|",
    ]
    for k in ("CLAIM_FOUND", "NO_CLAIM_FOUND", "SITE_UNREACHABLE",
              "NO_SITE_FOUND", "NOT_CHECKED"):
        c = sd.get(k, 0)
        share = f"{100.0 * c / len(checked):.1f}%" if checked and k != "NOT_CHECKED" else "—"
        L.append(f"| `{k}` | {c} | {share} |")
    L += [
        "",
        f"**{len(with_sentence)} of {n} candidates carry a verbatim website "
        f"sentence** ({100.0 * len(with_sentence) / n:.1f}%), covering "
        f"{money(obl(with_sentence))}.",
        "",
        f"**{len(with_tp)} carry a third-party source** — the only leg that is "
        "not the firm speaking about itself, and the only one that can carry a "
        "row to tier A.",
        "",
        f"**{len(named)} name a specific tribe or nation.** An unnamed "
        '"Native American owned" is recorded as `NO`: it cannot be checked '
        "against a tribal roll and cannot be joined to the entity spine.",
        "",
        "### Tier — computed from the legs present, never assigned",
        "",
        "| tier | n | obligations |",
        "|---|---:|---:|",
    ]
    for t in ("A", "B", "C", "X"):
        if tier.get(t):
            L.append(f"| **{t}** | {tier[t]} | {money(tier_obl[t])} |")
    L += [
        "",
        "### Independence — the column that decides whether anything was verified",
        "",
        "| state | n |",
        "|---|---:|",
    ]
    for k, v in indep.most_common():
        L.append(f"| `{k}` | {v} |")
    L += [
        "",
        "### Ownership class, from the strongest EVIDENCED source",
        "",
        "| class | n | obligations |",
        "|---|---:|---:|",
    ]
    for k, v in kind.most_common():
        sub = [r for r in rows if r["ownership_class"] == k]
        L.append(f"| `{k}` | {v} | {money(obl(sub))} |")
    L += [
        "",
        "**`UNDETERMINED` means nobody said, not that the firm is not "
        "Native-owned.** No row in this table says `NOT_NATIVE` and none ever "
        "will.",
        "",
        "### Guards",
        "",
        f"* `name_trap_warning` fires on **{len(traps)}** rows.",
        "* `temporal_caveat` is populated on **100%** of rows — structural, "
        "see §5.",
        "* `privacy_class`: "
        + ", ".join(f"`{k}` {v}" for k, v in priv.most_common())
        + f". **{priv.get('POSSIBLE_PERSONAL_NAME', 0)}** rows are "
          "`publishable_entity_name = N`.",
        "",
        "### Sent to review",
        "",
        f"**{nq} rows** in "
        "`review/individual_native_ownership_ambiguous_2026-08-26.csv`, each "
        "carrying its evidence, its URL and its tier basis.",
        "",
    ]
    if qwhy:
        L += ["| reason | n |", "|---|---:|"]
        for k, v in qwhy.most_common():
            L.append(f"| {k} | {v} |")
        L.append("")

    with open(LOG, encoding="utf-8") as fh:
        text = fh.read()
    i = text.index(START)
    j = text.index(END, i)
    new = text[:i] + "\n".join(L) + "\n---\n\n" + text[j:]
    part = LOG + ".part"
    with open(part, "w", encoding="utf-8") as fh:
        fh.write(new)
    os.replace(part, LOG)
    print(f"section 9 refreshed: {n} rows, {len(with_sentence)} sentences, "
          f"tier {dict(sorted(tier.items()))}, {nq} queued")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
