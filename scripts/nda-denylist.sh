#!/usr/bin/env bash
# scripts/nda-denylist.sh — pre-commit hook (F13). Blocks committing mentor/rubric/answer-key
# material into agentcore-studio-kit/ — this directory gets squash-exported (subtree-split.sh)
# to the OJT team's own repo, so anything committed here is one export away from being visible
# to the trainees. The allowlist (.subtree-allowlist) controls WHAT leaves; this hook controls
# WHAT CAN EVEN LAND here in the first place — belt and suspenders (F13).
set -euo pipefail

# Match the keyword ANYWHERE in a path segment (substring, case-insensitive) — NOT only when a
# separator follows it. The earlier `mentor[-_./]` form required a trailing separator, so
# `mentors/`, `rubrics/`, `mentornotes.md`, `solutions/` slipped through the guard. Keep these
# broad: a false positive on a legitimately-named file is a cheap rename; a leaked rubric is not.
DENYLIST_PATTERNS=(
  '(^|/)[^/]*mentor'
  '(^|/)[^/]*rubric'
  '(^|/)[^/]*answer[-_ ]?keys?'
  '(^|/)[^/]*solutions?'
  '(^|/)[^/]*grading'
  '\.rubric\.'
)

staged_files=$(git diff --cached --name-only --diff-filter=ACM || true)
blocked=0

for f in $staged_files; do
  for pattern in "${DENYLIST_PATTERNS[@]}"; do
    if echo "$f" | grep -qiE "$pattern"; then
      echo "BLOCKED (NDA denylist): '$f' matches pattern '$pattern' — mentor/rubric/answer-key" \
           "material must never enter agentcore-studio-kit/ (F13, subtree squash-export leak risk)." >&2
      blocked=1
    fi
  done
done

exit $blocked
