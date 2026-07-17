#!/usr/bin/env bash
# scripts/subtree-split.sh — F13: squashed, clean export of ONLY this kit's allowlisted paths
# into a fresh, single-commit history, for seeding the OJT team's own GitHub repo.
#
# Deliberately NOT `git subtree split --prefix=agentcore-studio-kit` without --squash: that
# replays every historical commit that touched this prefix, and git history is immutable — a
# mentor/rubric file that existed at this path in ANY earlier commit stays readable via
# `git show <old-sha>:path` forever, even if a later commit removed it. A squashed,
# allowlist-filtered snapshot is the only export shape that structurally cannot leak history.
#
# Mechanism: rsync --files-from=.subtree-allowlist (never `cp -r` the whole kit tree) into a
# throwaway directory, `git init` there, ONE commit. Exactly one commit means there is no
# history to archaeology through in the exported repo, by construction.
set -euo pipefail

KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ALLOWLIST="${KIT_ROOT}/.subtree-allowlist"
EXPORT_DIR="${1:-/tmp/agentcore-studio-kit-export}"
REMOTE_URL="${STUDIO_SUBTREE_REMOTE:-}"

if [ ! -f "$ALLOWLIST" ]; then
  echo "missing $ALLOWLIST — refusing to export without an explicit allowlist" >&2
  exit 1
fi

rm -rf "$EXPORT_DIR"
mkdir -p "$EXPORT_DIR"

# rsync only the allowlisted paths. Anything NOT on .subtree-allowlist (mentor notes, rubric,
# grading fixtures, if any ever land inside this kit tree) never touches the export directory —
# it is never even a candidate for a git-ignore-style after-the-fact filter.
#
# `-r` is REQUIRED explicitly: `--files-from` turns OFF the recursion that `-a` implies, so a
# directory entry in the allowlist (e.g. `packages/`) would otherwise copy the empty dir only,
# shipping an export with no source (rsync manual: "--files-from ... turns off the recursive
# behavior unless you specify -r"). The `--exclude`s keep build/cache artifacts (node_modules,
# dist, __pycache__, .venv, tool caches) out of the "clean" snapshot even though `apps/`/`tests/`
# recurse into them.
rsync -a -r \
  --exclude='node_modules/' --exclude='dist/' --exclude='.venv/' \
  --exclude='__pycache__/' --exclude='*.pyc' \
  --exclude='.mypy_cache/' --exclude='.ruff_cache/' --exclude='.pytest_cache/' \
  --exclude='.import_linter_cache/' \
  --files-from="$ALLOWLIST" "$KIT_ROOT"/ "$EXPORT_DIR"/

cd "$EXPORT_DIR"
git init -q
# Local identity for this throwaway repo so the export commit works on any machine, even one
# with no global git user configured (CI, a fresh clone) — never touches global git config.
git config user.email "kit-export@studio.local"
git config user.name "agentcore-studio-kit export"
git add -A
git commit -q -m "chore: squashed export of agentcore-studio-kit (subtree-split.sh, F13)"

echo "squashed export ready at $EXPORT_DIR — exactly 1 commit, no source history carried over."

if [ -n "$REMOTE_URL" ]; then
  git remote add origin "$REMOTE_URL"
  git push -u origin HEAD:main
  echo "pushed to $REMOTE_URL"
else
  echo "STUDIO_SUBTREE_REMOTE not set — export left at $EXPORT_DIR, push manually when ready:"
  echo "  cd $EXPORT_DIR && git remote add origin <url> && git push -u origin HEAD:main"
fi
