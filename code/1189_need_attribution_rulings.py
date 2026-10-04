#!/usr/bin/env python3
"""
1189 - apply the NEED attribution rulings and guards to the NEED files this repository serves.

    python3 code/1189_need_attribution_rulings.py report    # what would change, nothing written
    python3 code/1189_need_attribution_rulings.py apply     # rewrite the committed NEED files
    python3 code/1189_need_attribution_rulings.py verify    # exit 1 if any file is stale

WHY THIS EXISTS
---------------
The NEED linkage audit of 2026-10-04 (Lumecon-data `decisions/identity/need/README.md`)
found that 92 of the 100 rows in the public `dist/preview/need.csv` sat under the wrong
owner, and that the 10-row samples carried two more (Bowhead Marine Support Services under
the Barrow village government, Eagle Eye Electric under the Eagle village government).
Owner ruling 2026-10-04 (Elijah Moreno): the only hold is a specific record attributed to
the wrong entity. Each correction is a ruling in the cedar_rulings format, decided in
Lumecon-data `decisions/identity/need/attribution-2026-10-04/` and vendored here
unchanged as `data/cedar/need_attribution_rulings.csv` (source commit and SHA-256 in
`data/cedar/need_attribution_rulings.source.json`).

WHAT IT DOES TO A ROW
---------------------
`code/need_attribution.py` decides, rulings first and then the documented guards (the
same module 1072 now builds with and the Lumecon-data producer mirrors):

  corrected_by_ruling     the owner columns take the ruled owner (register name/class)
  rejected_by_ruling      the owner columns are blanked; the row stays
  misattribution_flagged  the owner columns are blanked pending a person; the row stays
  refused_by_guard        the owner columns are blanked; the row stays

Nothing else in a row changes, no row is added or removed, and no identifier is minted,
merged or transferred. Names that may be a private individual's are left exactly as the
delivered file has them (the personal-data rule is unchanged); their rulings are keyed by
a SHA-256 of the register key, never by the name.

WHY IT REWRITES COMMITTED FILES INSTEAD OF REBUILDING THEM
----------------------------------------------------------
`dist/preview/need.csv` is written by `1151 build` from `dist/customer/need.csv`, and the
samples by `1135` from `data/clean/need_enterprises.csv`. Neither input is in Git (the
5,820-row table lives in the preserved release 428d1104 and the owner's workspace). `1151`
now applies this module when it builds the NEED preview, so the next rebuild from the full
data comes out corrected; until then `apply` puts the same decisions on the files that are
already published, row for row, and `verify` keeps them there.

READS   data/cedar/need_attribution_rulings.csv, data/spine/cedar_identity_register.csv
WRITES  dist/preview/need.csv, dist/review/samples/need/need_enterprises__10.csv,
        data/cedar/samples/need__sample.csv,
        public/data/cedar/samples/need/need_enterprises__10.csv (where it exists)
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE = ROOT / "code"
RULINGS = ROOT / "data" / "cedar" / "need_attribution_rulings.csv"
RULINGS_SOURCE = ROOT / "data" / "cedar" / "need_attribution_rulings.source.json"
REGISTER = ROOT / "data" / "spine" / "cedar_identity_register.csv"
TARGETS = (
    "dist/preview/need.csv",
    "dist/review/samples/need/need_enterprises__10.csv",
    "data/cedar/samples/need__sample.csv",
    "public/data/cedar/samples/need/need_enterprises__10.csv",
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


na = _load("need_attribution", CODE / "need_attribution.py")
_m72 = None


def norm(name: str) -> str:
    """1072's normaliser: the register key is (owner, norm(name))."""
    global _m72
    if _m72 is None:
        _m72 = _load("need1072_for_1189", CODE / "1072_tribally_owned_enterprises.py")
    return _m72.norm(name)


