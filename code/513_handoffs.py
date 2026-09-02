#!/usr/bin/env python3
"""
Cedar Press - 513: agent HANDOFFS. Mission Phase 4.

    py -3 code/513_handoffs.py record --task "..." --claim "..." \\
        --by "<session/agent id>" --check "py -3 code/62_no_regression_check.py" \\
        [--check "py -3 code/510_assertions.py verify"] [--tables a.csv b.csv]
    py -3 code/513_handoffs.py verify <handoff_id> --by "<different id>"
    py -3 code/513_handoffs.py list [--unverified]

THE DEFECT THIS EXISTS FOR (mission spec, owner's words)
--------------------------------------------------------
    "agents claiming another agent handled something when nobody actually
    verified it."

That failure has a precise shape: a claim of completion travels between
sessions as PROSE, and prose cannot be re-executed. The next agent reads
"done", believes it, and builds on sand. This project's history already has
the specimens - "the backfill lands" quoted as pending weeks after it landed,
and six sessions in a row stepping around one gate failure (AGENTS.md).

THE PROTOCOL
------------
A handoff is a ROW, not a paragraph, and it is born UNVERIFIED:

  * `record` writes the claim with the COMMIT HASH of the tree that made it,
    the row counts of every table it says it touched, and - the load-bearing
    field - `verify_commands`: the exact commands whose exit 0 constitutes
    proof. An unverifiable claim (no commands) can still be recorded, but it
    says so, forever: verification_status = NO_CHECK_DECLARED.
  * `verify` RE-RUNS those commands, now, against the current tree. It does
    not read the claim and nod - it executes. Exit 0 on all -> VERIFIED, with
    who/when/at-what-commit. Any failure -> FAILED_VERIFICATION with the
    output tail preserved. Table row counts are re-measured and drift is
    reported (drift is not failure - later work moves tables - but it is
    recorded, because "verified" must say what state it verified).
  * the verifier MUST NOT be the claimant. `--by` is compared; a match is
    refused. Self-verification is the defect wearing a lanyard.

Append-only, like the correction register: a handoff is never edited, its
verification is a second event. The file is data/clean adjacent but lives in
review/ because it is process, not product.

Writes  review/agent_handoffs.csv          (append-only)
        review/handoff_verifications.csv   (append-only)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANDOFFS = ROOT / "review" / "agent_handoffs.csv"
VERIFICATIONS = ROOT / "review" / "handoff_verifications.csv"
csv.field_size_limit(10_000_000)
NOW = datetime.now().isoformat(timespec="seconds")

H_COLS = ["handoff_id", "recorded_at", "performed_by", "task", "claim",
          "commit", "tables_touched", "table_rows_at_claim",
          "verify_commands", "verification_status"]
V_COLS = ["handoff_id", "verified_at", "verified_by", "at_commit",
          "result", "commands_run", "failures", "row_drift", "output_tail"]


def read_csv(p: Path) -> list:
    if not p.exists():
        return []
    with p.open(encoding="utf-8-sig", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def append_row(p: Path, row: dict, cols) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    new = not p.exists()
    with p.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                       capture_output=True, text=True, timeout=60)
    return r.stdout.strip()


def rows_of(name: str) -> str:
    for d in ("data/clean", "data/spine"):
        p = ROOT / d / name
        if p.exists():
            try:
                with p.open(encoding="utf-8-sig", errors="replace") as fh:
                    return str(sum(1 for _ in fh) - 1)
            except Exception:
                return "unreadable"
    return "MISSING"


def latest_status(hid: str) -> str:
    vs = [v for v in read_csv(VERIFICATIONS) if v["handoff_id"] == hid]
    return vs[-1]["result"] if vs else ""


def cmd_record(a) -> int:
    commit = git_head()
    tables = a.tables or []
    counts = "; ".join(f"{t}={rows_of(t)}" for t in tables)
    checks = a.check or []
    hid = "HAND-" + hashlib.sha1(
        f"{a.task}|{a.by}|{commit}|{NOW}".encode()).hexdigest()[:10].upper()
    append_row(HANDOFFS, dict(
        handoff_id=hid, recorded_at=NOW, performed_by=a.by,
        task=a.task, claim=a.claim, commit=commit,
        tables_touched="; ".join(tables), table_rows_at_claim=counts,
        verify_commands=" && ".join(checks),
        verification_status=("UNVERIFIED" if checks else
                             "NO_CHECK_DECLARED - this claim cannot be "
                             "machine-verified and says so"),
    ), H_COLS)
    print(f"  recorded {hid} at commit {commit[:12]}")
    print(f"  status: {'UNVERIFIED - a DIFFERENT session must run: '
                       f'py -3 code/513_handoffs.py verify {hid} --by <id>'
                       if checks else 'NO_CHECK_DECLARED'}")
    return 0


def cmd_verify(a) -> int:
    hs = {h["handoff_id"]: h for h in read_csv(HANDOFFS)}
    h = hs.get(a.handoff_id)
    if not h:
        sys.exit(f"no such handoff: {a.handoff_id}")
    if a.by.strip().lower() == (h["performed_by"] or "").strip().lower():
        sys.exit(f"refusing: {a.by} recorded this handoff. Self-verification "
                 f"is the defect this protocol exists to prevent - a claim is "
                 f"verified by someone who did not make it.")
    cmds = [c.strip() for c in (h["verify_commands"] or "").split("&&")
            if c.strip()]
    if not cmds:
        sys.exit("this handoff declared no verify commands; it cannot be "
                 "machine-verified. Record a new handoff with --check.")
    failures, tails = [], []
    for c in cmds:
        print(f"  running: {c}")
        r = subprocess.run(c, shell=True, cwd=str(ROOT),
                           capture_output=True, text=True, timeout=3600)
        tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
        tails.append(f"[{c}] " + " | ".join(tail))
        if r.returncode != 0:
            failures.append(f"{c} -> exit {r.returncode}")
            print(f"    FAILED (exit {r.returncode})")
        else:
            print(f"    ok")
    drift = []
    for pair in (h["table_rows_at_claim"] or "").split(";"):
        pair = pair.strip()
        if "=" not in pair:
            continue
        name, then = pair.split("=", 1)
        now_rows = rows_of(name.strip())
        if now_rows != then.strip():
            drift.append(f"{name.strip()}: {then.strip()} -> {now_rows}")
    result = "FAILED_VERIFICATION" if failures else "VERIFIED"
    append_row(VERIFICATIONS, dict(
        handoff_id=a.handoff_id, verified_at=NOW, verified_by=a.by,
        at_commit=git_head(), result=result,
        commands_run=" && ".join(cmds),
        failures="; ".join(failures),
        row_drift="; ".join(drift) or "none",
        output_tail=" || ".join(tails)[:1500],
    ), V_COLS)
    print(f"\n  {result}"
          + (f" - {len(failures)} command(s) failed" if failures else "")
          + (f"; row drift since claim: {'; '.join(drift)}" if drift else ""))
    return 1 if failures else 0


def cmd_list(a) -> int:
    hs = read_csv(HANDOFFS)
    n_unv = 0
    for h in hs:
        status = latest_status(h["handoff_id"]) or h["verification_status"]
        if a.unverified and status not in ("UNVERIFIED",) \
                and not status.startswith("FAILED"):
            continue
        if status in ("UNVERIFIED",) or status.startswith("FAILED"):
            n_unv += 1
        print(f"  {h['handoff_id']}  {h['recorded_at'][:16]}  "
              f"{status:22s}  by {h['performed_by'][:18]:18s}  "
              f"{h['task'][:52]}")
    print(f"\n  {len(hs)} handoff(s), {n_unv} awaiting verification or failed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("--task", required=True)
    r.add_argument("--claim", required=True,
                   help="what is being claimed as done, one sentence")
    r.add_argument("--by", required=True, help="who performed the work")
    r.add_argument("--check", action="append",
                   help="a command whose exit 0 constitutes proof; repeatable")
    r.add_argument("--tables", nargs="*", help="tables the work touched")
    v = sub.add_parser("verify")
    v.add_argument("handoff_id")
    v.add_argument("--by", required=True, help="who is verifying - must "
                   "differ from the recorder")
    l = sub.add_parser("list")
    l.add_argument("--unverified", action="store_true")
    a = ap.parse_args()
    return {"record": cmd_record, "verify": cmd_verify,
            "list": cmd_list}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
