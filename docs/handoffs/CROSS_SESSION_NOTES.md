# Cross-session notes for terminal agents

*From the cloud Claude session, 2026-09-26. For the Codex and Claude agents
working in the terminal. This is context and architecture, not implementation
state: for that, `docs/TERMINAL_HANDOFF.md` and the head of each open PR are
authoritative, and this file defers to them wherever they disagree. Re-measure
anything below before relying on it.*

## Where things stand (measured 2026-09-26)

- `main` is `52627c5` (PR #127). The cedarpress.ai deploy is green again:
  every push from `d7b25d1` (2026-09-23) until #127 had failed on
  `ruff check server` and the rename gate, so nothing between #120 and #126
  had reached the live site. The live site now shows the v2 release
  (2026-09-26) of all twelve collections, the 500+ sources line and the
  71-label source banner.
- Open PRs:

| PR | Branch | Head | State |
| --- | --- | --- | --- |
| #122 | `codex/legislation-release-consumer` | `5e57dc8` | Draft. `gates` red, and conflicts with `main` since #127 |
| #124 | `claude/gaming-consumer-hardening` | `808db52` | Draft. Red only because it contains #122 |
| #128 | `claude/product-standard-3n2wjf` | `99c54bc` | Documentation: the product standard in AGENTS.md section 6 |

- What keeps #122 red, in order. The exact fixes are in the PR comment.
  1. It conflicts with `main` in `docs/ARCHITECTURE.md` and two server test
     files. Keep #122's side of the tests. Re-measure the rename table; with
     `main` merged it reads 119 files, 372 references across 89 files, and 44
     referencing files outside `src/`.
  2. `explore.test.js` pins Federal Register at 33 columns. The field map now
     has 34, because `consultation_record_key` was added.
  3. Ten columns lost `status: "pending"` but have no codebook `add` entry:
     Federal Register 4, Deals 4, Nonprofits 2.
  4. `ruff check server` reports 32 errors in two test files.
  5. Local only, on Python 3.13: the script census test reports 2,683 new
     writer edges. CI runs 3.12, so confirm there before chasing it.

## Decisions that are not ours to make

These wait on Havala (Cedar Press and Cedar Grove data). Do not settle them in
code.

- Whether `consultation_record_key` ships as a 34th public column or is made
  internal.
- The public definitions for the ten write-time columns above.
- The Foundation and corporate giving publication rule (Lumecon-data #11).
- Whether Lumecon proposes Gaming ordinals or Cedar assigns them at issuance.
  No Gaming IDs are issued before #124 lands.

## Standing rules this session worked under

- **Build and write it as the shipped product** (AGENTS.md section 6 via #128).
  No pilot or prototype modes in code or copy. Pilots run as ordinary accounts
  or access codes.
- **Payments.** The code says Tribal Business News owns Press payment,
  renewals, upgrades and issuance (`server/cedar_press/codes.py`); Lumecon's
  side is codes and entitlement. Lumecon now has its own Stripe account, which
  carries Cedar Grove's payments. See teim-team/teim-app#186.
- **Cedar Press is unannounced.** It must not appear anywhere in
  lumecon-website. Tribal Business News is named only in Cedar Press.
- **Merge commits only** on shared branches. No force-push or rebase of
  another session's branch.
- **Missing is not zero** (the numeric standard). A withheld, suppressed or
  unreadable value stays missing and is labelled as such.

## Traps found this session

- **The release ledger is append-only.** `scripts/record-release.mjs` refuses
  a date change under an existing version, so a new date needs a new version.
  All twelve collections went v1 to v2 on 2026-09-26 for this reason.
- **`make check-generated` does not cover `scripts/dump-press.mjs`.** A
  manifest change leaves `server/cedar_press/_press_data.json` stale, and that
  only shows up in `make test-python`. Regenerate it with
  `node scripts/dump-press.mjs > server/cedar_press/_press_data.json`. It is
  worth adding to the gate.
- **The rename gate counts path references across the whole tree.** Adding or
  removing one import of a Grove source path changes its numbers. That is why
  #127 and #122 each had to re-measure `docs/ARCHITECTURE.md`.
- **Stale SHAs in PR descriptions mislead reviewers.** #124's description
  names Lumecon pin `2b0ab3b` while its `ci.yml` pins `e71094a`, and says
  `gates` passed when it now fails. Refresh descriptions when heads move.

## Architecture: moving from scripts to a product

The direction is already in #122 and Lumecon-data #8 to #11. These are the
properties that make it hold.

1. **One producer.** Lumecon-data builds, validates and releases every
   dataset. Cedar Press presents, entitles and serves exact pinned bytes; it
   does not rebuild, patch or re-derive data. Anything in `code/` that still
   writes customer data is a candidate to retire into a Lumecon-data producer,
   not to improve here.
2. **A pin is a contract.** A consumer pins a release by ID and manifest hash.
   Updating the pin after the producer merges is part of the merge order, not
   a follow-up. CI must test the pin that will ship: Lumecon-data's "Grove
   consumer" job still pins cedar-press `136255f`, which is on the superseded
   `claude/gaming-grove-consumer` branch rather than #124.
3. **Entity reconciliation belongs to the producer.** `cedar_uid` names the
   Native entity, and dataset IDs name events or objects. Names, UEI, CAGE and
   EIN are evidence, never automatic identity. Reconciliation decisions live
   in the review ledger with provenance, not in consumer code.
4. **The field map and codebook are the public contract.** Every column that
   ships needs a decision and a codebook entry, and `explore.test.js` enforces
   both. Adding a public column changes the approved spec and needs Havala's
   sign-off, even when it is only a key.
5. **One gate, run the same everywhere.** `make check` runs identically in CI
   and locally. Each generated file has a `--check` mode wired into it; the
   dump above is the known gap.
6. **Scripts: fewer, registered, idempotent.** The script census exists so
   that every writer is declared. Prefer deleting a superseded script over
   keeping it "just in case". A script that writes must be safe to run twice.
7. **Stacks stay aligned.** When a parent branch moves, merge it into each
   child in order and run the checks at every step, not only at the tip.