def check_rulings_source() -> list[str]:
    problems = []
    if not RULINGS.exists() or not RULINGS_SOURCE.exists():
        return ["vendored rulings or their source record are absent"]
    meta = json.loads(RULINGS_SOURCE.read_text(encoding="utf-8"))
    digest = hashlib.sha256(RULINGS.read_bytes()).hexdigest()
    if meta.get("sha256") != digest:
        problems.append(f"need_attribution_rulings.csv sha256 {digest} != recorded "
                        f"{meta.get('sha256')}; re-vendor it from {meta.get('source')}")
    return problems


def annotate(rows: list[dict], *, rulings=None, register=None) -> Counter:
    """Apply rulings and guards to `rows` in place; -> Counter of statuses."""
    rulings = rulings or na.Rulings.from_csv(RULINGS)
    register = register or na.Register.from_csv(REGISTER)
    probe = []
    for r in rows:
        p = dict(r)
        p.setdefault("enterprise_name_normalized", norm(r.get("enterprise_name", "")))
        probe.append(p)
    ctx = na.TableContext(register, probe)
    seen = Counter()
    for r, p in zip(rows, probe):
        outcome = na.decide(p, rulings, ctx)
        seen[outcome.status] += 1
        fixed = na.apply(r, outcome, register, enterprise_table=True)
        if outcome.status in na.MASKED_STATUSES and "attribution_refusal" in r:
            code = (outcome.basis.split(":", 1)[0]
                    if outcome.status == na.STATUS_REFUSED
                    else "REJECTED_BY_RULING" if outcome.status == na.STATUS_REJECTED
                    else "MISATTRIBUTION_FLAGGED")
            fixed["attribution_refusal"] = code
        r.clear()
        r.update(fixed)
    return seen


def _read(path: Path):
    """(header line, fields, [(raw record text, row)]) - raw text kept per record."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    consumed: list[str] = []

    def feed():
        for line in lines:
            consumed.append(line)
            yield line

    reader = csv.reader(feed())
    fields = next(reader)
    header = "".join(consumed)
    records = []
    for values in reader:
        raw = "".join(consumed[len(header.splitlines(keepends=True)):])
        consumed[len(header.splitlines(keepends=True)):] = []
        records.append((raw, dict(zip(fields, values))))
    return header, fields, records


def _render_row(fields, row, newline: str) -> str:
    buf = io.StringIO()
    csv.DictWriter(buf, fieldnames=fields, lineterminator=newline).writerow(row)
    return buf.getvalue()


def run(mode: str) -> int:
    problems = check_rulings_source()
    rulings, register = na.Rulings.from_csv(RULINGS), na.Register.from_csv(REGISTER)
    stale = []
    for rel in TARGETS:
        path = ROOT / rel
        if not path.exists():
            continue
        header, fields, records = _read(path)
        rows = [dict(row) for _raw, row in records]
        seen = annotate(rows, rulings=rulings, register=register)
        original = path.read_bytes()
        newline = "\r\n" if b"\r\n" in original else "\n"
        # A row the rulings leave alone keeps its exact bytes: only owner columns of
        # decided rows change, never another writer's quoting.
        out = [header] + [raw if row == orig else _render_row(fields, row, newline)
                          for (raw, orig), row in zip(records, rows)]
        rendered = "".join(out).encode("utf-8")
        changed = rendered != original
        print(f"  {rel:<58} {len(rows):>3} rows  {dict(sorted(seen.items()))}"
              f"{'  <- changes' if changed else ''}")
        if changed:
            stale.append(rel)
            if mode == "apply":
                path.write_bytes(rendered)
    if mode == "verify":
        problems += [f"{rel} does not carry the NEED attribution rulings; run "
                     "`python3 code/1189_need_attribution_rulings.py apply`" for rel in stale]
    for p in problems:
        print("  FAIL", p)
    if mode == "report" and stale:
        print("  nothing written. re-run with `apply`.")
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else "report"
    if mode not in ("report", "apply", "verify"):
        print(__doc__)
        return 2
    return run(mode)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
