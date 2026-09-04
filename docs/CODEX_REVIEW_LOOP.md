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
5. **Fast-forward `codex-review-base` to the SHA Codex actually reviewed** —
   not to `origin/main`. See below; this is the step that used to lose work.

## Why the base advances rather than the PR merging

Merging a PR whose head is `main` into a base that is an ancestor of `main` does
nothing useful and confuses the history. The base is moved with a push instead:

```
# The SHA Codex names in "Reviewed commit:" on the round you just answered.
REVIEWED=95e8912eca            # <- read it off the review, never assume
git push origin "$REVIEWED":refs/heads/codex-review-base --force-with-lease
```

`--force-with-lease` rather than `--force`, so the push fails if someone else
moved the marker — the one thing that could silently drop a round of review.

### Why the reviewed SHA and not `origin/main`

**Codex, PR #44, P1 — and it is right.** This file used to say:

```
git push origin origin/main:refs/heads/codex-review-base --force-with-lease
```

Step 4 of the cycle *fixes on `main`*, so by the time step 5 runs, `origin/main`
is normally **ahead** of the commit Codex reviewed — by exactly the fix commits
that answered the findings, plus anything else that landed meanwhile. Advancing
the marker to `origin/main` therefore moves it **past commits nobody has
reviewed**, and those commits are then below the base of the next PR and never
appear in a diff again.

`--force-with-lease` does not catch this. The lease constrains the
DESTINATION's old value — it fails only if someone else moved
`codex-review-base`. It says nothing about how far the SOURCE has advanced, so
the unreviewed commits sail through a green push.

Pushing the reviewed SHA instead leaves every later commit above the marker,
where the next round's diff will pick it up. The cost is that the next PR
carries the fix commits as well as the new work, which is correct: a fix
answering a finding has not itself been reviewed.

The alternative, if you want the marker at the tip, is to trigger one more
review at that tip first and advance to *that* SHA. Either is fine. Advancing
to an unreviewed `origin/main` is not.

## What this does not solve

If a round of review is skipped, the next diff carries two rounds of work and
gets a shallower read. The marker makes that visible — the PR states how many
commits it covers — but it cannot prevent it.
