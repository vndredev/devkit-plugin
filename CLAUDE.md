# devkit-plugin

> *Busting Claude's balls - so you don't have to*

Claude Code Plugin für automatisierte Dev-Workflows. PR-Workflows mit GitHub Integration, Linter-Sync (ruff, ESLint, markdownlint), und Environment Management.

## Principles

- **KISS**: Keep it simple - no complexity without reason
- **YAGNI**: No maybe-later - only what's needed now
- **SOLID**: Single responsibility - one task per file
- **DRY**: Don't repeat - shared code in utils
- **CoC**: Convention over config - sensible defaults
- **PoLA**: No magic - predictable behavior
- **DOCS**: Docstrings/JSDoc for all functions - never remove

## Commands

All commands use the `/dk` prefix to avoid conflicts with native Claude CLI commands.

| Command | Description |
| ------- | ----------- |
| `/dk` | Show status and available commands |
| `/dk plugin` | Quick plugin status |
| `/dk plugin check` | Full health check |
| `/dk plugin update` | Sync all managed files |
| `/dk plugin init` | Initialize new project |
| `/dk dev feat <desc>` | Develop new feature |
| `/dk dev fix <desc>` | Fix a bug |
| `/dk dev chore <desc>` | Maintenance task |
| `/dk dev refactor <desc>` | Code refactoring |
| `/dk dev test <desc>` | Add tests |

## Git Workflow

| Command | Action |
| ------- | ------ |
| `/dk git init` | Initialize new project (full setup) |
| `/dk git update` | Sync files and GitHub settings |
| `/dk git pr` | Create pull request |
| `/dk git pr review [num]` | Check PR review comments |
| `/dk git pr merge [num]` | Merge PR (squash) |
| `/dk git branch <name>` | Create feature branch |
| `/dk git squash` | Squash commits |
| `/dk git cleanup` | Clean local tags + branches |
| `/dk git issue report` | Report bug in devkit-plugin |
| `/dk git issue create` | Create issue in current project |
| `/dk git issue list` | List open issues |
| `/dk git issue view [num]` | View issue details |

## Architecture

| Command | Action |
| ------- | ------ |
| `/dk arch` | Architecture overview |
| `/dk arch analyze` | Analyze dependencies and violations |
| `/dk arch check` | Check layer rule compliance |
| `/dk arch init [python\|ts]` | Scaffold Clean Architecture |
| `/dk arch layers` | Show layer documentation |

## Documentation

| Command | Action |
| ------- | ------ |
| `/dk docs` | Show CLAUDE.md status |
| `/dk docs update` | Update AUTO sections |
| `/dk docs init` | Create CLAUDE.md from template |

## Environment & Deployment

| Command | Action |
| ------- | ------ |
| `/dk env sync` | Sync .env to Vercel + GitHub |
| `/dk env pull` | Pull env vars from Vercel |
| `/dk env list` | List env vars |
| `/dk env clean` | Remove unused env vars |
| `/dk vercel connect` | Link project to Vercel |
| `/dk vercel env` | Manage Vercel env vars |
| `/dk neon branch list` | List NeonDB branches |
| `/dk neon branch create` | Create NeonDB branch |
| `/dk neon branch delete` | Delete NeonDB branch |
| `/dk neon branch switch` | Switch NeonDB branch |
| `/dk neon cleanup` | Clean stale branches |

## GitHub Actions

| Workflow | Trigger | Description |
| -------- | ------- | ----------- |
| release | push | Auto-release: changelog, version, tag, GitHub release |
| claude-code-review | pull_request | AI code review on PRs |
| claude | @claude mention | Claude assistant on issues/PRs |

## Commits & Changelog

**Conventional Commits** mit optionalem Scope: `type(scope): beschreibende message`

### Naming-Konventionen

| Element | Format | Beispiel |
| ------- | ------ | -------- |
| Branch | `type/bereich-kurz` | `fix/changelog-naming` |
| Commit | `type(scope): was wurde gemacht` | `fix(changelog): use commit message for PR title` |
| PR-Titel | = letzter Commit | automatisch |

**Wichtig**: Der Commit-Message-Titel wird für den Changelog verwendet!

### Scope → Changelog Formatierung

Commits mit Scope werden im Changelog fett formatiert:

| Commit | → Changelog |
| ------ | ----------- |
| `fix(review): switch to Opus agents` | `- **Review**: Switch to Opus agents` |
| `feat(git): add squash command` | `- **Git**: Add squash command` |
| `fix: login crash` | `- Login crash` |

### Internal Scopes (skip release notes)

| Scope | Use Case |
| ----- | -------- |
| `internal` | Interne Refactorings, Tooling |
| `review` | Code-Review Fixes |
| `ci` | CI/CD Workflow-Änderungen |
| `deps` | Dependency Updates |

**Examples:**
- `fix(review): linter warnings` → Skipped (internal)
- `feat(git): add squash` → `- **Git**: Add squash`
- `fix: login crash` → `- Login crash`

## Linters

- ruff (Python)
- markdownlint (Markdown)
- strict

## Tech Stack

- **Language**: Python 3.10+
- **Runtime**: Claude Code Hooks
- **Framework**: Custom Plugin System
- **Package Manager**: uv

## Prerequisites

Tools needed for full devkit-plugin functionality:

| Tool | Install | Purpose |
|------|---------|---------|
| **uv** | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | Python package manager (fast, modern) |
| **gh** | `brew install gh` | GitHub CLI for PRs, issues |
| **ruff** | `uv tool install ruff` | Python linter (fast, replaces flake8/black) |
| **Node.js** | `brew install node` | For ESLint, markdownlint |

**Optional (für spezifische Features):**

| Tool | Install | Purpose |
|------|---------|---------|
| vercel | `npm i -g vercel` | `/dk vercel` - Deployment |
| neonctl | `npm i -g neonctl` | `/dk neon` - Database branches |

**Quick Setup (macOS):**

```bash
# Core tools
curl -LsSf https://astral.sh/uv/install.sh | sh
brew install gh node
uv tool install ruff

# Auth
gh auth login
```

## Development

**IMPORTANT**: Always use `uv run` for Python commands, not `python3` directly.

```bash
# Correct
uv run pytest tests/
uv run python hooks/pr.py

# Wrong (uses system Python without dependencies)
python3 -m pytest tests/
python3 hooks/pr.py
```

## Documentation

- [Index](docs/INDEX.md) - File overview
- [Architecture](docs/ARCHITECTURE.md) - System design
- [Patterns](docs/PATTERNS.md) - Code patterns
- [Dependencies](docs/DEPENDENCIES.md) - Module graph

## Git

Protected branches: main

---
