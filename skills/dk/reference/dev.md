# /dk dev

**CRITICAL:** Development workflow commands. YOU MUST use these for ALL code changes.

## Why Use /dk dev?

**ALWAYS use `/dk dev` instead of directly entering Plan Mode!**

| Direct Plan Mode                  | `/dk dev` Workflow                      |
| --------------------------------- | --------------------------------------- |
| ❌ Might be on protected branch   | ✓ Creates feature branch automatically  |
| ❌ No git conventions enforced    | ✓ Branch name follows `{type}/{desc}`   |
| ❌ Easy to forget proper workflow | ✓ Guides through Explore → Plan → Build |
| ❌ Hooks only warn                | ✓ Proper workflow from the start        |

**If you're on `main` and enter Plan Mode, the hook will warn you to use `/dk dev` first.**

## Commands

| Command                   | Type     | Description        | Plan Mode? |
| ------------------------- | -------- | ------------------ | ---------- |
| `/dk dev feat <desc>`     | feat     | New feature        | YES        |
| `/dk dev fix <desc>`      | fix      | Bug fix            | Optional   |
| `/dk dev chore <desc>`    | chore    | Maintenance        | No         |
| `/dk dev refactor <desc>` | refactor | Restructure code   | YES        |
| `/dk dev test <desc>`     | test     | Add/improve tests  | No         |
| `/dk dev docs <desc>`     | docs     | Documentation      | No         |
| `/dk dev quick <desc>`    | chore    | Quick small change | No         |

---

## Workflow Overview

**YOU MUST follow this workflow for ALL code changes:**

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  1. Explore │ ──▶ │  2. Plan    │ ──▶ │  3. Build   │
│  (Context)  │     │  (Design)   │     │  (Implement)│
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │
      ▼                   ▼                   ▼
   Read files        Plan Mode           Code + Test
   Understand        (for feat/         Commit
   architecture      refactor)          Run checks
```

---

## Type-Specific Workflows

### `/dk dev feat <description>` - New Feature

**REQUIRES Plan Mode - YOU MUST call EnterPlanMode before coding.**

#### Step 1: Create Branch

```bash
git checkout -b feat/{short-name}
```

#### Step 2: Explore (Quick Context)

- Read `CLAUDE.md` for project rules
- Use Explore agent to understand affected areas
- Identify related files and patterns

#### Step 3: Enter Plan Mode (REQUIRED)

**YOU MUST call the `EnterPlanMode` tool now.** This ensures:

- User reviews the plan before any code is written
- Architecture decisions are documented
- Edge cases are considered upfront

In Plan Mode, write a plan that includes:

- **Goal**: What the feature does
- **Files**: Which files to create/modify
- **Approach**: How to implement it
- **Tests**: What tests to add
- **Edge Cases**: Error handling, validation

#### Step 4: Build (After Plan Approval)

- Implement in small, testable units
- Write tests alongside code
- Commit after each logical unit
- Run `/dk plugin check` before PR

**Example:**

```
/dk dev feat add user preferences page
```

---

### `/dk dev fix <description>` - Bug Fix

**Plan Mode optional - use for complex bugs affecting multiple files.**

#### Step 1: Create Branch

```bash
git checkout -b fix/{short-name}
```

#### Step 2: Investigate

- Reproduce the bug
- Read error logs/stack traces
- Identify root cause

#### Step 3: Plan Mode (If Complex)

**Call `EnterPlanMode` if the bug:**

- Affects multiple files
- Has unclear root cause
- Requires architectural changes
- Could have side effects

Skip Plan Mode for simple, isolated fixes.

#### Step 4: Fix

- Apply minimal fix
- Add regression test
- Run tests to verify

#### Step 5: Verify

- Confirm bug is fixed
- Check for side effects
- Run `/dk plugin check` before PR

**Example:**

```
/dk dev fix timeout in API calls not being handled
```

---

### `/dk dev refactor <description>` - Code Restructuring

**REQUIRES Plan Mode - YOU MUST call EnterPlanMode before refactoring.**

#### Step 1: Create Branch

```bash
git checkout -b refactor/{short-name}
```

#### Step 2: Analyze

- Run `/dk analyze quick` to identify issues
- Map dependencies with `/dk arch analyze`
- Understand current architecture

#### Step 3: Enter Plan Mode (REQUIRED)

**YOU MUST call the `EnterPlanMode` tool now.** This ensures:

- Refactoring steps are reviewed before changes
- Breaking changes are identified upfront
- Migration path is clear

In Plan Mode, write a plan that includes:

- **Current State**: What exists now
- **Target State**: What it should look like
- **Migration Steps**: Order of changes
- **Breaking Changes**: What might break
- **Verification**: How to confirm success

#### Step 4: Execute (After Plan Approval)

- Refactor in small steps
- Keep tests green throughout
- Commit after each step
- Run `/dk plugin check` before PR

**Example:**

```
/dk dev refactor extract API client into separate module
```

---

### `/dk dev chore <description>` - Maintenance

**No Plan Mode needed - straightforward tasks.**

1. **Execute**
   - Create branch: `git checkout -b chore/{short-name}`
   - Make changes
   - Verify nothing breaks

**Examples:**

- Update dependencies
- Clean up unused files
- Update CI configuration

```
/dk dev chore update pytest to 8.x
```

---

### `/dk dev test <description>` - Testing

**No Plan Mode needed.**

1. **Identify gaps**
   - Run coverage report
   - Find untested code paths

2. **Write tests**
   - Create branch: `git checkout -b test/{short-name}`
   - Add unit/integration tests
   - Ensure tests are meaningful

**Example:**

```
/dk dev test add tests for webhook handler
```

---

### `/dk dev docs <description>` - Documentation

**No Plan Mode needed.**

1. **Execute**
   - Create branch: `git checkout -b docs/{short-name}`
   - Update/create documentation
   - Verify links work

**Example:**

```
/dk dev docs update API documentation
```

---

### `/dk dev quick <description>` - Quick Small Change

**For tiny changes that don't warrant full workflow.**

Use this for:

- Single-line fixes
- Typo corrections
- Config tweaks
- Adding a log statement

**NOT for:**

- New features (use `feat`)
- Bug fixes (use `fix`)
- Multiple file changes (use appropriate type)

1. **Execute**
   - Create branch: `git checkout -b chore/{short-name}`
   - Make the small change
   - Commit immediately
   - Create PR with `/dk git pr`

**Example:**

```
/dk dev quick fix typo in error message
/dk dev quick add debug log to auth handler
```

---

## Rules (MANDATORY)

**YOU MUST follow these rules - NO EXCEPTIONS:**

- **ALWAYS** read `CLAUDE.md` before coding
- **ALWAYS** use `TodoWrite` to track progress
- **ALWAYS** commit after each logical unit
- **NEVER** create PRs with >20 files or >500 lines
- **ALWAYS** run tests before committing
- **ALWAYS** run linter after changes

---

## Commit Format

**YOU MUST use Conventional Commits**: `type(scope): message`

```bash
git commit -m "$(cat <<'EOF'
type(scope): description

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

