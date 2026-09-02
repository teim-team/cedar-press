# The Codex review loop on `teim-team/cedar-press`

*Live doc. The owner's instruction: "Have a standing pull request and keep
updating it so codex can flag stuff and respond to codex after every pull
request. We need to converge both strands of work — the product with the
data."*

This file is the Cedar-side record of that loop, because the data project and
the product repo are two different repositories and neither one's history tells
the whole story on its own.

---

## HOW TO ENUMERATE A CODEX REVIEW, AND THE MISTAKE THAT MAKES YOU MISS IT

**`gh api repos/teim-team/cedar-press/pulls/<n>/comments` can return an empty
list while a review holds six findings.** That endpoint returns review-thread
comments only, and a Codex review distributes its content across three places.
An agent read only that one, found nothing, and told the owner "Codex found no
findings" when there were six. Read all of these before concluding anything:

    /pulls/<n>/reviews              the review objects (state, commit reviewed)
    /pulls/<n>/reviews/<id>/comments   that review's findings
    /pulls/<n>/comments             review-thread comments, top level
    /issues/<n>/comments            the summary comment and any human replies

**The repo is public**, so all four are readable with no token at all:
`curl -s https://api.github.com/repos/teim-team/cedar-press/pulls/26/comments`.
Posting is what needs auth. Note also that `json.load` on those responses dies
on `cp1252` under Windows Python — open with `encoding="utf-8"`.

## AUTH, AS OF 2026-09-02 — READING IS FREE, WRITING IS NOT

On this machine there is **no `gh` CLI, no `GITHUB_TOKEN`/`GH_TOKEN`, no
`~/.netrc` and no `~/.config/gh/hosts.yml`.** `git push` works, because the
Windows Git Credential Manager answers for `github.com` silently — so a branch
can be published, and a pull request cannot be opened and a comment cannot be
posted. The Chrome extension route is also unavailable: no browser is
connected to this account.

**So an agent on this machine can push the work and cannot post the reply.**
Whoever wants that closed needs one of: `gh auth login`, a PAT exported as
`GH_TOKEN`, or a connected Chrome. Until then the reply text is written out
below verbatim, ready to paste, and the substance of it also lives in
`data/cedar/README.md` on the branch so it is not lost if nobody pastes it.

---

## PR #26 — opened 2026-09-01, MERGED 2026-09-02 04:39 UTC

Branch `cedar-data-samples`. Codex reviewed commit `7e3a536` and left **six**
findings: three P1, three P2. Round 1 answered all six in `d30a64b`.

| # | pri | file | finding | verdict |
|---|---|---|---|---|
| 1 | P1 | `collection_descriptors.json` | `CollectionDataset(**d)` raises `TypeError` on `n_rows`; `version` and `downloads` missing | **Right, and total.** Not one of the 13 could load. Fixed in round 1; re-verified 13/13 on 2026-09-02. |
| 2 | P1 | `collection_descriptors.json` | the product's id for that collection is `owned`, not `native-owned-businesses` | **Right.** Would have left a READY dataset silently unable to replace the demo record. Mapped. |
| 3 | P1 | `funding__sample.csv` | `PUEBLO OF ACOMA (INC)` resolves to Haaku Community Academy | **Right about the display, and the round-1 reply overstated it.** See the correction below. |
| 4 | P2 | `README.md` | the subaward overstatement is 86.9%, not 46.5% | **Right.** Round 1 fixed the descriptor and left this README saying 46.5%, so the two halves of the handoff then disagreed. Both now state the denominator. |
| 5 | P2 | `collection_descriptors.json` | every blocked dataset says only `BLOCKED` | **Right.** `cedar.blockers` now carries the named contract points. |
| 6 | P2 | `lobbying__sample.csv` | the README promises no natural persons and the sample publishes `STEPHEN GRAHAM` | **Right that the doc and the code disagreed; wrong about which to change.** An individual may register as a lobbyist and the registration IS the record the LDA creates. The claim was narrowed to personal data held apart from a public role. |

**Nothing Codex said in round 1 was wrong on the facts.** Finding 6 is the only
one where the right repair was the opposite of the one suggested, and Codex had
itself offered that as its second option.

---

## THE CORRECTION OWED ON FINDING 3 — text to post on PR #26

