.PHONY: lint test test-node test-python audit audit-node audit-python hooks check

# One place that names each gate, so the command a contributor runs and the
# command CI runs cannot drift apart. `deploy.yml` runs the same list before
# it ships, and `ci.yml` runs it on a pull request.

lint:
	npx --no-install eslint .
	ruff check server

test: test-node test-python

# The frontend suite, with a coverage floor. Measured 95.36 lines /
# 87.77 branches / 93.83 functions on 2026-09-22 over 271 passing tests; the
# floor sits at or just below each. It is a ratchet against regression, not a
# target: raise it when real coverage rises, never lower it to make a red run
# green.
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
# resolving is what a fresh `pip install -e server[dev]` actually does, and
# auditing the environment trips over this project's own unpublished,
# editable package. --strict fails on a dependency that could not be audited,
# so a silent skip is not a pass.
audit-python:
	uv pip compile server/pyproject.toml --extra dev -o .audit-requirements.txt --quiet
	pip-audit --strict --disable-pip --no-deps -r .audit-requirements.txt
	@rm -f .audit-requirements.txt

hooks:
	pre-commit install

check: lint test
