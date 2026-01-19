# /dk analyze

**CRITICAL:** Deep codebase analysis using parallel Opus agents.

**YOU MUST use this for comprehensive code quality analysis.**

## Pre-Condition: Feature Branch

**CRITICAL: Before running `/dk analyze`, verify you're on a feature branch!**

```bash
# Check current branch
BRANCH=$(git branch --show-current)
PROTECTED_BRANCHES="main master"

for protected in $PROTECTED_BRANCHES; do
    if [ "$BRANCH" = "$protected" ]; then
        echo "⚠️ You're on '$BRANCH' - use '/dk dev feat|fix|chore <desc>' first!"
        exit 1
    fi
done
echo "✓ On feature branch: $BRANCH"
```

If on a protected branch, **YOU MUST** redirect to `/dk dev` workflow first.

## Commands

| Command             | Action                                    |
| ------------------- | ----------------------------------------- |
| `/dk analyze`       | Full analysis with plan creation          |
| `/dk analyze quick` | Quick analysis (single agent, key areas)  |
| `/dk analyze fix`   | Continue fixing issues from existing plan |

---

## /dk analyze - Full Analysis

Runs comprehensive analysis using **parallel Opus agents** across all code areas.

### Phase 1: Detect Analysis Areas

**CRITICAL: Areas are derived dynamically from project config or structure.**

#### Option A: Use arch.layers from config (if defined)

```bash
# Check if arch.layers is defined in config
CONFIG_FILE=".claude/.devkit/config.jsonc"
if [ -f "$CONFIG_FILE" ]; then
    LAYERS=$(jq -r '.arch.layers // empty' "$CONFIG_FILE" 2>/dev/null)
fi
```

If `arch.layers` exists, create one agent per layer:

```
Example for project with 4 layers:
Agent 1: core (tier 0) - patterns: src/core/**
Agent 2: lib (tier 1) - patterns: src/lib/**
Agent 3: arch (tier 2) - patterns: src/arch/**
Agent 4: events (tier 3) - patterns: src/events/**
```

#### Option B: Auto-detect from project structure

If no `arch.layers` defined, detect areas from directory structure:

**Python projects** (pyproject.toml exists):

```
Agent 1: src/ or main package directory
Agent 2: tests/
Agent 3: Config files (pyproject.toml, setup.py, etc.)
```

**Node projects** (package.json exists):

```
Agent 1: src/ or lib/
Agent 2: tests/ or __tests__/
Agent 3: Config files (package.json, tsconfig.json, etc.)
```

**Always add these cross-cutting agents:**

```
Agent N-1: Config & Schema (config files, JSON schemas)
Agent N:   Tests (test coverage, missing tests)
```

### Phase 2: Launch Parallel Agents

Launch Opus agents for each detected area:

```python
# Example Task tool configuration
# CRITICAL: Use general-purpose (not Explore) to enable opus model
Task(
    subagent_type="general-purpose",
    model="opus",
    prompt=ANALYSIS_PROMPT.format(area=area, patterns=patterns),
    description=f"Analyze {area}"
)
```

**Analysis prompt template:**

```
Analyze ${AREA} (files matching: ${PATTERNS}) for issues.

## CRITICAL: Verify Before Reporting

Before reporting ANY issue, you MUST:
1. Check if it's INTENTIONAL (look for comments like "intentionally", "by design", "TODO")
2. Check if error handling exists ELSEWHERE (caller, wrapper, middleware)
3. Check if it's a KNOWN PATTERN in this codebase (look at similar code)
4. Check if the "missing" thing is actually UNNECESSARY in this context

ONLY report issues where you are 90%+ confident it's a REAL bug.

## What NOT to Report (Common False Positives)

- Missing timeout on quick local operations
- Broad except blocks that log or re-raise appropriately
- "Unsafe" patterns that are safe in their specific context
- Room/session passwords that don't need hashing (not user credentials)
- Missing validation when input comes from trusted internal source
- "Could be improved" suggestions - only report actual bugs

## Report Format

## ${AREA} Analysis

### CRITICAL (blocks functionality - 95%+ confidence)
- [file:line] Issue + WHY you're confident this is real

### HIGH (causes bugs or security - 90%+ confidence)
- [file:line] Issue + WHY you're confident this is real

### MEDIUM (likely bugs - 85%+ confidence)
- [file:line] Issue + evidence from code

(Skip LOW - too many false positives)

Focus ONLY on:
1. Unhandled exceptions that WILL crash (not might crash)
2. Security issues with ACTUAL exploit path
3. Logic errors that produce WRONG results
4. Race conditions with REAL impact
```

