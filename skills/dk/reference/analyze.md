# /dk analyze

**CRITICAL:** Deep codebase analysis using parallel Opus agents.

**YOU MUST use this for comprehensive code quality analysis.**

## Commands

| Command             | Action                                    |
| ------------------- | ----------------------------------------- |
| `/dk analyze`       | Full analysis with plan creation          |
| `/dk analyze quick` | Quick analysis (single agent, key areas)  |
| `/dk analyze fix`   | Continue fixing issues from existing plan |

---

## /dk analyze - Full Analysis

Runs comprehensive analysis using **parallel Opus agents** across all code areas.

### Phase 1: Parallel Agent Analysis

Launch 6-8 Opus agents simultaneously to analyze different areas:

```
Agent 1: Core Layer (types, errors, constants)
Agent 2: Lib Layer Part 1 (config, git, sync)
Agent 3: Lib Layer Part 2 (github, vercel, tools, webhooks)
Agent 4: Arch Layer (analyze, check, rules, consistency)
Agent 5: Events Layer (hooks, handlers)
Agent 6: Config & Schema (config.jsonc, schema, templates)
Agent 7: Skills & Docs (skill files, documentation)
Agent 8: Tests (test coverage, missing tests)
```

**Each agent receives this prompt:**

```
Analyze ${AREA} for issues. Report findings in this format:

## ${AREA} Analysis

### CRITICAL (blocks functionality)
- [file:line] Issue description

### HIGH (causes bugs or security issues)
- [file:line] Issue description

### MEDIUM (code quality, maintainability)
- [file:line] Issue description

### LOW (style, minor improvements)
- [file:line] Issue description

Focus on:
1. Unhandled exceptions (TimeoutExpired, OSError, etc.)
2. Missing error handling
3. Edge cases not covered
4. Missing tests for critical functions
5. Security issues (injection, path traversal)
6. Inconsistencies with documentation
7. Dead code or unused imports
```

### Phase 2: Consolidate & Create Plan

After all agents complete, consolidate findings into a plan file:

**Plan file location:** `~/.claude/plans/{project-name}-analysis.md`

**Plan structure:**

```markdown
# Codebase Analysis: {project-name}

**Date:** {date}
**Version:** {version}
**Agents:** 8 parallel Opus agents

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

**File:** `path/to/file.py:123`
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

### Phase 3: Execute Fixes

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

```bash
# Quick analysis prompt
Analyze this codebase for the most critical issues:

1. Unhandled exceptions in subprocess calls
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
**Parallelism:** 6-8 agents simultaneously
**Thoroughness:** `very thorough`

**Task tool configuration:**

```python
Task(
    subagent_type="Explore",
    model="opus",
    prompt="...",
    description="Analyze {area}"
)
```

---

## Cross-Check Phase

After individual analysis, run cross-checks:

| Check               | Description                             |
| ------------------- | --------------------------------------- |
| Hook Integration    | Verify all hooks are properly connected |
| Config-Schema Sync  | Verify schema matches config structure  |
| Import Dependencies | Check for layer violations              |
| Template Sync       | Verify templates match implementations  |
| Skill Integration   | Verify skill routes match handlers      |
| Version Sync        | Verify all version files match          |

---

## Output Example

```
=== Opus Deep Analysis ===

Launching 8 parallel agents...
  [1/8] Core Layer: analyzing...
  [2/8] Lib Layer Part 1: analyzing...
  [3/8] Lib Layer Part 2: analyzing...
  [4/8] Arch Layer: analyzing...
  [5/8] Events Layer: analyzing...
  [6/8] Config & Schema: analyzing...
  [7/8] Skills & Docs: analyzing...
  [8/8] Tests: analyzing...

All agents completed.

=== Consolidating Results ===

| Severity | Count |
|----------|-------|
| CRITICAL | 5     |
| HIGH     | 12    |
| MEDIUM   | 23    |
| LOW      | 18    |
| **Total**| 58    |

Plan created: ~/.claude/plans/devkit-plugin-analysis.md

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
