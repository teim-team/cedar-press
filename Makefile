.PHONY: lint test test-node test-python audit audit-node audit-python hooks check check-generated

# One place that names each gate, so the command a contributor runs and the
# command CI runs cannot drift apart. `deploy.yml` runs the same list before
# it ships, and `ci.yml` runs it on a pull request.

lint:
	npx --no-install eslint .
	ruff check server

test: test-node test-python

# The frontend suite, with a coverage floor over every production module --
# including the ones no test imports, which node's own report leaves out
# rather than counting as 0% (Codex, PR #105). scripts/coverage-gate.mjs
# holds the floor and the measurement behind it; `npm run test` runs it.
test-node:
	npm run test:coverage

# The API suite, with warnings as errors and a coverage floor (.coveragerc).
#
# One narrow, dated exception to `-W error`: starlette's own testclient module
# evaluates a deprecated anyio alias at import time, so it fires while
# unittest is still loading tests/test_api.py and tests/test_shelf.py and
# nothing in this repository can silence it at the source. Scoped to that
# exact message and module, so a real anyio deprecation in this project's
# code still fails. Recheck when starlette is next upgraded (noted
# 2026-09-22).
test-python:
	python3 -W error \
		-W "ignore:The anyio.abc.BlockingPortal alias is deprecated:DeprecationWarning:starlette.testclient" \
		-m coverage run -m unittest discover -s server/tests -t server
	python3 -m coverage report

audit: audit-node audit-python

# A CI gate -- see ci.yml, which runs it alongside `audit-python`. It reported
# one high advisory on 2026-09-22 (js-yaml 4.0.0-4.3.1, GHSA-2883-xcg3-v3hh),
# transitively under eslint; bumping the resolved js-yaml to 4.3.2 cleared it,
# and the gate went in from that clean state rather than with a backlog
# already inside it, which is the only way a gate like this stays meaningful.
audit-node:
	npm audit --audit-level=high

# Also a CI gate -- see ci.yml. It reported no known vulnerabilities on
# 2026-09-22, so it too is enforced from a clean state.
#
# Audits a resolved dependency set rather than the installed environment:
# auditing the environment trips over this project's own unpublished,
# editable package. --strict fails on a dependency that could not be audited,
# so a silent skip is not a pass.
#
# --all-extras, not `--extra dev`: that flag resolves the named group alone,
# so the `postgres` group -- psycopg and psycopg_pool, the stack everything a
# subscriber pays for runs on -- was never audited (Codex, PR #105). Checked
# 2026-09-23 by pinning a vulnerable urllib3 into `postgres`: `--extra dev`
# reported no known vulnerabilities, `--all-extras` failed on five. A new
# extra is covered the day it is added, and gateCopies.test.js fails if this
# recipe goes back to naming groups one at a time.
audit-python:
	uv pip compile server/pyproject.toml --all-extras -o .audit-requirements.txt --quiet
	pip-audit --strict --disable-pip --no-deps -r .audit-requirements.txt
	@rm -f .audit-requirements.txt

hooks:
	pre-commit install

# Every generated file the repository tracks, re-rendered from its source
# and compared with the tracked copy. Each script's `--check` exits 1 on a
# difference and names the command that rewrites the file, so a red run
# says which artifact drifted, not which test happened to notice. The node
# suite spawns each of these inside a test too; this is the gate that names
# them, runs in seconds, and does not wait on a coverage run to say so.
#
#   codebook-markdown   docs/DATASET_CODEBOOK.md            from data/cedar/codebook.json
#   derive-explore      data/cedar/explore.json             from the published samples
#   field-map-markdown  docs/FIELD_MAP_2026-09-05.md and
#                       docs/IDENTIFIER_RETIREMENT_2026-09-05.md from data/cedar/field_map.json
#   guides-markdown     docs/guides/<collection>.md         from four data/cedar JSON files
#   measure-samples     data/cedar/samples.published.json   from the git index
#   record-release      data/cedar/releases.json            from the manifest
#   seo-head            index.html's JSON-LD block and public/sitemap.xml from the catalog
#
# Deliberately absent (2026-09-22): the data workspace's three drift checks,
# `code/500_build_architecture_map.py --check`,
# `code/374_build_cedar_taxonomy_export.py --check` and
# `code/512_build_dataset_contracts.py verify`. Each measures data/clean,
# data/spine or dist/ tables that git does not track (the workspace is
# 38 GB), so a CI checkout and the owner's tree can never agree on their
# output: 374 aborts on the missing spine, 512 reports every collection as
# claiming zero tables, and 500 -- current today only because the tracked
# map was itself rendered from a data-less checkout -- would go red the first
# time it was regenerated beside real data. They run by hand, on the machine
# that holds the data. `code/1050_preflight.py` is not a check at all: it
# claims a script number as a side effect of running.
check-generated:
	node scripts/codebook-markdown.mjs --check
	node scripts/derive-explore.mjs --check
	node scripts/field-map-markdown.mjs --check
	node scripts/guides-markdown.mjs --check
	node scripts/measure-samples.mjs --check
	node scripts/record-release.mjs --check
	node scripts/seo-head.mjs --check

# Every gate CI runs, bar the Playwright smoke suite (it needs a browser
# installed once: `npx playwright install --with-deps chromium`, then
# `npm run test:smoke`). The audits are in it (Codex, PR #105): without them a
# vulnerable dependency passed `make check` and failed only in CI. They need
# the network. gateCopies.test.js fails if a `make` target a workflow runs is
# not reachable from here.
check: lint check-generated test audit