### Phase 3: Consolidate & Create Plan

After all agents complete, consolidate findings into a plan file:

**Plan file location:** `~/.claude/plans/{project-name}-analysis.md`

**Plan structure:**

```markdown
# Codebase Analysis: {project-name}

**Date:** {date}
**Version:** {version from config or package}
**Agents:** {N} parallel Opus agents

## Summary

| Severity  | Count |
| --------- | ----- |
| CRITICAL  | X     |
| HIGH      | X     |
| MEDIUM    | X     |
| LOW       | X     |
| **Total** | X     |

---

## CRITICAL Issues (Fix Immediately)

### 1. {Issue Title}

**File:** `path/to/file:123`
**Problem:** Description
**Fix:** Solution approach

---

## HIGH Priority Issues

### 1. {Issue Title}

...

---

## MEDIUM Priority Issues

...

---

## LOW Priority Issues

...

---

## Implementation Order

### Phase 1: CRITICAL (Blocking)

1. [ ] Fix {issue}
2. [ ] Fix {issue}

### Phase 2: HIGH (Important)

1. [ ] Fix {issue}

### Phase 3: MEDIUM + LOW (Quality)

1. [ ] Fix {issue}
```

### Phase 4: Execute Fixes

Work through issues in priority order:

1. **CRITICAL first** - These block functionality
2. **HIGH second** - These cause bugs or security issues
3. **MEDIUM + LOW last** - Code quality improvements

**For each fix:**

1. Mark todo as in_progress
2. Read the affected file
3. Implement the fix
4. Run tests to verify
5. Mark todo as completed

---

## /dk analyze quick

Quick single-agent analysis for key areas only:

```
Analyze this codebase for the most critical issues:

1. Unhandled exceptions in subprocess/async calls
2. Missing error handling in I/O operations
3. Security vulnerabilities
4. Missing tests for public functions

Report top 10 issues by severity.
```

---

## /dk analyze fix

Continue fixing issues from an existing analysis plan:

1. Read the plan file from `~/.claude/plans/`
2. Find uncompleted todos
3. Resume fixing from where you left off

---

## Agent Configuration

**Model:** `opus` (required for deep analysis)
**Parallelism:** One agent per detected area
**Thoroughness:** `very thorough`

**Task tool configuration:**

```python
# CRITICAL: Use general-purpose (not Explore) to enable opus model
Task(
    subagent_type="general-purpose",
    model="opus",
    prompt="...",
    description="Analyze {area}"
)
```

---

## Cross-Check Phase

After individual analysis, run cross-checks based on project config:

| Check              | When to Run                       |
| ------------------ | --------------------------------- |
| Layer Violations   | If `arch.layers` defined          |
| Config-Schema Sync | If schema files exist             |
| Hook Integration   | If `hooks` section in config      |
| Test Coverage      | If `testing.enabled` is true      |
| Consistency Rules  | If `consistency.enabled` is true  |
| Version Sync       | If multiple version sources exist |

---

## Output Example

```
=== Opus Deep Analysis ===

Detecting analysis areas...
  Found arch.layers: core, lib, arch, events
  Adding: config, tests

Launching 6 parallel agents...
  [1/6] core: analyzing src/core/**
  [2/6] lib: analyzing src/lib/**
  [3/6] arch: analyzing src/arch/**
  [4/6] events: analyzing src/events/**
  [5/6] config: analyzing config files
  [6/6] tests: analyzing test coverage

All agents completed.

=== Consolidating Results ===

| Severity | Count |
|----------|-------|
| CRITICAL | 5     |
| HIGH     | 12    |
| MEDIUM   | 23    |
| LOW      | 18    |
| **Total**| 58    |

Plan created: ~/.claude/plans/{project}-analysis.md

=== Ready to Fix ===

Start with CRITICAL issues? [Y/n]
```

---

## Notes

- **Always use Opus model** for deep analysis (better reasoning)
- **Run in parallel** to reduce total analysis time
- **Create plan file** before starting fixes
- **Track progress** with TodoWrite tool
- **Commit after each phase** (CRITICAL, HIGH, MEDIUM/LOW)
- **Areas are dynamic** - derived from config or project structure

---