> **Correcting my own round-1 reply on the Acoma finding. I told you this was
> "a real defect, and worse than the ten rows showed — 2,434 rows and
> $1.008B." That was wrong, and the correction is more useful than the original
> claim.**
>
> **The keyed columns are correct.** Those rows carry
> `cedar_uid = CE-0011W-HN`, which the identity register resolves to Pueblo of
> Acoma — a federally recognized tribe, not a subordinate institution. This is
> a **labelling** defect and not an attribution one. `canonical_name` in that
> table is copied verbatim by `24_funding_merge.load_tribe_names()` out of
> `lineageA_dta_corrtd_tribe_key.csv`, a legacy do-file key that literally
> contains `{234, 'haaku community academy', NM}`. It is not a Cedar name at
> all, and the register records the reconciliation explicitly.
>
> At scale: of 552,602 rows carrying a `cedar_uid`, 345,108 have a
> `canonical_name` that disagrees with the register's name for that uid, and
> **339,129 of those — 98.3%, $94.0B — are explained entirely by that legacy
> reconciliation.** Right identity, stale label. Of the 5,979 not so explained,
> 3,620 are a *blank* `canonical_name` with a uid present, which is a missing
> label rather than a wrong one.
>
> The register holds the real sub-hubs separately and the table uses them
> correctly when the recipient genuinely is the school — Blackfeet Community
> College is `CE-0010N-2P`, 312 rows. So entity-level grouping on `cedar_uid`,
> which is the key ADR-009 mandates, credits the tribe. Only grouping on the
> legacy display name credits the school. **The funding sample now ships
> `cedar_uid` beside `canonical_name`**, which is what the ten rows were
> missing: you were shown the unreliable half of a correctly attributed row.
>
> **The genuinely wrong attribution turned up while chasing yours, and it is
> smaller in rows and worse in kind.** Legacy id 347 mapped **820 rows and
> $181,881,441.37 of United Keetoowah Band obligations onto Cherokee Nation** —
> two distinct federally recognized tribes merged into one uid on a loose token
> match on the word "Cherokee", with United Keetoowah Band sitting in the
> register in its own right as `CE-001BS-HA` / `TRBF-UKEETW-00`. The crosswalk
> row contradicted itself and said why: its proposed name read "United
> Keetoowah Band of Cherokee Indians in Oklahoma" while its id read
> `TRBF-CHKNAT-00`. Fixed at source in `7b35193`, and the whole legacy CICD id
> scheme has since been retired in `b3a0d7f`.
>
> So: your finding was right, the row you pointed at was not the defect, and
> pulling on it found one that was. Thank you — and the reason the sample let
> me misread it is now fixed rather than argued about.

---

## FINDINGS FOUND BY THIS SIDE WHILE ADDRESSING CODEX'S

Recorded because they came out of the review loop and would not otherwise be
attributed to it.

- **`parent_contract_number` was documented as populated on all 1,217,768 rows
  and was not.** 262,773 rows (21.6%) held the literal string `nan` — a pandas
  float through `str()` on the way to CSV, which counts as present and means
  absent. Found only because Codex's finding 3-adjacent complaint about
  `contract_number` forced that column into the sample. Cleared by
  `772_strip_nan_sentinels.py`; a sweep of the same table found 953,785 such
  cells across twelve columns, most of which a concurrent rebuild had already
  cleaned.
- **The pair is the key, and the cross-tab proves it.** 664,470 rows carry a
  real parent and a full child PIID, 290,525 a real parent and a modification
  stub, 262,773 no parent and a complete standalone PIID, and **zero rows have
  neither**.
- **770 was deleting requested columns.** Any column blank across the ten
  sampled rows was silently dropped, so the sample *schema* was a function of
  the sample. Fixed; blank columns now ship and are named, and a `SHOW` entry
  for a column the table does not carry is a hard `verify` failure.
- **The Eastern/Chickahominy collision is a matcher defect and a blanket
  exclusion would be the wrong fix.** All 44 rows keyed to `Chickahominy
  Indians-Eastern Division` turn on the token `EASTERN` and none is in
  Virginia — but three are real Native organisations keyed to the *wrong*
  tribe, so the instrument is a redirect, not a block. Handed on rather than
  patched.

---

## PR AFTER #26

#26 merged into `main`, and GitHub deleted the branch on merge. `cedar-data-samples`
has been re-pushed on top of `main` at `1241a19`. **A new PR must be opened for
the standing loop to continue** — that is the one action on this page that
cannot be done from this machine. Once it exists, Codex reviews on open; read
all four endpoints listed at the top before deciding it found nothing.

### The PR to open, ready to paste

    gh pr create --repo teim-team/cedar-press \
      --base main --head cedar-data-samples \
      --title "Cedar data: the Acoma correction, and four defects a buyer would have seen"

Body:

> Standing PR for the data side of the handshake. #26 merged and GitHub deleted
> the branch; this re-opens the loop on top of `main`.
>
> **The correction first, because it is owed.** Round 1 told Codex that the
> `PUEBLO OF ACOMA (INC)` finding was "a real defect, and worse than the ten
> rows showed — 2,434 rows and $1.008B." **That was wrong.** The keyed columns
> are correct: those rows carry `cedar_uid = CE-0011W-HN`, Pueblo of Acoma,
> federally recognized. It is a labelling defect — `canonical_name` is copied
> verbatim from a legacy do-file key that literally holds
> `{234, 'haaku community academy', NM}`. Of 552,602 keyed rows, 345,108
> disagree with the register and 339,129 of those (98.3%, $94.0B) are that same
> legacy reconciliation: right identity, stale label. The genuinely wrong
> attribution found by chasing it was **820 rows and $181,881,441.37 of United
> Keetoowah Band obligations credited to Cherokee Nation**, fixed at source in
> `7b35193`; the legacy id scheme is retired in `b3a0d7f`.
>
> **Four defects out of the samples.** `contract_number` was shipping FPDS
> modification stubs (`0098`, `0006`, `SBA0001`) as if they were keys —
> `parent_contract_number` now ships beside it and the pair is the key, and
> adding it exposed 262,773 rows holding the literal string `nan`. The
> nonprofits sample showed `classification_ruling`, which is filled on 3.1% of
> rows, instead of `funnel_stage`, which is where the 4,651 exclusions live.
> `deals` shipped no dollar value though the descriptor promises one.
> `certification_expiration` shipped in six date formats and every date that
> reached a customer was un-normalised.
>
> **And a failure mode in the builder.** It silently deleted any requested
> column that was blank across the ten sampled rows, so the sample schema was
> not stable across rebuilds. Fixed, and the new hard check caught a live drift
> within the hour.
>
> The 46.5% / 86.9% split is closed by stating the denominator in all four
> places. 11 of 13 datasets are READY, up from 4. All 13 descriptors verified
> against the `CollectionDataset` dataclass on `main`.
