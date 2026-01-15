# devkit-plugin - Plugin Internals

> Auto-generated documentation. Do not edit manually.

## Overview

Claude Code plugin for python projects.

## Architecture

Clean Architecture with dependency rule: higher tiers import from lower only.

```
src/core/  (TIER 0)
src/lib/  (TIER 1)
src/arch/  (TIER 2)
src/events/  (TIER 3)
```

| Layer | Tier | Responsibility |
|-------|------|----------------|
| core | 0 | Pure functions, no I/O |
| lib | 1 | I/O adapters (config, git, tools) |
| arch | 2 | Architecture analysis |
| events | 3 | Claude Code hook handlers |

## Events (Hooks)

| Event | Handler | Action |
|-------|---------|--------|
| SessionStart | session.py | Show git status, load config |
| PreToolUse | validate.py | Block force push, validate commits |
| PostToolUse | format.py | Auto-format edited files |
| ExitPlanMode | plan.py | Inject development instructions |

## Configuration

Location: `.claude/.devkit/config.json`

### Project

| Field | Description |
|-------|-------------|
| `project.name` | Project name |
| `project.type` | python, nextjs, typescript, javascript |
| `project.slogan` | Tagline for docs |
| `project.description` | Brief description |
| `project.principles` | Array of principles |

### Git Conventions

| Field | Description |
|-------|-------------|
| `git.protected_branches` | Branches protected from force push |
| `git.conventions.types` | Allowed commit types |
| `git.conventions.scopes.mode` | strict, warn, or off |
| `git.conventions.scopes.allowed` | Allowed scope names |
| `git.conventions.scopes.internal` | Scopes that skip release notes |

### Architecture

| Field | Description |
|-------|-------------|
| `arch.layers.<name>.tier` | Layer tier (0=innermost) |

### Managed Files

| Field | Description |
|-------|-------------|
| `managed.linters` | Linter config files |
| `managed.github` | Workflows, issue templates |
| `managed.docs` | Documentation files |
| `managed.ignore` | Ignore files |

## Skills

All commands via `/dk <module>`. See `/dk` for full list.

| Module | Purpose |
|--------|---------|
| dev | Feature development workflow |
| git | PR, branch, issue management |
| arch | Layer analysis, scaffolding |
| docs | Documentation generation |
| env | Environment variable sync |
| vercel | Deployment |
| neon | Database branch management |