# Next session — start here

*Left 2026-08-30 by the integrator session. Read this, then
`docs/DATASET_READINESS.md`. Everything below is verified against live data
unless it says otherwise.*

---

## READY datasets: 2 / 13

| | |
|---|---|
| **READY** | `nagpra` (4 tables), `federal-register` (22 tables) |
| **BLOCKED** | 11 |
| **NOT_TESTED** | 0 |

Regenerate the scoreboard: `py -3 code/518_dataset_readiness.py`

Three statuses only. Never write "mostly ready".

---

## 1. ~~THE GATE IS RED~~ — CLEARED 2026-09-01, gate exit 0

Register row written, and the allowance itself needed two more fixes: it
compared dist-to-dist when the metric sums `min(dist, clean)`, and then
`ship_ratio_pct` failed for the same fall the line above had just allowed.
Both fixed; baseline recorded while green.

**Read `docs/TWELVE_DATASET_PLAN.md` — that is now the operating plan.**

### Superseded — kept for the reasoning

```
py -3 code/62_no_regression_check.py     # exit 1
!! ship_dist_rows FELL 8,463,001 -> 8,461,252   (-1,749)
```

**This is a legitimate, verified improvement, not a defect.**
`prime_contracts_entity_year.csv` was correctly regrained from 8,464 to 6,715
rows (8,464 − 1,751 surplus variants + 2 new entity-years = 6,715, exact).

The shipping allowance now works (it was broken — see §4) but **nobody wrote
the register row that consumes it.** Do this:

1. Append a correction-register row for `prime_contracts_entity_year.csv`
   with `rows_removed = 1749`, `action = REGRAIN`, and a reason naming the
   join fan-out it fixed. Use `354_correction_register.record()` — do **not**
   hand-edit the CSV.
2. Re-run the gate. The allowance should fire and print an "EXACTLY the 1,749
   row(s)" line.
3. Only then `--baseline`, and only while green.

**Do not re-baseline to clear this.** The allowance exists precisely so this
does not become the seventh session to step around a red line.

---

## 2. What just landed (all integrator-verified)

- **`nagpra` READY** — and closure found a rebuild that was destroying
  `cedar_uid` on a *lobbying* table, plus two buyer traps now in the contract
  (the title index is neither subset nor superset of the notice product;
  `*_entity_ids` are pipe-delimited lists, not join keys).
- **`federal-register` READY** — two PKs were **declared but never tested**;
  a shipping customer table had **no rebuilder** the planner could see; and
  `build.py plan federal-register` is *not* the update path (its phase 1 drops
  columns another script wrote in place — `342` is correct and says so in its
  own docstring).
- **`prime_contracts_entity_year` regrained** — join fan-out 1.26× → 1.000×.
- **Ownership status shipped** — `prime_contracts.csv` now carries
  `owner_attribution_status`. **$45.63B may present a definite as-of owner;
  the rest reads not-definite and is never filled from current ownership.**
- **`prime_contracts` 80,778 "duplicates" → 0** with no row and no dollar
  removed.

---

## 3. Three things that were WRONG and are now right — do not re-inherit them

1. **"A buyer summing by tribe-year double-counts."** Both the outside
   reviewer and I said this. **It was false.** Keyed either way the file sums
   to the identical cent. The real harm was **join fan-out** — a buyer merging
   *their own* table on the promised key got up to 3 copies of *their* rows.
   Right fix, wrong mental model; the wrong model would have produced a
   destructive de-dupe.
2. **`prime_contracts`' 80,778 "literal duplicates" were distinct FPDS
   transactions** — different `modification_number`s the mapper never carried,
   4,961 of 5,194 surplus rows at $0 (administrative modifications).
   **De-duping on the audit's reading would have deleted real transactions.**
3. **`517_export_safety` treated `RESOLVED` as definite.** Of 10,983 RESOLVED
   ownership cells only 3,669 agree with the shipped uid. That conflation
   counted **$86.1B** as safe. Fixed by the three-way split now in
   `prime_contracts`; **517 itself still needs updating to match** — see §5.

---

## 4. Open, in priority order

1. **Register row for the 1,749** (§1). Clears the gate.
2. **`517_export_safety` still calls `RESOLVED` definite.** The pipeline now
   knows better than the gate does. Align 517 with the three-way split
   (`CONFIRMED_AS_OF` is the only definite state).
3. **`native-owned-businesses`** is the next closest to READY — one blocker,
   C5 row-conservation. `nagpra` and `federal-register` both have working
   patterns to copy (`review/*_row_conservation.csv`).
4. **C9 is written but never tested for either READY dataset.** The contract
   says "another session can execute the update procedure from the document
   alone". Nobody has tried. Run `docs/datasets/nagpra.md` from a fresh
   session with no history and see if it works — that is the real test, and
   it may demote a dataset back to BLOCKED. That is fine and is the point.
5. **`faads_transactions_all_agencies.csv`** — 179,259 rows with the same
   destroyed-identity defect as `prime_contracts`, diagnosed but not repaired.
   Needs a full re-extract of a 2.77M-row shipped table; do it deliberately,
   not unattended.
6. **`69 → 514 → 510` chain** — a safe spine rebuild was measured (changes ONE
   cell, complete no-op on 1,536 spine rows) but not run, because the agent
   was not permitted `510 --apply`. Sequence is in
   `docs/datasets/federal-register.md`.
7. **7 federal-register tables gained `cedar_uid` after the last ship** — the
   advertised join key is live but not in the release. Closes on next ship.
8. `subawards.csv` — 10,770 duplicates, same shape suspected, unproven.

---

## 5. Standing rules that keep being earned

- **A check reading a key that does not exist passes for the same reason it is
  useless.** This bit three times in two days, twice in my own new code.
  Verify your input contains what you think before trusting green.
- **A check does not count until a fixture proves it FIRES** — and asserts the
  *named* invariant fired, not merely that the gate went red.
- **Unknown stays unknown.** Never invent a date, owner or boundary to make a
  column deterministic. Deterministically wrong metadata is worse than
  deterministically missing metadata.
- **Fix the generating pipeline, never the output CSV.**
- **Check `cedar_pipeline.NEVER_RUN` and `build.py plan <collection>` before
  any rebuild.** Several destroy later enrichment.

---

## 6. Waiting on the owner

`review/OWNER_DECISION_QUEUE.md` — one page, each item with evidence attached
and the consequence of each answer stated. Includes the BBAHC repoint
(evidence complete, sign-off only), the blocklisted-parent policy, the $2.1B
contradiction bucket, and the grain rulings.

## 7. Handoff board

`py -3 code/513_handoffs.py list` — every completed claim, and whether a
*different* session re-executed its checks. Three from this session
(`nagpra`, `federal-register`, correctness) are recorded and **not yet
independently verified**. Verifying them is a legitimate first task.
