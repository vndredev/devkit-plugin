# /dk git

Git workflow commands with Conventional Commits.

## Commands

| Command | Description |
|---------|-------------|
| `/dk git init` | Initialize new project (git, config, files, commit) |
| `/dk git update` | Sync managed files and GitHub settings |
| `/dk git pr` | Create pull request |
| `/dk git pr review [n]` | Check PR review status |
| `/dk git pr merge [n]` | Merge PR (squash) |
| `/dk git branch <name>` | Create feature branch |
| `/dk git squash` | Squash commits on branch |
| `/dk git cleanup` | Clean local tags + branches |
| `/dk git issue report` | Report bug in devkit-plugin |
| `/dk git issue create` | Create issue in current project |
| `/dk git issue list` | List open issues |
| `/dk git issue view [n]` | View issue details |

---

## Commit Format

**Conventional Commits**: `type(scope): message`

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `chore` | Maintenance |
| `refactor` | Restructure |
| `test` | Tests |
| `ci` | CI/CD |

### Internal Scopes (skip release notes)

| Scope | Use Case |
|-------|----------|
| `internal` | Internal refactoring |
| `review` | Code review fixes |
| `ci` | CI/CD changes |
| `deps` | Dependency updates |

---

## /dk git init

Initialize a new project with full setup:

```bash
/dk git init                      # Auto-detect type
/dk git init --name myapp         # With name
/dk git init --type node          # With type (python, node)
/dk git init --github user/repo   # With GitHub setup
```

**Workflow:**

1. `git init` (if not already initialized)
2. Detect project type (pyproject.toml → python, package.json → node)
3. Create `.claude/.devkit/config.jsonc`
4. Sync all managed files (linters, workflows, templates, CLAUDE.md)
5. Create first commit: `chore: initial commit`
6. (Optional) Create GitHub repo + configure settings

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.setup import git_init
for step, ok, msg in git_init():
    icon = '✓' if ok else '✗'
    print(f'{icon} {step}: {msg}')
"
```

---

## /dk git update

Sync managed files and GitHub settings for existing project:

```bash
/dk git update          # Sync all
/dk git update --force  # Overwrite manual changes
```

**Workflow:**

1. Validate config.jsonc exists
2. Sync managed files (only changed)
3. Update GitHub settings if remote configured

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from lib.setup import git_update
for step, ok, msg in git_update():
    icon = '✓' if ok else '✗'
    print(f'{icon} {step}: {msg}')
"
```

---

## /dk git pr

Create PR for current branch using the PR template.

**Reads config from `.claude/.devkit/config.jsonc`:**
- `github.pr.auto_merge` - Enable auto-merge (default: false)
- `github.pr.delete_branch` - Delete branch after merge (default: true)
- `github.pr.merge_method` - squash/merge/rebase (default: squash)

```bash
BRANCH=$(git branch --show-current)
git push -u origin "$BRANCH"

# Get commit info
TITLE=$(git log -1 --format=%s)
COMMITS=$(git log main..$BRANCH --format='- %s' | head -10)

# Read PR config
CONFIG_FILE=".claude/.devkit/config.jsonc"
AUTO_MERGE=$(jq -r '.github.pr.auto_merge // false' "$CONFIG_FILE" 2>/dev/null || echo "false")
DELETE_BRANCH=$(jq -r '.github.pr.delete_branch // true' "$CONFIG_FILE" 2>/dev/null || echo "true")
MERGE_METHOD=$(jq -r '.github.pr.merge_method // "squash"' "$CONFIG_FILE" 2>/dev/null || echo "squash")

# Determine change type from first commit
TYPE=$(echo "$TITLE" | grep -oE '^(feat|fix|docs|chore|refactor|test|ci)' || echo "chore")

# Map type to checkbox
case "$TYPE" in
  feat)     CHECKBOX="- [x] Feature - New functionality" ;;
  fix)      CHECKBOX="- [x] Bug Fix - Fix for existing issue" ;;
  refactor) CHECKBOX="- [x] Refactor - Code restructuring" ;;
  docs)     CHECKBOX="- [x] Docs - Documentation only" ;;
  *)        CHECKBOX="- [x] Chore - Maintenance/tooling" ;;
esac

# Build PR body from template structure
BODY="## Summary
$COMMITS

## Type of Change
$CHECKBOX

## Changes
$COMMITS

## Checklist (Author)
- [ ] Self-review completed
- [ ] No secrets committed
- [ ] Tests added (if needed)
- [ ] Linter passes

## Checklist (Claude Review)
- [ ] Security OK
- [ ] No Bugs Found
- [ ] Code Quality OK
- [ ] Architecture OK

## Test Plan
<!-- How was this tested? -->

## Related Issues
<!-- Closes #123 -->

---
Generated with [Claude Code](https://claude.ai/code)"

# Create PR
gh pr create --title "$TITLE" --body "$BODY"

# Enable auto-merge if configured
if [ "$AUTO_MERGE" = "true" ]; then
  PR_NUM=$(gh pr view --json number -q .number)
  gh pr merge "$PR_NUM" --auto --$MERGE_METHOD
  echo "Auto-merge enabled ($MERGE_METHOD)"
fi
```

---

## /dk git pr review

Check PR review status (traffic light system):

```bash
PR_NUM=${1:-$(gh pr view --json number -q .number)}
gh pr checks $PR_NUM
```

- 🟢 **APPROVE** = Ready to merge
- 🟠 **APPROVE with suggestions** = Blocked
- 🔴 **REQUEST_CHANGES** = Blocked

---

## /dk git pr merge

Merge PR using config settings:

```bash
PR_NUM=${1:-$(gh pr view --json number -q .number)}

# Read PR config
CONFIG_FILE=".claude/.devkit/config.jsonc"
DELETE_BRANCH=$(jq -r '.github.pr.delete_branch // true' "$CONFIG_FILE" 2>/dev/null || echo "true")
MERGE_METHOD=$(jq -r '.github.pr.merge_method // "squash"' "$CONFIG_FILE" 2>/dev/null || echo "squash")

# Build merge command
MERGE_ARGS="--$MERGE_METHOD"
[ "$DELETE_BRANCH" = "true" ] && MERGE_ARGS="$MERGE_ARGS --delete-branch"

gh pr merge "$PR_NUM" $MERGE_ARGS
git checkout main && git pull
```

---

## /dk git branch

Create feature branch:

```bash
git checkout -b "feat/${1}"
```

---

## /dk git squash

Squash all commits on current branch:

```bash
COUNT=$(git rev-list --count main..HEAD)
MSG=$(git log -1 --format=%s)
git reset --soft main
git commit -m "$MSG"
```

---

## /dk git cleanup

Clean local git state:

1. Fetch and prune: `git fetch --prune origin`
2. Delete orphaned tags (local tags not on remote)
3. Delete merged branches (except main)

---

## /dk git issue

Issue management commands:

```bash
# report - bug in devkit-plugin
gh issue create --repo "andreschmidt/devkit-plugin" --title "$TITLE" --label "bug"

# create - issue in current project
gh issue create --title "$TITLE" --label "$TYPE"

# list - open issues
gh issue list --state open

# view - issue details
gh issue view "$NUM"
```
