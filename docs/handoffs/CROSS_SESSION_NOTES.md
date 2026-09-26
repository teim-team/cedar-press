# Cross-session notes for terminal agents

*From the cloud Claude session, 2026-09-26. For the Codex and Claude agents
working in the terminal. This is context and architecture, not implementation
state: for that, `docs/TERMINAL_HANDOFF.md` and the head of each open PR are
authoritative, and this file defers to them wherever they disagree. Re-measure
anything below before relying on it.*

## Where things stand (measured 2026-09-26, updated the same evening)

- `main` is `52627c5` (PR #127). The cedarpress.ai deploy is green: the site
  shows the v2 release (2026-09-26) of all twelve collections, the 500+
  sources line and the 71-label source banner.
- Open PRs:

| PR | Branch | Head | State |
| --- | --- | --- | --- |
| #122 | `codex/legislation-release-consumer` | `0413b4f` | Draft. Main merged in; every local gate passes |
| #124 | `claude/gaming-consumer-hardening` | `e10c537` | Draft. #122 merged in; every local gate passes |
| #128 | `claude/product-standard-3n2wjf` | `99c54bc` | Documentation: the product standard in AGENTS.md section 6 |

- What was keeping #122 red, and what fixed it (all in `9fa3fed` and after):
  1. Conflicts with `main`, formatting only. #122's side kept; the rename
     table re-measured (119 files, 372 references across 89 files on #122;
     120 and 378 across 91 on #124).
  2. Federal Register ships 34 columns: the producer builds
     `consultation_record_key` at write time. `explore.test.js` expects 34.
  3. The ten write-time columns now have codebook entries, each written from
     the field map's own `why`. contractors' default viewer used a name the
     map had renamed (`affiliation_attribution_status`); fixed at the source.
  4. `ruff check server`: 43 errors fixed.
  5. The census "2,683 new writer edges" was real on every Python after
     3.12, not a local quirk: see Traps. Python 3.12, 3.13 and 3.14.7 all
     pass 411+ tests now.
- Lumecon-data CI now pins these heads: #9 and #11 test the Press consumer at
  #122 `9fa3fed`; #10 tests the Grove consumer at #124 `2619ab6`. The pins
  trail the heads by docs-only commits on purpose: repinning in both
  directions after every commit chases itself.

## For Havala to review (code is done, sign-off is hers)

- `consultation_record_key` now ships as a 34th public Federal Register
  column because the producer builds it. It is a key, not a finding; if it
  should be internal, flip its field-map entry and the test count together.
- The ten new codebook definitions (Federal Register 4, Deals 4, Nonprofits
  2) and the two contractor attribution entries, which now say the
  attribution is source-described, not certified by Cedar.
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
- **Generated files and their gate.** `scripts/dump-press.mjs` now has
  `--check` and runs in `make check-generated` (on #122). Before that, a
  stale `server/cedar_press/_press_data.json` surfaced only in
  `make test-python`.
- **The rename gate counts every path reference in the tree**, including
  strings in test data and baselines. Adding one string that names a Grove
  source path moves the table in `docs/ARCHITECTURE.md`.
- **Hashes recorded on Windows fail on Linux.** Three review hashes in
  `code/521_inventory.py` were taken from a CRLF checkout. The digest now
  reads CRLF as LF, so both agree.
- **`ast.dump` changed in Python 3.13**, so writer signatures differed by
  interpreter and the census reported 2,683 phantom edges. Signatures now use
  one format on every version. If you edit `521_inventory.py`, refresh its
  own row in `docs/schema/inventory.json`: its unresolved writes are keyed to
  the whole module.
- **Personal machine paths.** Docs and code carried one Windows home
  directory. Living docs now say `<cedar-press checkout>`,
  `<lumecon-data checkout>`, `<data workspace>` and `<checkpoint root>`.
  `server/tests/test_portable_paths.py` fails on any new file that names a
  home directory; 65 old files are grandfathered, mostly `code/` scripts
  bound for retirement, and the list can only shrink. Lumecon-data is at zero
  and has the same test.
- **Stale SHAs in PR descriptions mislead reviewers.** Refresh the
  description when the head moves.

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
8. **Portable by construction.** Nothing names one person's machine. Paths
   come from arguments, environment variables or the repository root, and
   hashes and signatures must come out the same on Windows, macOS and Linux
   and on every supported Python.
