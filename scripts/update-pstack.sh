#!/usr/bin/env bash
# Sync skills/pstack/ from the upstream cursor/plugins pstack plugin.
# Keeps our meta skills/pstack/SKILL.md (upstream has none) and stamps the
# upstream version into it and the README. Commits and pushes only on change.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

UPSTREAM="https://github.com/cursor/plugins.git"
PSTACK_DIR="skills/pstack"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

git clone --depth 1 --filter=blob:none --sparse "$UPSTREAM" "$WORK/upstream"
git -C "$WORK/upstream" sparse-checkout set pstack

VERSION="$(grep -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$WORK/upstream/pstack/plugin.json" | head -1 | sed 's/.*"\(.*\)"/\1/')"
echo "upstream pstack version: ${VERSION}"

# wipe previously synced content, keep our meta SKILL.md
find "$PSTACK_DIR" -mindepth 1 -maxdepth 1 ! -name 'SKILL.md' -exec rm -rf {} +

cp -r "$WORK/upstream/pstack/skills/." "$PSTACK_DIR/"
mkdir -p "$PSTACK_DIR/agents"
cp "$WORK/upstream/pstack/agents/"*.md "$PSTACK_DIR/agents/"

# stamp the upstream version into our files
sed -i -E "s/\(v[0-9]+\.[0-9]+\.[0-9]+, MIT/(v${VERSION}, MIT/" "$PSTACK_DIR/SKILL.md"
sed -i -E "s|tree/main/pstack\) v[0-9]+\.[0-9]+\.[0-9]+|tree/main/pstack) v${VERSION}|" README.md

git add -A
if git diff --cached --quiet; then
  echo "pstack already up to date (v${VERSION})"
else
  git -c user.name="github-actions[bot]" -c user.email="github-actions[bot]@users.noreply.github.com" \
    commit -m "chore(pstack): sync from cursor/plugins pstack v${VERSION}"
  git push
  echo "pushed pstack v${VERSION}"
fi