## /dk analyze system

**System-wide audit checking plugin configuration, sync status, and consistency.**

| Command                    | Action                              |
| -------------------------- | ----------------------------------- |
| `/dk analyze system`       | Full system audit                   |
| `/dk analyze system quick` | Quick consistency check (core only) |

### Core Files (ALWAYS Checked)

These 3 files form the foundation of every devkit-plugin project:

```
1. .claude/.devkit/config.jsonc  → Single Source of Truth
2. CLAUDE.md                      → Project Documentation (AUTO:START/END)
3. docs/ARCHITECTURE.md           → Layer Documentation (if arch.layers)
```

### Phase 1: Core Validation

**Always runs regardless of config:**

```python
# Core checks (always run):
checks = [
    ("Config Schema", "config.jsonc validates against schema"),
    ("Required Fields", "project.name, project.type present"),
    ("CLAUDE.md Sync", "AUTO sections match config"),
]
```

### Phase 2: Dynamic Checks (Based on Config)

**Checks are enabled dynamically based on what's configured:**

```python
# Example: Dynamically determine which checks to run
if get("arch.layers"):
    checks.append(("Architecture Compliance", "imports respect layer tiers"))
    checks.append(("ARCHITECTURE.md Sync", "docs match config"))

if get("consistency.rules"):
    for rule_name, rule_config in get("consistency.rules").items():
        if rule_config.get("enabled"):
            checks.append((f"Consistency: {rule_name}", "rule validation"))

if get("hooks"):
    checks.append(("Hook Handlers", "enabled hooks have handler files"))

if get("managed"):
    checks.append(("Managed Files", "templates in sync"))

if get("git.conventions"):
    checks.append(("Git Conventions", "types/scopes valid"))
```

### Phase 3: Run Plugin Health Check

**Uses existing infrastructure:**

```bash
PYTHONPATH=${PLUGIN_ROOT}/src uv run python -c "
from arch.check import check_all, format_report
results = check_all()
print(format_report(results))
"
```

### Output Format

```
=== System Audit ===

── Core Files ──────────────────────
✓ config.jsonc valid
✓ CLAUDE.md AUTO sections in sync
✓ docs/ARCHITECTURE.md in sync

── Dynamic Checks ──────────────────
✓ Architecture: 4 layers, no violations
✓ Consistency: 4/4 rules pass
✓ Hooks: 4/4 handlers present
✓ Managed: 12/12 files in sync
✓ Git: conventions valid

── Versions ────────────────────────
✓ All in sync: 0.26.0
  (plugin.json, pyproject.toml, config.jsonc)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: HEALTHY

=== System Audit Complete ===
```

### Issue Format

When issues are found:

```
=== System Audit ===

── Core Files ──────────────────────
✓ config.jsonc valid
✗ CLAUDE.md AUTO sections outdated
  → Run: /dk plugin update

── Dynamic Checks ──────────────────
✗ Architecture: 2 layer violations
  - events imports from core (tier 3 → tier 0)
  - lib imports from arch (tier 1 → tier 2)
✓ Consistency: 4/4 rules pass
✗ Managed: 2/12 files outdated
  - .github/workflows/release.yml
  - ruff.toml

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: 4 issues found
Action: /dk plugin update

=== Recommended Fixes ===

1. Run `/dk plugin update` to sync files
2. Fix layer violations in:
   - src/events/format.py:12
   - src/lib/sync.py:45
```

### Quick Mode

`/dk analyze system quick` runs only core checks:

```python
# Quick mode - core checks only
checks = [
    "Config Schema",
    "CLAUDE.md Sync",
    "Version Sync",
]
# Skip: Architecture, Consistency, Managed Files
```

### Key Principle: Config-Driven

**NO hardcoded paths!** All checks derive from config:

```python
# WRONG (hardcoded):
check_file("src/events/validate.py")

# RIGHT (from config):
for layer_name, layer_config in get("arch.layers", {}).items():
    for pattern in layer_config.get("patterns", []):
        check_files_matching(pattern)
```

### Integration with /dk plugin check

`/dk analyze system` is complementary to `/dk plugin check`:

| Command              | Focus                           | Output        |
| -------------------- | ------------------------------- | ------------- |
| `/dk plugin check`   | Plugin health status            | Quick summary |
| `/dk analyze system` | Deep audit with recommendations | Full report   |

Both use the same underlying `check_all()` function but with different verbosity.
