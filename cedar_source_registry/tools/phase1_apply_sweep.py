#!/usr/bin/env python3
"""Phase 1 — apply search-sweep verification results to the registry.

Usage: phase1_apply_sweep.py results.jsonl [more.jsonl ...]

Input rows (produced by the Wave 5.1 search sweep):
  {source_id, searches, outcome, evidence_urls, evidence_date, basis, new_url, notes}

This pass ran with page fetches blocked by the build environment's egress
policy, so the only evidence channel was web search. Consequences, encoded
here rather than left to memory:
  - No status_group is ever changed by this script. Upgrades need page-level
    evidence; downgrades (defunct/gone) are individual judgment calls made in
    a follow-up edit, never mechanically.
  - Every touched row's caveats gain a dated "search-only" sentence so a
    2026-08-27 last_checked from this pass is never mistaken for the wave-5
    page inspections that share the date.
  - Every log line carries channel: web_search_only plus the evidence URLs.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK_DATE = "2026-08-27"

CAVEAT = {
    "corroborated_current": (
        "current evidence in search results ({date_clause}); page-level "
        "inspection still pending"
    ),
    "corroborated_exists": (
        "directory page indexed in search results; currency unconfirmed"
    ),
    "moved": "search evidence the canonical URL moved — see verification log",
    "login_gated": "search evidence access is login-gated — see verification log",
    "program_defunct": "search evidence the program ended — see verification log",
    "not_found": (
        "no trace in search results; needs fetch-based re-check — not evidence "
        "the source is dead"
    ),
    "unresolved": "search evidence ambiguous — see verification log",
}

RESULT = {
    "corroborated_current": "Search-corroborated; current evidence",
    "corroborated_exists": "Search-corroborated existing; currency unconfirmed",
    "moved": "Search evidence of moved URL; not applied without page inspection",
    "login_gated": "Login-gated per search evidence",
    "program_defunct": "Program reported ended per search evidence; status review needed",
    "not_found": "Not found in search; needs fetch-based re-check",
    "unresolved": "Search evidence ambiguous; unresolved this pass",
}


def main(paths: list[str]) -> int:
    results: dict[str, dict] = {}
    for p in paths:
        for line in Path(p).read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            results[row["source_id"]] = row

    src_path = ROOT / "sources.jsonl"

    # Fail before writing anything if a result targets an unknown source_id —
    # a misspelled id must not let the batch report success while a requested
    # verification silently goes unapplied.
    known_ids = {
        json.loads(line)["source_id"]
        for line in src_path.read_text().splitlines()
        if line.strip()
    }
    unknown = sorted(set(results) - known_ids)
    if unknown:
        print(f"FAIL: results for ids not in sources.jsonl: {unknown}",
              file=sys.stderr)
        return 1

    # Idempotency: a retried batch must not append duplicate log events.
    # A result is "already applied" if the log holds a line with the same
    # source_id, checked date, channel, and result.
    log_path = ROOT / "verification_log.jsonl"
    already = set()
    for line in log_path.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        already.add(
            (row.get("source_id"), row.get("checked"), row.get("channel"),
             row.get("result"))
        )
    skipped = [
        sid for sid, r in list(results.items())
        if (sid, CHECK_DATE, "web_search_only", RESULT[r["outcome"]]) in already
    ]
    for sid in skipped:
        del results[sid]
    if skipped:
        print(f"skipping {len(skipped)} already-applied results: {skipped}",
              file=sys.stderr)
    out, log_lines, review = [], [], []
    for line in src_path.read_text().splitlines():
        s = json.loads(line)
        r = results.pop(s["source_id"], None)
        if r is None:
            out.append(line)
            continue
        outcome = r["outcome"]
        date_clause = (
            f"dated evidence {r['evidence_date']}" if r.get("evidence_date") else "undated"
        )
        caveat_body = CAVEAT[outcome].format(date_clause=date_clause)
        sentence = (
            f" Wave 5.1 search-only re-check {CHECK_DATE} (page fetch blocked by "
            f"build-environment egress policy): {caveat_body}."
        )
        if sentence.strip() not in (s.get("caveats") or ""):
            s["caveats"] = ((s.get("caveats") or "").rstrip() + sentence).strip()
        s["last_checked"] = CHECK_DATE
        out.append(json.dumps(s, ensure_ascii=False))

        notes = r["basis"]
        if r.get("notes"):
            notes += f" | {r['notes']}"
        if r.get("new_url"):
            notes += f" | candidate new URL (not applied): {r['new_url']}"
        log_lines.append(json.dumps({
            "source_id": s["source_id"],
            "source": f"{s['nation_source']} — {s['directory_registry']}",
            "result": RESULT[outcome],
            "notes": notes,
            "checked": CHECK_DATE,
            "channel": "web_search_only",
            "evidence_urls": r.get("evidence_urls") or [],
        }, ensure_ascii=False))
        if outcome in ("moved", "login_gated", "program_defunct", "not_found", "unresolved"):
            review.append((s["source_id"], outcome, r["basis"], r.get("notes")))

    src_path.write_text("\n".join(out) + "\n")
    with log_path.open("a") as f:
        for line in log_lines:
            f.write(line + "\n")
    print(f"applied {len(log_lines)} results", file=sys.stderr)
    if review:
        print("NEEDS INDIVIDUAL REVIEW (status/URL decisions are manual):",
              file=sys.stderr)
        for sid, outcome, basis, notes in review:
            print(f"  {sid} [{outcome}] {basis} | {notes}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
