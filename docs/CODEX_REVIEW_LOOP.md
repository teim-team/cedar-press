# The Codex review loop, with one working branch

*Owner, 2026-09-02: "periodically work with one branch on git and address to codex."*

Those two pull against each other and the tension is worth naming, because the
obvious resolutions are both bad. Codex reviews **pull requests**, so it needs a
diff. One working branch means there is nothing to open a pull request *from*.
Cutting a feature branch per change gives Codex its diff and gives us the branch
sprawl that has already been consolidated three times today.

## The arrangement

`main` is the only branch anyone works on. Everything lands there.

`codex-review-base` is a **marker, not a workspace**. Nobody commits to it. It
sits at the last commit Codex has finished reviewing, and it is the base of a
pull request whose head is `main`. The diff is therefore exactly the work done
since the last review — which is the thing a reviewer wants and the thing a
branch-per-change never quite gives, because it shows one change in isolation
rather than everything that has moved.

```
main                 ●───●───●───●───●   <- everyone works here
                     ↑                ↑
codex-review-base ───┘                └── review PR: base=codex-review-base
                                          head=main
```

## The cycle

1. Work lands on `main`.
2. Open a PR, base `codex-review-base`, head `main`. Comment `@codex review`.
3. Answer every finding. Verify each against **current** `main` before fixing —
   the tree moves fast and findings routinely arrive against code that has
   already changed. Say plainly which do not reproduce, with the measurement.
4. Fix on `main`.
5. **Fast-forward `codex-review-base` to the reviewed tip.** The next round's
   diff starts clean.

## Why the base advances rather than the PR merging

Merging a PR whose head is `main` into a base that is an ancestor of `main` does
nothing useful and confuses the history. The base is moved with a push instead:

```
git push origin origin/main:refs/heads/codex-review-base --force-with-lease
```

`--force-with-lease` rather than `--force`, so the push fails if someone else
moved the marker — the one thing that could silently drop a round of review.

## What this does not solve

If a round of review is skipped, the next diff carries two rounds of work and
gets a shallower read. The marker makes that visible — the PR states how many
commits it covers — but it cannot prevent it.