**ALLOWED types:** `feat`, `fix`, `chore`, `refactor`, `test`, `docs`, `perf`, `ci`

**Scope is optional** but if used, must be from allowed list in config.

**NEVER** use other commit types. **NEVER** skip the Co-Authored-By line.

---

## Integration with /dk analyze

For large tasks or quality improvements:

1. **Run full analysis first:**

   ```
   /dk analyze
   ```

   Creates a comprehensive plan with all issues.

2. **Fix issues by priority:**

   ```
   /dk analyze fix
   ```

   Continues fixing from the existing plan.

3. **Quick check before PR:**
   ```
   /dk analyze quick
   ```
   Fast single-agent check for critical issues.

---

## Pre-Commit Checklist

Before committing, verify:

```bash
# Run tests
uv run pytest tests/ -v

# Run linter
uv run ruff check src/

# Check plugin consistency
/dk plugin check
```

---

## Documentation Resources

**ALWAYS use these resources:**

- Claude Code questions → **ALWAYS** use `claude-code-guide` agent
- Library docs → **ALWAYS** use Context7 MCP tools

---

## Consistency Checklist

**After creating new files, verify these artifacts exist:**

- [ ] **Tests**: New modules in `src/` need test files in `tests/test_{module}.py`
- [ ] **Handlers**: Enabled hooks need handler files in `src/events/`
- [ ] **Docs**: New skills need reference docs in `skills/dk/reference/`

**Run `/dk plugin check` to verify all consistency rules.**

---

## IMPORTANT Reminders

1. **NEVER** use raw `gh pr create` - **ALWAYS** use `/dk git pr`
2. **NEVER** skip tests - **ALWAYS** run `uv run pytest` before committing
3. **NEVER** skip linting - **ALWAYS** run `uv run ruff check` after changes
4. **ALWAYS** run `/dk plugin check` before creating a PR
5. **For large tasks** - Consider `/dk analyze` first to plan systematically
