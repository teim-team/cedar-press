#!/usr/bin/env bash
# The pre-commit hook `no-secrets-committed` (.pre-commit-config.yaml).
# pre-commit passes the staged file names as arguments; any that look like a
# credential fail the commit, naming the file.
#
# .env.example is the tracked template. A real .env holds the DATABASE_URL
# and the subscriber session secret, and Git history is the one place a
# mistake cannot simply be deleted later.
#
# A script rather than a `bash -c` string inside the YAML, so the thing
# secretsHook.test.js runs is the thing the hook runs: a folded YAML scalar
# re-joins lines by its own rules, and a quoting slip there would turn this
# guard into a green no-op with nothing to notice it (Codex, PR #105).

bad=0
for f in "$@"; do
  case "$f" in
    .env | .env.* | */.env | */.env.*)
      if [ "${f##*/}" != ".env.example" ]; then
        echo "$f holds secrets; it belongs outside Git"
        bad=1
      fi
      ;;
    *.pem | *.key | *credentials*.json)
      echo "$f looks like a credential; it belongs outside Git"
      bad=1
      ;;
  esac
done
exit "$bad"
