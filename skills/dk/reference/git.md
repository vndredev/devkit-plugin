# /dk git

**CRITICAL:** Git workflow commands with Conventional Commits.

## When to Use /dk git vs /dk dev

| Scenario                      | Use                               |
| ----------------------------- | --------------------------------- |
| Starting new code work        | `/dk dev feat\|fix\|chore <desc>` |
| Creating PR after code done   | `/dk git pr`                      |
| Just git operations (no code) | `/dk git branch\|squash\|cleanup` |

**Rule:** Use `/dk dev` to START work, use `/dk git` for git operations AFTER coding.

## MANDATORY Rules

**YOU MUST follow these rules - NO EXCEPTIONS:**

1. **ALWAYS** use `/dk git pr` for pull requests - **NEVER** use raw `gh pr create`
2. **ALWAYS** use `/dk git branch` for branches - **NEVER** create branches manually
3. **ALWAYS** use conventional commits: `type(scope): message`
4. **NEVER** force push to protected branches
5. **NEVER** execute raw `gh` commands when `/dk git` equivalents exist

## Commands

| Command             | Description                                   |
| ------------------- | --------------------------------------------- |
| `/dk git init`      | Initialize new project (git, config, files)   |
| `/dk git update`    | Sync managed files and GitHub settings        |
| `/dk git pr`        | Create pull request (**USE THIS, NOT gh**)    |
| `/dk git pr review` | Check PR review status                        |
| `/dk git pr merge`  | Merge PR (squash)                             |
| `/dk git branch`    | Create feature branch                         |
| `/dk git squash`    | Squash commits on branch                      |
| `/dk git cleanup`   | Clean local tags + branches                   |
| `/dk git issue`     | Issue management (report, create, list, view) |

---

## Commit Format

**YOU MUST use Conventional Commits**: `type(scope): message`

| Type       | Description   |
| ---------- | ------------- |
| `feat`     | New feature   |
| `fix`      | Bug fix       |
| `docs`     | Documentation |
| `chore`    | Maintenance   |
| `refactor` | Restructure   |
| `test`     | Tests         |
| `perf`     | Performance   |
| `ci`       | CI/CD         |

### Internal Scopes (skip release notes)

| Scope      | Use Case             |
| ---------- | -------------------- |
| `internal` | Internal refactoring |
| `review`   | Code review fixes    |
| `ci`       | CI/CD changes        |
| `deps`     | Dependency updates   |

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
7. (Optional) Setup branch protection ruleset

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

## Branch Protection

Branch protection is automatically configured during `/dk git init` based on your GitHub plan:

| Repo Type | Plan            | Bypass Actors | Solution                      |
| --------- | --------------- | ------------- | ----------------------------- |
| User      | Free            | ❌ No         | Warning: RELEASE_PAT required |
| User      | Pro             | ✅ Yes        | Ruleset with admin bypass     |
| Org       | Free            | ⚠️ Limited    | Warning about limitations     |
| Org       | Team/Enterprise | ✅ Yes        | Ruleset with admin bypass     |

**Config options** (in `config.jsonc`):

```jsonc
"github": {
  "protection": {
    "enabled": true,           // Enable branch protection
    "require_reviews": 1,      // Required PR reviews (0 to disable)
    "linear_history": true,    // Require linear commit history
    "admin_bypass": true,      // Allow admins to bypass (requires Pro/Team+)
    "dismiss_stale_reviews": false
  }
}
```

**What gets created:**

- Ruleset named `devkit-protection` on `main` branch
- Linear history requirement (no merge commits)
- Required PR reviews (configurable)
- Admin bypass (if plan supports it)

**If you're on Free plan:**

You need a `RELEASE_PAT` secret for automated releases:

```bash
# Create a fine-grained PAT at https://github.com/settings/tokens
# Then add it as a secret:
gh secret set RELEASE_PAT
```

---

## /dk git pr

**CRITICAL: YOU MUST use this command for ALL pull requests.**

**NEVER use raw `gh pr create` - ALWAYS use `/dk git pr`.**

This command creates a PR with the proper template and configuration.

**Reads config from `.claude/.devkit/config.jsonc`:**

- `github.pr.auto_merge` - Enable auto-merge (default: false)
- `github.pr.delete_branch` - Delete branch after merge (default: true)
- `github.pr.merge_method` - squash/merge/rebase (default: squash)

### Workflow Steps

**YOU MUST execute ALL steps in order - DO NOT skip any step:**

1. **Push branch** to remote
2. **Read config** for auto_merge, delete_branch, merge_method
3. **Create PR** with template body
4. **Enable auto-merge** if `auto_merge: true` in config - **YOU MUST NOT SKIP THIS**
5. **Return to main** and pull latest

### Commands

**YOU MUST run these commands in sequence:**

```bash
# Step 1: Push branch
BRANCH=$(git branch --show-current)
git push -u origin "$BRANCH"

# Step 2: Get commit info
TITLE=$(git log -1 --format=%s)
COMMITS=$(git log main..$BRANCH --format='- %s' | head -10)

# Step 3: Read PR config (use lib.config for JSONC support)
read AUTO_MERGE DELETE_BRANCH MERGE_METHOD <<< $(PYTHONPATH=${PLUGIN_ROOT}/src python3 -c "
from lib.config import get
print(str(get('github.pr.auto_merge', False)).lower(), str(get('github.pr.delete_branch', True)).lower(), get('github.pr.merge_method', 'squash'))
" 2>/dev/null || echo "false true squash")

# Step 4: Determine change type from first commit
TYPE=$(echo "$TITLE" | grep -oE '^(feat|fix|docs|chore|refactor|test|ci)' || echo "chore")

# Map type to checkbox
case "$TYPE" in
  feat)     CHECKBOX="- [x] Feature - New functionality" ;;
  fix)      CHECKBOX="- [x] Bug Fix - Fix for existing issue" ;;
  refactor) CHECKBOX="- [x] Refactor - Code restructuring" ;;
  docs)     CHECKBOX="- [x] Docs - Documentation only" ;;
  *)        CHECKBOX="- [x] Chore - Maintenance/tooling" ;;
esac

# Step 5: Build PR body from template structure
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

# Step 6: Create PR
gh pr create --title "$TITLE" --body "$BODY"
```

**CRITICAL - YOU MUST execute this auto-merge step if AUTO_MERGE is true:**

```bash
# Step 7: Enable auto-merge if configured - DO NOT SKIP
if [ "$AUTO_MERGE" = "true" ]; then
  PR_NUM=$(gh pr view --json number -q .number)
  gh pr merge "$PR_NUM" --auto --$MERGE_METHOD
  echo "✓ Auto-merge enabled ($MERGE_METHOD)"
fi
```

**CRITICAL - YOU MUST return to main after PR creation:**

```bash
# Step 8: Return to main and pull to stay in sync
echo ""
echo "Returning to main branch..."
git checkout main && git pull
echo "✅ Ready for next task - run /dk dev to start"
```

### Post-PR Verification

**YOU MUST verify these after PR creation:**

- [ ] PR URL is shown to user
- [ ] Auto-merge enabled (if configured) - check for "✓ Auto-merge enabled" message
- [ ] Returned to `main` branch
- [ ] `main` is up to date with remote

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

# Read PR config (use lib.config for JSONC support)
read DELETE_BRANCH MERGE_METHOD <<< $(PYTHONPATH=${PLUGIN_ROOT}/src python3 -c "
from lib.config import get
print(str(get('github.pr.delete_branch', True)).lower(), get('github.pr.merge_method', 'squash'))
" 2>/dev/null || echo "true squash")

# Build merge command with separate flags
DELETE_FLAG=""
[ "$DELETE_BRANCH" = "true" ] && DELETE_FLAG="--delete-branch"

gh pr merge "$PR_NUM" "--$MERGE_METHOD" $DELETE_FLAG
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

> **WARNING:** This command rewrites history. Only use on branches that have NOT been pushed, or force-push will be required. Data may be lost if uncommitted changes exist.

```bash
COUNT=$(git rev-list --count main..HEAD)
MSG=$(git log -1 --format=%s)
# Ensure no uncommitted changes
git diff --quiet || { echo "Error: uncommitted changes"; exit 1; }
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
gh issue create --repo "vndredev/devkit-plugin" --title "$TITLE" --label "bug"

# create - issue in current project
gh issue create --title "$TITLE" --label "$TYPE"

# list - open issues
gh issue list --state open

# view - issue details
gh issue view "$NUM"
```
